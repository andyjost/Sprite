#include "sprite/tags.hpp"
#include "sprite/symbols.hpp"
#include "sprite/graph/node.hpp"

namespace sprite
{
  InfoTable FwdInfo{
      /*name*/       "_Fwd"
    , /*arity*/      1
    , /*tag*/        T_FWD
    , /*step*/       nullptr
    , /*show*/       nullptr
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    , /*flags*/      0
    , /*format*/     "p"
    , /*alloc_size*/ sizeof(FwdNode)
    };
}
