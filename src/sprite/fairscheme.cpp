#include "sprite/builtins.hpp"
#include "sprite/fairscheme.hpp"
#include "sprite/graph/indexing.hpp"
#include "sprite/graph/variable.hpp"
#include "sprite/inspect.hpp"
#include "sprite/state/rts.hpp"

namespace sprite
{
  Expr RuntimeState::procD()
  {
    Queue * Q         = nullptr;
    Configuration * C = nullptr;
    Node * tmp        = nullptr;
    tag_type tag      = NOTAG;

    while(this->ready())
    {
      Q = this->Q();
      C = Q->front();
      tag = inspect::tag_of(C->root);
    redoD:
      switch(tag)
      {
        case T_UNBOXED : return this->release_value();
        case T_SETGRD  : assert(0); continue;
        case T_FAIL    : this->drop();
                         continue;
        case T_CONSTR  : if(!this->constrain_equal(C, C->root))
                           { this->drop(); continue; }
                         else
                         {
                           *C->root = NodeU{C->root}.constr->value;
                           tag = inspect::tag_of(C->root);
                           goto redoD;
                         }
        case T_FREE    : tmp = this->replace_freevar(C);
                         if(tmp)
                         {
                           *C->root = tmp;
                           tag = inspect::tag_of(C->root);
                           goto redoD;
                         }
                         else
                           return this->release_value();
        case T_FWD     : compress_fwd_chain(C->root);
                         tag = inspect::tag_of(C->root);
                         goto redoD;
        case T_CHOICE  : this->fork(Q, C);
                         continue;
        case T_FUNC    : tag = this->procS(C);
                         goto redoD;
        case E_RESTART : tag = inspect::tag_of(C->root);
                         goto redoD;
        case E_RESIDUAL: assert(0); continue;
        default        : switch(this->procN(C, tag))
                         {
                           case N_YIELD: return this->release_value();
                           case N_REDO:  goto redoD;
                         }
      }
    }
    return Expr{};
  }

  NStatus RuntimeState::procN(Configuration * C, tag_type & tag)
  {
    Node * tmp = nullptr;
    size_t ret = 0;
    for(Search * search = &C->search; *search; ++(*search))
    {
      tag = inspect::tag_of(search->cursor());
    redoN:
      switch(tag)
      {
        case T_UNBOXED : continue;
        case T_SETGRD  : assert(0); continue;
        case T_FAIL    : tag = C->root->node->make_failure();
                         return N_REDO;
        case T_CONSTR  : *C->root = this->lift_constraint(C, C->root, search->cursor());
                         tag = inspect::tag_of(C->root);
                         search->reset();
                         return N_REDO;
        case T_FREE    : tmp = this->replace_freevar(C);
                         if(tmp)
                         {
                           *C->root = tmp;
                           search->reset();
                           tag = inspect::tag_of(tmp);
                           return N_REDO;
                         }
                         else
                           continue;
        case T_FWD     : compress_fwd_chain(search->cursor());
                         tag = inspect::tag_of(search->cursor());
                         goto redoN;
        case T_CHOICE  : *C->root = this->pull_tab(C, C->root, search->cursor());
                         search->reset();
                         assert(C->root.info()->tag == T_CHOICE);
                         return N_REDO;
        case T_FUNC    : ret = search->size();
                         tag = this->procS(C);
                         search->resize(ret);
                         goto redoN;
        case E_RESTART : tag = inspect::tag_of(C->root);
                        return N_REDO;
        case E_RESIDUAL: assert(0); continue;
        default        :
          if(search->cursor().info()->typetag != PARTIAL_TYPE)
            search->push();
      }
    }
    return N_YIELD;
  }

  SStatus RuntimeState::procS(Configuration * C)
  {
    Cursor _0 = C->cursor();
    std::cout << "S <<< " << _0->node->str() << std::endl;
    auto status = _0.info()->step(this, C);
    std::cout << "S >>> " << _0->node->str() << std::endl;
    return status;
  }

  SStatus RuntimeState::hnf(
      Configuration * C, RealpathResult * inductive, void const * guides
    )
  {
    Cursor _0 = C->cursor();
    tag_type tag = inspect::tag_of(inductive->target);
    size_t ret = 0;
    while(true)
    {
      switch(tag)
      {
        case T_SETGRD: assert(0); continue;
        case T_FAIL  : _0->node->forward_to(Fail);
                       return T_FWD;
        case T_CONSTR: _0->node->forward_to(
                           this->lift_constraint(C, inductive)
                         );
                       return T_FWD;
        case T_FREE  : tag = this->replace_freevar(C, inductive, guides);
                       continue;
        case T_FWD   : compress_fwd_chain(inductive->target);
                       tag = inspect::tag_of(inductive->target);
                       this->stepcount++;
                       continue;
        case T_CHOICE: _0->node->forward_to(
                           this->pull_tab(C, inductive)
                         );
                       return T_FWD;
        case T_FUNC  : ret = C->search.extend(inductive);
                       tag = this->procS(C);
                       C->search.resize(ret);
                       continue;
        default      : return tag;
      }
    }
  }

  SStatus RuntimeState::hnf_or_free(
      Configuration * C, RealpathResult * inductive
    , void const * guides
    )
  {
    tag_type tag = this->hnf(C, inductive, guides);
    if(tag == E_RESIDUAL && inspect::isa_freevar(inductive->target))
      return T_FREE;
    else
      return tag;
  }
}

