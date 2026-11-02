#include "curryrt/curryrt.hpp"
#include "curryrt/currylib/prelude.hpp"
#include "curryrt/currylib/library.hpp"
#include "curryrt/module.hpp"
#include "curryrt/platform.hpp"
#include <chrono>
#include <ctime>
#include <cstdlib>
#include <cstring>
#include <algorithm>
#include <cctype>
#include <cmath>
#include <sstream>
#include "curryrt/graph/show.hpp"
#include "curryrt/graph/walk.hpp"
#include <unordered_set>
#include "curryrt/bigint.hpp"
#include "curryrt/utf8.hpp"
#include "curryrt/exceptions.hpp"

using namespace curryrt;

namespace
{
  std::string install_prefix;
  auto const start = std::chrono::steady_clock::now();

  tag_type finish(Configuration * C, Node * value, bool monadic=true)
  {
    C->cursor()->forward_to(monadic ? io(value) : value);
    return T_FWD;
  }

  tag_type io_error(Configuration * C, int code, std::string const & name = "")
  {
    std::string message = name.empty() ? std::strerror(code) : name + ": " + std::strerror(code);
    C->set_error(Node::create(ioerror_info(IO_ERROR),
        build_curry_string(message.c_str())), "i/o error: " + message,
        ErrorKind::io);
    return E_ERROR;
  }

  tag_type distribution(RuntimeState *, Configuration * C)
  {
    std::string name = C->cursor()->info->name;
    Node * value;
    if(name == "curryCompiler" || name == "curryRuntime")
      value = build_curry_string("sprite");
    else if(name == "baseVersion")
      value = build_curry_string(SPRITE_BASE_VERSION);
    else if(name == "installDir")
      value = build_curry_string(install_prefix.c_str());
    else if(name.find("Major") != std::string::npos)
      value = int_(SPRITE_VERSION_MAJOR);
    else if(name.find("Minor") != std::string::npos)
      value = int_(SPRITE_VERSION_MINOR);
    else
      value = int_(SPRITE_VERSION_PATCH);
    return finish(C, value, false);
  }

  tag_type cpu_time(RuntimeState *, Configuration * C)
  {
    auto ticks = std::clock();
    return finish(C, int_(ticks < 0 ? 0 :
        static_cast<unboxed_int_type>(1000.0 * ticks / CLOCKS_PER_SEC)));
  }

  tag_type elapsed_time(RuntimeState *, Configuration * C)
  {
    return finish(C, int_(std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start).count()));
  }

  tag_type windows(RuntimeState *, Configuration * C)
  {
#if defined(_WIN32)
    return finish(C, true_(), false);
#else
    return finish(C, false_(), false);
#endif
  }

  tag_type environment(RuntimeState *, Configuration * C)
  {
    Cursor root = C->cursor();
    // The Curry wrappers normalize the complete strings before this step.
    std::string name = extract_string(root[0].target);
    std::string operation = root->info->name;
    if(operation == "prim_getEnviron")
    {
      auto value = std::getenv(name.c_str());
      return finish(C, build_curry_string(value ? value : ""));
    }
    int error;
    if(name.empty() || name.find('=') != std::string::npos ||
        name.find('\0') != std::string::npos)
      error = EINVAL;
    else if(operation == "prim_setEnviron")
    {
      std::string value = extract_string(root[1].target);
      error = value.find('\0') != std::string::npos ? EINVAL :
          platform::set_environment(name, value);
    }
    else
      error = platform::unset_environment(name);
    return error ? io_error(C, error, name) : finish(C, unit());
  }

  extern DataType const ref_type;
  InfoTable const ref_info{T_CTOR, 1, sizeof(Node1), F_STATIC_OBJECT | F_OPAQUE,
      "IORef", "p", nullptr, &ref_type};
  InfoTable const * const ref_ctors[] = {&ref_info};
  DataType const ref_type{ref_ctors, 1, 't', F_STATIC_OBJECT, "IORef"};

  tag_type new_ref(RuntimeState *, Configuration * C)
  {
    return finish(C, Node::create(&ref_info, C->cursor()[0].rvalue()));
  }

  tag_type read_ref(RuntimeState * rts, Configuration * C)
  {
    Variable ref = C->cursor()[0];
    auto tag = rts->hnf(C, &ref);
    if(tag < T_CTOR) return tag;
    return finish(C, ref.successor_node(0));
  }

  tag_type write_ref(RuntimeState * rts, Configuration * C)
  {
    Variable ref = C->cursor()[0];
    auto tag = rts->hnf(C, &ref);
    if(tag < T_CTOR) return tag;
    ref.set_successor(0, C->cursor()[1].rvalue());
    return finish(C, unit());
  }

  ValueSet const free_in_configuration{nullptr, 0, 'v'};

  // An observation of an absent binding belongs to this configuration.
  tag_type observed(Configuration * C, Node * value)
  {
    *C->root = C->scan.copy_spine(C->root, value);
    return E_RESTART;
  }

  tag_type unsafe_io(RuntimeState * rts, Configuration * C)
  {
    Variable action = C->cursor()[0];
    auto tag = rts->hnf(C, &action, &IO_Type, true);
    if(tag < T_CTOR) return tag;
    return finish(C, action.successor_node(0), false);
  }

  tag_type inspect_term(RuntimeState *, Configuration *, Variable, bool,
      bool &, std::unordered_set<Node *> &);

  tag_type spawn_constraint(RuntimeState * rts, Configuration * C)
  {
    GcClamp clamp;
    Residuals saved;
    C->residuals.swap(saved);
    while(true)
    {
      auto steps = rts->stepcount;
      Variable constraint = C->cursor()[0];
      auto tag = rts->hnf(C, &constraint, &Bool_Type);
      if(tag == T_TRUE || tag == T_FALSE)
      {
        C->residuals.swap(saved);
        if(tag == T_FALSE) rts->record_failure(C, &constraint);
        return finish(C, tag == T_TRUE ? C->cursor()[1].rvalue() : Fail, false);
      }
      if(tag != E_RESIDUAL)
      {
        C->residuals.swap(saved);
        return tag;
      }
      bool ground = true;
      std::unordered_set<Node *> seen;
      tag = inspect_term(rts, C, C->cursor()[1], true, ground, seen);
      if(tag != E_RESIDUAL && tag < T_CTOR)
      {
        C->residuals.swap(saved);
        return tag;
      }
      if(rts->stepcount == steps)
      {
        C->residuals.merge(saved);
        return E_RESIDUAL;
      }
    }
  }

  tag_type variable_test(RuntimeState * rts, Configuration * C)
  {
    std::string operation = C->cursor()->info->name;
    index_type offset = operation == "isVar" || operation == "identicalVar" ? 1 : 0;
    Variable lhs = C->cursor()[offset];
    auto tag = rts->hnf_or_free(C, &lhs, &free_in_configuration);
    if(tag != T_FREE && tag < T_CTOR) return tag;
    bool result = tag == T_FREE;
    if(operation == "prim_identicalVar" || operation == "identicalVar")
    {
      Variable rhs = C->cursor()[offset+1];
      auto other = rts->hnf_or_free(C, &rhs, &free_in_configuration);
      if(other != T_FREE && other < T_CTOR) return other;
      result = result && other == T_FREE
          && C->grp_id(obj_id(lhs.target)) == C->grp_id(obj_id(rhs.target));
    }
    return observed(C, result ? True : False);
  }

  // Normalize with the configuration's guides, retaining free variables.
  // The non-evaluating variant only resolves bindings in an expression.
  tag_type inspect_term(RuntimeState * rts, Configuration * C, Variable var,
      bool evaluate, bool & ground, std::unordered_set<Node *> & seen)
  {
    if(var.target.kind != 'p') return T_CTOR;
    tag_type tag = var.target->info->tag;
    if(evaluate || tag == T_FREE)
    {
      tag = rts->hnf_or_free(C, &var, &free_in_configuration);
      if(tag != T_FREE && tag < T_CTOR) return tag;
    }
    if(tag == T_FREE)
    {
      ground = false;
      auto vid = obj_id(var.target);
      auto gid = C->grp_id(vid);
      if(vid != gid)
      {
        C->scan.push(&var);
        *C->root = C->scan.copy_spine(C->root, rts->get_freevar(gid));
        C->scan.pop();
        return E_RESTART;
      }
      return T_CTOR;
    }
    Node * node = var.target;
    if(!seen.insert(node).second || is_bigint(node)) return T_CTOR;
    for(index_type i=0; i<node->info->arity; ++i)
      if(node->info->format[i] == 'p')
      {
        auto status = inspect_term(rts, C, var[i], evaluate, ground, seen);
        if(status < T_CTOR) return status;
      }
    return T_CTOR;
  }

  // Decimal character escapes need a separator before a following digit.
  // Keep this in the unsafe read/show pair rather than changing curry.show.
  struct TermShowMonitor : ShowMonitor
  {
    bool numeric = false;
    void enter(std::ostream & os, Walk2 const * walk, char context) override
    {
      Cursor cur = walk->cursor();
      if(cur.kind == 'c' && context == 'c')
      {
        auto value = cur.arg->ub_char;
        if(numeric && value >= '0' && value <= '9') os << "\\&";
        numeric = value < 0x20 || value >= 0x7f;
        switch(value)
        {
          case '\a': case '\b': case '\f': case '\n':
          case '\r': case '\t': case '\v': numeric = false;
        }
      }
      else if(!(cur.kind == 'p' && is_char(*cur->info) && context == '`'))
        numeric = false;
    }
    void exit(std::ostream &, Walk2 const *, char) override {}
  };

  tag_type term_observation(RuntimeState * rts, Configuration * C)
  {
    GcClamp clamp;
    std::string operation = C->cursor()->info->name;
    bool ground = true;
    std::unordered_set<Node *> seen;
    index_type offset = operation == "isGround" ? 1 : 0;
    auto tag = inspect_term(rts, C, C->cursor()[offset],
        operation != "showAnyExpression", ground, seen);
    if(tag < T_CTOR) return tag;
    if(operation == "prim_isGround" || operation == "isGround")
      return observed(C, ground ? True : False);
    TermShowMonitor monitor;
    std::ostringstream text;
    show(text, C->cursor()[offset].target, SHOW_STR_SUBST_FREEVARS, &monitor);
    return observed(C, build_curry_string(text.str().c_str()));
  }

  template<class T> int order(T const & a, T const & b)
    { return a < b ? -1 : b < a ? 1 : 0; }

  tag_type compare_terms(RuntimeState * rts, Configuration * C,
      Variable lhs, Variable rhs, int & result)
  {
    auto ltag = rts->hnf_or_free(C, &lhs, &free_in_configuration);
    if(ltag != T_FREE && ltag != T_UNBOXED && ltag < T_CTOR) return ltag;
    auto rtag = rts->hnf_or_free(C, &rhs, &free_in_configuration);
    if(rtag != T_FREE && rtag != T_UNBOXED && rtag < T_CTOR) return rtag;
    if(ltag == T_FREE || rtag == T_FREE)
    {
      result = ltag == rtag
          ? order(C->grp_id(obj_id(lhs.target)), C->grp_id(obj_id(rhs.target)))
          : ltag == T_FREE ? -1 : 1;
      return T_CTOR;
    }
    auto l = lhs.target;
    auto r = rhs.target;
    if(l.kind != 'p' || r.kind != 'p')
    {
      result = order(l.kind, r.kind);
      if(!result) switch(l.kind)
      {
        case 'i': result = order(l.arg->ub_int, r.arg->ub_int); break;
        case 'c': result = order(l.arg->ub_char, r.arg->ub_char); break;
        case 'f': {
          auto a = l.arg->ub_float, b = r.arg->ub_float;
          result = std::isnan(a) ? (std::isnan(b) ? 0 : 1)
              : std::isnan(b) ? -1 : order(a, b);
          break;
        }
        default: result = std::less<void const *>{}(l.arg->blob, r.arg->blob) ? -1
            : std::less<void const *>{}(r.arg->blob, l.arg->blob) ? 1 : 0;
      }
      return T_CTOR;
    }
    bool lp = is_partial(*l->info), rp = is_partial(*r->info);
    result = order(lp ? 0 : 1, rp ? 0 : 1);
    if(result) return T_CTOR;
    if(is_int(*l->info) && is_int(*r->info))
      result = integer_compare(l, r);
    else if(l->info != r->info)
    {
      auto key = [](InfoTable const * info) {
        return owner_of(info) + "." + (info->type ? info->type->name : info->name);
      };
      result = order(key(l->info), key(r->info));
      if(!result) result = order(l->info->tag, r->info->tag);
      if(!result) result = order(std::string(l->info->name), std::string(r->info->name));
    }
    if(result || (is_int(*l->info) && is_int(*r->info))) return T_CTOR;
    if(lp)
    {
      auto a = NodeU{l}.partapplic, b = NodeU{r}.partapplic;
      result = order(owner_of(a->head_info) + "." + a->head_info->name,
                     owner_of(b->head_info) + "." + b->head_info->name);
      if(!result) result = order(a->missing, b->missing);
      if(result) return T_CTOR;
    }
    for(index_type i=lp ? 2 : 0; i<l->info->arity; ++i)
    {
      auto tag = compare_terms(rts, C, lhs[i], rhs[i], result);
      if(tag < T_CTOR || result) return tag;
    }
    return T_CTOR;
  }

  tag_type compare_any(RuntimeState * rts, Configuration * C)
  {
    int result = 0;
    auto tag = compare_terms(rts, C, C->cursor()[0], C->cursor()[1], result);
    if(tag < T_CTOR) return tag;
    return observed(C, Node::create(Module::find_symbol("Prelude",
        result < 0 ? "LT" : result > 0 ? "GT" : "EQ")));
  }

  struct TermReader
  {
    RuntimeState * rts;
    std::vector<std::string> modules;
    std::string text;
    size_t pos = 0;
    std::unordered_map<std::string, Node *> variables;

    void space()
    {
      while(pos < text.size() && std::isspace((unsigned char)text[pos])) ++pos;
    }
    bool take(char c)
    {
      space();
      if(pos < text.size() && text[pos] == c) { ++pos; return true; }
      return false;
    }
    void need(char c)
    {
      if(!take(c)) throw std::invalid_argument("term syntax");
    }
    unboxed_char_type character()
    {
      if(pos == text.size()) throw std::invalid_argument("character");
      char c = text[pos++];
      if(c != '\\')
      {
        --pos;
        char const * p = text.data() + pos;
        auto value = utf8_decode(p, text.data() + text.size());
        pos = p - text.data();
        return value;
      }
      if(pos == text.size()) throw std::invalid_argument("escape");
      c = text[pos++];
      switch(c)
      {
        case 'a': return '\a'; case 'b': return '\b'; case 'f': return '\f';
        case 'n': return '\n'; case 'r': return '\r'; case 't': return '\t';
        case 'v': return '\v'; case '\\': return '\\'; case '\'': return '\''; case '"': return '"';
        default:
          if(c >= '0' && c <= '9')
          {
            unsigned long value = c - '0';
            while(pos < text.size() && std::isdigit((unsigned char)text[pos]))
            {
              value = value * 10 + text[pos++] - '0';
              if(value > 0x10ffff) throw std::invalid_argument("character range");
            }
            return value;
          }
          throw std::invalid_argument("escape");
      }
    }
    Node * constructor(std::string const & name)
    {
      InfoTable const * info = nullptr;
      for(auto const & module: modules)
      {
        info = Module::find_symbol(module, name);
        if(info && info->tag >= T_CTOR) break;
        info = nullptr;
      }
      if(!info) throw std::invalid_argument("constructor");
      std::vector<Arg> args;
      for(index_type i=0; i<info->arity; ++i)
      {
        if(info->format[i] != 'p') throw std::invalid_argument("constructor field");
        args.emplace_back(term(true));
      }
      return Node::create(info, args.data());
    }
    Node * term(bool atom=false)
    {
      space();
      if(pos == text.size()) throw std::invalid_argument("empty term");
      Node * node;
      if(take('['))
      {
        std::vector<Node *> items;
        if(!take(']'))
        {
          do { items.push_back(term()); } while(take(','));
          need(']');
        }
        node = Nil;
        for(auto it=items.rbegin(); it!=items.rend(); ++it) node = cons(*it, node);
      }
      else if(take('('))
      {
        if(take(')')) node = unit();
        else if(pos < text.size() && text[pos] == ':')
        {
          size_t begin = pos;
          while(pos < text.size() && std::strchr("!#$%&*+./<=>?@\\^|~:-", text[pos])) ++pos;
          auto name = text.substr(begin, pos-begin);
          need(')');
          node = constructor(name);
        }
        else
        {
          node = term();
          if(take(','))
          {
            std::vector<Arg> args{node};
            do { args.emplace_back(term()); } while(take(','));
            std::string name = "(" + std::string(args.size()-1, ',') + ")";
            auto info = Module::find_symbol("Prelude", name);
            if(!info) throw std::invalid_argument("tuple");
            node = Node::create(info, args.data());
          }
          need(')');
        }
      }
      else if(take('"'))
      {
        std::vector<unboxed_char_type> chars;
        while(pos < text.size() && text[pos] != '"')
        {
          if(text.compare(pos, 2, "\\&") == 0) pos += 2;
          else chars.push_back(character());
        }
        need('"'); node = Nil;
        for(auto it=chars.rbegin(); it!=chars.rend(); ++it) node = cons(char_(*it), node);
      }
      else if(take('\''))
      {
        auto value = character(); need('\''); node = char_(value);
      }
      else if(text.compare(pos, 9, "-Infinity") == 0)
      {
        pos += 9;
        node = float_(-INFINITY);
      }
      else if(std::isdigit((unsigned char)text[pos]) || text[pos] == '-')
      {
        size_t begin = pos;
        if(text[pos] == '-') ++pos;
        size_t digits = pos;
        while(pos < text.size() && std::isdigit((unsigned char)text[pos])) ++pos;
        if(pos == digits) throw std::invalid_argument("number");
        bool floating = false;
        if(pos < text.size() && text[pos] == '.')
        { floating = true; ++pos; while(pos < text.size() && std::isdigit((unsigned char)text[pos])) ++pos; }
        if(pos < text.size() && (text[pos] == 'e' || text[pos] == 'E'))
        {
          floating = true; ++pos;
          if(pos < text.size() && (text[pos] == '+' || text[pos] == '-')) ++pos;
          digits = pos;
          while(pos < text.size() && std::isdigit((unsigned char)text[pos])) ++pos;
          if(pos == digits) throw std::invalid_argument("exponent");
        }
        auto value = text.substr(begin, pos-begin);
        node = floating ? float_(std::stod(value)) : integer(value.c_str());
      }
      else if(text[pos] == ':')
      {
        size_t begin = pos;
        while(pos < text.size() && std::strchr("!#$%&*+./<=>?@\\^|~:-", text[pos])) ++pos;
        node = constructor(text.substr(begin, pos-begin));
      }
      else
      {
        size_t begin = pos;
        while(pos < text.size() && (std::isalnum((unsigned char)text[pos]) || text[pos]=='_' || text[pos]=='\'')) ++pos;
        if(begin == pos) throw std::invalid_argument("name");
        auto name = text.substr(begin, pos-begin);
        if(name[0] == '_')
        {
          auto & var = variables[name];
          if(!var) var = rts->freshvar();
          node = var;
        }
        else
        {
          if(name == "Infinity") node = float_(INFINITY);
          else if(name == "NaN") node = float_(NAN);
          else node = constructor(name);
        }
      }
      if(!atom)
      {
        size_t end = pos;
        if(take(':')) node = cons(node, term());
        else pos = end;
      }
      return node;
    }
  };

  tag_type read_any(RuntimeState * rts, Configuration * C)
  {
    GcClamp clamp;
    bool ground = true;
    std::unordered_set<Node *> seen;
    for(index_type i=0; i<2; ++i)
    {
      auto tag = inspect_term(rts, C, C->cursor()[i], true, ground, seen);
      if(tag < T_CTOR) return tag;
    }
    if(!ground) throw InstantiationError("term reader needs ground strings");
    TermReader reader{rts, {}, extract_string(C->cursor()[1].target)};
    Node * prefixes = C->cursor()[0].target;
    while(prefixes->info->tag == T_CONS)
    {
      reader.modules.push_back(extract_string(Variable(prefixes, 0).target));
      prefixes = Variable(prefixes, 1).target;
    }
    try
    {
      Node * value = reader.term();
      auto tail = reader.text.substr(reader.pos);
      return finish(C, cons(pair(value, build_curry_string(tail.c_str())), Nil), false);
    }
    catch(std::invalid_argument const &) { return finish(C, Nil, false); }
    catch(std::out_of_range const &) { return finish(C, Nil, false); }
  }

  void primitive(char const * module, char const * name, index_type arity,
                 stepfunc_type step, bool monadic=true)
  {
    // Tables live for the process, just as the static Prelude tables do.
    auto format = new char[arity + 1];
    std::fill_n(format, arity, 'p');
    format[arity] = 0;
    auto info = new InfoTable(T_FUNC, arity,
        sizeof(void *) * std::max<int>(arity + 1, 2),
        F_STATIC_OBJECT | (monadic ? F_MONADIC : 0), name, format, step, nullptr);
    Module::register_primitive(std::string(module) + "." + name, info);
  }

  int register_library()
  {
    for(auto name: {"curryCompiler", "curryCompilerMajorVersion",
        "curryCompilerMinorVersion", "curryCompilerRevisionVersion",
        "curryRuntime", "curryRuntimeMajorVersion", "curryRuntimeMinorVersion",
        "baseVersion", "installDir"})
      primitive("Curry.Compiler.Distribution", name, 0, distribution, false);
    primitive("System.CPUTime", "getCPUTime", 0, cpu_time);
    primitive("System.CPUTime", "getElapsedTime", 0, elapsed_time);
    primitive("System.Environment", "isWindows", 0, windows, false);
    primitive("System.Environment", "prim_getEnviron", 1, environment);
    primitive("System.Environment", "prim_setEnviron", 2, environment);
    primitive("System.Environment", "prim_unsetEnviron", 1, environment);
    Module::register_builtin_module("Data.IORef", {{"IORef", &ref_type}},
        {{"IORef", &ref_info}});
    primitive("Data.IORef", "newIORef", 1, new_ref);
    primitive("Data.IORef", "prim_readIORef", 1, read_ref);
    primitive("Data.IORef", "prim_writeIORef", 2, write_ref);
    // Bypass upstream strict-application wrappers: their normalization can
    // write shared spines before the observation gets its private result.
    // The public Data operations take an unused dictionary first.
    primitive("System.IO.Unsafe", "isVar", 2, variable_test, false);
    primitive("System.IO.Unsafe", "identicalVar", 3, variable_test, false);
    primitive("System.IO.Unsafe", "isGround", 2, term_observation, false);
    primitive("System.IO.Unsafe", "showAnyTerm", 1, term_observation, false);
    primitive("System.IO.Unsafe", "unsafePerformIO", 1, unsafe_io, false);
    primitive("System.IO.Unsafe", "spawnConstraint", 2, spawn_constraint, false);
    primitive("System.IO.Unsafe", "prim_isVar", 1, variable_test, false);
    primitive("System.IO.Unsafe", "prim_identicalVar", 2, variable_test, false);
    primitive("System.IO.Unsafe", "prim_isGround", 1, term_observation, false);
    primitive("System.IO.Unsafe", "prim_showAnyTerm", 1, term_observation, false);
    primitive("System.IO.Unsafe", "showAnyExpression", 1, term_observation, false);
    primitive("System.IO.Unsafe", "compareAnyTerm", 2, compare_any, false);
    primitive("System.IO.Unsafe", "prim_readsAnyUnqualifiedTerm", 2, read_any, false);
    return 0;
  }
  int const registered = register_library();
}

namespace curryrt
{
  bool is_io_ref(InfoTable const * info) { return info == &ref_info; }

  void set_install_prefix(std::string const & prefix) { install_prefix = prefix; }
}
