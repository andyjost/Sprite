#include "sprite/builtins.hpp"

namespace sprite
{
  inline bool RuntimeState::is_narrowed(Configuration * C, id_type vid)
  {
    return this->read_fp(C, vid) != UNDETERMINED;
  }

  inline bool RuntimeState::is_narrowed(Configuration * C, Node * x)
  {
    id_type vid = obj_id(x);
    id_type gid = C->grp_id(vid);
    return this->is_narrowed(C, gid);
  }

  inline Node * RuntimeState::get_freevar(id_type vid)
  {
    return this->vtable[vid];
  }

  inline Node * RuntimeState::get_generator(Configuration * C, Node * x)
  {
    id_type vid = obj_id(x);
    id_type gid = C->grp_id(vid);
    return this->get_generator(C, gid);
  }

  inline Node * has_generator(Node * freevar)
  {
    Node * genexpr = NodeU{freevar}.free->genexpr;
    return genexpr->info == &Unit_Info ? nullptr : genexpr;
  }
}
