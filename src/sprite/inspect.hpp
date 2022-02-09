#pragma once
#include "sprite/graph/node.hpp"

namespace sprite { namespace inspect
{
  bool isa_setguard(Node *);
  bool isa_choice(Node *);
  bool isa_freevar(Cursor);
  bool is_nondet(Cursor);
  Cursor fwd_target(Cursor);
  Cursor fwd_chain_target(Cursor);
  sid_type get_set_id(Node *);
  id_type get_choice_id(Node *);
  id_type get_freevar_id(Node *);
  Cursor get_setguard_value(Node *);

  tag_type tag_of(Node *);
  tag_type tag_of(Cursor);

  InfoTable const * info_of(Node *);
  InfoTable const * info_of(Cursor);
}}

#include "sprite/inspect.hxx"
