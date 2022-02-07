#pragma once
#include <cassert>
#include "sprite/graph/infotable.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/fwd.hpp"

namespace sprite
{
  static constexpr tag_type T_CONS  = T_CTOR;
  static constexpr tag_type T_NIL   = T_CTOR + 1;
  static constexpr tag_type T_FALSE = T_CTOR;
  static constexpr tag_type T_TRUE  = T_CTOR + 1;

  extern Node * Fail_Node;
  extern Node * False_Node;
  extern Node * Nil_Node;
  extern Node * True_Node;
  extern Node * Unit_Node;

  extern InfoTable const Char_Info;
  extern InfoTable const Choice_Info;
  extern InfoTable const Cons_Info;
  extern InfoTable const Fail_Info;
  extern InfoTable const False_Info;
  extern InfoTable const Float_Info;
  extern InfoTable const Free_Info;
  extern InfoTable const Fwd_Info;
  extern InfoTable const Int_Info;
  extern InfoTable const Nil_Info;
  extern InfoTable const NonStrictConstraint_Info;
  extern InfoTable const Pair_Info;
  extern InfoTable const PartApplic_Info;
  extern InfoTable const PartialS_Info;
  extern InfoTable const SetEval_Info;
  extern InfoTable const SetGuard_Info;
  extern InfoTable const StrictConstraint_Info;
  extern InfoTable const True_Info;
  extern InfoTable const Unit_Info;
  extern InfoTable const ValueBinding_Info;

  extern Type const Bool_Type;
  extern Type const Char_Type;
  extern Type const Float_Type;
  extern Type const Int_Type;
  extern Type const List_Type;
  extern Type const Pair_Type;
  extern Type const PartApplic_Type;
  extern Type const PartialS_Type;
  extern Type const SetEval_Type;
  extern Type const SetGuard_Type;
  extern Type const Unit_Type;

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
    id_type vid;
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
    id_type cid;
    Node *  lhs;
    Node *  rhs;
    static constexpr InfoTable const * static_info = &Choice_Info;
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
    Node * term;
  };

  struct ConsNode : Head
  {
    Node * head;
    Node * tail;
    static constexpr InfoTable const * static_info = &Cons_Info;
  };

  struct PairNode : Head
  {
    Node * lhs;
    Node * rhs;
    static constexpr InfoTable const * static_info = &Pair_Info;
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

  template<typename NodeType, typename ... Args>
  Node * make_node(Args && ... args)
  {
    auto target = (void *) node_alloc(sizeof(NodeType));
    assert(target);
    new(target) NodeType{NodeType::static_info, std::forward<Args>(args)...};
    return (Node *) target;
  }

  InfoTable const * builtin_info(char);

  inline Node * char_(unboxed_char_type x)   { return make_node<CharNode>(x); }
  inline Node * choice(id_type cid, Node * lhs, Node * rhs)
      { return make_node<ChoiceNode>(cid, lhs, rhs); }
  inline Node * cons(Node * h, Node * t)     { return make_node<ConsNode>(h, t); }
  inline Node * fail()                       { return Fail_Node; }
  inline Node * float_(unboxed_float_type x) { return make_node<FloatNode>(x); }
  inline Node * free(id_type vid)            { return make_node<FreeNode>(vid, Unit_Node); }
  inline Node * fwd(Node * tgt)              { return make_node<FwdNode>(tgt); }
  inline Node * int_(unboxed_int_type x)     { return make_node<IntNode>(x); }
  inline Node * nil()                        { return Nil_Node; }
  inline Node * pair(Node * a, Node * b)     { return make_node<PairNode>(a, b); }
  inline Node * unit()                       { return Unit_Node; }
  inline Node * false_()                     { return False_Node; }
  inline Node * true_()                      { return True_Node; }
}
