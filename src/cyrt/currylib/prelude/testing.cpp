#include "cyrt/cyrt.hpp"

namespace cyrt { inline namespace
{
  tag_type not_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf(C, &_1, &Bool_Type);
    switch(tag)
    {
      case T_FALSE: _0->forward_to(True);
                    return T_FWD;
      case T_TRUE:  _0->forward_to(False);
                    return T_FWD;
      default: return tag;
    }
  }
}}

namespace cyrt
{
  InfoTable const not_Info{
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "not"
    , /*format*/     "p"
    , /*step*/       &not_step
    , /*typedef*/    nullptr
    };
}
