#pragma once
#include "cyrt/graph/node.hpp"

namespace cyrt { namespace inspect
{
  bool isa_setguard(Node *);
  bool isa_choice(Node *);
  bool isa_freevar(Cursor);
  bool is_nondet(Cursor);
  Cursor fwd_target(Cursor);
  Cursor fwd_chain_target(Cursor);
  Set * get_set(Node *);
  Cursor get_setguard_value(Node *);

  xid_type get_choice_id(Node *);
  xid_type get_choice_id(Node *);
  xid_type xget_freevar_id(Node *);
  xid_type xget_freevar_id(Node *);

  tag_type tag_of(Node *);
  tag_type tag_of(Cursor);

  InfoTable const * info_of(Node *);
  InfoTable const * info_of(Cursor);
}}

#include "cyrt/inspect.hxx"
