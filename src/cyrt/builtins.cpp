#include "cyrt/builtins.hpp"
#include "cyrt/graph/node.hpp"
#include <cstring>

using namespace cyrt;

extern "C"
{
  InfoTable const SetGuard_Info{
      /*tag*/        T_SETGRD
    , /*arity*/      2
    , /*alloc_size*/ sizeof(FwdNode)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "_SetGuard"
    , /*format*/     "xp"
    , /*step*/       nullptr
    , /*type*/       &SetGuard_Type
    };

  InfoTable const Fail_Info{
      /*tag*/        T_FAIL
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "failed"
    , /*format*/     ""
    , /*step*/       nullptr
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
    , /*format*/     "i"
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

  InfoTable const PartApplic_Info{
      /*tag*/        T_CTOR
    , /*arity*/      3
    , /*alloc_size*/ sizeof(PartApplicNode)
    , /*flags*/      F_PARTIAL_TYPE | F_STATIC_OBJECT
    , /*name*/       "_PartApplic"
    , /*format*/     "ixp"
    , /*step*/       nullptr
    , /*type*/       &PartApplic_Type
    };

  InfoTable const False_Info{
      /*tag*/        T_FALSE
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      F_BOOL_TYPE | F_STATIC_OBJECT
    , /*name*/       "False"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*type*/       &Bool_Type
    };

  InfoTable const True_Info{
      /*tag*/        T_TRUE
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      F_BOOL_TYPE | F_STATIC_OBJECT
    , /*name*/       "True"
    , /*format*/     ""
    , /*step*/       nullptr
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
    , /*flags*/      F_LIST_TYPE | F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "[]"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*type*/       &List_Type
    };

  InfoTable const Unit_Info{
      /*tag*/        T_CTOR
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      F_TUPLE_TYPE | F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "()"
    , /*format*/     ""
    , /*step*/       nullptr
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

  static Node Fail_Node_{&Fail_Info};
  static Node False_Node_{&False_Info};
  static Node True_Node_{&True_Info};
  static Node Nil_Node_{&Nil_Info};
  static Node Unit_Node_{&Unit_Info};

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
    return this->is_encapsulated()
      ? this->terms : Node::from_partial(this, arg);
  }
}
