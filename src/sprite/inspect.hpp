#pragma once
#include "sprite/graph/node.hpp"
#include "sprite/symbols.hpp"

namespace sprite { namespace inspect
{
  inline bool isa_setguard(Node * node)
  {
    // FIXME
    return true;
  }

  inline Cursor fwd_target(Cursor arg)
  {
    if(arg.kind != 'p' || arg->node->info != &FwdInfo)
      return Cursor();
    NodeU u{arg};
    return u.fwd->target;
  }

  inline Cursor fwd_chain_target(Cursor arg)
  {
    while(true)
    {
      Cursor after = fwd_target(arg);
      if(!after)
        return arg;
      else
        arg = after;
    }
  }
  #if 0
  inline Node ** fwd_target(Node *& node)
  {
    if(node->info != &FwdInfo)
      return nullptr;
    NodeU u{node};
    return &u.fwd->target;
  }

  inline Node *& fwd_chain_target(Node *& arg)
  {
    Node ** tmp = &arg;
    while(true)
    {
      Node ** after = fwd_target(*tmp);
      if(!after)
        return *tmp;
      else
        tmp = after;
    }
  }
  #endif

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

  inline Cursor get_setguard_value(Node * node)
  {
    if(isa_setguard(node))
    {
      NodeU u{node};
      return u.setgrd->value;
    }
    else
      return Cursor();
  }
}}
