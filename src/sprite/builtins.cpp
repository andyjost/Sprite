#include "sprite/tags.hpp"
#include "sprite/builtins.hpp"
#include "sprite/graph/node.hpp"

namespace sprite
{
  InfoTable SetGuard_Info{
      /*name*/       "_SetGuard"
    , /*arity*/      2
    , /*tag*/        T_SETGRD
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      NO_FLAGS
    , /*format*/     "ip"
    , /*alloc_size*/ sizeof(FwdNode)
    };

  InfoTable Fail_Info{
      /*name*/       "_Failure"
    , /*arity*/      0
    , /*tag*/        T_FAIL
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      NO_FLAGS
    , /*format*/     ""
    , /*alloc_size*/ sizeof(Node0)
    };

  InfoTable StrictConstraint_Info{
      /*name*/       "_StrictConstraint"
    , /*arity*/      2
    , /*tag*/        T_CONSTR
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      NO_FLAGS
    , /*format*/     "pp"
    , /*alloc_size*/ sizeof(ConstrNode)
    };

  InfoTable NonStrictConstraint_Info{
      /*name*/       "_NonStrictConstraint"
    , /*arity*/      2
    , /*tag*/        T_CONSTR
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      NO_FLAGS
    , /*format*/     "pp"
    , /*alloc_size*/ sizeof(ConstrNode)
    };

  InfoTable ValueBinding_Info{
      /*name*/       "_ValueBinding"
    , /*arity*/      2
    , /*tag*/        T_CONSTR
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      NO_FLAGS
    , /*format*/     "pp"
    , /*alloc_size*/ sizeof(ConstrNode)
    };

  InfoTable Free_Info{
      /*name*/       "_Free"
    , /*arity*/      2
    , /*tag*/        T_FREE
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      NO_FLAGS
    , /*format*/     "ip"
    , /*alloc_size*/ sizeof(FreeNode)
    };

  InfoTable Fwd_Info{
      /*name*/       "_Fwd"
    , /*arity*/      1
    , /*tag*/        T_FWD
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      NO_FLAGS
    , /*format*/     "p"
    , /*alloc_size*/ sizeof(FwdNode)
    };

  InfoTable Choice_Info{
      /*name*/       "_Choice"
    , /*arity*/      3
    , /*tag*/        T_CHOICE
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      NO_FLAGS
    , /*format*/     "ipp"
    , /*alloc_size*/ sizeof(ChoiceNode)
    };

  InfoTable Int_Info{
      /*name*/       "Int"
    , /*arity*/      1
    , /*tag*/        T_CTOR
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      INT_TYPE
    , /*format*/     "i"
    , /*alloc_size*/ sizeof(IntNode)
    };

  InfoTable Float_Info{
      /*name*/       "Float"
    , /*arity*/      1
    , /*tag*/        T_CTOR
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      FLOAT_TYPE
    , /*format*/     "f"
    , /*alloc_size*/ sizeof(FloatNode)
    };

  InfoTable Char_Info{
      /*name*/       "Char"
    , /*arity*/      1
    , /*tag*/        T_CTOR
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      CHAR_TYPE
    , /*format*/     "f"
    , /*alloc_size*/ sizeof(CharNode)
    };

  InfoTable PartApplic_Info{
      /*name*/       "_PartApplic"
    , /*arity*/      2
    , /*tag*/        T_CTOR
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      PARTIAL_TYPE
    , /*format*/     ""
    , /*alloc_size*/ sizeof(PartApplicNode)
    };

  InfoTable False_Info{
      /*name*/       "False"
    , /*arity*/      0
    , /*tag*/        T_CTOR
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      BOOL_TYPE
    , /*format*/     ""
    , /*alloc_size*/ sizeof(Node0)
    };

  InfoTable True_Info{
      /*name*/       "True"
    , /*arity*/      0
    , /*tag*/        T_CTOR + 1
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      BOOL_TYPE
    , /*format*/     ""
    , /*alloc_size*/ sizeof(Node0)
    };

  InfoTable Cons_Info{
      /*name*/       ":"
    , /*arity*/      2
    , /*tag*/        T_CTOR
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      LIST_TYPE
    , /*format*/     "pp"
    , /*alloc_size*/ sizeof(ConsNode)
    };

  InfoTable Nil_Info{
      /*name*/       "[]"
    , /*arity*/      0
    , /*tag*/        T_CTOR + 1
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      LIST_TYPE
    , /*format*/     ""
    , /*alloc_size*/ sizeof(Node0)
    };

  InfoTable Unit_Info{
      /*name*/       "()"
    , /*arity*/      0
    , /*tag*/        T_CTOR
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      TUPLE_TYPE
    , /*format*/     ""
    , /*alloc_size*/ sizeof(Node0)
    };

  InfoTable Pair_Info{
      /*name*/       "(,)"
    , /*arity*/      2
    , /*tag*/        T_CTOR
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      TUPLE_TYPE
    , /*format*/     "pp"
    , /*alloc_size*/ sizeof(PairNode)
    };

  InfoTable PartialS_Info{
      /*name*/       "PartialS"
    , /*arity*/      2
    , /*tag*/        T_CTOR
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      PARTIAL_TYPE
    , /*format*/     "ip"
    , /*alloc_size*/ sizeof(Node2)
    };

  InfoTable SetEval_Info{
      /*name*/       "SetEval"
    , /*arity*/      2
    , /*tag*/        T_CTOR
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      NO_FLAGS
    , /*format*/     "ip"
    , /*alloc_size*/ sizeof(Node2)
    };

}
