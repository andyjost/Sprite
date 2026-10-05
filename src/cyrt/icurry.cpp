#include <alloca.h>
#include <cassert>
#include <cstring>
#include <new>
#include <stdexcept>
#include "cyrt/builtins.hpp"
#include "cyrt/currylib/setfunctions.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/icurry.hpp"
#include "cyrt/state/rts.hpp"

// The ICurry interpreter.  See icurry.hpp for the machine and the opcodes.
//
// The interpreter mirrors the generated code of backends/cxx/compiler.py
// statement by statement: a register is the Node * of a pass-through
// argument (Node::successor_node, Variable::successor_node), a variable is
// the Variable of a scrutinee (the indexer of Variable), a case is a call of
// hnf followed by a switch on the tag, and a return writes its result into
// the redex when the result fits (Node::rewrite) or forwards the redex to
// it.  So the two forms of a function take the same steps and allocate the
// same nodes, and the scheduler sees no difference between them.
namespace cyrt
{
  namespace
  {
    // Every bytecode lives as long as the process, like the info tables of
    // a loaded module.
    std::deque<std::unique_ptr<Bytecode>> g_functions;

    char const * const OPCODE_NAMES[NUM_OPCODES] = {
        "LOAD_ROOT_SUCC", "LOAD_VAR_SUCC", "BIND_ROOT", "BIND_VAR"
      , "COPY_REG", "COPY_VAR", "FREE_REG", "PUSH_REG", "PUSH_VAR"
      , "PUSH_ROOT", "PUSH_CONST", "PUSH_SUCC", "PUSH_PATH", "MAKE"
      , "MAKE_PARTIAL", "MAKE_STRING", "STORE_REG", "STORE_VAR", "SET_SUCC"
      , "EXEMPT", "RET_REF", "RET_NODE", "RET_STRING", "CASE_CONS"
      , "CASE_LIT"
      };

    // The Variable objects of a frame.  They are made in place when the
    // step starts and destroyed on every way out of it, so that a path or a
    // guard list that outgrew its inline room is released.
    struct Frame
    {
      Frame(void * storage, uint32_t n)
        : vars((Variable *) storage), n(n)
      {
        for(uint32_t i=0; i<n; ++i)
          new(this->vars + i) Variable();
      }
      ~Frame()
      {
        for(uint32_t i=0; i<this->n; ++i)
          this->vars[i].~Variable();
      }
      Frame(Frame const &) = delete;
      Frame & operator=(Frame const &) = delete;
      Variable * vars;
      uint32_t   n;
    };

    // A node of ``info`` with the ``n`` successors ``args``, as Node::create
    // makes it: the static object of a pinned constructor, and otherwise a
    // new block.  Every slot of a node ICurry spells holds a node.
    inline Node * make_node(
        InfoTable const * info, Node * const * args, uint32_t n
      )
    {
      if(is_pinned(*info))
        return (Node *) info->step;
      assert(n == info->arity);
      Node * node;
      do
      {
        node = node_reserve(info->alloc_size);
        assert(node);
        RawNodeMemory mem{node};
        *mem.info++ = info;
        for(uint32_t i=0; i<n; ++i)
          *mem.boxed++ = args[i];
      } while(!node_commit(node, info->alloc_size));
      // The two kinds of node the collector finalizes (see Node::create).
      if(info == &_biGenerator_Info)
        gc_register_generator(node);
      else if(info == &SetEval_Info)
        gc_register_seteval(node);
      return node;
    }

    // The variable at the end of ``path`` from the redex (ROOT_VAR) or from
    // a variable of the frame: the indexer of Variable, one entry at a time.
    inline Variable index_path(
        Cursor const & redex, Variable const * vars, uint32_t base
      , uint32_t const * path, uint32_t n
      )
    {
      assert(n >= 1);
      Variable var = base == ROOT_VAR
          ? Variable(*redex, (index_type) path[0])
          : vars[base][(index_type) path[0]];
      for(uint32_t i=1; i<n; ++i)
        var = var[(index_type) path[i]];
      return var;
    }

    inline uint64_t read_u64(uint32_t const * units)
    {
      return uint64_t(units[0]) | (uint64_t(units[1]) << 32);
    }
  }

  tag_type icurry_step(RuntimeState * rts, Configuration * C)
  {
    Cursor const _0 = C->cursor();
    Bytecode const * bc = (Bytecode const *) _0->info->aux;
    assert(bc);
    uint32_t const * const code = bc->code.data();
    void const * const * const K = bc->consts.data();
    // The frame.  The registers start null: a plain variable not yet
    // assigned reads as null, as an unassigned Variable does (a recursive
    // let refers to a cell before it exists).
    Node ** const regs = (Node **) alloca(sizeof(Node *) * (bc->nregs + 1));
    std::memset(regs, 0, sizeof(Node *) * bc->nregs);
    Node ** const stack = (Node **) alloca(sizeof(Node *) * (bc->nstack + 1));
    Node ** const cells = (Node **) alloca(sizeof(Node *) * (bc->nvars + 1));
    Frame frame(alloca(sizeof(Variable) * (bc->nvars + 1)), bc->nvars);
    Variable * const vars = frame.vars;
    uint32_t pc = 0;
    size_t sp = 0;
    while(true)
    {
      uint32_t const * const op = code + pc;
      switch((Opcode) op[0])
      {
        case OP_LOAD_ROOT_SUCC:
          regs[op[1]] = _0->successor_node((index_type) op[2]);
          pc += 3;
          break;
        case OP_LOAD_VAR_SUCC:
          regs[op[1]] = vars[op[2]].successor_node((index_type) op[3]);
          pc += 4;
          break;
        case OP_BIND_ROOT:
          vars[op[1]] = index_path(_0, vars, ROOT_VAR, op + 3, op[2]);
          pc += 3 + op[2];
          break;
        case OP_BIND_VAR:
          vars[op[1]] = index_path(_0, vars, op[2], op + 4, op[3]);
          pc += 4 + op[3];
          break;
        case OP_COPY_REG:
          regs[op[1]] = regs[op[2]];
          pc += 3;
          break;
        case OP_COPY_VAR:
          vars[op[1]] = vars[op[2]];
          pc += 3;
          break;
        case OP_FREE_REG:
          regs[op[1]] = rts->freshvar();
          pc += 2;
          break;
        case OP_PUSH_REG:
          stack[sp++] = regs[op[1]];
          pc += 2;
          break;
        case OP_PUSH_VAR:
          stack[sp++] = vars[op[1]].rvalue();
          pc += 2;
          break;
        case OP_PUSH_ROOT:
          stack[sp++] = *_0;
          pc += 1;
          break;
        case OP_PUSH_CONST:
          stack[sp++] = (Node *) K[op[1]];
          pc += 2;
          break;
        case OP_PUSH_SUCC:
          stack[sp++] = op[1] == ROOT_VAR
              ? _0->successor_node((index_type) op[2])
              : vars[op[1]].successor_node((index_type) op[2]);
          pc += 3;
          break;
        case OP_PUSH_PATH:
          stack[sp++] = index_path(_0, vars, op[1], op + 3, op[2]).rvalue();
          pc += 3 + op[2];
          break;
        case OP_MAKE:
        {
          uint32_t const n = op[2];
          assert(sp >= n);
          Node * node = make_node(
              (InfoTable const *) K[op[1]], stack + sp - n, n
            );
          sp -= n;
          stack[sp++] = node;
          pc += 3;
          break;
        }
        case OP_MAKE_PARTIAL:
        {
          uint32_t const n = op[2];
          assert(sp >= n && n >= 1);
          static_assert(sizeof(Arg) == sizeof(Node *), "");
          // The array form: the count is a size_t, or the call resolves to
          // the variadic form.
          Node * node = Node::create_partial(
              (InfoTable const *) K[op[1]], (Arg const *) (stack + sp - n)
            , (size_t) n
            );
          sp -= n;
          stack[sp++] = node;
          pc += 3;
          break;
        }
        case OP_MAKE_STRING:
          stack[sp++] = cstring((char const *) K[op[1]]);
          pc += 2;
          break;
        case OP_STORE_REG:
          assert(sp >= 1);
          regs[op[1]] = stack[--sp];
          pc += 2;
          break;
        case OP_STORE_VAR:
        {
          // As the generated code does for a variable assigned a new node:
          // the Variable targets a cell of the frame, with no path and no
          // guard (Node * tmp = ...; var.target = tmp;).
          assert(sp >= 1);
          uint32_t const v = op[1];
          cells[v] = stack[--sp];
          vars[v] = Variable();
          vars[v].target = Cursor(cells[v]);
          pc += 2;
          break;
        }
        case OP_SET_SUCC:
        {
          // The patch of a recursive let: index to the parent of the slot,
          // then write the slot (Variable::set_successor).
          assert(sp >= 1);
          uint32_t const n = op[2];
          uint32_t const * path = op + 3;
          Node * value = stack[--sp];
          if(n == 1)
            vars[op[1]].set_successor((index_type) path[0], value);
          else
          {
            Variable parent = index_path(_0, vars, op[1], path, n - 1);
            parent.set_successor((index_type) path[n - 1], value);
          }
          pc += 3 + n;
          break;
        }
        case OP_EXEMPT:
          return _0->make_failure();
        case OP_RET_REF:
          assert(sp == 1);
          return _0->forward_or_copy(stack[0]);
        case OP_RET_NODE:
        {
          InfoTable const * info = (InfoTable const *) K[op[1]];
          uint32_t const n = op[2];
          assert(sp == n);
          Node * const redex = *_0;
          // The result is written into the redex when it fits the block
          // (Node::rewrite): the arguments are on the stack already, so a
          // successor of the redex among them is read before the slots are
          // written.  A pinned constructor is never written into a redex.
          if(!is_pinned(*info) && info->alloc_size <= redex->info->alloc_size)
          {
            assert(!gc_is_literal(redex));
            size_t const old_bytes = redex->info->alloc_size;
            RawNodeMemory mem{redex};
            *mem.info++ = info;
            for(uint32_t i=0; i<n; ++i)
              *mem.boxed++ = stack[i];
            gc_pad_slack(redex, old_bytes, info->alloc_size);
            return info->tag;
          }
          redex->forward_to(make_node(info, stack, n));
          return T_FWD;
        }
        case OP_RET_STRING:
          // A string node has the smallest block, so it always fits.
          assert(sp == 0);
          return _0->rewrite(&_biString_Info, (char const *) K[op[1]]);
        case OP_CASE_CONS:
        {
          assert(sp == 0);
          uint32_t const ntab = op[3];
          tag_type const tag = rts->hnf(C, &vars[op[1]], K[op[2]]);
          if((uint32_t) tag < ntab)
          {
            uint32_t const target = op[4 + tag];
            if(target != NO_BRANCH)
            {
              pc = target;
              break;
            }
          }
          return tag;
        }
        case OP_CASE_LIT:
        {
          assert(sp == 0);
          Variable & var = vars[op[1]];
          tag_type const tag = rts->hnf(C, &var, K[op[2]]);
          if(tag < T_CTOR)
            return tag;
          Node * const node = *var.target;
          uint32_t const n = op[4];
          uint32_t const * entry = op + 5;
          switch(op[3])
          {
            case 'i':
            {
              uint64_t const value = (uint64_t) NodeU{node}.int_->value;
              for(uint32_t i=0; i<n; ++i, entry += 3)
                if(read_u64(entry) == value)
                  goto found;
              break;
            }
            case 'c':
            {
              uint64_t const value = (uint64_t) NodeU{node}.char_->value;
              for(uint32_t i=0; i<n; ++i, entry += 3)
                if(read_u64(entry) == value)
                  goto found;
              break;
            }
            case 'f':
            {
              double const value = NodeU{node}.float_->value;
              for(uint32_t i=0; i<n; ++i, entry += 3)
              {
                uint64_t const bits = read_u64(entry);
                double branch_value;
                std::memcpy(&branch_value, &bits, sizeof(double));
                if(branch_value == value)
                  goto found;
              }
              break;
            }
            default:
              assert(false);
          }
          return _0->make_failure();
        found:
          pc = entry[2];
          break;
        }
        default:
          throw std::logic_error(
              std::string("bad opcode in the bytecode of ") + _0->info->name
            );
      }
    }
  }

  void icurry_attach(InfoTable * info, std::unique_ptr<Bytecode> code)
  {
    if(!info || !code)
      throw std::invalid_argument("icurry_attach: a null argument");
    if(info->tag != T_FUNC)
      throw std::invalid_argument(
          std::string("icurry_attach: ") + info->name + " is not a function"
        );
    if(is_static(*info))
      throw std::invalid_argument(
          std::string("icurry_attach: ") + info->name
          + " is a static info table (a built-in or a compiled module)"
        );
    if(info->step)
      throw std::invalid_argument(
          std::string("icurry_attach: ") + info->name + " has a step already"
        );
    info->aux = code.get();
    info->step = &icurry_step;
    g_functions.push_back(std::move(code));
  }

  Bytecode const * icurry_bytecode(InfoTable const * info)
  {
    if(info && info->step == &icurry_step)
      return (Bytecode const *) info->aux;
    return nullptr;
  }

  size_t icurry_num_functions()
  {
    return g_functions.size();
  }

  char const * icurry_opcode_name(uint32_t opcode)
  {
    return opcode < NUM_OPCODES ? OPCODE_NAMES[opcode] : nullptr;
  }
}
