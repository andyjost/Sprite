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
    Node * tmp = nullptr;
    tag_type tag = NOTAG;
    StepStatus status = E_OK;

  procD:
    Q = rts->Q();
    while(rts->ready())
    {
      C = Q->front();
    redoD:
      tag = inspect::tag_of(C->root);
      switch(tag)
      {
        case T_UNBOXED: return rts->release_value();
        case T_SETGRD : assert(0); continue;
        case T_FAIL   : rts->drop(); continue;
        case T_CONSTR : if(!rts->constrain_equal(C, C->root))
                          { rts->drop(); continue; }
                        else
                        {
                          *C->root = NodeU{C->root}.constr->value;
                          goto redoD;
                        }
        case T_FREE   : tmp = rts->replace_freevar(C);
                        if(tmp)
                          { *C->root = tmp; goto redoD; }
                        else
                          return rts->release_value();
        case T_FWD    : *C->root = compress_fwd_chain(C->root); goto redoD;
        case T_CHOICE : rts->fork(Q); continue;
        case T_FUNC   : status = rts->S(C, Redex(C->callstack.search));
                        switch(status)
                        {
                          case E_OK      : goto redoD;
                          case E_RESIDUAL: assert(0); goto procD;
                          case E_UNWIND  : assert(0); goto procD;
                          case E_RESTART : assert(0); goto procD;
                          default        : assert(0); __builtin_unreachable();
                        }
        default       : goto procN;
      }
    }
    return Expr{};

  procN:
    for(state = &C->callstack.search; *state; ++(*state))
    {
    redoN:
      tag = inspect::tag_of(state->cursor());
      switch(tag)
      {
        case T_UNBOXED: continue;
        case T_SETGRD : assert(0); continue;
        case T_FAIL   : rts->drop(); goto procD;
        case T_CONSTR : C->reset(rts->lift_constraint(C, C->root, state->cursor()));
                        goto redoD;
        case T_FREE   : tmp = rts->replace_freevar(C);
                        if(tmp) { C->reset(tmp); goto redoD; } else continue;
        case T_FWD    : compress_fwd_chain(state->cursor()); goto redoN;
        case T_CHOICE : C->reset(rts->pull_tab(C, C->root, state->cursor()));
                        goto redoD;
        case T_FUNC   : status = rts->S(C, Redex(C->callstack.search));
                        switch(status)
                        {
                          case E_OK      : goto redoN;
                          case E_RESIDUAL: assert(0); goto procD;
                          case E_UNWIND  : assert(0); goto procD;
                          case E_RESTART : assert(0); goto procD;
                          default        : assert(0); __builtin_unreachable();
                        }
        default:
          if(state->cursor().info()->typetag != PARTIAL_TYPE)
            state->push();
      }
    }
    return rts->release_value();
  }

  StepStatus RuntimeState::S(Configuration * C, Redex const & _0)
  {
    // std::cout << "S <<< " << _0.root()->str() << std::endl;
    auto status = _0.root()->info->step(this, C, &_0);
    // std::cout << "S >>> " << _0.root()->str() << std::endl;
    return status;
  }

  StepStatus RuntimeState::hnf(
      Configuration * C, Variable * inductive, void const * guides
    )
  {
    StepStatus status = E_OK;
    while(true)
    {
      switch(inspect::tag_of(inductive->target()))
      {
        case T_SETGRD : assert(0); continue;
        case T_FAIL   : inductive->root()->make_failure();
                        return E_UNWIND;
        case T_CONSTR : inductive->root()->forward_to(
                            this->lift_constraint(C, inductive)
                          );
                        return E_UNWIND;
        case T_FREE   : status = this->replace_freevar(C, inductive, guides);
                        if(status == E_OK) continue; else return status;
        case T_FWD    : compress_fwd_chain(inductive->target());
                        continue;
        case T_CHOICE : inductive->root()->forward_to(
                            this->pull_tab(C, inductive)
                          );
                        return E_UNWIND;
        case T_FUNC   : status = this->S(C, Redex(*inductive));
                        if(status == E_OK) continue; else return status;
        case T_UNBOXED:
        default       : return E_OK;
      }
    }
  }
}

