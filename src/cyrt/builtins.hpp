#pragma once
#include <cassert>
#include "cyrt/fwd.hpp"
#include "cyrt/graph/infotable.hpp"
#include "cyrt/graph/memory.hpp"
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
  extern InfoTable const Int_Info;
  extern InfoTable const IO_Info;
  extern InfoTable const Nil_Info;
  extern InfoTable const NonStrictConstraint_Info;
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

  struct PartApplicNode : Head
  {
    unboxed_int_type missing;
    InfoTable * head_info;
    Node * terms;

    bool complete(Node * = nullptr) const;
    Node * materialize(Node * = nullptr) const;
    bool is_encapsulated() const;
  };

  struct biStringNode : Head
  {
    char const * data;
    static constexpr InfoTable const * static_info = &_biString_Info;
  };

  struct biGeneratorNode : Head
  {
    void * data; // using void * to avoid adding a dependency on Python.
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
    auto target = (void *) node_alloc(sizeof(NodeType));
    assert(target);
    new(target) NodeType{NodeType::static_info, std::forward<Args>(args)...};
    return (Node *) target;
  }

  InfoTable const * builtin_info(char);
  ConstraintType constraint_type(Node *);
  tag_type not_used(RuntimeState *, Configuration *);
  std::string extract_string(Node *);
  Node * build_curry_string(char const *);
  enum IOErrorKind { IO_ERROR, USER_ERROR, FAIL_ERROR, NONDET_ERROR };
  InfoTable const * ioerror_info(IOErrorKind);
  char const * intern_message(std::string const &);

  // Registers the system functions needed to interact with Python generators.
  void register_generator_funcs(generator_next_type);

  inline Node * char_(unboxed_char_type x)     { return make_node<CharNode>(x); }
  inline Node * choice(xid_type cid, Node * lhs, Node * rhs)
      { return make_node<ChoiceNode>(cid, lhs, rhs); }
  inline Node * cons(Node * h, Node * t)       { return make_node<ConsNode>(h, t); }
  inline Node * fail()                         { return Fail; }
  inline Node * float_(unboxed_float_type x)   { return make_node<FloatNode>(x); }
  inline Node * free(xid_type vid)             { return make_node<FreeNode>(vid, Unit); }
  inline Node * fwd(Node * tgt)                { return make_node<FwdNode>(tgt); }
  inline Node * io(Node * value)               { return make_node<IONode>(value); }
  inline Node * int_(unboxed_int_type x)       { return make_node<IntNode>(x); }
  inline Node * nil()                          { return Nil; }
  inline Node * pair(Node * a, Node * b)       { return make_node<PairNode>(a, b); }
  inline Node * unit()                         { return Unit; }
  inline Node * false_()                       { return False; }
  inline Node * true_()                        { return True; }
  inline Node * cstring(char const * str)      { return make_node<biStringNode>(str); }
  inline Node * generator(void * data)         { return make_node<biGeneratorNode>(data); }
  inline Node * guard(Set * set, Node * value) { return make_node<SetGrdNode>(set, value); }
}
