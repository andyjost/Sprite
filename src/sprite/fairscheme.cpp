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
          status = rts->S(C, &Variable(C->callstack.search));
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
          status = rts->S(C, &Variable(C->callstack.search));
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

  StepStatus RuntimeState::S(Configuration * C, Variable * _0)
  {
    // Node * root = C->cursor()->node;
    std::cout << "S <<< " << _0->root()->str() << std::endl;
    // Variable _0(&C->callstack.search);
    auto status = root->info->step(this, C, _0);
    std::cout << "S >>> " << _0->root()->str() << std::endl;
    return status;
  }

  StepStatus RuntimeState::hnf(
      Configuration * C, Variable * var
    // , Node * root
    // , std::initializer_list<index_type> path
    // , Typedef const * typedef_, void const * values
    )
  {
    StepStatus status = E_OK;
    // Variable inductive(C->callstack.search, root, path);
    // auto const ret = C->callstack.search.size();
    // for(index_type i: path)
    //   C->callstack.search.extend(i);
    while(true)
    {
      // switch(inspect::tag_of(C->cursor()))
       switch(inspect::tag_of(var->target()))
      {
        case T_SETGRD : assert(0); continue;
        case T_FAIL   : var->root()->make_failure();
                        status = E_UNWIND;
                        goto exit;
        case T_CONSTR : assert(0); continue;
        case T_FREE   : assert(0); continue;
        // case T_FWD    : compress_fwd_chain(C->cursor());
        case T_FWD    : compress_fwd_chain(var->target());
                        continue;
        case T_CHOICE : var->root()->forward_to(
                            this->pull_tab(C, var->root())
                          );
                        status = E_UNWIND;
                        goto exit;
        case T_FUNC   : status = this->S(C, &Variable(var);
                        if(status != E_OK) goto exit; else continue;
        case T_UNBOXED:
        default       : status = E_OK; goto exit;
      }
    }
  exit:
    // C->callstack.search.resize(ret);
    return status;
  }
}

