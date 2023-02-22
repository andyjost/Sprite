#include "cyrt/builtins.hpp"
#include "cyrt/graph/indexing.hpp"
#include "cyrt/inspect.hpp"
#include "cyrt/state/rts.hpp"
#include <iostream>


#ifdef SPRITE_TRACE_ENABLED
  #define TRACE_STEP_ENTER(cursor) \
      if(this->trace) { this->trace->enter_rewrite(this->Q(), cursor); }
  #define TRACE_STEP_EXIT(cursor) \
      if(this->trace) { this->trace->exit_rewrite(this->Q(), cursor); }
#else
  #define TRACE_STEP_ENTER(cursor)
  #define TRACE_STEP_EXIT(cursor)
#endif

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
                         tag = this->check_steps(tag);
                         goto redoD;
        case T_CHOICE  : if(this->choice_escapes(C, obj_id(C->root)))
                           return Expr{C->root};
                         else
                           this->fork(Q, C);
                         continue;
        case T_FUNC    : tag = this->procS(C);
                         goto redoD;
        case E_ERROR   : C->raise_error();
        case E_ROTATE  :
        case E_RESIDUAL: this->rotate(Q);
                         continue;
        case E_RESTART : tag = inspect::tag_of(C->root);
                         goto redoD;
        default        : TRACE_STEP_ENTER(C->root)
                         tag = this->procN(C, C->root);
                         TRACE_STEP_EXIT(C->root)
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
    #ifdef SPRITE_TRACE_ENABLED
    PositionKey key;
    #endif
    for(auto * scan = &C->scan; *scan; ++(*scan))
    {
      tag = inspect::tag_of(scan->cursor());
    redoN:
      switch(tag)
      {
        case T_UNBOXED : continue;
        case T_SETGRD  : scan->extend(); ++(*scan); continue;
        case T_FAIL    : return root->make_failure();
        case T_CONSTR  : *root = this->lift_constraint(C, root, scan->cursor());
                         return inspect::tag_of(root);
        case T_FREE    : tag = this->replace_freevar(C, root);
                         if(tag <= E_RESTART) goto redoN; else continue;
        case T_FWD     : compress_fwd_chain(scan->cursor());
                         tag = inspect::tag_of(scan->cursor());
                         tag = this->check_steps(tag);
                         goto redoN;
        case T_CHOICE  : *root = this->pull_tab(C, root, scan->cursor());
                         return T_CHOICE;
        case T_FUNC    : ret = scan->size();
                         #ifdef SPRITE_TRACE_ENABLED
                         if(this->trace) { key = this->trace->enter_position(this->Q(), *scan); }
                         #endif
                         tag = this->procS(C);
                         #ifdef SPRITE_TRACE_ENABLED
                         if(this->trace) { this->trace->exit_position(this->Q(), key); }
                         #endif
                         scan->resize(ret);
                         goto redoN;
        case E_ERROR   :
        case E_RESIDUAL:
        case E_RESTART : return tag;
        default        :
          if(!is_partial(*scan->cursor()->info))
            scan->extend();
      }
    }
    return T_CTOR;
  }

  tag_type RuntimeState::procS(Configuration * C)
  {
    TRACE_STEP_ENTER(C->cursor())
    auto status = C->cursor()->info->step(this, C);
    TRACE_STEP_EXIT(C->cursor())
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
                       tag = this->check_steps(tag);
                       continue;
        case T_CHOICE: inductive->update_escape_sets(); // move this into pull_tab?
                       _0->forward_to(this->pull_tab(C, inductive));
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

