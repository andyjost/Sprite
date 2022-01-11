#pragma once
#include "sprite/graph/infotable.hpp"
#include "sprite/fwd.hpp"
// #include "sprite/graph/node.hpp"

namespace sprite
{
  static constexpr tag_type T_CONS  = T_CTOR;
  static constexpr tag_type T_NIL   = T_CTOR + 1;
  static constexpr tag_type T_FALSE = T_CTOR;
  static constexpr tag_type T_TRUE  = T_CTOR + 1;

  extern InfoTable SetGuard_Info;
  extern InfoTable Fail_Info;
  extern InfoTable StrictConstraint_Info;
  extern InfoTable NonStrictConstraint_Info;
  extern InfoTable ValueBinding_Info;
  extern InfoTable Free_Info;
  extern InfoTable Fwd_Info;
  extern InfoTable Choice_Info;
  //
  extern InfoTable Int_Info;
  extern InfoTable Float_Info;
  extern InfoTable Char_Info;
  extern InfoTable PartApplic_Info;
  extern InfoTable False_Info;
  extern InfoTable True_Info;
  extern InfoTable Cons_Info;
  extern InfoTable Nil_Info;
  extern InfoTable Unit_Info;
  extern InfoTable Pair_Info;
  extern InfoTable PartialS_Info;
  extern InfoTable SetEval_Info;

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

  struct SetGrdNode : Head
  {
    sid_type sid;
    Node *   value;
  };

  struct ConstrNode : Head
  {
    Node * value;
    Node * pair;
  };

  struct FreeNode : Head
  {
    cid_type cid;
    Node *   genexpr;
  };

  struct FwdNode : Head
  {
    Node * target;
  };

  struct ChoiceNode : Head
  {
    unboxed_int_type id;
    Node * lhs;
    Node * rhs;
  };
  struct IntNode : Head
  {
    unboxed_int_type value;
  };

  struct FloatNode : Head
  {
    unboxed_float_type value;
  };

  struct CharNode : Head
  {
    unboxed_char_type value;
  };

  struct PartApplicNode : Head
  {
    unboxed_int_type missing;
    Node * term;
  };

  struct ConsNode : Head
  {
    Node * head;
    Node * tail;
  };

  struct PairNode : Head
  {
    Node * lhs;
    Node * rhs;
  };

  struct SetEvalNode : Head
  {
    sid_type sid;
    qid_type qid;
  };

  union NodeU
  {
    Node           * head;
    Node_<1>       * nodeN;
    SetGrdNode     * setgrd;
    ConstrNode     * constr;
    FreeNode       * free;
    FwdNode        * fwd;
    ChoiceNode     * choice;
    IntNode        * int_;
    FloatNode      * float_;
    CharNode       * char_;
    PartApplicNode * partapplic;
    ConsNode       * cons;
    PairNode       * pair;
    SetEvalNode    * seteval;
  };
}
