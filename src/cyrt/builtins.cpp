#include <cassert>
#include <cstring>
#include "cyrt/builtins.hpp"
#include "cyrt/dynload.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/inspect.hpp"
#include "cyrt/module.hpp"
#include "cyrt/utf8.hpp"
#include <deque>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>

using namespace cyrt;

extern "C"
{
  extern Node Fail_Node_;
  extern Node False_Node_;
  extern Node True_Node_;
  extern Node Nil_Node_;
  extern Node Unit_Node_;

  InfoTable const SetGuard_Info{
      /*tag*/        T_SETGRD
    , /*arity*/      2
    , /*alloc_size*/ sizeof(SetGrdNode)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "_SetGuard"
    , /*format*/     "xp"
    , /*step*/       nullptr
    , /*type*/       nullptr
    };

  InfoTable const Fail_Info{
      /*tag*/        T_FAIL
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      F_STATIC_OBJECT | F_PINNED
    , /*name*/       "failed"
    , /*format*/     ""
    , /*step*/       (stepfunc_type) &Fail_Node_
    , /*type*/       nullptr
    };

  InfoTable const StrictConstraint_Info{
      /*tag*/        T_CONSTR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(ConstrNode)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "_StrictConstraint"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*type*/       nullptr
    };

  InfoTable const NonStrictConstraint_Info{
      /*tag*/        T_CONSTR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(ConstrNode)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "_NonStrictConstraint"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*type*/       nullptr
    };

  InfoTable const ValueBinding_Info{
      /*tag*/        T_CONSTR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(ConstrNode)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "_ValueBinding"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*type*/       nullptr
    };

  InfoTable const Free_Info{
      /*tag*/        T_FREE
    , /*arity*/      2
    , /*alloc_size*/ sizeof(FreeNode)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "_Free"
    , /*format*/     "ip"
    , /*step*/       nullptr
    , /*type*/       nullptr
    };

  InfoTable const Fwd_Info{
      /*tag*/        T_FWD
    , /*arity*/      1
    , /*alloc_size*/ sizeof(FwdNode)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "_Fwd"
    , /*format*/     "p"
    , /*step*/       nullptr
    , /*type*/       nullptr
    };

  InfoTable const FwdSz_Info{
      /*tag*/        T_FWD
    , /*arity*/      2
    , /*alloc_size*/ sizeof(FwdSzNode)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "_FwdSz"
    , /*format*/     "pi"
    , /*step*/       nullptr
    , /*type*/       nullptr
    };

  InfoTable const Pad_Info{
      /*tag*/        T_PAD
    , /*arity*/      0
    , /*alloc_size*/ sizeof(PadNode)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "_Pad"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*type*/       nullptr
    };

  InfoTable const PadSz_Info{
      /*tag*/        T_PAD
    , /*arity*/      1
    , /*alloc_size*/ sizeof(PadSzNode)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "_PadSz"
    , /*format*/     "i"
    , /*step*/       nullptr
    , /*type*/       nullptr
    };

  InfoTable const Choice_Info{
      /*tag*/        T_CHOICE
    , /*arity*/      3
    , /*alloc_size*/ sizeof(ChoiceNode)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "_Choice"
    , /*format*/     "ipp"
    , /*step*/       nullptr
    , /*type*/       nullptr
    };

  InfoTable const IO_Info{
      /*tag*/        T_CTOR
    , /*arity*/      1
    , /*alloc_size*/ sizeof(IONode)
    , /*flags*/      F_IO_TYPE | F_STATIC_OBJECT
    , /*name*/       "IO"
    , /*format*/     "p"
    , /*step*/       nullptr
    , /*type*/       &IO_Type
    };


  InfoTable const Int_Info{
      /*tag*/        T_CTOR
    , /*arity*/      1
    , /*alloc_size*/ sizeof(IntNode)
    , /*flags*/      F_INT_TYPE | F_STATIC_OBJECT
    , /*name*/       "Int"
    , /*format*/     "i"
    , /*step*/       nullptr
    , /*type*/       &Int_Type
    };

  InfoTable const Float_Info{
      /*tag*/        T_CTOR
    , /*arity*/      1
    , /*alloc_size*/ sizeof(FloatNode)
    , /*flags*/      F_FLOAT_TYPE | F_STATIC_OBJECT
    , /*name*/       "Float"
    , /*format*/     "f"
    , /*step*/       nullptr
    , /*type*/       &Float_Type
    };

  InfoTable const Char_Info{
      /*tag*/        T_CTOR
    , /*arity*/      1
    , /*alloc_size*/ sizeof(CharNode)
    , /*flags*/      F_CHAR_TYPE | F_STATIC_OBJECT
    , /*name*/       "Char"
    , /*format*/     "c"
    , /*step*/       nullptr
    , /*type*/       &Char_Type
    };

  // The partial application without arguments.  The tables for one or more
  // arguments come from g_partapplic_infos (see builtins.hpp).
  InfoTable const PartApplic_Info{
      /*tag*/        T_CTOR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(PartApplicNode)
    , /*flags*/      F_PARTIAL_TYPE | F_STATIC_OBJECT
    , /*name*/       "_PartApplic"
    , /*format*/     "ix"
    , /*step*/       nullptr
    , /*type*/       &PartApplic_Type
    };

  InfoTable const False_Info{
      /*tag*/        T_FALSE
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      F_BOOL_TYPE | F_STATIC_OBJECT | F_PINNED
    , /*name*/       "False"
    , /*format*/     ""
    , /*step*/       (stepfunc_type) &False_Node_
    , /*type*/       &Bool_Type
    };

  InfoTable const True_Info{
      /*tag*/        T_TRUE
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      F_BOOL_TYPE | F_STATIC_OBJECT | F_PINNED
    , /*name*/       "True"
    , /*format*/     ""
    , /*step*/       (stepfunc_type) &True_Node_
    , /*type*/       &Bool_Type
    };

  InfoTable const Cons_Info{
      /*tag*/        T_CONS
    , /*arity*/      2
    , /*alloc_size*/ sizeof(ConsNode)
    , /*flags*/      F_LIST_TYPE | F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       ":"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*type*/       &List_Type
    };

  InfoTable const Nil_Info{
      /*tag*/        T_NIL
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      F_LIST_TYPE | F_OPERATOR | F_STATIC_OBJECT | F_PINNED
    , /*name*/       "[]"
    , /*format*/     ""
    , /*step*/       (stepfunc_type) &Nil_Node_
    , /*type*/       &List_Type
    };

  InfoTable const Unit_Info{
      /*tag*/        T_CTOR
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      F_TUPLE_TYPE | F_OPERATOR | F_STATIC_OBJECT | F_PINNED
    , /*name*/       "()"
    , /*format*/     ""
    , /*step*/       (stepfunc_type) &Unit_Node_
    , /*type*/       &Unit_Type
    };

  InfoTable const Pair_Info{
      /*tag*/        T_CTOR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(PairNode)
    , /*flags*/      F_TUPLE_TYPE | F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "(,)"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*type*/       &Pair_Type
    };

  Node Fail_Node_{&Fail_Info};
  Node False_Node_{&False_Info};
  Node True_Node_{&True_Info};
  Node Nil_Node_{&Nil_Info};
  Node Unit_Node_{&Unit_Info};

  static InfoTable const * Bool_Ctors[] = { &False_Info, &True_Info };
  DataType const Bool_Type { Bool_Ctors, 2, 't', F_STATIC_OBJECT, "Bool" };

  static InfoTable const * Char_Ctors[] = { &Char_Info };
  DataType const Char_Type { Char_Ctors, 1, 't', F_STATIC_OBJECT, "Char" };

  static InfoTable const * Float_Ctors[] = { &Float_Info };
  DataType const Float_Type { Float_Ctors, 1, 't', F_STATIC_OBJECT, "Float" };

  static InfoTable const * IO_Ctors[] = { &IO_Info };
  DataType const IO_Type { IO_Ctors, 1, 't', F_STATIC_OBJECT, "IO" };

  static InfoTable const * Int_Ctors[] = { &Int_Info };
  DataType const Int_Type { Int_Ctors, 1, 't', F_STATIC_OBJECT, "Int" };

  static InfoTable const * List_Ctors[] = { &Cons_Info, &Nil_Info };
  DataType const List_Type { List_Ctors, 2, 't', F_STATIC_OBJECT, "[]" };

  static InfoTable const * Pair_Ctors[] = { &Pair_Info };
  DataType const Pair_Type { Pair_Ctors, 1, 't', F_STATIC_OBJECT, "(,)" };

  static InfoTable const * PartApplic_Ctors[] = { &PartApplic_Info };
  DataType const PartApplic_Type { PartApplic_Ctors, 1, 't', F_STATIC_OBJECT, "PartApplic" };

  static InfoTable const * SetGuard_Ctors[] = { &SetGuard_Info };
  DataType const SetGuard_Type { SetGuard_Ctors, 1, 't', F_STATIC_OBJECT, "SetGuard" };

  static InfoTable const * Unit_Ctors[] = { &Unit_Info };
  DataType const Unit_Type { Unit_Ctors, 1, 't', F_STATIC_OBJECT, "()" };
}

namespace cyrt
{
  Node * Fail = &Fail_Node_;
  Node * False = &False_Node_;
  Node * True = &True_Node_;
  Node * Nil = &Nil_Node_;
  Node * Unit = &Unit_Node_;

  Node * g_small_ints[SMALL_INT_MAX - SMALL_INT_MIN + 1];
  Node * g_small_chars[SMALL_CHAR_MAX + 1];

  Node * literal_node(InfoTable const * info, Arg value)
  {
    assert(is_primitive(*info));
    Node * node = literal_reserve(info->alloc_size);
    RawNodeMemory mem{node};
    *mem.info++ = info;
    pack(mem, info->format, &value);
    return node;
  }

  Node * partial_node(InfoTable const * head, unboxed_int_type missing)
  {
    assert(head);
    assert(missing > 0);
    Node * node = literal_reserve(PartApplic_Info.alloc_size);
    RawNodeMemory mem{node};
    *mem.info++ = &PartApplic_Info;
    *mem.ub_int++ = missing;
    *mem.ub_ptr++ = (void *) head;
    return node;
  }

  // Fills the tables when the library loads.  The info tables above are
  // initialized first (same translation unit), and the arena needs no
  // initialization (see graph/memory.cpp).
  static struct _LiteralTables
  {
    _LiteralTables()
    {
      for(unboxed_int_type i=SMALL_INT_MIN; i<=SMALL_INT_MAX; ++i)
        g_small_ints[i - SMALL_INT_MIN] = literal_node(&Int_Info, Arg(i));
      for(unboxed_char_type c=0; c<=SMALL_CHAR_MAX; ++c)
        g_small_chars[c] = literal_node(&Char_Info, Arg(c));
    }
  } _literal_tables;

  InfoTable const * builtin_info(char kind)
  {
    switch(kind)
    {
      case 'i': return &Int_Info;
      case 'f': return &Float_Info;
      case 'c': return &Char_Info;
      default: assert(0); __builtin_unreachable();
    }
  }

  ConstraintType constraint_type(Node * constraint)
  {
    if(constraint->info == &StrictConstraint_Info)
      return STRICT_CONSTRAINT;
    else if(constraint->info == &NonStrictConstraint_Info)
      return NONSTRICT_CONSTRAINT;
    else
    {
      assert(constraint->info == &ValueBinding_Info);
      return VALUE_BINDING;
    }
  }

  bool PartApplicNode::complete(Node * arg) const
  {
    assert(!this->is_encapsulated() || !arg);
    return this->is_encapsulated()
        || this->missing - (arg ? 1 : 0) == 0;
  }

  bool PartApplicNode::is_encapsulated() const
    { return this->missing == ENCAPSULATED_EXPR; }

  Node * PartApplicNode::materialize(Node * arg) const
  {
    assert(this->complete(arg));
    if(this->is_encapsulated())
    {
      assert(this->nargs() == 1);
      return this->args()[0];
    }
    return Node::from_partial(this, arg);
  }

  // The box rule of the dissertation (chapter 4) for a partial application
  // reached through set guards: a reference to a boxed expression is boxed.
  // The step that applies a partial application (apply) or boxes one (set,
  // applyS) copies its arguments out of it, so each argument goes under the
  // guards crossed on the way to the application, nested as
  // Variable::guarded_rvalue nests them.  Nothing happens for a variable
  // that crossed no guard.  A guard without a set, the box of an argument
  // of a PartialS (set_step, applyS_step), stays outermost: evalS_step
  // gives the new set to the direct successors of its goal alone.  The
  // crossed guards go on the value inside that box.  The successor array
  // is addressed through the node after each guard is made.
  void guard_successors(
      Node * node, index_type begin, index_type end, GuardList const & guards
    )
  {
    if(guards.empty())
      return;
    gc_count_write(node);
    for(index_type i=begin; i<end; ++i)
    {
      if(node->info->format[i] != 'p')
        continue;
      Node * value = node->successors()[i].node;
      bool const boxed = inspect::info_of(value) == &SetGuard_Info
          && !inspect::get_set(value);
      if(boxed)
        value = inspect::get_setguard_value(value);
      for(Set * set: guards)
        value = guard(set, value);
      if(boxed)
        value = guard(nullptr, value);
      node->successors()[i] = Arg(value);
    }
  }

  PartialInfoFamily g_partapplic_infos{{&PartApplic_Info}, nullptr};

  namespace
  {
    // The tables a family makes on demand.  A deque keeps the addresses of
    // its elements, and the tables point into the formats.  The storage is
    // never freed: a generated module may refer to a table for as long as
    // the process runs.
    struct PartialInfoStorage
    {
      std::deque<InfoTable> tables;
      std::deque<std::string> formats;
      std::unordered_map<index_type, InfoTable const *> large;
    };
  }

  InfoTable const * PartialInfoFamily::make(index_type nargs)
  {
    InfoTable const * base = this->tables[0];
    assert(base);
    assert(base->arity == 2);
    auto * store = (PartialInfoStorage *) this->storage;
    if(!store)
    {
      store = new PartialInfoStorage;
      this->storage = store;
    }
    if(nargs >= CACHED)
    {
      auto p = store->large.find(nargs);
      if(p != store->large.end())
        return p->second;
    }
    size_t const arity = size_t(nargs) + 2;
    size_t const alloc_size = sizeof(Head) + arity * sizeof(Arg);
    if(alloc_size > std::numeric_limits<index_type>::max())
      throw std::length_error("too many arguments in a partial application");
    std::string & format = store->formats.emplace_back("ix");
    format.append(nargs, 'p');
    InfoTable const & info = store->tables.emplace_back(
        base->tag, (index_type) arity, (index_type) alloc_size, base->flags
      , base->name, format.c_str(), base->step, base->type
      );
    if(nargs < CACHED)
      this->tables[nargs] = &info;
    else
      store->large[nargs] = &info;
    return &info;
  }

  // The constructors of IOError are defined in Curry, so their tables come
  // from the loaded Prelude: the compiled library, or the tables made at
  // run time when the Prelude is interpreted (see Module::find_symbol).
  InfoTable const * ioerror_info(IOErrorKind kind)
  {
    assert(((int) kind) >=0 && ((int) kind) < 4);
    static char const * symbol_names[] = {
        "IOError", "UserError", "FailError", "NondetError"
      };
    InfoTable const * info = Module::find_symbol("Prelude", symbol_names[kind]);
    if(!info)
      throw std::logic_error(
          std::string("the Prelude is not loaded: no constructor ")
          + symbol_names[kind]
        );
    return info;
  }

  char const * intern_message(std::string const & msg)
  {
    static std::string saved;
    saved = msg;
    return saved.c_str();
  }

  // The UTF-8 text of a ground string.
  std::string extract_string(Node * str)
  {
    assert(str);
    if(typetag(*str->info) == F_CSTRING_TYPE)
      return NodeU{str}.c_str->data;
    // A normal form may hold forward nodes left by a rewrite in place;
    // follow them, as Node::successor_node does.
    auto const target = [](Node * node)
    {
      while(node->info->tag == T_FWD)
        node = NodeU{node}.fwd->target;
      return node;
    };
    std::string out;
    while(true)
    {
      str = target(str);
      switch(str->info->tag)
      {
        case T_CONS: utf8_encode(
                         out, NodeU{target(NodeU{str}.cons->head)}.char_->value
                       );
                     str = NodeU{str}.cons->tail;
                     break;
        case T_NIL:  return out;
        default:
          throw std::invalid_argument(
              std::string("bad Curry string: node ") + str->info->name
            + " (tag " + std::to_string(str->info->tag) + ")"
            );
      }
    }
  }

  // A Curry string with one Char per code point of the UTF-8 text.
  Node * build_curry_string(char const * str)
  {
    Node * head = nil();
    Node ** tail = &head;
    char const * end = str + std::strlen(str);
    while(str != end)
    {
      *tail = cons(char_(utf8_decode(str, end)), nil());
      tail = &NodeU{*tail}.cons->tail;
    }
    return head;
  }
}
