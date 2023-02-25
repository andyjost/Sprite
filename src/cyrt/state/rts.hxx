#include "cyrt/builtins.hpp"
#include "cyrt/graph/memory.hpp"

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

  inline tag_type RuntimeState::check_interrupts(tag_type tag)
  {
    return g_gc_collect
        ? E_GC
        : (!(++this->stepcount & 0xffff) && this->Q()->size() > 1)
            ? E_ROTATE
            : tag;
  }
}
