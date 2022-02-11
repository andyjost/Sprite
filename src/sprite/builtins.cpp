#include "sprite/builtins.hpp"
#include "sprite/graph/node.hpp"

namespace sprite
{
  InfoTable const SetGuard_Info{
      /*tag*/        T_SETGRD
    , /*arity*/      2
    , /*alloc_size*/ sizeof(FwdNode)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "_SetGuard"
    , /*format*/     "xp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &SetGuard_Type
    };

  InfoTable const Fail_Info{
      /*tag*/        T_FAIL
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "failed"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const StrictConstraint_Info{
      /*tag*/        T_CONSTR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(ConstrNode)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "_StrictConstraint"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const NonStrictConstraint_Info{
      /*tag*/        T_CONSTR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(ConstrNode)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "_NonStrictConstraint"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const ValueBinding_Info{
      /*tag*/        T_CONSTR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(ConstrNode)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "_ValueBinding"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const Free_Info{
      /*tag*/        T_FREE
    , /*arity*/      2
    , /*alloc_size*/ sizeof(FreeNode)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "_Free"
    , /*format*/     "ip"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const Fwd_Info{
      /*tag*/        T_FWD
    , /*arity*/      1
    , /*alloc_size*/ sizeof(FwdNode)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "_Fwd"
    , /*format*/     "p"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const Choice_Info{
      /*tag*/        T_CHOICE
    , /*arity*/      3
    , /*alloc_size*/ sizeof(ChoiceNode)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "_Choice"
    , /*format*/     "ipp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const IO_Info{
      /*tag*/        T_CTOR
    , /*arity*/      1
    , /*alloc_size*/ sizeof(IONode)
    , /*typetag*/    IO_TYPE
    , /*flags*/      NO_FLAGS
    , /*name*/       "IO"
    , /*format*/     "i"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &IO_Type
    };


  InfoTable const Int_Info{
      /*tag*/        T_CTOR
    , /*arity*/      1
    , /*alloc_size*/ sizeof(IntNode)
    , /*typetag*/    INT_TYPE
    , /*flags*/      NO_FLAGS
    , /*name*/       "Int"
    , /*format*/     "i"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &Int_Type
    };

  InfoTable const Float_Info{
      /*tag*/        T_CTOR
    , /*arity*/      1
    , /*alloc_size*/ sizeof(FloatNode)
    , /*typetag*/    FLOAT_TYPE
    , /*flags*/      NO_FLAGS
    , /*name*/       "Float"
    , /*format*/     "f"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &Float_Type
    };

  InfoTable const Char_Info{
      /*tag*/        T_CTOR
    , /*arity*/      1
    , /*alloc_size*/ sizeof(CharNode)
    , /*typetag*/    CHAR_TYPE
    , /*flags*/      NO_FLAGS
    , /*name*/       "Char"
    , /*format*/     "c"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &Char_Type
    };

  InfoTable const PartApplic_Info{
      /*tag*/        T_CTOR
    , /*arity*/      3
    , /*alloc_size*/ sizeof(PartApplicNode)
    , /*typetag*/    PARTIAL_TYPE
    , /*flags*/      NO_FLAGS
    , /*name*/       "_PartApplic"
    , /*format*/     "ixp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &PartApplic_Type
    };

  InfoTable const False_Info{
      /*tag*/        T_FALSE
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*typetag*/    BOOL_TYPE
    , /*flags*/      NO_FLAGS
    , /*name*/       "False"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &Bool_Type
    };

  InfoTable const True_Info{
      /*tag*/        T_TRUE
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*typetag*/    BOOL_TYPE
    , /*flags*/      NO_FLAGS
    , /*name*/       "True"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &Bool_Type
    };

  InfoTable const Cons_Info{
      /*tag*/        T_CONS
    , /*arity*/      2
    , /*alloc_size*/ sizeof(ConsNode)
    , /*typetag*/    LIST_TYPE
    , /*flags*/      NO_FLAGS
    , /*name*/       ":"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &List_Type
    };

  InfoTable const Nil_Info{
      /*tag*/        T_NIL
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*typetag*/    LIST_TYPE
    , /*flags*/      NO_FLAGS
    , /*name*/       "[]"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &List_Type
    };

  InfoTable const Unit_Info{
      /*tag*/        T_CTOR
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*typetag*/    TUPLE_TYPE
    , /*flags*/      NO_FLAGS
    , /*name*/       "()"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &Unit_Type
    };

  InfoTable const Pair_Info{
      /*tag*/        T_CTOR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(PairNode)
    , /*typetag*/    TUPLE_TYPE
    , /*flags*/      NO_FLAGS
    , /*name*/       "(,)"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &Pair_Type
    };

  InfoTable const PartialS_Info{
      /*tag*/        T_CTOR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    PARTIAL_TYPE
    , /*flags*/      NO_FLAGS
    , /*name*/       "PartialS"
    , /*format*/     "ip"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &PartialS_Type
    };

  InfoTable const SetEval_Info{
      /*tag*/        T_CTOR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "SetEval"
    , /*format*/     "ip"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &SetEval_Type
    };

  static Node Fail_Node_{&Fail_Info};
  Node * Fail_Node = &Fail_Node_;

  static Node False_Node_{&False_Info};
  Node * False_Node = &False_Node_;

  static Node True_Node_{&True_Info};
  Node * True_Node = &True_Node_;

  static Node Nil_Node_{&Nil_Info};
  Node * Nil_Node = &Nil_Node_;

  static Node Unit_Node_{&Unit_Info};
  Node * Unit_Node = &Unit_Node_;

  static InfoTable const * Bool_Ctors[] = { &False_Info, &True_Info };
  Type const Bool_Type { Bool_Ctors, 2 };

  static InfoTable const * Char_Ctors[] = { &Char_Info };
  Type const Char_Type { Char_Ctors, 1 };

  static InfoTable const * Float_Ctors[] = { &Float_Info };
  Type const Float_Type { Float_Ctors, 1 };

  static InfoTable const * IO_Ctors[] = { &IO_Info };
  Type const IO_Type { IO_Ctors, 1 };

  static InfoTable const * Int_Ctors[] = { &Int_Info };
  Type const Int_Type { Int_Ctors, 1 };

  static InfoTable const * List_Ctors[] = { &Cons_Info, &Nil_Info };
  Type const List_Type { List_Ctors, 2 };

  static InfoTable const * Pair_Ctors[] = { &Pair_Info };
  Type const Pair_Type { Pair_Ctors, 1 };

  static InfoTable const * PartApplic_Ctors[] = { &PartApplic_Info };
  Type const PartApplic_Type { PartApplic_Ctors, 1 };

  static InfoTable const * PartialS_Ctors[] = { &PartialS_Info };
  Type const PartialS_Type { PartialS_Ctors, 1 };

  static InfoTable const * SetEval_Ctors[] = { &SetEval_Info };
  Type const SetEval_Type { SetEval_Ctors, 1 };

  static InfoTable const * SetGuard_Ctors[] = { &SetGuard_Info };
  Type const SetGuard_Type { SetGuard_Ctors, 1 };

  static InfoTable const * Unit_Ctors[] = { &Unit_Info };
  Type const Unit_Type { Unit_Ctors, 1 };

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
    assert(!this->is_encapsulated || !arg);
    return this->is_encapsulated()
        || this->missing - (arg ? 1 : 0) == 0;
  }

  bool PartApplicNode::is_encapsulated() const
    { return this->missing == ENCAPSULATED_EXPR; }

  Node * PartApplicNode::materialize(Node * arg) const
  {
    assert(this->complete(arg));
    return this->is_encapsulated()
      ? this->terms : Node::from_partial(this, arg);
  }
}
