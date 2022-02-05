#include "sprite/builtins.hpp"
#include "sprite/fairscheme.hpp"
#include "sprite/graph/indexing.hpp"
#include "sprite/graph/variable.hpp"
#include "sprite/inspect.hpp"
#include "sprite/state/rts.hpp"

namespace sprite
{
  Expr eval_next(RuntimeState * rts)
  {
    Queue * Q = nullptr;
    Configuration * C = nullptr;
    Walk * state = nullptr;
    Cursor * cur;
    tag_type tag = NOTAG;
    StepStatus status = E_OK;
    // void * l_ret = nullptr;

  procD:
    Q = rts->Q();
    while(rts->ready())
    {
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
        case T_FUNC   :
          status = rts->S(C, Redex(C->callstack.search));
          switch(status)
          {
            case E_OK      : goto redoD;
            case E_RESIDUAL: assert(0); goto procD;
            case E_UNWIND  : assert(0); goto procD;
            case E_RESTART : assert(0); goto procD;
          }
          break;
        default       : goto procN;
      }
    }
    return Expr{};

  procN:
    for(state = &C->callstack.search; *state; ++(*state))
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
        case T_FWD    : compress_fwd_chain(*cur); goto redoN;
        case T_CHOICE : C->reset(rts->pull_tab(C, C->root));
                        goto procD;
        case T_FUNC   :
          status = rts->S(C, Redex(C->callstack.search));
          switch(status)
          {
            case E_OK      : goto redoN;
            case E_RESIDUAL: assert(0); goto procD;
            case E_UNWIND  : assert(0); goto procD;
            case E_RESTART : assert(0); goto procD;
          }
          break;
        default:
          if(cur->info()->typetag != PARTIAL_TYPE)
            state->push();
      }
    }
    return rts->release_value();

  // procS:
  //   C->callstack.push();
  //   while(C->callstack)
  //   {
  //     status = C->callstack.runframe(rts, C);
  //     switch(status)
  //     {
  //       case E_OK      : C->callstack.exit(); break;
  //       case E_RESIDUAL: assert(0); goto procD;
  //       case E_UNWIND  : assert(0); goto procD;
  //       case E_RESTART : assert(0); goto procD;
  //       case E_CONTINUE: continue;
  //     }
  //   }
  //   goto *l_ret;
  }

  StepStatus RuntimeState::S(Configuration * C, Redex const & redex)
  {
    Redex * _0 = const_cast<Redex *>(&redex);
    std::cout << "S <<< " << _0->root()->str() << std::endl;
    auto status = _0->root()->info->step(this, C, _0);
    std::cout << "S >>> " << _0->root()->str() << std::endl;
    return status;
  }

  StepStatus RuntimeState::hnf(
      Configuration * C, Variable * inductive
    // , Typedef const * typedef_, void const * values
    )
  {
    while(true)
    {
      switch(inspect::tag_of(inductive->target()))
      {
        case T_SETGRD : assert(0); continue;
        case T_FAIL   : inductive->root()->make_failure();
                        return E_UNWIND;
        case T_CONSTR : assert(0); continue;
        case T_FREE   : assert(0); continue;
        case T_FWD    : compress_fwd_chain(inductive->target());
                        continue;
        case T_CHOICE : inductive->root()->forward_to(
                            this->pull_tab(C, inductive->root())
                          );
                        return E_UNWIND;
        case T_FUNC   : switch(this->S(C, Redex(*inductive)))
                        {
                          case E_OK      : continue;
                          case E_RESIDUAL: return E_RESIDUAL;
                          case E_UNWIND  : return E_UNWIND;
                          case E_RESTART : return E_RESTART;
                        }
        case T_UNBOXED:
        default       : return E_OK;
      }
    }
  }
}

