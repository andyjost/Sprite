#include "sprite/state/rts.hpp"

namespace sprite
{
  bool RuntimeState::add_binding(Configuration * C, id_type vid, Node * value)
  {
    if(C->has_binding(vid))
    {
      Node * current = this->get_binding(C, vid);
      // assert(current->info->typedef in rts->builtin_types);
      return current->info == value->info && obj_id(current) == obj_id(value);
    }
    else
    {
      id_type gid = C->grp_id(vid);
      write(C->bindings)[gid] = value;
      return true;
    }
  }

  void RuntimeState::update_binding(Configuration * C, id_type vid)
  {
    id_type gid = C->grp_id(vid);
    if(vid != gid)
      if(C->bindings->count(vid))
        this->add_binding(C, gid, this->get_binding(C, vid));
  }
}
