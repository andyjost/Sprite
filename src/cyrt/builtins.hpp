#pragma once
#include <cassert>
#include "cyrt/fwd.hpp"
#include "cyrt/graph/infotable.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/smallvec.hpp"
#include <string>

#define Char_Info                CyI7Prelude4Char
#define Choice_Info              CyI7Prelude5Choice
#define Cons_Info                CyI7Prelude2_C // (:)
#define _biString_Info           CyI7Prelude10__biString
#define _biGenerator_Info        CyI7Prelude13__biGenerator
#define Fail_Info                CyI7Prelude4Fail
#define False_Info               CyI7Prelude5False
#define Float_Info               CyI7Prelude5Float
#define Free_Info                CyI7Prelude4Free
#define Fwd_Info                 CyI7Prelude3Fwd
#define FwdSz_Info               CyI7Prelude5FwdSz
#define Pad_Info                 CyI7Prelude3Pad
#define PadSz_Info               CyI7Prelude5PadSz
#define Int_Info                 CyI7Prelude3Int
#define IO_Info                  CyI7Prelude2IO
#define Nil_Info                 CyI7Prelude4_K_k // []
#define NonStrictConstraint_Info CyI7Prelude19NonStrictConstraint
#define Pair_Info                CyI7Prelude6_Y_m_y // (,)
#define PartApplic_Info          CyI7Prelude10PartApplic
#define SetGuard_Info            CyI7Prelude8SetGuard
#define StrictConstraint_Info    CyI7Prelude16StrictConstraint
#define True_Info                CyI7Prelude4True
#define Unit_Info                CyI7Prelude4_Y_y // ()
#define ValueBinding_Info        CyI7Prelude12ValueBinding

#define Bool_Type           CyD7Prelude4Bool
#define Char_Type           CyD7Prelude4Char
#define CStaticString_Type  CyD7Prelude12StaticString
#define Float_Type          CyD7Prelude5Float
#define IO_Type             CyD7Prelude2IO
#define Int_Type            CyD7Prelude3Int
#define List_Type           CyD7Prelude4_K_k // []
#define Pair_Type           CyD7Prelude6_Y_m_y // (,)
#define PartApplic_Type     CyD7Prelude10PartApplic
#define SetGuard_Type       CyD7Prelude8SetGuard
#define Unit_Type           CyD7Prelude4_Y_y // ()

extern "C"
{
  using namespace cyrt;

  extern InfoTable const Char_Info;
  extern InfoTable const Choice_Info;
  extern InfoTable const Cons_Info;
  extern InfoTable const _biString_Info;
  extern InfoTable const _biGenerator_Info;
  extern InfoTable const Fail_Info;
  extern InfoTable const False_Info;
  extern InfoTable const Float_Info;
  extern InfoTable const Free_Info;
  extern InfoTable const Fwd_Info;
  extern InfoTable const FwdSz_Info;
  extern InfoTable const Int_Info;
  extern InfoTable const IO_Info;
  extern InfoTable const Nil_Info;
  extern InfoTable const NonStrictConstraint_Info;
  extern InfoTable const Pad_Info;
  extern InfoTable const PadSz_Info;
  extern InfoTable const Pair_Info;
  extern InfoTable const PartApplic_Info;
  extern InfoTable const SetGuard_Info;
  extern InfoTable const StrictConstraint_Info;
  extern InfoTable const True_Info;
  extern InfoTable const Unit_Info;
  extern InfoTable const ValueBinding_Info;

  extern DataType const Bool_Type;
  extern DataType const Char_Type;
  extern DataType const CStaticString_Type;
  extern DataType const Float_Type;
  extern DataType const IO_Type;
  extern DataType const Int_Type;
  extern DataType const List_Type;
  extern DataType const Pair_Type;
  extern DataType const PartApplic_Type;
  extern DataType const SetGuard_Type;
  extern DataType const Unit_Type;
}

namespace cyrt
{
  static constexpr unboxed_int_type ENCAPSULATED_EXPR = -1;

  static constexpr tag_type T_CONS  = T_CTOR;
  static constexpr tag_type T_NIL   = T_CTOR + 1;
  static constexpr tag_type T_FALSE = T_CTOR;
  static constexpr tag_type T_TRUE  = T_CTOR + 1;
  static constexpr tag_type T_UNIT  = T_CTOR;

  extern Node * Fail;
  extern Node * False;
  extern Node * Nil;
  extern Node * True;
  extern Node * Unit;

  template<index_type N>
  struct Node_ : Head
  {
    static constexpr index_type Arity = N;
    Arg data[N];
  };

  using Node0 = Head;
  using Node1 = Node_<1>;
  using Node2 = Node_<2>;
  using Node3 = Node_<3>;

  struct PairNode : Head
  {
    Node * lhs;
    Node * rhs;
    static constexpr InfoTable const * static_info = &Pair_Info;
  };

  struct SetGrdNode : Head
  {
    Set  * set;
    Node * value;
    static constexpr InfoTable const * static_info = &SetGuard_Info;
  };

  struct ConstrNode : Head
  {
    Node * value;
    Node * pair;
    Node * lhs() const { return ((PairNode *) this->pair)->lhs; }
    Node * rhs() const { return ((PairNode *) this->pair)->rhs; }
  };

  struct FreeNode : Head
  {
    xid_type vid;
    Node *  genexpr;
    static constexpr InfoTable const * static_info = &Free_Info;
  };

  struct FwdNode : Head
  {
    Node * target;
    static constexpr InfoTable const * static_info = &Fwd_Info;
  };

  struct FwdSzNode : Head
  {
    Node * target;
    size_t bytes;
    static constexpr InfoTable const * static_info = &FwdSz_Info;
  };

  struct ChoiceNode : Head
  {
    xid_type cid;
    Node *  lhs;
    Node *  rhs;
    static constexpr InfoTable const * static_info = &Choice_Info;
  };

  struct IONode : Head
  {
    Node * value;
    static constexpr InfoTable const * static_info = &IO_Info;
  };

  struct IntNode : Head
  {
    unboxed_int_type value;
    static constexpr InfoTable const * static_info = &Int_Info;
  };

  struct FloatNode : Head
  {
    unboxed_float_type value;
    static constexpr InfoTable const * static_info = &Float_Info;
  };

  struct CharNode : Head
  {
    unboxed_char_type value;
    static constexpr InfoTable const * static_info = &Char_Info;
  };

  struct PadNode : Head
  {
    static constexpr InfoTable const * static_info = &Pad_Info;
  };

  struct PadSzNode : Head
  {
    size_t bytes;
    static constexpr InfoTable const * static_info = &PadSz_Info;
  };

  // A partial application: a function or constructor applied to fewer
  // arguments than its arity.  The arguments are inline: slot 0 holds the
  // number of arguments still missing, slot 1 the info table of the head,
  // and the slots after them the arguments supplied, in call order.  So a
  // partial application of n arguments has arity 2 + n and the format "ix"
  // followed by n times 'p', and each n has an info table of its own
  // (partapplic_info below); the collector, the copier, the equality, and
  // show read it by that format like any node.  apply appends an argument
  // in one allocation (Node::extend_partial) and writes the function node
  // of a completed application in one copy (Node::from_partial).  The set
  // functions use the same layout under their own info tables (PartialS;
  // see currylib/setfunctions.hpp): an encapsulated expression has missing
  // == ENCAPSULATED_EXPR, no head, and the expression as its one argument.
  struct PartApplicNode : Head
  {
    unboxed_int_type missing;
    InfoTable const * head_info;
    // The arguments follow.

    index_type nargs() const { return this->info->arity - 2; }
    Node ** args() { return (Node **) (&this->head_info + 1); }
    Node * const * args() const { return (Node * const *) (&this->head_info + 1); }

    bool complete(Node * = nullptr) const;
    Node * materialize(Node * = nullptr) const;
    bool is_encapsulated() const;
  };

  // The info tables of a family of partial applications, one per number of
  // arguments inline: tables[0] is the table without arguments
  // (PartApplic_Info, or PartialS_Info for the set functions), and the table
  // for n arguments has arity 2 + n, the format "ix" with n times 'p', the
  // block for it, and the name, flags, and type of tables[0].  The tables are
  // made on demand and live as long as the process.  The first CACHED are
  // found by an index; the rest by a map (see builtins.cpp).  An object of
  // this type is constant-initialized, so a generated module may use one
  // while the library loads.
  struct PartialInfoFamily
  {
    static constexpr index_type CACHED = 32;
    InfoTable const * tables[CACHED];
    void * storage; // the tables made on demand

    InfoTable const * get(index_type nargs)
    {
      if(nargs < CACHED)
        if(InfoTable const * info = this->tables[nargs])
          return info;
      return this->make(nargs);
    }
    InfoTable const * make(index_type nargs);
  };

  // The family of Prelude._PartApplic.
  extern PartialInfoFamily g_partapplic_infos;
  inline InfoTable const * partapplic_info(index_type nargs)
    { return g_partapplic_infos.get(nargs); }

  struct biStringNode : Head
  {
    char const * data;
    static constexpr InfoTable const * static_info = &_biString_Info;
  };

  // A Python iterator as a lazy Curry list.  ``data`` is a PyObject *, kept
  // as void * so that the runtime does not depend on Python.  A live
  // generator node owns one reference to the object: the bindings take it
  // when they make the node (Node.create), a copy of the node takes one of
  // its own (graph/copy.cpp), the step hands it to the node of the rest of
  // the list or releases it when the iterator is exhausted, and the
  // collector releases it when the node dies before it is stepped (see
  // gc/wdgc.cpp).  See register_generator_funcs.
  struct biGeneratorNode : Head
  {
    void * data;
    static constexpr InfoTable const * static_info = &_biGenerator_Info;
  };

  struct ConsNode : Head
  {
    Node * head;
    Node * tail;
    static constexpr InfoTable const * static_info = &Cons_Info;
  };

  struct SetEvalNode : Head
  {
    Set   * set;
    Queue * queue;
  };

  union NodeU
  {
    Node              * head;
    Node_<1>          * nodeN;
    SetGrdNode        * setgrd;
    ConstrNode        * constr;
    FreeNode          * free;
    FwdNode           * fwd;
    FwdSzNode         * fwdsz;
    PadNode           * pad;
    PadSzNode         * padsz;
    ChoiceNode        * choice;
    biStringNode      * c_str;
    biGeneratorNode   * generator;
    IntNode           * int_;
    FloatNode         * float_;
    CharNode          * char_;
    PartApplicNode    * partapplic;
    ConsNode          * cons;
    PairNode          * pair;
    SetEvalNode       * seteval;
  };

  template<typename NodeType, typename ... Args>
  Node * make_node(Args && ... args)
  {
    Node * target;
    do
    {
      target = node_reserve(sizeof(NodeType));
      assert(target);
      new(target) NodeType{NodeType::static_info, std::forward<Args>(args)...};
    } while(!node_commit(target, sizeof(NodeType)));
    return target;
  }

  InfoTable const * builtin_info(char);
  ConstraintType constraint_type(Node *);
  tag_type not_used(RuntimeState *, Configuration *);
  std::string extract_string(Node *);
  Node * build_curry_string(char const *);
  enum IOErrorKind { IO_ERROR, USER_ERROR, FAIL_ERROR, NONDET_ERROR };
  InfoTable const * ioerror_info(IOErrorKind);
  // The text of the error for a choice in a monadic action.  The Python
  // backend raises NondetMonadError with the same text.
  inline constexpr char NONDET_MONAD_ERROR_TEXT[] =
      "non-determinism in monadic actions occurred!";
  char const * intern_message(std::string const &);

  // Registers the functions that drive a Python iterator (biGeneratorNode):
  // the next item, and the functions that take and release the reference a
  // generator node owns.  Without a registration (a program without Python)
  // generator_acquire and generator_release do nothing.
  void register_generator_funcs(
      generator_next_type, generator_hold_type acquire
    , generator_hold_type release
    );
  void generator_acquire(void * data);
  void generator_release(void * data);

  // The shared nodes of the small values.  The integers from SMALL_INT_MIN to
  // SMALL_INT_MAX and the characters up to SMALL_CHAR_MAX have one node each,
  // made when the library loads and kept for the life of the process (the
  // arena of literal_reserve in graph/memory.hpp).  int_ and char_ return
  // them, so a step that spells such a literal allocates nothing.  One node
  // can serve every occurrence of a value: a node of a primitive value is
  // never written (a rewrite targets a redex, and a forward targets a redex
  // or a free variable; see Node::rewrite and Node::forward_or_copy), the
  // bindings compare primitive values by value (RuntimeState::add_binding),
  // and so does the equality.  The generator spells a literal outside the
  // tables as a node of its module (literal_node; see
  // backends/cxx/compiler.py).
  static constexpr unboxed_int_type SMALL_INT_MIN = -128;
  static constexpr unboxed_int_type SMALL_INT_MAX = 1023;
  static constexpr unboxed_char_type SMALL_CHAR_MAX = 127;
  extern Node * g_small_ints[SMALL_INT_MAX - SMALL_INT_MIN + 1];
  extern Node * g_small_chars[SMALL_CHAR_MAX + 1];

  // A node of a primitive value that lives as long as the process, from the
  // arena of literal_reserve.  The tables above are made of these, and a
  // generated module makes one for each of its other literals when it
  // loads.
  Node * literal_node(InfoTable const *, Arg);

  // A partial application without arguments that lives as long as the
  // process, from the same arena: ``missing`` is the arity of ``head``.  A
  // generated module makes one for each function or constructor it uses as
  // a value (f in map f xs) when it loads, so a step that spells one
  // allocates nothing.  Such a node is never written: a partial application
  // is a constructor, so it is never a redex, and it has no node successor,
  // so the collector need not look below it.  The missing count is passed
  // in, because the info table of a head defined in the same module may not
  // be initialized yet when the module's static objects are made.
  Node * partial_node(InfoTable const * head, unboxed_int_type missing);

  inline Node * char_(unboxed_char_type x)
  {
    if(x <= SMALL_CHAR_MAX)
    {
      assert(g_small_chars[x]);
      return g_small_chars[x];
    }
    return make_node<CharNode>(x);
  }
  inline Node * choice(xid_type cid, Node * lhs, Node * rhs)
      { return make_node<ChoiceNode>(cid, lhs, rhs); }
  inline Node * cons(Node * h, Node * t)       { return make_node<ConsNode>(h, t); }
  inline Node * fail()                         { return Fail; }
  inline Node * float_(unboxed_float_type x)   { return make_node<FloatNode>(x); }
  inline Node * free(xid_type vid)             { return make_node<FreeNode>(vid, Unit); }
  inline Node * fwd(Node * tgt)                { return make_node<FwdNode>(tgt); }
  inline Node * io(Node * value)               { return make_node<IONode>(value); }
  inline Node * int_(unboxed_int_type x)
  {
    if(SMALL_INT_MIN <= x && x <= SMALL_INT_MAX)
    {
      assert(g_small_ints[x - SMALL_INT_MIN]);
      return g_small_ints[x - SMALL_INT_MIN];
    }
    return make_node<IntNode>(x);
  }
  inline Node * nil()                          { return Nil; }
  inline Node * pair(Node * a, Node * b)       { return make_node<PairNode>(a, b); }
  inline Node * unit()                         { return Unit; }
  inline Node * false_()                       { return False; }
  inline Node * true_()                        { return True; }
  inline Node * cstring(char const * str)      { return make_node<biStringNode>(str); }
  // A generator node is registered with the collector, which releases its
  // iterator when the node dies unstepped (see gc/wdgc.cpp).
  inline Node * generator(void * data)
  {
    Node * node = make_node<biGeneratorNode>(data);
    gc_register_generator(node);
    return node;
  }
  inline Node * guard(Set * set, Node * value) { return make_node<SetGrdNode>(set, value); }
  // Puts the pointer successors [begin, end) of ``node`` under ``guards``,
  // the guards a variable crossed; see builtins.cpp.
  void guard_successors(
      Node * node, index_type begin, index_type end, GuardList const & guards
    );
}
