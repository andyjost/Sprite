#include "sprite/fairscheme.hpp"
#include "sprite/inspect.hpp"

namespace sprite
{
  Expr FairSchemeAlgo::eval()
  {
    static void * procs[] = {&&procD, &&procN};
  entry:
    goto *procs[0];
    
  procD:
    while(rts->ready())
    {
      auto tag = inspect::tag_of(rts->E());
      switch(tag)
      {
        case T_SETGRD: assert(0); continue;
        case T_FAIL  : rts->drop(); continue;
        case T_CONSTR: assert(0); continue;
        case T_FREE  : assert(0); continue;
        case T_FWD   : assert(0); continue;
        case T_CHOICE: assert(0); continue;
        case T_FUNC  : assert(0); continue;
        default:
          break;
      }
    }
    return Expr();

  procN:
  }
}
