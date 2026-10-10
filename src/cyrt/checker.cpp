#include "cyrt/builtins.hpp"
#include "cyrt/checker.hpp"
#include "cyrt/currylib/setfunctions.hpp"
#include "cyrt/fingerprint.hpp"
#include "cyrt/graph/infotable.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/icurry.hpp"
#include "cyrt/inspect.hpp"
#include "cyrt/state/rts.hpp"
#include "cyrt/unionfind.hpp"
#include <algorithm>
#include <cstring>
#include <sstream>
#include <type_traits>

// The C++ mirror of the checker of the Python backend.  See checker.hpp and
// backends/py/eval/checker.py, whose module documentation lists the events
// and the checks at each.  The code below follows that file section by
// section; a comment names a difference where there is one.
namespace cyrt
{
  namespace
  {
    struct OverBudget {};

    // ------------------------------------------------------------------------
    // Read-only views of the state.  The checker must not change the state,
    // so it reads the union-find without path compression, the fingerprints
    // without the growth of check_alloc, and the bindings without the
    // absorption of get_binding.
    // ------------------------------------------------------------------------

    inline ChoiceState fp_test(Fingerprint const & fp, xid_type id)
    {
      return id < fp.capacity() ? fp.test_no_check(id) : UNDETERMINED;
    }

    // The root of the group of ``i`` in C, without path compression.
    xid_type group_root(Configuration const * C, xid_type i)
    {
      auto const & data = C->strict_constraints->data;
      size_t hops = 0;
      while(i < data.size() && data[i].parent != i && ++hops < 1000000)
        i = data[i].parent;
      return i;
    }

    // The entries of a fingerprint, read from the blocks of its tree (see
    // Fingerprint::read_block for the layout of an id).
    void fp_entries_rec(
        fingerprints::Node const * p, int level, size_t base
      , std::vector<FpEntry> & out
      )
    {
      if(level < 0)
      {
        auto const & block = p->block;
        using bits_type = std::make_unsigned_t<decltype(block.used)>;
        bits_type used = (bits_type) block.used;
        bits_type const lr = (bits_type) block.lr;
        // Most blocks of a large tree are empty: one test each.
        while(used)
        {
          size_t const off = __builtin_ctzll((unsigned long long) used);
          out.emplace_back(base | off, ((lr >> off) & 1) ? RIGHT : LEFT);
          used &= used - 1;
        }
        return;
      }
      for(size_t k = 0; k < FP_BRANCH_SIZE; ++k)
        fp_entries_rec(
            &p->branch->next[k], level - 1
          , base | (k << (level * FP_BRANCH_SHIFT + FP_BLOCK_SHIFT)), out
          );
    }

    std::vector<FpEntry> fp_entries(Fingerprint const & fp)
    {
      std::vector<FpEntry> out;
      fp_entries_rec(&fp.root(), (int) fp.depth() - 1, 0, out);
      return out;
    }

    // The entries of ``a`` that ``b`` lacks or decides the other way (lost)
    // and the entries of ``b`` that ``a`` lacks (added).  A subtree the two
    // trees share (copy on write) is skipped, so the diff of a clone against
    // its parent costs the path of the written block alone.
    void fp_diff_rec(
        fingerprints::Node const * pa, fingerprints::Node const * pb, int level
      , size_t base, std::vector<xid_type> & lost, std::vector<xid_type> & added
      )
    {
      if(level < 0)
      {
        using bits_type = std::make_unsigned_t<decltype(pa->block.used)>;
        bits_type const ua = (bits_type) pa->block.used, la = (bits_type) pa->block.lr;
        bits_type const ub = (bits_type) pb->block.used, lb = (bits_type) pb->block.lr;
        bits_type lost_bits = (ua & ~ub) | (ua & ub & (la ^ lb));
        bits_type added_bits = ub & ~ua;
        while(lost_bits)
        {
          size_t const off = __builtin_ctzll((unsigned long long) lost_bits);
          lost.push_back(base | off);
          lost_bits &= lost_bits - 1;
        }
        while(added_bits)
        {
          size_t const off = __builtin_ctzll((unsigned long long) added_bits);
          added.push_back(base | off);
          added_bits &= added_bits - 1;
        }
        return;
      }
      if(pa->branch == pb->branch)
        return;
      for(size_t k = 0; k < FP_BRANCH_SIZE; ++k)
        fp_diff_rec(
            &pa->branch->next[k], &pb->branch->next[k], level - 1
          , base | (k << (level * FP_BRANCH_SHIFT + FP_BLOCK_SHIFT)), lost, added
          );
    }

    // False when the trees differ in depth (the clone grew its tree).
    bool fp_diff(
        Fingerprint const & a, Fingerprint const & b
      , std::vector<xid_type> & lost, std::vector<xid_type> & added
      )
    {
      if(a.depth() != b.depth())
        return false;
      fp_diff_rec(&a.root(), &b.root(), (int) a.depth() - 1, 0, lost, added);
      return true;
    }

    char const * side_name(ChoiceState lr)
    {
      switch(lr)
      {
        case LEFT:  return "LEFT";
        case RIGHT: return "RIGHT";
        default:    return "UNDETERMINED";
      }
    }

    // Passes through forward nodes and set guards.
    inline Node * deref(Node * node)
    {
      size_t hops = 0;
      while(node && ++hops < 100000)
      {
        tag_type const tag = node->info->tag;
        if(tag == T_FWD)
          node = NodeU{node}.fwd->target;
        else if(tag == T_SETGRD)
          node = NodeU{node}.setgrd->value;
        else
          break;
      }
      return node;
    }

    // Passes through forward nodes alone.
    inline Node * deref_fwd(Node * node)
    {
      size_t hops = 0;
      while(node && node->info->tag == T_FWD && ++hops < 100000)
        node = NodeU{node}.fwd->target;
      return node;
    }

    inline bool is_pointer_slot(Node * node, size_t i)
    {
      return node && i < node->info->arity && node->info->format[i] == 'p';
    }

    // The node at ``path`` from ``root``: plain indexing.
    Node * at(Node * root, PathList const & path)
    {
      Node * node = root;
      for(index_type i: path)
      {
        if(!is_pointer_slot(node, i))
          return nullptr;
        node = node->successors()[i].node;
      }
      return node;
    }

    // The node at the logical ``path`` from ``node``: through forward nodes
    // and guards.
    Node * logical(Node * node, index_type const * path, size_t n)
    {
      for(size_t k = 0; k < n; ++k)
      {
        node = deref(node);
        if(!is_pointer_slot(node, path[k]))
          return nullptr;
        node = node->successors()[path[k]].node;
      }
      return deref(node);
    }

    // The node at the logical ``path`` from a redex given by its successors.
    Node * logical_from_args(
        std::vector<Node *> const & args, PathList const & path
      )
    {
      if(path.empty() || path[0] >= args.size())
        return nullptr;
      return logical(args[path[0]], path.data() + 1, path.size() - 1);
    }

    std::vector<Node *> successor_nodes(Node * node)
    {
      std::vector<Node *> args;
      if(!node)
        return args;
      InfoTable const * info = node->info;
      Arg const * data = node->successors();
      for(index_type i = 0; i < info->arity; ++i)
        args.push_back(info->format[i] == 'p' ? data[i].node : nullptr);
      return args;
    }

    // The logical path of a real path from ``root``: the steps through
    // forward nodes and set guards removed.  False when the path leaves the
    // graph.
    bool logical_path(Node * root, RealPath const & realpath, PathList & path)
    {
      Node * node = root;
      for(index_type i: realpath)
      {
        if(!node)
          return false;
        tag_type const tag = node->info->tag;
        if(tag != T_FWD && tag != T_SETGRD)
          path.push_back(i);
        if(!is_pointer_slot(node, i))
          return false;
        node = node->successors()[i].node;
      }
      return true;
    }

    // The branch key of a constructor cell: its tag, or its literal value.
    bool cell_key(Node * cell, bool literal, uint64_t & key)
    {
      if(!cell || cell->info->tag < T_CTOR)
        return false;
      if(!literal)
      {
        key = (uint64_t) cell->info->tag;
        return true;
      }
      switch(typetag(*cell->info))
      {
        case F_INT_TYPE:
          key = (uint64_t) NodeU{cell}.int_->value;
          return true;
        case F_CHAR_TYPE:
          key = (uint64_t) NodeU{cell}.char_->value;
          return true;
        case F_FLOAT_TYPE:
        {
          double const value = NodeU{cell}.float_->value;
          std::memcpy(&key, &value, sizeof(key));
          return true;
        }
        default:
          return false;
      }
    }

    // Small set operations on a SetList.
    inline bool contains(SetList const & v, Set * s)
    {
      return std::find(v.begin(), v.end(), s) != v.end();
    }
    inline void add(SetList & v, Set * s)
    {
      if(s && !contains(v, s))
        v.push_back(s);
    }
    inline void add_all(SetList & v, SetList const & w)
    {
      for(Set * s: w)
        add(v, s);
    }
    inline bool subset(SetList const & a, SetList const & b)
    {
      for(Set * s: a)
        if(!contains(b, s))
          return false;
      return true;
    }
    inline bool intersects(SetList const & a, SetList const & b)
    {
      for(Set * s: a)
        if(contains(b, s))
          return true;
      return false;
    }

    template<typename T>
    std::string list_text(std::vector<T> const & items)
    {
      std::ostringstream os;
      os << '[';
      for(size_t i = 0; i < items.size(); ++i)
        os << (i ? ", " : "") << items[i];
      os << ']';
      return os.str();
    }

    std::string ids_text(std::vector<xid_type> ids)
    {
      std::sort(ids.begin(), ids.end());
      return list_text(ids);
    }

    std::string path_text(PathList const & path)
    {
      std::vector<size_t> items(path.begin(), path.end());
      return list_text(items);
    }

    std::string set_ids_text(std::unordered_set<xid_type> const & ids)
    {
      return ids_text(std::vector<xid_type>(ids.begin(), ids.end()));
    }

    // 64-bit mixing for the signatures of the reducts.
    inline uint64_t mix64(uint64_t x)
    {
      x ^= x >> 30;
      x *= 0xbf58476d1ce4e5b9ULL;
      x ^= x >> 27;
      x *= 0x94d049bb133111ebULL;
      x ^= x >> 31;
      return x;
    }
    inline uint64_t combine(uint64_t h, uint64_t v)
    {
      return mix64(h ^ (mix64(v) + 0x9e3779b97f4a7c15ULL + (h << 6) + (h >> 2)));
    }
    inline uint64_t label(char kind, uint64_t v)
    {
      return combine((uint64_t) (unsigned char) kind, v);
    }

    // ------------------------------------------------------------------------
    // The definitional tree of an interpreted operation, from its bytecode.
    // The bytecode spells the ICurry body statement by statement
    // (backends/cxx/bytecode.py), so the case structure is read back from
    // it: BIND_ROOT and BIND_VAR give a variable its position, COPY_VAR an
    // alias, STORE_VAR a value that is not a position, and a CASE opcode
    // names the variable it scrutinizes and the positions of its branches.
    // Every block ends with a return, an exempt, or a case.
    // ------------------------------------------------------------------------

    struct PathEnv
    {
      std::vector<bool> known;
      std::vector<PathList> paths;
      explicit PathEnv(size_t nvars) : known(nvars, false), paths(nvars) {}
    };

    std::unique_ptr<CheckerTree> build_tree(
        Bytecode const & bc, uint32_t pc, PathEnv env, size_t depth
      )
    {
      auto tree = std::make_unique<CheckerTree>();
      if(depth > 64)
        return tree;
      uint32_t const * const code = bc.code.data();
      size_t const n = bc.code.size();
      auto var_ok = [&](uint32_t v) { return v < env.known.size(); };
      while(pc < n)
      {
        uint32_t const * op = code + pc;
        switch((Opcode) op[0])
        {
          case OP_LOAD_ROOT_SUCC: pc += 3; break;
          case OP_LOAD_VAR_SUCC:  pc += 4; break;
          case OP_BIND_ROOT:
          {
            uint32_t const v = op[1], count = op[2];
            if(var_ok(v))
            {
              env.known[v] = true;
              env.paths[v].assign(op + 3, op + 3 + count);
            }
            pc += 3 + count;
            break;
          }
          case OP_BIND_VAR:
          {
            uint32_t const v = op[1], w = op[2], count = op[3];
            if(var_ok(v))
            {
              if(var_ok(w) && env.known[w])
              {
                env.known[v] = true;
                env.paths[v] = env.paths[w];
                env.paths[v].insert(env.paths[v].end(), op + 4, op + 4 + count);
              }
              else
                env.known[v] = false;
            }
            pc += 4 + count;
            break;
          }
          case OP_COPY_REG: pc += 3; break;
          case OP_COPY_VAR:
          {
            uint32_t const v = op[1], w = op[2];
            if(var_ok(v))
            {
              env.known[v] = var_ok(w) && env.known[w];
              if(env.known[v])
                env.paths[v] = env.paths[w];
            }
            pc += 3;
            break;
          }
          case OP_FREE_REG:     pc += 2; break;
          case OP_PUSH_REG:     pc += 2; break;
          case OP_PUSH_VAR:     pc += 2; break;
          case OP_PUSH_ROOT:    pc += 1; break;
          case OP_PUSH_CONST:   pc += 2; break;
          case OP_PUSH_SUCC:    pc += 3; break;
          case OP_PUSH_PATH:    pc += 3 + op[2]; break;
          case OP_MAKE:         pc += 3; break;
          case OP_MAKE_PARTIAL: pc += 3; break;
          case OP_MAKE_STRING:  pc += 2; break;
          case OP_STORE_REG:    pc += 2; break;
          case OP_STORE_VAR:
            if(var_ok(op[1]))
              env.known[op[1]] = false;
            pc += 2;
            break;
          case OP_SET_SUCC:     pc += 3 + op[2]; break;
          case OP_EXEMPT:
            tree->kind = CheckerTree::EXEMPT;
            return tree;
          case OP_RET_REF:
            tree->kind = CheckerTree::RETURN_REF;
            return tree;
          case OP_RET_NODE:
          case OP_RET_STRING:
            tree->kind = CheckerTree::RETURN_NODE;
            return tree;
          case OP_CASE_CONS:
          {
            uint32_t const v = op[1], ntab = op[3];
            tree->kind = CheckerTree::CASE;
            tree->literal = false;
            if(var_ok(v) && env.known[v])
            {
              tree->position_known = true;
              tree->path = env.paths[v];
            }
            for(uint32_t tag = 0; tag < ntab; ++tag)
            {
              uint32_t const target = op[4 + tag];
              if(target != NO_BRANCH && target < n)
                tree->branches[tag] = build_tree(bc, target, env, depth + 1);
            }
            return tree;
          }
          case OP_CASE_LIT:
          {
            uint32_t const v = op[1], count = op[4];
            tree->kind = CheckerTree::CASE;
            tree->literal = true;
            tree->litkind = (char) op[3];
            if(var_ok(v) && env.known[v])
            {
              tree->position_known = true;
              tree->path = env.paths[v];
            }
            uint32_t const * entry = op + 5;
            for(uint32_t i = 0; i < count; ++i, entry += 3)
            {
              uint64_t const value = uint64_t(entry[0]) | (uint64_t(entry[1]) << 32);
              if(entry[2] < n)
                tree->branches[value] = build_tree(bc, entry[2], env, depth + 1);
            }
            return tree;
          }
          default:
            return tree;
        }
      }
      return tree;
    }

    char const * leaf_name(CheckerTree const * node)
    {
      switch(node->kind)
      {
        case CheckerTree::CASE:        return "case";
        case CheckerTree::EXEMPT:      return "exempt";
        case CheckerTree::RETURN_REF:  return "return (reference)";
        case CheckerTree::RETURN_NODE: return "return";
        default:                       return "unknown";
      }
    }

    std::string matched_text(std::vector<std::string> const & matched)
    {
      return "matched: " + list_text(matched);
    }
  }

  // --------------------------------------------------------------------------
  // The violation.
  // --------------------------------------------------------------------------

  InvariantViolation::InvariantViolation(
      std::string invariant_, std::string event_, std::string detail_
    , std::string const & message
    )
    : std::logic_error(message)
    , invariant(std::move(invariant_)), event(std::move(event_))
    , detail(std::move(detail_))
  {}

  // --------------------------------------------------------------------------
  // The checker.
  // --------------------------------------------------------------------------

  struct Checker::SigState
  {
    size_t budget;
    std::unordered_map<Node *, uint64_t> memo;
    std::unordered_set<Node *> onstack;
    bool reached = false;
    Node * watch;
    // The queues of the capsules the walk meets (the SetEval nodes), when
    // the caller collects them.
    std::vector<Queue *> * queues = nullptr;
    std::unordered_set<Queue *> * seen_queues = nullptr;
    SigState(size_t budget, Node * watch = nullptr)
      : budget(budget), watch(watch)
    {}
  };

  Checker::Checker(RuntimeState & rts) : rts(rts) {}

  Checker::~Checker()
  {
    for(Node * node: this->rooted)
      gc_remove_root(node);
  }

  Configuration * Checker::current()
  {
    if(this->rts.qstack.empty() || this->rts.qstack.back()->empty())
      return nullptr;
    return this->rts.qstack.back()->front();
  }

  void Checker::root_node(Node * node)
  {
    if(node && this->rooted.insert(node).second)
      gc_add_root(node);
  }

  std::string Checker::set_name(Set * set)
  {
    if(!set)
      return "none";
    auto p = this->set_serials.find(set);
    if(p == this->set_serials.end())
      p = this->set_serials.emplace(set, this->set_serials.size() + 1).first;
    return "#" + std::to_string(p->second);
  }

  std::string Checker::set_names(SetList const & sets)
  {
    std::vector<std::string> names;
    for(Set * s: sets)
      names.push_back(this->set_name(s));
    std::sort(names.begin(), names.end());
    return list_text(names);
  }

  // A bounded description of an expression.
  std::string Checker::text(Node * root, size_t limit)
  {
    std::ostringstream os;
    size_t count = 0;
    std::vector<std::pair<Node *, size_t>> todo;
    // A recursive printer with an explicit depth; the limit bounds the work.
    struct Printer
    {
      Checker * self;
      std::ostringstream & os;
      size_t & count;
      size_t limit;
      void go(Node * n, size_t depth)
      {
        if(++count > limit || depth > 40)
        {
          os << "...";
          return;
        }
        if(!n)
        {
          os << "null";
          return;
        }
        InfoTable const * info = n->info;
        switch(info->tag)
        {
          case T_FWD:
            go(NodeU{n}.fwd->target, depth + 1);
            return;
          case T_CHOICE:
            os << "(?" << NodeU{n}.choice->cid << ' ';
            go(NodeU{n}.choice->lhs, depth + 1);
            os << ' ';
            go(NodeU{n}.choice->rhs, depth + 1);
            os << ')';
            return;
          case T_FREE:
            os << "_x" << NodeU{n}.free->vid;
            return;
          case T_SETGRD:
            os << "{box " << self->set_name(NodeU{n}.setgrd->set) << '|';
            go(NodeU{n}.setgrd->value, depth + 1);
            os << '}';
            return;
          default:
            break;
        }
        if(info->arity == 0)
        {
          os << info->name;
          return;
        }
        Arg const * data = n->successors();
        if(is_primitive(*info))
        {
          switch(info->format[0])
          {
            case 'i': os << data[0].ub_int; return;
            case 'f': os << data[0].ub_float; return;
            case 'c': os << "'" << (unsigned long) data[0].ub_char << "'"; return;
            default: break;
          }
        }
        os << '(' << info->name;
        for(index_type i = 0; i < info->arity; ++i)
        {
          os << ' ';
          switch(info->format[i])
          {
            case 'p': go(data[i].node, depth + 1); break;
            case 'i': os << data[i].ub_int; break;
            case 'f': os << data[i].ub_float; break;
            case 'c': os << "'" << (unsigned long) data[i].ub_char << "'"; break;
            default:  os << "<x>"; break;
          }
        }
        os << ')';
      }
    };
    Printer printer{this, os, count, limit};
    printer.go(root, 0);
    return os.str();
  }

  std::vector<FpEntry> Checker::entries(Configuration const * cfg) const
  {
    return fp_entries(cfg->fingerprint);
  }

  std::vector<std::string> Checker::describe(Configuration * cfg)
  {
    std::vector<std::string> lines;
    if(!cfg)
      return lines;
    Queue * where = nullptr;
    size_t index = 0;
    auto locate = [&](Queue * Q)
    {
      size_t k = 0;
      for(Configuration * C: *Q)
      {
        if(C == cfg)
        {
          where = Q;
          index = k;
          return true;
        }
        ++k;
      }
      return false;
    };
    for(Queue * Q: this->rts.qstack)
      if(locate(Q))
        break;
    if(!where)
      for(Queue * Q: this->describe_queues)
        if(locate(Q))
          break;
    {
      std::ostringstream os;
      os << "configuration: queue ";
      if(where)
        os << '#' << where->serial << " (set " << this->set_name(where->set)
           << "), index " << index;
      else
        os << "? (not in a queue), index ?";
      os << ", escape_all=" << (cfg->escape_all ? 1 : 0);
      lines.push_back(os.str());
    }
    {
      std::ostringstream os;
      os << "fingerprint: {";
      bool first = true;
      for(auto const & entry: fp_entries(cfg->fingerprint))
      {
        os << (first ? "" : ", ") << entry.first << ':'
           << (entry.second == LEFT ? 'L' : 'R');
        first = false;
      }
      os << '}';
      lines.push_back(os.str());
    }
    {
      std::ostringstream os;
      os << "groups (member, root): [";
      bool first = true;
      auto const & data = cfg->strict_constraints->data;
      for(size_t i = 0; i < data.size(); ++i)
        if(data[i].parent != i)
        {
          os << (first ? "" : ", ") << '(' << i << ", " << group_root(cfg, i) << ')';
          first = false;
        }
      os << ']';
      lines.push_back(os.str());
    }
    {
      std::vector<size_t> position;
      auto const & frames = cfg->scan.frames();
      for(size_t i = 0; i + 1 < frames.size(); ++i)
        position.push_back(frames[i].index);
      lines.push_back("goal position: " + list_text(position));
    }
    lines.push_back("root: " + this->text(cfg->root.arg ? *cfg->root : nullptr));
    return lines;
  }

  void Checker::violation(
      char const * invariant, char const * event, std::string const & detail
    , Configuration * cfg, std::vector<xid_type> ids
    , std::vector<std::string> extra
    )
  {
    std::ostringstream os;
    os << "Fair Scheme invariant " << invariant << " violated at " << event
       << ": " << detail;
    if(!ids.empty())
      os << "\n  identifiers: " << ids_text(ids);
    for(auto const & line: this->describe(cfg))
      os << "\n  " << line;
    for(auto const & line: extra)
      os << "\n  " << line;
    ++this->counts["violations"];
    throw InvariantViolation(invariant, event, detail, os.str());
  }

  // --------------------------------------------------------------------------
  // Read-only views.
  // --------------------------------------------------------------------------

  // The decision of identifier ``i`` for ``cfg``, read through its group
  // and the dispatch chain, as read_fp reads it.
  ChoiceState Checker::decision(xid_type i, Configuration * cfg)
  {
    xid_type const r = group_root(cfg, i);
    ChoiceState d = fp_test(cfg->fingerprint, r);
    if(d != UNDETERMINED)
      return d;
    auto const & qstack = this->rts.qstack;
    if(qstack.empty())
      return UNDETERMINED;
    for(auto p = qstack.rbegin() + 1, e = qstack.rend(); p != e; ++p)
    {
      if((*p)->empty())
        continue;
      d = fp_test((*p)->front()->fingerprint, r);
      if(d != UNDETERMINED)
        return d;
    }
    return UNDETERMINED;
  }

  // The binding of variable ``vid`` for ``cfg``, or null: the walk of
  // get_binding without its absorption.
  Node * Checker::binding(Configuration * cfg, xid_type vid)
  {
    xid_type const gid = group_root(cfg, vid);
    auto p = cfg->bindings->find(gid);
    if(p != cfg->bindings->end())
      return p->second;
    size_t k = 0;
    auto const & qstack = this->rts.qstack;
    for(auto q = qstack.rbegin(), e = qstack.rend(); q != e; ++q, ++k)
    {
      Queue * Q = *q;
      xid_type key = gid;
      Node * node = nullptr;
      if(k)
      {
        if(Q->empty())
          continue;
        Configuration * outer = Q->front();
        key = group_root(outer, gid);
        auto r = outer->bindings->find(key);
        if(r != outer->bindings->end())
          node = r->second;
      }
      if(!node)
      {
        auto a = Q->absorbed.find(key);
        if(a != Q->absorbed.end())
          node = a->second;
      }
      if(node)
        return node;
    }
    return nullptr;
  }

  // The sets of the boxes above the current site: the guards crossed on the
  // path from the root of each configuration of the dispatch chain to its
  // cursor (the levels of its scan, the pushed inductive paths included),
  // and the set of a configuration whose root was under the guard of its
  // own set (escape_all).
  SetList Checker::boxes_above()
  {
    SetList boxes;
    for(Queue * Q: this->rts.qstack)
    {
      if(Q->empty())
        continue;
      Configuration * C = Q->front();
      if(C->escape_all && Q->set)
        add(boxes, Q->set);
      for(auto const & level: C->scan.frames())
      {
        Cursor const & cur = level.cur;
        if(cur.kind == 'p' && cur.arg && *cur && (*cur)->info->tag == T_SETGRD)
          add(boxes, NodeU{*cur}.setgrd->set);
      }
    }
    return boxes;
  }

  SetList const & Checker::flags_of(Node * node)
  {
    static SetList const empty;
    auto p = this->flags.find(node);
    return p == this->flags.end() ? empty : p->second;
  }

  SetList const & Checker::tags_of(xid_type id)
  {
    static SetList const empty;
    auto p = this->tags.find(id);
    return p == this->tags.end() ? empty : p->second;
  }

  // The configurations of the dispatch chain, innermost first: the fronts
  // of the queues of the stack, the current queue included or not.
  std::vector<Configuration *> Checker::chain(bool include_current)
  {
    std::vector<Configuration *> out;
    auto const & qstack = this->rts.qstack;
    if(qstack.empty())
      return out;
    auto p = qstack.rbegin();
    if(!include_current)
      ++p;
    for(auto e = qstack.rend(); p != e; ++p)
      if(!(*p)->empty())
        out.push_back((*p)->front());
    return out;
  }

  void Checker::tag(xid_type id, Set * set)
  {
    add(this->tags[id], set);
  }

  // Records an insertion into the escape set of ``set`` as seen, for the
  // tests.
  void Checker::note_escape(Set * set, xid_type cid)
  {
    this->escape_sets[set].insert(cid);
  }

  // --------------------------------------------------------------------------
  // B1: fingerprints.
  // --------------------------------------------------------------------------

  // The fingerprint of ``cfg`` is a function, its group invariant holds, and
  // it agrees with the fingerprints of ``chain`` (the enclosing
  // configurations).  A used bit of a block is LEFT or RIGHT, so the
  // undetermined entry of the Python check cannot occur here.
  void Checker::check_fingerprint(
      Configuration * cfg, char const * event
    , std::vector<Configuration *> const & chain
    )
  {
    // The group invariant can fail at a member of a group alone, and every
    // member of a group of two or more is among the ids united, so those
    // are read instead of every entry of the fingerprint: the cost of a
    // fork stays flat along a long chain of narrowings.
    for(xid_type i: cfg->strict_constraints->united)
    {
      ChoiceState const d = fp_test(cfg->fingerprint, i);
      if(d == UNDETERMINED)
        continue;
      xid_type const r = group_root(cfg, i);
      ChoiceState const dr = fp_test(cfg->fingerprint, r);
      if(dr != d)
        this->violation(
            "B1 (group)", event
          , "identifier " + std::to_string(i) + " is decided " + side_name(d)
            + ", the root " + std::to_string(r) + " of its group is "
            + side_name(dr)
          , cfg, {i, r}
          );
    }
    if(chain.empty())
      return;
    auto const entries = fp_entries(cfg->fingerprint);
    for(Configuration * outer: chain)
      for(auto const & entry: entries)
      {
        xid_type const i = entry.first;
        ChoiceState const d = entry.second;
        xid_type const r = group_root(outer, i);
        for(xid_type j: {i, r})
        {
          ChoiceState const dj = fp_test(outer->fingerprint, j);
          if(dj != UNDETERMINED && dj != d)
          {
            std::vector<std::string> extra;
            for(auto const & line: this->describe(outer))
              extra.push_back("enclosing " + line);
            this->violation(
                "B1 (dispatch chain)", event
              , "identifier " + std::to_string(i) + " is decided " + side_name(d)
                + " here and " + side_name(dj) + " (as " + std::to_string(j)
                + ") in an enclosing configuration"
              , cfg, {i, j}, extra
              );
          }
        }
      }
  }

  // Every escape set holds what the hooks saw, and nothing less.
  void Checker::check_escape_sets(char const * event, Configuration * cfg)
  {
    for(auto const & entry: this->escape_sets)
    {
      Set * set = entry.first;
      auto const & shadow = entry.second;
      auto const & actual = set->escape_set;
      std::vector<xid_type> lost, gained;
      for(xid_type cid: shadow)
        if(!actual.count(cid))
          lost.push_back(cid);
      if(!lost.empty())
        this->violation(
            "S0 (escape sets grow)", event
          , "the escape set of set " + this->set_name(set) + " lost "
            + ids_text(lost)
          , cfg, lost
          );
      for(xid_type cid: actual)
        if(!shadow.count(cid))
          gained.push_back(cid);
      if(!gained.empty())
        this->violation(
            "S0 (escape sets grow)", event
          , "the escape set of set " + this->set_name(set) + " gained "
            + ids_text(gained) + " outside the rule"
          , cfg, gained
          );
    }
  }

  // ``copy`` is a fresh copy of the spine from ``root`` along ``path`` with
  // ``end`` at its end: fresh cells of the same symbols along the path, the
  // cells off the path shared.
  void Checker::check_spine_copy(
      Node * root, PathList const & path, Node * copy, Node * end
    , char const * invariant, char const * event, char const * side
    , Configuration * cfg
    )
  {
    std::string const prefix = std::string("the ") + side + (*side ? " copy" : "copy");
    Node * orig = root;
    Node * cp = copy;
    for(size_t k = 0; k < path.size(); ++k)
    {
      index_type const i = path[k];
      if(cp == orig)
        this->violation(
            invariant, event
          , prefix + " shares the cell at depth " + std::to_string(k)
            + " of the spine"
          , cfg
          );
      if(!cp || !orig || cp->info != orig->info)
        this->violation(
            invariant, event
          , prefix + " has " + this->text(cp) + " at depth " + std::to_string(k)
            + " where the spine has " + this->text(orig)
          , cfg
          );
      if(!is_pointer_slot(orig, i))
        this->violation(
            invariant, event
          , prefix + ": the path leaves the spine at depth " + std::to_string(k)
          , cfg
          );
      Arg const * so = orig->successors();
      Arg const * sc = cp->successors();
      for(index_type j = 0; j < orig->info->arity; ++j)
        if(j != i && sc[j].blob != so[j].blob)
          this->violation(
              invariant, event
            , prefix + " does not share the cell off the path at depth "
              + std::to_string(k) + ", index " + std::to_string(j)
            , cfg
            );
      orig = so[i].node;
      cp = sc[i].node;
    }
    if(end && cp != end)
      this->violation(
          invariant, event
        , "the end of " + prefix + " is " + this->text(cp)
          + ", not the replacement " + this->text(end)
        , cfg
        );
  }

  // --------------------------------------------------------------------------
  // The events.
  // --------------------------------------------------------------------------

  void Checker::fork(
      Queue * Q, Configuration * C, Configuration * const * clones, size_t n
    )
  {
    ++this->counts["forks"];
    Node * root = C->root.arg ? *C->root : nullptr;
    if(!root || root->info->tag != T_CHOICE)
      this->violation("B1", "fork", "the root of the configuration is not a choice", C);
    xid_type const cid = NodeU{root}.choice->cid;
    auto const enclosing = this->chain(false);
    this->check_fingerprint(C, "fork", enclosing);
    std::vector<ChoiceState> sides;
    for(size_t k = 0; k < n; ++k)
    {
      Configuration * clone = clones[k];
      this->check_fingerprint(clone, "fork", enclosing);
      this->check_clone(clone, cid, C);
      // The decision is recorded in the clone, or an enclosing
      // configuration made it before (update_fp writes nothing then, and
      // one side alone survives).
      ChoiceState const d = this->decision(cid, clone);
      if(d == UNDETERMINED)
        this->violation(
            "B1", "fork"
          , "the clone does not record the decision of " + std::to_string(cid)
          , clone, {cid}
          );
      sides.push_back(d);
    }
    if(n > 2 || (n == 2 && sides[0] == sides[1]))
    {
      std::vector<std::string> names;
      for(ChoiceState d: sides)
        names.push_back(side_name(d));
      this->violation(
          "B1", "fork"
        , "the clones decide " + std::to_string(cid) + " as " + list_text(names)
        , C, {cid}
        );
    }
    if(this->rts.in_recursive_call() && !Q->decided(cid))
    {
      // def:s-escapes: the choice escapes when it is argument-derived for
      // the capsule or for an enclosing one, or when an enclosing
      // configuration decided it.  A fork on such an identifier is allowed
      // after the split alone (cid in the decisions of the queue).
      Set * set = Q->set;
      SetList const & t = this->tags_of(cid);
      if(set && contains(t, set) && !this->unbounded_sets.count(set))
        this->violation(
            "S0", "fork"
          , "identifier " + std::to_string(cid) + " is argument-derived for set "
            + this->set_name(set) + " (tags " + this->set_names(t)
            + ") and forks inside the capsule; it is not in the escape set "
            + set_ids_text(set->escape_set) + " and the queue was not split on it"
          , C, {cid}
          );
      // The enclosing capsules: the escape sets themselves (the tags of an
      // enclosing set over-approximate them).
      SetList escaped;
      for(Queue * q: this->rts.qstack)
      {
        Set * s = q->set;
        if(!s || s == set)
          continue;
        auto e = this->escape_sets.find(s);
        if(e != this->escape_sets.end() && e->second.count(cid))
          add(escaped, s);
      }
      if(!escaped.empty())
        this->violation(
            "S0", "fork"
          , "identifier " + std::to_string(cid)
            + " is in the escape sets of the enclosing sets "
            + this->set_names(escaped) + " and forks inside the capsule of set "
            + this->set_name(set) + "; the queue was not split on it"
          , C, {cid}
          );
      xid_type const gid = group_root(C, cid);
      for(Configuration * outer: enclosing)
        if(fp_test(outer->fingerprint, gid) != UNDETERMINED
            || fp_test(outer->fingerprint, cid) != UNDETERMINED)
        {
          std::vector<std::string> extra;
          for(auto const & line: this->describe(outer))
            extra.push_back("enclosing " + line);
          this->violation(
              "S0", "fork"
            , "identifier " + std::to_string(cid)
              + " was decided by an enclosing configuration and forks inside "
                "the capsule of set " + this->set_name(set)
              + "; the queue was not split on it"
            , C, {cid, gid}, extra
            );
        }
    }
    this->check_escape_sets("fork", C);
  }

  // Rule D.2: the clone keeps every decision of its parent (``parent`` lists
  // the entries of the parent's fingerprint), and adds at most the forked
  // identifier ``cid`` and the root of its group.
  void Checker::check_clone(
      Configuration * clone, xid_type cid, Configuration * parent
    )
  {
    // The clone's fingerprint is a copy of its parent's with one or two
    // bits written, so the two trees share every other block: the diff
    // reads the written path alone.  The trees differ in depth when the
    // clone grew its tree; every entry is read then.
    std::vector<xid_type> lost, added;
    if(!fp_diff(parent->fingerprint, clone->fingerprint, lost, added))
    {
      std::unordered_set<xid_type> known;
      for(auto const & entry: fp_entries(parent->fingerprint))
      {
        known.insert(entry.first);
        if(fp_test(clone->fingerprint, entry.first) != entry.second)
          lost.push_back(entry.first);
      }
      for(auto const & entry: fp_entries(clone->fingerprint))
        if(!known.count(entry.first))
          added.push_back(entry.first);
    }
    for(xid_type i: lost)
    {
      ChoiceState const d = fp_test(parent->fingerprint, i);
      ChoiceState di = fp_test(clone->fingerprint, i);
      if(di == UNDETERMINED)
        di = fp_test(clone->fingerprint, group_root(clone, i));
      if(di != d)
        this->violation(
            "B1 (fork)", "fork"
          , "the clone lost the decision " + std::string(side_name(d))
            + " of identifier " + std::to_string(i) + " of its parent (it reads "
            + side_name(di) + ")"
          , clone, {i, cid}
          );
    }
    // A fork on a free variable applies its bindings and equates its group,
    // so the clone may add more entries.
    if(this->rts.get_freevar(cid))
      return;
    xid_type const gid = group_root(clone, cid);
    std::vector<xid_type> extra;
    for(xid_type i: added)
      if(i != cid && i != gid)
        extra.push_back(i);
    if(!extra.empty())
      this->violation(
          "B1 (fork)", "fork"
        , "the clone adds the identifiers " + ids_text(extra)
          + " beside the forked identifier " + std::to_string(cid)
          + " and its root " + std::to_string(gid)
        , clone, extra
        );
  }

  void Checker::escape(
      Queue * Q, xid_type cid, std::vector<Configuration *> const & before
    , Queue * R
    )
  {
    ++this->counts["escapes"];
    struct Named
    {
      Checker * self;
      ~Named() { self->describe_queues.clear(); }
    } named{this};
    this->describe_queues = {Q, R};
    Set * set = Q->set;
    auto const full_chain = this->chain(true);
    for(Configuration * cfg: before)
      this->check_fingerprint(cfg, "escape", full_chain);
    std::unordered_set<Configuration *> kept(Q->begin(), Q->end());
    std::unordered_set<Configuration *> moved(R->begin(), R->end());
    std::unordered_set<Configuration *> known(before.begin(), before.end());
    for(Configuration * cfg: before)
    {
      ChoiceState const d = fp_test(cfg->fingerprint, group_root(cfg, cid));
      bool const expect_kept = d != RIGHT;
      bool const expect_moved = d != LEFT;
      bool const is_kept = kept.count(cfg) != 0;
      bool const is_moved = moved.count(cfg) != 0;
      if(is_kept != expect_kept || is_moved != expect_moved)
        this->violation(
            "S-split", "escape"
          , "a configuration that decided " + std::to_string(cid) + " as "
            + side_name(d) + " is kept=" + (is_kept ? "1" : "0") + ", moved="
            + (is_moved ? "1" : "0")
          , cfg, {cid}
          );
    }
    for(auto const & pair: {std::make_pair(Q, "kept"), std::make_pair(R, "new")})
      for(Configuration * cfg: *pair.first)
        if(!known.count(cfg))
          this->violation(
              "S-split", "escape"
            , std::string("the ") + pair.second
              + " queue holds a configuration that was not in the queue"
            , cfg, {cid}
            );
    if(!Q->decided(cid) || !R->decided(cid))
      this->violation(
          "S-split", "escape"
        , "the queues do not both record " + std::to_string(cid) + " (kept "
          + ids_text(Q->decisions) + ", new " + ids_text(R->decisions) + ")"
        , nullptr, {cid}
        );
    if(R->set != set)
      this->violation(
          "S-split", "escape"
        , "the new queue names set " + this->set_name(R->set)
          + ", the kept queue set " + this->set_name(set)
        , nullptr, {cid}
        );
    if(!this->unbounded_sets.count(set))
    {
      SetList chain_sets;
      for(Queue * q: this->rts.qstack)
        add(chain_sets, q->set);
      add(chain_sets, set);
      SetList const & t = this->tags_of(cid);
      if(!intersects(t, chain_sets))
      {
        bool decided = false;
        for(Configuration * cfg: full_chain)
          if(fp_test(cfg->fingerprint, group_root(cfg, cid)) != UNDETERMINED)
            decided = true;
        if(!decided)
          this->violation(
              "S0", "escape"
            , "identifier " + std::to_string(cid) + " escapes set "
              + this->set_name(set) + " but is function-derived: its tags are "
              + this->set_names(t) + ", the capsules of the chain are "
              + this->set_names(chain_sets)
              + ", and no enclosing configuration decided it"
            , full_chain.empty() ? nullptr : full_chain[0], {cid}
            );
      }
    }
    this->check_escape_sets("escape", nullptr);
  }

  // The real path of a pull-tab or a copy, from the scan of C: the indices
  // of the levels from the one whose slot holds ``source`` down to the one
  // above the deepest level, which is the target.  copy_spine copies those
  // levels.  Without a level that holds the source every level is taken, as
  // copy_spine does.
  bool Checker::scan_path(Configuration * C, Node * source, PathList & path)
  {
    auto const & frames = C->scan.frames();
    size_t const n = frames.size();
    if(n < 2)
      return false;
    size_t k = 0;
    for(size_t i = n - 1; i-- > 0;)
    {
      Cursor const & cur = frames[i].cur;
      if(cur.kind == 'p' && cur.arg && *cur == source)
      {
        k = i;
        break;
      }
    }
    for(size_t i = k; i + 1 < n; ++i)
      path.push_back(frames[i].index);
    return true;
  }

  void Checker::pulltab_begin(Configuration * C, Node * source, Node * target)
  {
    PathList path;
    this->scan_path(C, source, path);
    this->pulltab_begin_at(C, source, target, path);
  }

  // Before the copies are made: the source is at the recorded path, and the
  // identifier enters the escape set of every box the path crosses (S0, E
  // in A: the insertion is of an argument-derived identifier).  The runtime
  // inserts at the pull-tab (update_escape_sets, copy_spine), so the
  // insertion the Python checker sees at update_escape_set is seen here,
  // at the first crossing, and recorded in the shadow of the set.
  void Checker::pulltab_begin_at(
      Configuration * C, Node * source, Node * target, PathList const & path
    )
  {
    ++this->counts["pulltabs"];
    if(!target || target->info->tag != T_CHOICE)
      this->violation("B1 (pull-tab)", "pull-tab", "the target is not a choice", C);
    xid_type const cid = NodeU{target}.choice->cid;
    if(at(source, path) != target)
      this->violation(
          "B1 (pull-tab)", "pull-tab"
        , "the source is not at the path " + path_text(path) + " of the target"
        , C, {cid}
        );
    Node * node = source;
    for(size_t k = 0; k < path.size() && node; ++k)
    {
      if(node->info->tag == T_SETGRD)
      {
        Set * set = NodeU{node}.setgrd->set;
        if(set)
        {
          this->root_node(node);
          auto & shadow = this->escape_sets[set];
          if(!shadow.count(cid))
          {
            if(!this->unbounded_sets.count(set) && !contains(this->tags_of(cid), set))
              this->violation(
                  "S0 (E in A)", "escape-set insertion"
                , "identifier " + std::to_string(cid)
                  + " enters the escape set of set " + this->set_name(set)
                  + " but is not argument-derived for it (tags "
                  + this->set_names(this->tags_of(cid)) + ")"
                , C, {cid}
                );
            shadow.insert(cid);
          }
        }
      }
      node = is_pointer_slot(node, path[k]) ? node->successors()[path[k]].node : nullptr;
    }
    this->pt_path = path;
  }

  void Checker::pulltab_end(
      Configuration * C, Node * source, Node * target, Node * lhs, Node * rhs
    , Node * result
    )
  {
    this->pulltab_end_at(C, source, target, this->pt_path, lhs, rhs, result);
  }

  // After the choice over the copies is made: the copies are faithful, the
  // identifier is in the escape set of every box the path crosses
  // (def:s-pull), the created choice carries the identifier of its source,
  // and the copies inherit the flags of the source.
  void Checker::pulltab_end_at(
      Configuration * C, Node * source, Node * target, PathList const & path
    , Node * lhs, Node * rhs, Node * result
    )
  {
    ChoiceNode const * choice = NodeU{target}.choice;
    xid_type const cid = choice->cid;
    this->check_spine_copy(
        source, path, lhs, choice->lhs, "B1 (pull-tab)", "pull-tab", "left", C
      );
    this->check_spine_copy(
        source, path, rhs, choice->rhs, "B1 (pull-tab)", "pull-tab", "right", C
      );
    Node * node = source;
    for(size_t k = 0; k < path.size() && node; ++k)
    {
      if(node->info->tag == T_SETGRD)
      {
        Set * set = NodeU{node}.setgrd->set;
        if(set && !set->escape_set.count(cid))
          this->violation(
              "S0 (pull-tab)", "pull-tab"
            , "identifier " + std::to_string(cid) + " crosses the box of set "
              + this->set_name(set) + " at depth " + std::to_string(k)
              + " of the path " + path_text(path)
              + " but is not in its escape set " + set_ids_text(set->escape_set)
            , C, {cid}
            );
        auto e = this->escape_sets.find(set);
        if(set && (e == this->escape_sets.end() || !e->second.count(cid)))
          this->violation(
              "S0 (pull-tab)", "pull-tab"
            , "identifier " + std::to_string(cid) + " crosses the box of set "
              + this->set_name(set) + " at depth " + std::to_string(k)
              + " of the path " + path_text(path)
              + " but no insertion into its escape set was seen"
            , C, {cid}
            );
      }
      node = is_pointer_slot(node, path[k]) ? node->successors()[path[k]].node : nullptr;
    }
    if(result)
    {
      if(result->info->tag != T_CHOICE || NodeU{result}.choice->cid != cid)
        this->violation(
            "B1 (pull-tab)", "pull-tab"
          , "the created choice carries identifier "
            + (result->info->tag == T_CHOICE
                ? std::to_string(NodeU{result}.choice->cid) : std::string("none"))
            + ", the source " + std::to_string(cid)
          , C, {cid}
          );
    }
    SetList const f = this->flags_of(source);
    if(!f.empty())
    {
      this->propagate(lhs, f, choice->lhs);
      this->propagate(rhs, f, choice->rhs);
    }
  }

  void Checker::yield_(Configuration * C)
  {
    ++this->counts["yields"];
    auto const enclosing = this->chain(false);
    this->check_fingerprint(C, "yield", enclosing);
    this->check_value(C);
    this->check_decided_variables(C);
    this->check_escape_sets("yield", C);
  }

  // No choice, operation, failure or constraint cell is reachable from the
  // root of C, and no bound or decided variable remains in it (X-c).  The
  // generator of a free variable and the arguments of a partial application
  // are not entered, as in the Python checker.
  void Checker::check_value(Configuration * C)
  {
    std::unordered_set<Node *> seen;
    std::vector<Node *> stack;
    if(C->root.arg)
      stack.push_back(*C->root);
    while(!stack.empty())
    {
      Node * node = stack.back();
      stack.pop_back();
      if(!node || !seen.insert(node).second)
        continue;
      InfoTable const * info = node->info;
      tag_type const tag = info->tag;
      if(tag == T_FWD)
        stack.push_back(NodeU{node}.fwd->target);
      else if(tag == T_SETGRD)
        stack.push_back(NodeU{node}.setgrd->value);
      else if(tag == T_CHOICE)
      {
        xid_type const cid = NodeU{node}.choice->cid;
        this->violation(
            "B1 (yield)", "yield"
          , "choice " + std::to_string(cid) + " is reachable from the yielded value"
          , C, {cid}
          );
      }
      else if(tag == T_FREE)
      {
        xid_type const vid = NodeU{node}.free->vid;
        if(this->binding(C, vid))
          this->violation(
              "X-c", "yield"
            , "variable " + std::to_string(vid) + " is bound and remains in the value"
            , C, {vid}
            );
        ChoiceState const d = this->decision(vid, C);
        if(d != UNDETERMINED)
          this->violation(
              "X-c", "yield"
            , "variable " + std::to_string(vid) + " is decided " + side_name(d)
              + " and remains in the value"
            , C, {vid}
            );
      }
      else if(tag == T_FUNC || tag == T_FAIL || tag == T_CONSTR)
        this->violation(
            "B1 (yield)", "yield"
          , std::string("the cell ") + info->name + " is reachable from the yielded value"
          , C
          );
      else if(tag >= T_CTOR && !is_partial(*info))
      {
        Arg const * data = node->successors();
        for(index_type i = 0; i < info->arity; ++i)
          if(info->format[i] == 'p')
            stack.push_back(data[i].node);
      }
    }
  }

  // Every identifier on the decided path of the generator of a decided
  // variable is decided (X-c).
  void Checker::check_decided_variables(Configuration * C)
  {
    for(auto const & entry: this->rts.istate.vtable)
    {
      xid_type const vid = entry.first;
      Node * x = entry.second;
      if(!x || x->info->tag != T_FREE)
        continue;
      Node * gen = has_generator(x);
      if(!gen)
        continue;
      if(this->decision(vid, C) == UNDETERMINED)
        continue;
      Node * node = deref(gen);
      size_t hops = 0;
      while(node && node->info->tag == T_CHOICE && ++hops < 100000)
      {
        xid_type const cid = NodeU{node}.choice->cid;
        ChoiceState const d = this->decision(cid, C);
        if(d == UNDETERMINED)
          this->violation(
              "X-c", "yield"
            , "variable " + std::to_string(vid) + " is decided but the inner "
              "identifier " + std::to_string(cid) + " of its generator is not"
            , C, {vid, cid}
            );
        node = deref(d == LEFT ? NodeU{node}.choice->lhs : NodeU{node}.choice->rhs);
      }
    }
  }

  // --------------------------------------------------------------------------
  // FS-x: generators, the slot writes, the private copies.
  // --------------------------------------------------------------------------

  void Checker::variable(Node * node)
  {
    xid_type const vid = NodeU{node}.free->vid;
    this->created.emplace(vid, "variable");
    add_all(this->tags[vid], this->boxes_above());
  }

  void Checker::generator(Node * x, Node * gen)
  {
    ++this->counts["generators"];
    xid_type const vid = NodeU{x}.free->vid;
    auto known = this->generators.find(vid);
    if(known != this->generators.end() && known->second != gen)
      this->violation(
          "X1", "generator"
        , "variable " + std::to_string(vid) + " gets a second generator"
        , this->current(), {vid}
        );
    // The table of the generators compares its entries by address alone,
    // so the nodes need no root: a variable alive keeps its generator, and
    // the id of a dead one never returns.
    this->generators[vid] = gen;
    Node * root = deref(gen);
    if(!root || root->info->tag != T_CHOICE || NodeU{root}.choice->cid != vid)
      this->violation(
          "X1", "generator"
        , "the root of the generator of variable " + std::to_string(vid)
          + " is " + this->text(root)
        , this->current(), {vid}
        );
    SetList base = this->boxes_above();
    add_all(base, this->tags_of(vid));
    add_all(base, this->flags_of(x));
    this->tags[vid] = base;
    this->created.emplace(vid, "generator");
    std::vector<Node *> stack{gen};
    std::unordered_set<Node *> seen;
    while(!stack.empty())
    {
      Node * node = stack.back();
      stack.pop_back();
      if(!node || !seen.insert(node).second)
        continue;
      tag_type const tag = node->info->tag;
      if(tag == T_CHOICE)
      {
        xid_type const cid = NodeU{node}.choice->cid;
        if(cid != vid)
          this->created.emplace(cid, "generator");
        add_all(this->tags[cid], base);
        stack.push_back(NodeU{node}.choice->lhs);
        stack.push_back(NodeU{node}.choice->rhs);
      }
      else if(tag == T_FREE)
        add_all(this->tags[NodeU{node}.free->vid], base);
      else
      {
        Arg const * data = node->successors();
        for(index_type i = 0; i < node->info->arity; ++i)
          if(node->info->format[i] == 'p')
            stack.push_back(data[i].node);
      }
    }
    SetList const f = this->flags_of(x);
    if(!f.empty())
      this->propagate(gen, f, nullptr);
  }

  void Checker::attach_generator(Node * x, Node * gen)
  {
    gc_count_write(x);
    NodeU{x}.free->genexpr = gen;
    this->generator(x, gen);
  }

  void Checker::value_bindings(Node * x, Node * tree)
  {
    xid_type const vid = NodeU{x}.free->vid;
    SetList base = this->boxes_above();
    add_all(base, this->tags_of(vid));
    add_all(base, this->flags_of(x));
    std::vector<Node *> stack{tree};
    while(!stack.empty())
    {
      Node * node = stack.back();
      stack.pop_back();
      if(node && node->info->tag == T_CHOICE)
      {
        xid_type const cid = NodeU{node}.choice->cid;
        this->created.emplace(cid, "binding");
        add_all(this->tags[cid], base);
        stack.push_back(NodeU{node}.choice->lhs);
        stack.push_back(NodeU{node}.choice->rhs);
      }
    }
  }

  // Before the write of a generator into the slot of a variable: the slot
  // holds the variable, the generator is its generator (X1), and the
  // reducts of the configurations that reference the redex are read (X-b).
  void Checker::instantiate_begin(
      Configuration * C, Variable const * var, Node * gen, char const * event
    )
  {
    ++this->counts[std::strcmp(event, "instantiation") == 0 ? "instantiations" : "slot_writes"];
    PathList const path(var->realpath.begin(), var->realpath.end());
    Node * x = var->target.kind == 'p' && var->target.arg ? *var->target : nullptr;
    if(!x || x->info->tag != T_FREE)
      this->violation(
          "X1", event
        , "the slot at " + path_text(path) + " holds " + this->text(x)
          + ", not a free variable"
        , C
        );
    xid_type const vid = NodeU{x}.free->vid;
    if(NodeU{x}.free->genexpr != gen)
      this->violation(
          "X1", event
        , "the generator written for variable " + std::to_string(vid)
          + " is not its generator"
        , C, {vid}
        );
    auto known = this->generators.find(vid);
    if(known != this->generators.end() && known->second != gen)
      this->violation(
          "X1", event
        , "variable " + std::to_string(vid) + " has two generators"
        , C, {vid}
        );
    this->inst_var = var;
    this->inst_gen = gen;
    this->inst_vid = vid;
    Node * redex = C->cursor().arg ? *C->cursor() : nullptr;
    this->inst_reducts.clear();
    // A lone configuration (one queue of one configuration, no capsule
    // entered) is the only one that references the redex, and its own
    // reduct reads the variable and the generator alike (the group of the
    // variable, or the decided side): the comparison is skipped.  A
    // sequence of a million narrowings stays linear.
    bool const alone = this->rts.qstack.size() == 1
        && this->rts.qstack.front()->size() == 1
        && this->counts.count("capsules") == 0;
    if(alone)
    {
      ++this->counts["reducts_skipped"];
      this->inst_valid = false;
    }
    else
      this->inst_valid = redex && this->reducts(redex, this->inst_reducts);
  }

  // After the write: the slot holds the generator, and the reduct of every
  // configuration that references the redex is unchanged under the
  // fingerprint it is compatible with (X-b).  The write changes one slot
  // and makes no cell, so no flags propagate (the Python backend copies the
  // spine there and flags the copy).
  void Checker::instantiate_end(
      Configuration * C, Variable const * var, char const * event
    )
  {
    PathList const path(var->realpath.begin(), var->realpath.end());
    Node * now = var->target.kind == 'p' && var->target.arg ? *var->target : nullptr;
    if(now != this->inst_gen)
      this->violation(
          "X-b", event
        , "the slot at " + path_text(path) + " holds " + this->text(now)
          + " after the write, not the generator"
        , C, {this->inst_vid}
        );
    if(this->inst_valid)
      this->compare_reducts(this->inst_reducts, event, this->inst_vid);
    this->inst_var = nullptr;
    this->inst_gen = nullptr;
    this->inst_valid = false;
    this->inst_reducts.clear();
  }

  void Checker::copied(
      Configuration * C, Cursor root, Node * old_root, Node * new_root
    , Node * end, char const * kind
    )
  {
    // The path: the levels of the scan from the slot ``root`` down to the
    // level above the deepest one (the slot of the variable).
    auto const & frames = C->scan.frames();
    size_t const n = frames.size();
    size_t k = n;
    for(size_t i = 0; i < n; ++i)
      if(frames[i].cur == root)
      {
        k = i;
        break;
      }
    // copy_spine copies the levels of the scan from the slot down: a slot
    // that is not a level is a defect of the copy, not a case the check
    // can skip.
    if(k == n || n < 1)
      this->violation(
          "X-b'", (std::string("copy (") + kind + ")").c_str()
        , "the slot of the copy is not a level of the scan (" + std::to_string(n)
          + " levels)"
        , C
        );
    PathList path;
    for(size_t i = k; i + 1 < n; ++i)
      path.push_back(frames[i].index);
    this->copied_at(C, old_root, new_root, path, end, kind);
  }

  // After a private copy of the spine from ``old_root`` along ``path`` with
  // ``end`` at its end was made for the current configuration (rule N.x):
  // the copy is faithful, and its reduct under the fingerprint of the
  // configuration equals the reduct of the root it replaces (X-b').
  void Checker::copied_at(
      Configuration * C, Node * old_root, Node * new_root, PathList const & path
    , Node * end, char const * kind
    )
  {
    ++this->counts["copies"];
    std::string const event = std::string("copy (") + kind + ")";
    this->check_spine_copy(old_root, path, new_root, end, "X-b'", event.c_str(), "", C);
    bool compared = false;
    uint64_t a = 0, b = 0;
    try
    {
      SigState state(CHECKER_SIGNATURE_BUDGET);
      a = this->sig(old_root, C, state);
      b = this->sig(new_root, C, state);
      compared = true;
    }
    catch(OverBudget const &)
    {
      ++this->counts["over_budget"];
    }
    if(compared && a != b)
      this->violation(
          "X-b'", event.c_str()
        , "the reduct of the configuration changed under its fingerprint"
        , C, {}
        , {"before: " + this->text(old_root), "after: " + this->text(new_root)}
        );
    SetList const f = this->flags_of(old_root);
    if(!f.empty())
      this->propagate(new_root, f, end);
  }

  // The reducts of the configurations that reach the cell ``watch``, in the
  // queues of this evaluation: the queues of the dispatch chain and the
  // queues of the capsules their graphs reach (the SetEval nodes the walk
  // meets).  The Python checker reads every queue of its table; the queue
  // registry of the collector also holds the queues of other evaluations
  // and of unloaded interpreters, whose nodes this evaluation must not
  // read.  False when the walk exceeds the budget.  One signature state per
  // configuration: the signature of a cell depends on the fingerprint.  The
  // budget is shared.
  bool Checker::reducts(Node * watch, std::vector<ReductRecord> & out)
  {
    size_t budget = CHECKER_SIGNATURE_BUDGET;
    std::vector<Queue *> queues(this->rts.qstack.begin(), this->rts.qstack.end());
    std::unordered_set<Queue *> seen(queues.begin(), queues.end());
    try
    {
      for(size_t k = 0; k < queues.size(); ++k)
        for(Configuration * cfg: *queues[k])
        {
          if(!cfg->root.arg)
            continue;
          SigState state(budget, watch);
          state.queues = &queues;
          state.seen_queues = &seen;
          uint64_t const s = this->sig(*cfg->root, cfg, state);
          budget = state.budget;
          if(state.reached)
            out.push_back(ReductRecord{cfg, s});
        }
    }
    catch(OverBudget const &)
    {
      ++this->counts["over_budget"];
      return false;
    }
    return true;
  }

  void Checker::compare_reducts(
      std::vector<ReductRecord> const & records, char const * event, xid_type vid
    )
  {
    try
    {
      for(ReductRecord const & rec: records)
      {
        SigState state(CHECKER_SIGNATURE_BUDGET);
        uint64_t const after = this->sig(*rec.cfg->root, rec.cfg, state);
        if(after != rec.sig)
          this->violation(
              "X-b", event
            , "the reduct of a configuration that references the redex changed "
              "under its fingerprint at the " + std::string(event)
              + " of variable " + std::to_string(vid)
            , rec.cfg, {vid}
            );
      }
    }
    catch(OverBudget const &)
    {
      ++this->counts["over_budget"];
    }
  }

  // The signature of the reduct of ``node`` under the fingerprint of
  // ``cfg``, read with the generator image: a decided choice is its side, a
  // bound variable its binding or its generator, a free variable and an
  // undecided generator root the group of the variable.
  uint64_t Checker::sig(Node * node, Configuration * cfg, SigState & state)
  {
    size_t hops = 0;
    tag_type tag = NOTAG;
    while(true)
    {
      if(!node)
        return label('L', 0);
      if(node == state.watch)
        state.reached = true;
      auto hit = state.memo.find(node);
      if(hit != state.memo.end())
        return hit->second;
      if(state.onstack.count(node))
        return label('Y', 0);
      tag = node->info->tag;
      if(++hops > 100000)
        return label('Y', 1);
      if(tag == T_FWD)
        node = NodeU{node}.fwd->target;
      else if(tag == T_SETGRD)
        node = NodeU{node}.setgrd->value;
      else if(tag == T_CHOICE)
      {
        // The root of the generator of a variable reads as the variable
        // does: as the binding of a bound variable (rule S.x writes the
        // generator into a slot that a configuration with a binding of the
        // variable may share; its fork applies the binding), as its side
        // when decided, and as the group of the variable otherwise.
        xid_type const cid = NodeU{node}.choice->cid;
        bool const is_variable = this->rts.get_freevar(cid) != nullptr;
        Node * b = is_variable ? this->binding(cfg, cid) : nullptr;
        ChoiceState const d = b ? UNDETERMINED : this->decision(cid, cfg);
        if(b)
          node = b;
        else if(d == LEFT)
          node = NodeU{node}.choice->lhs;
        else if(d == RIGHT)
          node = NodeU{node}.choice->rhs;
        else if(is_variable)
          return label('F', group_root(cfg, cid));
        else
          break;
      }
      else if(tag == T_FREE)
      {
        // A decided variable reads as its generator.  A variable without
        // one, decided through its group, reads as the generator of the
        // representative of the group: that is the node the runtime puts
        // into the copy of rule N.x (get_generator reads it by the group
        // id), where the Python backend clones a generator for the
        // variable first.
        xid_type const vid = NodeU{node}.free->vid;
        Node * b = this->binding(cfg, vid);
        Node * gen = nullptr;
        if(!b && this->decision(vid, cfg) != UNDETERMINED)
        {
          gen = has_generator(node);
          if(!gen)
            if(Node * rep = this->rts.get_freevar(group_root(cfg, vid)))
              if(rep->info->tag == T_FREE)
                gen = has_generator(rep);
        }
        if(b)
          node = b;
        else if(gen)
          node = gen;
        else
          return label('F', group_root(cfg, vid));
      }
      else
        break;
    }
    if(state.budget == 0)
      throw OverBudget();
    --state.budget;
    uint64_t h;
    state.onstack.insert(node);
    if(tag == T_CHOICE)
    {
      h = label('?', NodeU{node}.choice->cid);
      h = combine(h, this->sig(NodeU{node}.choice->lhs, cfg, state));
      h = combine(h, this->sig(NodeU{node}.choice->rhs, cfg, state));
    }
    else
    {
      InfoTable const * info = node->info;
      h = label('N', (uint64_t) (uintptr_t) info);
      Arg const * data = node->successors();
      if(info == &SetEval_Info && state.queues)
      {
        Queue * queue = NodeU{node}.seteval->queue;
        if(queue && state.seen_queues->insert(queue).second)
          state.queues->push_back(queue);
      }
      for(index_type i = 0; i < info->arity; ++i)
      {
        switch(info->format[i])
        {
          case 'p': h = combine(h, this->sig(data[i].node, cfg, state)); break;
          case 'i': h = combine(h, label('i', (uint64_t) data[i].ub_int)); break;
          case 'c': h = combine(h, label('c', (uint64_t) data[i].ub_char)); break;
          case 'f':
          {
            uint64_t bits;
            std::memcpy(&bits, &data[i].ub_float, sizeof(bits));
            h = combine(h, label('f', bits));
            break;
          }
          default:  h = combine(h, label('x', (uint64_t) (uintptr_t) data[i].blob)); break;
        }
      }
    }
    state.onstack.erase(node);
    state.memo[node] = h;
    return h;
  }

  // --------------------------------------------------------------------------
  // FS-S: the tags and the flags.
  // --------------------------------------------------------------------------

  // After evalS_step made the queue of the capsule of ``set`` over
  // ``goal``: every cell reachable from a boxed argument of the goal is
  // inside the capsule (the entry step of def:s-flags).  A capsule without
  // a box (an encapsulated expression) gets no shadow: no identifier can
  // enter its escape set, and nothing keeps its set alive.
  void Checker::capsule_entry(Set * set, Node * goal)
  {
    ++this->counts["capsules"];
    this->set_name(set);
    if(!goal || !set)
      return;
    std::vector<Node *> stack;
    {
      Arg const * data = goal->successors();
      for(index_type i = 0; i < goal->info->arity; ++i)
        if(goal->info->format[i] == 'p')
        {
          Node * s = data[i].node;
          if(s && s->info->tag == T_SETGRD && NodeU{s}.setgrd->set == set)
            stack.push_back(s);
        }
    }
    if(stack.empty())
    {
      ++this->counts["capsules_without_box"];
      return;
    }
    this->escape_sets.emplace(set, std::unordered_set<xid_type>());
    size_t budget = CHECKER_ENTRY_BUDGET;
    while(!stack.empty())
    {
      Node * node = stack.back();
      stack.pop_back();
      if(!node)
        continue;
      auto p = this->flags.find(node);
      if(p != this->flags.end() && contains(p->second, set))
        continue;
      if(budget == 0)
      {
        this->unbounded_sets.insert(set);
        ++this->counts["entry_over_budget"];
        return;
      }
      --budget;
      add(this->flags[node], set);
      this->root_node(node);
      tag_type const tag = node->info->tag;
      if(tag == T_CHOICE)
      {
        xid_type const cid = NodeU{node}.choice->cid;
        this->created.emplace(cid, "entry");
        add(this->tags[cid], set);
      }
      else if(tag == T_FREE)
        add(this->tags[NodeU{node}.free->vid], set);
      Arg const * data = node->successors();
      for(index_type i = 0; i < node->info->arity; ++i)
        if(node->info->format[i] == 'p')
          stack.push_back(data[i].node);
    }
  }

  // A constructor or a failure without a successor cell.
  static bool is_leaf_value(Node * n)
  {
    InfoTable const * info = n->info;
    if(info->tag < T_CTOR && info->tag != T_FAIL)
      return false;
    for(index_type i = 0; i < info->arity; ++i)
      if(info->format[i] == 'p')
        return false;
    return true;
  }

  // The cells reachable from ``node`` that carry no flags yet inherit
  // ``f``: the cells a pull-tab, a copy or a generator created at a
  // flagged site.  The walk stops at a flagged cell and at ``stop_at``.
  void Checker::propagate(Node * node, SetList const & f, Node * stop_at)
  {
    this->propagate(std::vector<Node *>{node}, f, stop_at);
  }

  // The same walk from every cell of ``stack`` under one budget: the cells
  // a step made (see step_end).  A walk over the budget leaves cells
  // without the flags, so the sets of ``f`` become unbounded: their checks
  // of S0 are suppressed, not reported, as after an entry walk over its
  // budget.  A leaf value (a constructor or Fail without a successor, the
  // static True, False, Nil, Fail and the small literals among them) is
  // not flagged: it never steps and holds no cell.
  void Checker::propagate(
      std::vector<Node *> stack, SetList const & f, Node * stop_at
    )
  {
    size_t budget = CHECKER_PROPAGATE_BUDGET;
    while(!stack.empty())
    {
      Node * n = stack.back();
      stack.pop_back();
      if(!n || n == stop_at || is_leaf_value(n))
        continue;
      auto p = this->flags.find(n);
      if(p != this->flags.end())
      {
        if(!subset(f, p->second))
          add_all(p->second, f);
        continue;
      }
      if(budget == 0)
      {
        for(Set * set: f)
          this->unbounded_sets.insert(set);
        ++this->counts["propagate_over_budget"];
        return;
      }
      --budget;
      this->flags[n] = f;
      this->root_node(n);
      tag_type const tag = n->info->tag;
      if(tag == T_CHOICE)
        add_all(this->tags[NodeU{n}.choice->cid], f);
      else if(tag == T_FREE)
        add_all(this->tags[NodeU{n}.free->vid], f);
      Arg const * data = n->successors();
      for(index_type i = 0; i < n->info->arity; ++i)
        if(n->info->format[i] == 'p')
          stack.push_back(data[i].node);
    }
  }

  // --------------------------------------------------------------------------
  // Steps and the definitional trees.
  // --------------------------------------------------------------------------

  void Checker::step_begin(Configuration * C)
  {
    Node * redex = C->cursor().arg ? *C->cursor() : nullptr;
    StepRecord rec{redex, redex ? redex->info : nullptr, this->step_args.size(), 0};
    if(redex)
    {
      InfoTable const * info = redex->info;
      Arg const * data = redex->successors();
      for(index_type i = 0; i < info->arity; ++i)
        this->step_args.push_back(info->format[i] == 'p' ? data[i].node : nullptr);
      rec.nargs = info->arity;
    }
    this->step_stack.push_back(rec);
  }

  // After a step returned ``status``.  A completed step: the choice it
  // created is tagged with the boxes above it and the flags of the redex,
  // the cells it made at a flagged redex inherit the flags, and a
  // replacement by failure comes from an exempt leaf (B2 c).
  void Checker::step_end(Configuration * C, tag_type status)
  {
    if(this->step_stack.empty())
      return;
    StepRecord const rec = this->step_stack.back();
    this->step_stack.pop_back();
    std::vector<Node *> args;
    if(rec.offset <= this->step_args.size())
    {
      args.assign(this->step_args.begin() + rec.offset, this->step_args.end());
      this->step_args.resize(rec.offset);
    }
    if(status < E_RESTART || !rec.redex)
      return;
    ++this->counts["steps"];
    Node * const redex = rec.redex;
    SetList const flagged = this->flags_of(redex);
    bool const has_flags = this->flags.count(redex) != 0;
    Node * const result = deref_fwd(redex);
    if(result && result->info->tag == T_CHOICE)
    {
      xid_type const cid = NodeU{result}.choice->cid;
      if(!this->created.count(cid))
      {
        this->created[cid] = "choice";
        SetList t = this->boxes_above();
        add_all(t, flagged);
        add_all(this->tags[cid], t);
      }
    }
    if(has_flags && result)
    {
      // The cells the step made inherit the flags of the redex: the result,
      // when the step forwarded the redex to a fresh cell, and the cells
      // under it.  The redex carries the flags already, so a walk that
      // started there stopped at once, and a cell made under it (the ? of
      // Just (A ? B)) inherited nothing: the false report of S0 (E in A) at
      // the pull-tab across the box (2026-10-09).
      std::vector<Node *> seeds;
      if(result != redex && !is_leaf_value(result))
        seeds.push_back(result);
      Arg const * data = result->successors();
      for(index_type i = 0; i < result->info->arity; ++i)
        if(result->info->format[i] == 'p')
          seeds.push_back(data[i].node);
      this->propagate(std::move(seeds), flagged, nullptr);
    }
    if(result && result->info->tag == T_FAIL)
    {
      CheckerTree const * tree = this->tree_of(rec.info);
      if(tree)
        this->check_exempt(rec.info, args, tree, C);
    }
  }

  void Checker::check_failed_step(
      Configuration * C, InfoTable const * info, std::vector<Node *> const & args
    )
  {
    CheckerTree const * tree = this->tree_of(info);
    if(tree)
      this->check_exempt(info, args, tree, C);
    else
      ++this->counts["step_untracked"];
  }

  void Checker::hnf(Configuration * C, Variable const * inductive)
  {
    ++this->counts["hnfs"];
    Node * redex = C->cursor().arg && C->cursor().kind == 'p' ? *C->cursor() : nullptr;
    if(!redex || redex->info->tag != T_FUNC)
      return;
    CheckerTree const * tree = this->tree_of(redex->info);
    if(!tree)
    {
      ++this->counts["hnf_untracked"];
      return;
    }
    PathList path;
    if(!logical_path(redex, inductive->realpath, path))
    {
      ++this->counts["hnf_untracked"];
      return;
    }
    this->check_position(redex, tree, path, C);
  }

  // ``path`` is the position of a case of ``tree`` whose branches above it
  // match the constructors at their positions (B2 a, b).
  void Checker::check_position(
      Node * redex, CheckerTree const * tree, PathList const & path
    , Configuration * C
    )
  {
    std::vector<Node *> const args = successor_nodes(redex);
    char const * name = redex->info->name;
    CheckerTree const * node = tree;
    std::vector<std::string> matched;
    while(node->kind == CheckerTree::CASE)
    {
      if(!node->position_known)
      {
        ++this->counts["hnf_untracked"];
        return;
      }
      if(node->path == path)
        return;
      Node * cell = logical_from_args(args, node->path);
      uint64_t key = 0;
      if(!cell_key(cell, node->literal, key))
        this->violation(
            "B2", "hnf"
          , std::string("operation ") + name + " demands position " + path_text(path)
            + " before the inductive position " + path_text(node->path)
            + " above it, which holds " + this->text(cell)
          , C, {}, {matched_text(matched)}
          );
      auto branch = node->branches.find(key);
      if(branch == node->branches.end())
        this->violation(
            "B2", "hnf"
          , std::string("operation ") + name + " demands position " + path_text(path)
            + " under a constructor at " + path_text(node->path)
            + " that matches no branch"
          , C, {}, {matched_text(matched)}
          );
      matched.push_back(path_text(node->path) + ":" + std::to_string(key));
      node = branch->second.get();
    }
    this->violation(
        "B2", "hnf"
      , std::string("operation ") + name + " demands position " + path_text(path)
        + ", which is not an inductive position of a branch that matches (the "
          "tree ends in " + leaf_name(node) + ")"
      , C, {}, {matched_text(matched)}
      );
  }

  // A replacement by failure comes from an exempt leaf or from a failure at
  // an inductive position (B2 c).  The second source is a completed step
  // here: hnf forwards the redex to the failure and the step returns (the
  // Python backend unwinds there, and its check never sees it).  A return
  // of a reference forwards the redex to the node the reference denotes,
  // which may be a failure: such a leaf is no replacement by failure (the
  // Python backend writes a forward node there, which its check never
  // sees).
  void Checker::check_exempt(
      InfoTable const * info, std::vector<Node *> const & args
    , CheckerTree const * tree, Configuration * C
    )
  {
    CheckerTree const * node = tree;
    std::vector<std::string> matched;
    while(node->kind == CheckerTree::CASE)
    {
      if(!node->position_known)
        return;
      Node * cell = logical_from_args(args, node->path);
      if(cell && cell->info->tag == T_FAIL)
        return;
      uint64_t key = 0;
      if(!cell_key(cell, node->literal, key))
        this->violation(
            "B2 (failure)", "step"
          , std::string("operation ") + info->name
            + " failed while its inductive position " + path_text(node->path)
            + " holds " + this->text(cell)
          , C, {}, {matched_text(matched)}
          );
      auto branch = node->branches.find(key);
      if(branch == node->branches.end())
      {
        if(node->literal)
          return;
        this->violation(
            "B2 (failure)", "step"
          , std::string("operation ") + info->name
            + " failed on a constructor at " + path_text(node->path)
            + " that matches no branch"
          , C, {}, {matched_text(matched)}
          );
      }
      matched.push_back(path_text(node->path) + ":" + std::to_string(key));
      node = branch->second.get();
    }
    if(node->kind != CheckerTree::EXEMPT && node->kind != CheckerTree::RETURN_REF)
      this->violation(
          "B2 (failure)", "step"
        , std::string("operation ") + info->name
          + " was replaced by a failure from a " + leaf_name(node) + " leaf"
        , C, {}, {matched_text(matched)}
        );
  }

  // The definitional tree of the operation with ``info``, or null for a
  // built-in, a compiled function, or an operation the checker cannot read.
  // The tree is built from the bytecode of an interpreted function at its
  // first use and kept: a function the tiered mode swaps to compiled code
  // afterwards keeps its tree, since the compiled form takes the same
  // steps.
  CheckerTree const * Checker::tree_of(InfoTable const * info)
  {
    if(!info)
      return nullptr;
    auto hit = this->trees.find(info);
    if(hit != this->trees.end())
      return hit->second.get();
    std::unique_ptr<CheckerTree> tree;
    if(Bytecode const * bc = icurry_bytecode(info))
      tree = build_tree(*bc, 0, PathEnv(bc->nvars), 0);
    CheckerTree const * result = tree.get();
    this->trees[info] = std::move(tree);
    return result;
  }
}
