#pragma once
#include "sprite/builtins.hpp"

namespace sprite { namespace inspect
{
  inline bool isa_setguard(Node * node)
  {
    // FIXME
    return true;
  }

  inline Cursor fwd_target(Cursor arg)
  {
    if(arg.kind != 'p' || arg->node->info != &Fwd_Info)
      return Cursor();
    else
      return NodeU{arg}.fwd->target;
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

  inline tag_type tag_of(Node * node)
  {
    return node->info->tag;
  }

  inline sid_type get_set_id(Node * node)
  {
    if(isa_setguard(node))
      return NodeU{node}.setgrd->sid;
    else
      return NOSID;
  }

  inline Cursor get_setguard_value(Node * node)
  {
    if(isa_setguard(node))
      return NodeU{node}.setgrd->value;
    else
      return Cursor();
  }
}}
