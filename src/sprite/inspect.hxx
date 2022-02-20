#include "sprite/builtins.hpp"
#include "sprite/graph/node.hpp"

namespace sprite { namespace inspect
{
  inline bool isa_setguard(Node * node)
  {
    return node->info->tag == T_SETGRD;
  }

  inline bool isa_choice(Node * node)
  {
    return node->info->tag == T_CHOICE;
  }

  inline bool isa_freevar(Cursor arg)
  {
    return tag_of(arg) == T_FREE;
  }

  inline bool is_nondet(Cursor arg)
  {
    switch(tag_of(arg))
    {
      case T_CHOICE:
      case T_FREE  : return true;
      default      : return false;
    }
  }

  inline Cursor fwd_target(Cursor arg)
  {
    if(arg.kind != 'p' || arg->node->info->tag != T_FWD)
      return Cursor();
    else
      return NodeU{arg->node}.fwd->target;
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

  inline xid_type xget_choice_id(Node * node)
  {
    return NodeU{node}.choice->cid;
  }

  inline xid_type get_choice_id(Node * node)
  {
    if(isa_choice(node))
      return xget_choice_id(node);
    else
      return NOXID;
  }

  inline xid_type xget_freevar_id(Node * node)
  {
    return NodeU{node}.free->vid;
  }

  inline xid_type get_freevar_id(Node * node)
  {
    if(isa_freevar(node))
      return xget_freevar_id(node);
    else
      return NOXID;
  }

  inline Set * get_set(Node * node)
  {
    if(isa_setguard(node))
      return NodeU{node}.setgrd->set;
    else
      return nullptr;
  }

  inline Cursor get_setguard_value(Node * node)
  {
    if(isa_setguard(node))
      return NodeU{node}.setgrd->value;
    else
      return Cursor();
  }

  inline InfoTable const * info_of(Node * node)
  {
    return node ? node->info : nullptr;
  }

  inline InfoTable const * info_of(Cursor cur)
  {
    return cur.kind == 'p' ? info_of(cur->node) : nullptr;
  }

  inline tag_type tag_of(Node * node)
  {
    return node->info->tag;
  }

  inline tag_type tag_of(Cursor cur)
  {
    switch(cur.kind)
    {
      case 'p': return cur.info()->tag;
      case 'i':
      case 'f':
      case 'c': return T_UNBOXED;
      default: assert(0); __builtin_unreachable();
    }
  }
}}

namespace sprite
{
  inline Cursor & Cursor::skipfwd()
  {
    **this = *inspect::fwd_chain_target(*this);
    return *this;
  }
}
