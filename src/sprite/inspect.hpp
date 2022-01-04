#pragma once
#include "sprite/graph/node.hpp"

namespace sprite { namespace inspect
{
  inline bool isa_setguard(Node * node)
  {
    // FIXME
    return true;
  }

  inline Node * fwd_target(Node * node)
  {
    NodeU u{node};
    return u.fwd->target;
  }

  inline tag_type tag_of(Node * node)
  {
    return node->info->tag;
  }

  inline sid_type get_set_id(Node * node)
  {
    if(isa_setguard(node))
    {
      NodeU u{node};
      return u.setgrd->sid;
    }
    else
      return NOSID;
  }

  inline Node * get_setguard_value(Node * node)
  {
    if(isa_setguard(node))
    {
      NodeU u{node};
      return u.setgrd->value;
    }
    else
      return nullptr;
  }
}}
