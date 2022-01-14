#include "sprite/builtins.hpp"
#include "sprite/fairscheme.hpp"
#include "sprite/graph/indexing.hpp"
#include "sprite/inspect.hpp"

namespace sprite
{
  Expr FairSchemeAlgo::eval()
  {
    // static void * procs[] = {&&procD, &&procN};
    Queue * Q = nullptr;
    Configuration * C = nullptr;
    Walk * state = nullptr;
    Cursor * cur;
    tag_type tag = NOTAG;
    // cid_type cid = NOCID;

  // jump:
  //   goto *procs[0];

  procD:
    while(rts->ready())
    {
      Q = &rts->Q();
      C = Q->front();
    redoD:
      tag = inspect::tag_of(C->root);
      switch(tag)
      {
        case T_UNBOXED: return Expr{C->root};
        case T_SETGRD : assert(0); continue;
        case T_FAIL   : rts->drop(); continue;
        case T_CONSTR : assert(0); continue;
        case T_FREE   : assert(0); continue;
        case T_FWD    : C->reset(compress_fwd_chain(C->root)); goto redoD;
        case T_CHOICE : rts->forkD(Q); continue;
        case T_FUNC   : assert(0); continue;
        default       : goto procN;
      }
    }
    return Expr{};

  procN:
    for(state = &C->callstack.state; *state; ++(*state))
    {
      cur = &state->cursor();
    redoN:
      tag = inspect::tag_of(*cur);
      switch(tag)
      {
        case T_UNBOXED: continue;
        case T_SETGRD : assert(0); continue;
        case T_FAIL   : rts->drop(); goto procD;
        case T_CONSTR : assert(0); continue;
        case T_FREE   : assert(0); continue;
        case T_FWD    : *cur = compress_fwd_chain(*cur); goto redoN;
        case T_CHOICE : rts->forkN(Q); goto procD;
        case T_FUNC   : assert(0); continue;
        default:
          if((*cur)->node->info->typetag != PARTIAL_TYPE)
            state->push();
          break;
      }
    }
    return rts->release_value();
  }
}
