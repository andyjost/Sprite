#pragma once
#include "sprite/graph/node.hpp"

namespace sprite { namespace inspect
{
  bool isa_setguard(Node *);
  Cursor fwd_target(Cursor);
  Cursor fwd_chain_target(Cursor);
  sid_type get_set_id(Node *);
  Cursor get_setguard_value(Node *);

  tag_type tag_of(Node *);
  tag_type tag_of(Cursor);

  InfoTable const * info_of(Node *);
  InfoTable const * info_of(Cursor);
}}

#include "sprite/inspect.hxx"
