#include "cyrt/builtins.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/tiered.hpp"
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
    vtable_type const & table = this->istate.vtable;
    auto p = table.find(vid);
    return p == table.end() ? nullptr : p->second;
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

  // Every 65536 completed rewrite steps (procS), requests a rotation.  The
  // target is the outermost queue that holds more than one configuration, so
  // a set function cannot starve the alternatives outside it.  procD hands
  // E_ROTATE outward until it reaches the target.  On the way out, each
  // nested procD rotates its own queue when that queue holds more than one
  // configuration, so a nested sibling gets its turn as well.  A collection
  // request (E_GC) comes after the rotation check, and every step counts: so
  // the rotation schedule is the same whether a collection is due or not,
  // and the stress mode of the collector, which keeps the request set,
  // rotates as a normal run does.  The same safepoint applies the compiled
  // objects that finished in the background (cyrt/tiered.hpp): a swap only
  // writes step pointers, so the schedule is unchanged.
  inline tag_type RuntimeState::check_interrupts(tag_type tag)
  {
    if(!(++this->stepcount & 0xffff))
    {
      if(g_tiered_pending.load(std::memory_order_relaxed))
        tiered_apply_pending(true);
      for(Queue * Q: this->qstack)
        if(Q->size() > 1)
        {
          this->rotate_target = Q;
          return E_ROTATE;
        }
    }
    if(g_gc_collect)
      return E_GC;
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
    #ifdef SPRITE_SCHEDULER_COUNTERS
    if(this->qstack.front()->size() == 1)
      ++this->counters.steps_serial;
    if(this->qstack.size() > 1)
      ++this->counters.steps_nested;
    #endif
  }

  #ifdef SPRITE_SCHEDULER_COUNTERS
  // Records the end of configuration ``C``, the front of the current queue,
  // with the steps it took.  A nested queue is a queue of a set function.
  inline void RuntimeState::count_end(Configuration * C, ConfigurationEnd end)
  {
    this->counters.end_configuration(this->in_recursive_call(), end, C->steps);
  }

  // Counts a completed step of ``C`` on ``redex`` as shared work when
  // another configuration created the redex.  A node without a creator was
  // built outside the scheduler.
  inline void RuntimeState::count_shared(Node * redex, Configuration * C)
  {
    size_t const creator = node_creator(redex);
    if(creator && creator != C->serial)
      ++this->counters.steps_shared;
  }

  // Names the configuration whose step runs, for the creator word of the
  // nodes it allocates (see graph/memory.hpp), and restores the enclosing
  // one on exit.  procD holds one for the whole run of its loop.
  struct CreatorScope
  {
    CreatorScope() : saved(g_creator_serial) {}
    ~CreatorScope() { g_creator_serial = this->saved; }
    CreatorScope(CreatorScope const &) = delete;
    CreatorScope & operator=(CreatorScope const &) = delete;
    size_t saved;
  };
  #endif

  // Leaves a nested procD without a value.  allValues_step returns ``status``
  // (E_UNWIND, E_ROTATE, or E_GC) to the enclosing evaluation, whose procD
  // handles it.  The nested queue keeps its configurations and resumes
  // later.
  inline Expr RuntimeState::yield_control(tag_type status)
  {
    assert(this->in_recursive_call());
    assert(this->pending_control == NOTAG);
    this->pending_control = status;
    return Expr{};
  }
}
