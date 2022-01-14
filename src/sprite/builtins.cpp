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
    , /*format*/     "ip"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable const Fail_Info{
      /*tag*/        T_FAIL
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "_Failure"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
    };

  InfoTable const PartApplic_Info{
      /*tag*/        T_CTOR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(PartApplicNode)
    , /*typetag*/    PARTIAL_TYPE
    , /*flags*/      NO_FLAGS
    , /*name*/       "_PartApplic"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
    , /*typedef*/    nullptr
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
}
