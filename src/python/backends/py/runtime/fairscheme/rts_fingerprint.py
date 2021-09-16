'''
Implements RuntimeState methods related to the fingerprint.  This module is not
intended to be imported except by state.py.
'''

from copy import copy
from .....common import T_VAR, T_CHOICE, LEFT, RIGHT, UNDETERMINED, ChoiceState
from ..graph import Node
from ..graph.replacer import Replacer

__all__ = [
    'equate_fp', 'grp_id', 'obj_id', 'make_left', 'make_right', 'read_fp'
  , 'update_fp'
  ]

def grp_id(self, arg=None, config=None):
  '''
  Returns the group ID.  The argument must be a choice or variable node,
  or ID.

  Every distinct group of free variables constrained equal with (=:=) belong to
  a group with a unique group ID.  The group ID is the object ID of one
  arbitrary, distinguished member, called the representative.

  Two variables are constrained equal if and only if they share the same group
  ID (reflexivity permitted).
  '''
  config = config or self.C
  return config.strict_constraints.read.root(self.obj_id(arg, config))

def obj_id(self, arg=None, config=None):
  '''
  Returns the choice or variable ID of a node.  The node argument must be a
  choice or free variable node.  For convenience, ``arg`` may be an ID, in
  which case it is simply returned.
  '''
  arg = (config or self.C).root if arg is None else arg
  if isinstance(arg, int):
    return arg
  else:
    if arg.info.tag == T_CHOICE:
      cid, _, _ = arg
      return cid
    elif arg.info.tag == T_VAR:
      vid, _ = arg
      return vid

def read_fp(self, arg=None, config=None):
  '''
  Read the fingerprint for the given argument.  The argument must be a choice
  or variable node, ID, or ChoiceState.  The group ID is always used to read a
  fingerprint.  For convenience, if a ChoiceState is provided, it is simply
  returned.
  '''
  if isinstance(arg, ChoiceState):
    return arg
  else:
    config = config or self.C
    return config.fingerprint[self.grp_id(arg, config=config)]

def fork(self, config=None):
  '''
  Fork a choice-rooted configuration.  Yields each consistent configuration
  arising from fixing the choice to the LEFT or RIGHT.
  '''
  config = config or self.C
  for idx, choicestate in [(1, LEFT), (2, RIGHT)]:
    clone = config.clone(Node.getitem(config.root, idx))
    if self.update_fp(choicestate, config.root, config=clone):
      if self.obj_id(config=config) in self.vtable:
        i = self.obj_id(config=config)
        j = self.grp_id(i, config=clone)
        self.apply_binding(i, config=clone)
        self.apply_binding(j, config=clone)
        if not self.constrain_equal(*map(self.get_variable, [i,j]), config=clone):
          continue
      yield clone

def equate_fp(self, arg0, arg1, config=None):
  '''
  Equate two IDs in a fingerprint.  Set both to the same value and return
  True, if that is consistent, or return False otherwise.
  '''
  return self.update_fp(arg0, arg1, config=config) \
     and self.update_fp(arg1, arg0, config=config)

def make_choice(rts, cid, node, path, generator=None, rewrite=None):
  '''
  Make a choice node with ID ``cid`` whose alternatives are derived by
  replacing ``node[path]`` with the alternatives of choice-rooted
  expression``alternatives``.  If ``alternatives`` is not specified, then
  ``node[path]`` is used.  If ``rewrite`` is supplied, the specified node is
  overwritten.  Otherwise a new node is created.
  '''
  R = Replacer(node, path, alternatives=generator)
  return Node(rts.prelude._Choice, cid, R[1], R[2], target=rewrite)

def update_fp(self, choicestate, arg=None, config=None):
  '''
  Update the fingerprint to reflect the ID associated with ``arg``` being
  set to ``choicestate.``

  If ``choicestate`` is ``UNDETERMINED``, this does nothing.  Otherwise, the
  current value of ``arg`` is determined, consulting the fingerprint, if
  necessary.  If it is consistent with ``choicestate`` then it is updated and
  True is returned.  Otherwise, False is returned.

  Parameters:
  -----------
      ``choicestate``
          The choice state to set.  Must be a ChoiceState, choice or free
          variable node, or ID.
      ``arg``
          The ID to update in the fingerprint.  Must be a choice or free variable node,
          or ID.
      ``config``
          The Configuration to use as context.

  Returns:
  --------
  A Boolean indicating whether the change is consistent.
  '''
  config = config or self.C
  choicestate = self.read_fp(choicestate, config=config)
  if choicestate == UNDETERMINED:
    return True
  current = self.read_fp(arg, config=config)
  if current == UNDETERMINED:
    config.fingerprint = copy(config.fingerprint)
    config.fingerprint[self.obj_id(arg, config)] = choicestate
    config.fingerprint[self.grp_id(arg, config)] = choicestate
    return True
  else:
    return current == choicestate

