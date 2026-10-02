#include "cyrt/builtins.hpp"
#include "cyrt/graph/memory.hpp"
#include <cstdint>

namespace cyrt
{
  inline bool RuntimeState::is_narrowed(Configuration * C, xid_type vid)
  {
    return this->read_fp(C, vid) != UNDETERMINED;
  }

  inline bool RuntimeState::is_narrowed(Configuration * C, Node * x)
  {
    xid_type vid = obj_id(x);
    xid_type gid = C->grp_id(vid);
    return this->is_narrowed(C, gid);
  }

  inline Node * RuntimeState::get_freevar(xid_type vid)
  {
    return this->vtable[vid];
  }

  inline Node * RuntimeState::get_generator(Configuration * C, Node * x)
  {
    xid_type vid = obj_id(x);
    return this->get_generator(C, vid);
  }

  inline Node * RuntimeState::get_binding(Configuration * C, Node * x)
  {
    xid_type vid = obj_id(x);
    xid_type gid = C->grp_id(vid);
    return this->get_binding(C, gid);
  }

  inline Node * has_generator(Node * freevar)
  {
    Node * genexpr = NodeU{freevar}.free->genexpr;
    return genexpr->info == &Unit_Info ? nullptr : genexpr;
  }

  inline bool RuntimeState::in_recursive_call() const
  {
    return this->qstack.size() > 1;
  }

  // True when the C stack used below the outermost procD exceeds the room.
  // The two addresses do not belong to one object, so the distance is
  // computed on integers.  The stack grows downward on every supported
  // platform.  The absolute value keeps the test correct either way.
  inline bool RuntimeState::stack_exhausted() const
  {
    if(this->stack_room == NOLIMIT || !this->stack_base)
      return false;
    char probe;
    std::uintptr_t const base = (std::uintptr_t) this->stack_base;
    std::uintptr_t const here = (std::uintptr_t) &probe;
    std::uintptr_t const used = base > here ? base - here : here - base;
    return used > this->stack_room;
  }

  // Every 65536 forward nodes compressed (about one per rewrite step),
  // requests a rotation.  The target is the outermost queue that holds more
  // than one configuration, so a set function cannot starve the alternatives
  // outside it.  procD hands E_ROTATE outward until it reaches the target.
  // On the way out, each nested procD rotates its own queue when that queue
  // holds more than one configuration, so a nested sibling gets its turn as
  // well.
  inline tag_type RuntimeState::check_interrupts(tag_type tag)
  {
    if(g_gc_collect)
      return E_GC;
    if(!(++this->stepcount & 0xffff))
      for(Queue * Q: this->qstack)
        if(Q->size() > 1)
        {
          this->rotate_target = Q;
          return E_ROTATE;
        }
    return tag;
  }

  // Accounts for one rewrite step.  The step belongs to the configuration at
  // the head of the current queue and to the head of every enclosing queue,
  // because a set-function evaluation runs inside a step of the enclosing
  // configuration.
  inline void RuntimeState::count_step()
  {
    ++this->steps_total;
    for(Queue * Q: this->qstack)
      if(!Q->empty())
        ++Q->front()->steps;
  }

  // Leaves a nested procD without a value.  allValues_step returns ``status``
  // (E_UNWIND or E_ROTATE) to the enclosing evaluation, whose procD handles
  // it.  The nested queue keeps its configurations and resumes later.
  inline Expr RuntimeState::yield_control(tag_type status)
  {
    assert(this->in_recursive_call());
    assert(this->pending_control == NOTAG);
    this->pending_control = status;
    return Expr{};
  }
}
