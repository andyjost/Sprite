#include "cyrt/cyrt.hpp"

using namespace cyrt;

static tag_type choice_step(RuntimeState * rts, Configuration * C)
{
  Cursor _0 = C->cursor();
  Node * replacement = choice(rts->istate.xidfactory++, _0->successor(0), _0->successor(1));
  _0->forward_to(replacement);
  return T_FWD;
}

static tag_type failed_step(RuntimeState * rts, Configuration * C)
{
  Cursor _0 = C->cursor();
  return _0->make_failure();
}

extern "C"
{
  InfoTable const choice_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "?"
    , /*format*/     "pp"
    , /*step*/       choice_step
    , /*type*/       nullptr
    };

  InfoTable const failed_Info {
      /*tag*/        T_FUNC
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "failed"
    , /*format*/     ""
    , /*step*/       failed_step
    , /*type*/       nullptr
    };

  #define NAME error
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME notused
  #include "cyrt/currylib/defs/not_used.def"
}
