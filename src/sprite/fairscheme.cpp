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
    Queue * Q         = nullptr;
    Configuration * C = nullptr;
    Search * search   = nullptr;
    Node * tmp        = nullptr;
    tag_type tag      = NOTAG;

  procD:
    Q = rts->Q();
    while(rts->ready())
    {
      C = Q->front();
      tag = inspect::tag_of(C->root);
    redoD:
      switch(tag)
      {
        case T_UNBOXED: return rts->release_value();
        case T_SETGRD : assert(0); continue;
        case T_FAIL   : rts->drop();
                        continue;
        case T_CONSTR : if(!rts->constrain_equal(C, C->root))
                          { rts->drop(); continue; }
                        else
                        {
                          *C->root = NodeU{C->root}.constr->value;
                          tag = inspect::tag_of(C->root);
                          goto redoD;
                        }
        case T_FREE   : tmp = rts->replace_freevar(C);
                        if(tmp)
                        {
                          *C->root = tmp;
                          tag = inspect::tag_of(C->root);
                          goto redoD;
                        }
                        else
                          return rts->release_value();
        case T_FWD    : compress_fwd_chain(C->root);
                        tag = inspect::tag_of(C->root);
                        goto redoD;
        case T_CHOICE : rts->fork(Q, C);
                        continue;
        case T_FUNC   : tag = rts->S(C, Redex(C->search));
                        goto redoD;
        case E_RESTART: tag = inspect::tag_of(C->root);
                        goto redoD;
        case E_RESIDUAL: assert(0); continue;
        default       : goto procN;
      }
    }
    return Expr{};

  procN:
    for(search = &C->search; *search; ++(*search))
    {
      tag = inspect::tag_of(search->cursor());
    redoN:
      switch(tag)
      {
        case T_UNBOXED: continue;
        case T_SETGRD : assert(0); continue;
        case T_FAIL   : rts->drop();
                        goto procD;
        case T_CONSTR : *C->root = rts->lift_constraint(C, C->root, search->cursor());
                        tag = inspect::tag_of(C->root);
                        search->reset();
                        goto redoD;
        case T_FREE   : tmp = rts->replace_freevar(C);
                        if(tmp)
                        {
                          *C->root = tmp;
                          search->reset();
                          tag = inspect::tag_of(tmp);
                          goto redoD;
                        }
                        else
                          continue;
        case T_FWD    : compress_fwd_chain(search->cursor());
                        tag = inspect::tag_of(search->cursor());
                        goto redoN;
        case T_CHOICE : *C->root = rts->pull_tab(C, C->root, search->cursor());
                        search->reset();
                        assert(C->root.info()->tag == T_CHOICE);
                        goto redoD;
        case T_FUNC   : tag = rts->S(C, Redex(C->search));
                        goto redoN;
        case E_RESTART: tag = inspect::tag_of(C->root);
                        goto redoD;
        case E_RESIDUAL: assert(0); continue;
        default:
          if(search->cursor().info()->typetag != PARTIAL_TYPE)
            search->push();
      }
    }
    return rts->release_value();
  }

  step_status RuntimeState::S(Configuration * C, Redex const & _0)
  {
    // std::cout << "S <<< " << _0.root()->str() << std::endl;
    auto status = _0.root()->info->step(this, C, &_0);
    // std::cout << "S >>> " << _0.root()->str() << std::endl;
    return status;
  }

  step_status RuntimeState::hnf(
      Configuration * C, Variable * inductive, void const * guides
    )
  {
    tag_type tag = inspect::tag_of(inductive->target());
    while(true)
    {
      switch(tag)
      {
        case T_SETGRD: assert(0); continue;
        case T_FAIL  : inductive->root()->forward_to(fail());
                       return T_FWD;
        case T_CONSTR: inductive->root()->forward_to(
                           this->lift_constraint(C, inductive)
                         );
                       return T_FWD;
        case T_FREE  : tag = this->replace_freevar(C, inductive, guides);
                       continue;
        case T_FWD   : compress_fwd_chain(inductive->target());
                       tag = inspect::tag_of(inductive->target());
                       this->stepcount++;
                       continue;
        case T_CHOICE: inductive->root()->forward_to(
                           this->pull_tab(C, inductive)
                         );
                       return T_FWD;
        case T_FUNC  : tag = this->S(C, Redex(*inductive));
                       continue;
        default      : return tag;
      }
    }
  }

  step_status RuntimeState::hnf_or_free(
      Configuration * C, Variable * inductive, void const * guides
    )
  {
    tag_type tag = this->hnf(C, inductive, guides);
    if(tag == E_RESIDUAL && inspect::isa_freevar(inductive->target()))
      return T_FREE;
    else
      return tag;
  }
}

