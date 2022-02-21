#include "sprite/builtins.hpp"
#include "sprite/graph/indexing.hpp"
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
        default        : if(this->procN(C, tag))
                           return this->release_value();
                         else
                           goto redoD;
      }
    }
    return Expr{};
  }

  bool RuntimeState::procN(Configuration * C, tag_type & tag)
  {
    Node * tmp = nullptr;
    size_t ret = 0;
    for(auto * scan = &C->scan; *scan; ++(*scan))
    {
      tag = inspect::tag_of(scan->cursor());
    redoN:
      switch(tag)
      {
        case T_UNBOXED : continue;
        case T_SETGRD  : assert(0); continue;
        case T_FAIL    : tag = C->root->make_failure();
                         return false;
        case T_CONSTR  : *C->root = this->lift_constraint(
                             C, C->root, scan->cursor()
                           );
                         tag = inspect::tag_of(C->root);
                         scan->reset();
                         return false;
        case T_FREE    : tmp = this->replace_freevar(C);
                         if(tmp)
                         {
                           *C->root = tmp;
                           scan->reset();
                           tag = inspect::tag_of(tmp);
                           return false;
                         }
                         else
                           continue;
        case T_FWD     : compress_fwd_chain(scan->cursor());
                         tag = inspect::tag_of(scan->cursor());
                         goto redoN;
        case T_CHOICE  : *C->root = this->pull_tab(
                             C, C->root, scan->cursor()
                           );
                         scan->reset();
                         assert(C->root->info->tag == T_CHOICE);
                         return false;
        case T_FUNC    : ret = scan->size();
                         tag = this->procS(C);
                         scan->resize(ret);
                         goto redoN;
        case E_RESTART : tag = inspect::tag_of(C->root);
                         return false;
        case E_RESIDUAL: assert(0); continue;
        default        :
          if(scan->cursor()->info->typetag != PARTIAL_TYPE)
            scan->extend();
      }
    }
    return true;
  }

  tag_type RuntimeState::procS(Configuration * C)
  {
    Cursor _0 = C->cursor();
    // std::cout << "S <<< " << _0->str() << std::endl;
    auto status = _0->info->step(this, C);
    // std::cout << "S >>> " << _0->str() << std::endl;
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
                       continue;
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

