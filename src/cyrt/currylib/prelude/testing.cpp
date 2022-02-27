#include "cyrt/builtins.hpp"
#include "cyrt/currylib/prelude.hpp"
#include "cyrt/state/rts.hpp"

namespace cyrt { inline namespace
{
  tag_type not_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = variable(_0, 0);
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
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "not"
    , /*format*/     "p"
    , /*step*/       &not_step
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };
}
