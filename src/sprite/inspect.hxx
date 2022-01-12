#include "sprite/builtins.hpp"
#include "sprite/graph/node.hpp"

namespace sprite { namespace inspect
{
  inline bool isa_setguard(Node * node)
  {
    // FIXME
    return true;
  }

  inline Cursor fwd_target(Cursor arg)
  {
    if(arg.kind != 'p' || arg->node->info->tag != T_FWD)
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

	inline tag_type tag_of(Cursor cur)
	{
		switch(cur.kind)
		{
			case 'p': return cur.info()->tag;
			case 'i':
			case 'f':
			case 'c': return T_CTOR;
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
