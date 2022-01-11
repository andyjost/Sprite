#include "sprite/tags.hpp"
#include "sprite/builtins.hpp"
#include "sprite/graph/node.hpp"

namespace sprite
{
  InfoTable SetGuard_Info{
      /*tag*/        T_SETGRD
    , /*arity*/      2
    , /*alloc_size*/ sizeof(FwdNode)
    , /*flags*/      NO_FLAGS
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "_SetGuard"
    , /*format*/     "ip"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable Fail_Info{
      /*tag*/        T_FAIL
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      NO_FLAGS
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "_Failure"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable StrictConstraint_Info{
      /*tag*/        T_CONSTR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(ConstrNode)
    , /*flags*/      NO_FLAGS
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "_StrictConstraint"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable NonStrictConstraint_Info{
      /*tag*/        T_CONSTR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(ConstrNode)
    , /*flags*/      NO_FLAGS
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "_NonStrictConstraint"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable ValueBinding_Info{
      /*tag*/        T_CONSTR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(ConstrNode)
    , /*flags*/      NO_FLAGS
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "_ValueBinding"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable Free_Info{
      /*tag*/        T_FREE
    , /*arity*/      2
    , /*alloc_size*/ sizeof(FreeNode)
    , /*flags*/      NO_FLAGS
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "_Free"
    , /*format*/     "ip"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable Fwd_Info{
      /*tag*/        T_FWD
    , /*arity*/      1
    , /*alloc_size*/ sizeof(FwdNode)
    , /*flags*/      NO_FLAGS
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "_Fwd"
    , /*format*/     "p"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable Choice_Info{
      /*tag*/        T_CHOICE
    , /*arity*/      3
    , /*alloc_size*/ sizeof(ChoiceNode)
    , /*flags*/      NO_FLAGS
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "_Choice"
    , /*format*/     "ipp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable Int_Info{
      /*tag*/        T_CTOR
    , /*arity*/      1
    , /*alloc_size*/ sizeof(IntNode)
    , /*flags*/      INT_TYPE
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "Int"
    , /*format*/     "i"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable Float_Info{
      /*tag*/        T_CTOR
    , /*arity*/      1
    , /*alloc_size*/ sizeof(FloatNode)
    , /*flags*/      FLOAT_TYPE
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "Float"
    , /*format*/     "f"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable Char_Info{
      /*tag*/        T_CTOR
    , /*arity*/      1
    , /*alloc_size*/ sizeof(CharNode)
    , /*flags*/      CHAR_TYPE
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "Char"
    , /*format*/     "c"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable PartApplic_Info{
      /*tag*/        T_CTOR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(PartApplicNode)
    , /*flags*/      PARTIAL_TYPE
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "_PartApplic"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable False_Info{
      /*tag*/        T_FALSE
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      BOOL_TYPE
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "False"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable True_Info{
      /*tag*/        T_TRUE
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      BOOL_TYPE
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "True"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable Cons_Info{
      /*tag*/        T_CONS
    , /*arity*/      2
    , /*alloc_size*/ sizeof(ConsNode)
    , /*flags*/      LIST_TYPE
    , /*bitflags*/   NO_FLAGS
    , /*name*/       ":"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable Nil_Info{
      /*tag*/        T_NIL
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      LIST_TYPE
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "[]"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable Unit_Info{
      /*tag*/        T_CTOR
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      TUPLE_TYPE
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "()"
    , /*format*/     ""
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable Pair_Info{
      /*tag*/        T_CTOR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(PairNode)
    , /*flags*/      TUPLE_TYPE
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "(,)"
    , /*format*/     "pp"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable PartialS_Info{
      /*tag*/        T_CTOR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      PARTIAL_TYPE
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "PartialS"
    , /*format*/     "ip"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  InfoTable SetEval_Info{
      /*tag*/        T_CTOR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      NO_FLAGS
    , /*bitflags*/   NO_FLAGS
    , /*name*/       "SetEval"
    , /*format*/     "ip"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };
}
