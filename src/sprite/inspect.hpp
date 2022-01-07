#pragma once
#include "sprite/graph/node.hpp"

namespace sprite { namespace inspect
{
  bool isa_setguard(Node *);
  Cursor fwd_target(Cursor);
  Cursor fwd_chain_target(Cursor);
  tag_type tag_of(Node *);
  sid_type get_set_id(Node *);
  Cursor get_setguard_value(Node *);
}}

#include "sprite/inspect.hxx"
