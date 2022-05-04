#include "cyrt/builtins.hpp"
#include "cyrt/graph/indexing.hpp"
#include "cyrt/inspect.hpp"
#include "cyrt/state/rts.hpp"

namespace cyrt
{
  Expr RuntimeState::procD()
  {
    Queue * Q         = nullptr;
    Configuration * C = nullptr;
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
        case T_CONSTR  : if(this->constrain_equal(C, C->root))
                         {
                           *C->root = NodeU{C->root}.constr->value;
                           tag = inspect::tag_of(C->root);
                           goto redoD;
                         }
        case T_FAIL    : this->drop();
                         continue;
        case T_FREE    : tag = this->replace_freevar(C, C->root);
                         if(tag == T_FREE)
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
        default        : tag = this->procN(C, C->root);
                         if(tag == T_CTOR)
                           return this->release_value();
                         else
                         {
                           C->scan.reset();
                           goto redoD;
                         }
      }
    }
    return Expr{};
  }

  tag_type RuntimeState::procN(Configuration * C, Cursor root)
  {
    size_t ret = 0;
    tag_type tag = 0;
    for(auto * scan = &C->scan; *scan; ++(*scan))
    {
      tag = inspect::tag_of(scan->cursor());
    redoN:
      switch(tag)
      {
        case T_UNBOXED : continue;
        case T_SETGRD  : assert(0); continue;
        case T_FAIL    : return root->make_failure();
        case T_CONSTR  : *root = this->lift_constraint(C, root, scan->cursor());
                         return inspect::tag_of(root);
        case T_FREE    : tag = this->replace_freevar(C, root);
                         continue;
        case T_FWD     : compress_fwd_chain(scan->cursor());
                         tag = inspect::tag_of(scan->cursor());
                         goto redoN;
        case T_CHOICE  : *root = this->pull_tab(C, root, scan->cursor());
                         return T_CHOICE;
        case T_FUNC    : ret = scan->size();
                         tag = this->procS(C);
                         scan->resize(ret);
                         goto redoN;
        case E_RESTART : return inspect::tag_of(root);
        case E_RESIDUAL: assert(0); continue;
        default        :
          if(!is_partial(*scan->cursor()->info))
            scan->extend();
      }
    }
    return T_CTOR;
  }

  tag_type RuntimeState::procS(Configuration * C)
  {
    Cursor _0 = C->cursor();
    std::cout << "S <<< " << _0->str() << std::endl;
    auto status = _0->info->step(this, C);
    std::cout << "S >>> " << _0->str() << std::endl;
    return status;
  }

  tag_type RuntimeState::hnf(
      Configuration * C, Variable * inductive, void const * guides
    )
  {
    Cursor _0 = C->cursor();
    tag_type tag = inspect::tag_of(inductive->target);
    while(true)
    {
      switch(tag)
      {
        case T_SETGRD: assert(0); continue;
        case T_FAIL  : _0->forward_to(Fail);
                       return T_FWD;
        case T_CONSTR: _0->forward_to(this->lift_constraint(C, inductive));
                       return T_FWD;
        case T_FREE  : tag = this->replace_freevar(C, inductive, guides);
                       return tag;
        case T_FWD   : compress_fwd_chain(inductive->target);
                       tag = inspect::tag_of(inductive->target);
                       this->stepcount++;
                       continue;
        case T_CHOICE: _0->forward_to(this->pull_tab(C, inductive));
                       return T_FWD;
        case T_FUNC  : C->scan.push(inductive);
                       tag = this->procS(C);
                       C->scan.pop();
                       continue;
        default      : return tag;
      }
    }
  }

  tag_type RuntimeState::hnf_or_free(
      Configuration * C, Variable * inductive, void const * guides
    )
  {
    tag_type tag = this->hnf(C, inductive, guides);
    if(tag == E_RESIDUAL && inspect::isa_freevar(inductive->target))
      return T_FREE;
    else
      return tag;
  }
}

