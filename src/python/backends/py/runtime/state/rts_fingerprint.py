'''
Implements RuntimeState methods related to the fingerprint.  This module is not
intended to be imported except by state.py.
'''

from copy import copy
from .....common import T_FREE, T_CHOICE, LEFT, RIGHT, UNDETERMINED, ChoiceState
from .. import graph
from ..... import inspect

__all__ = ['equate_fp', 'grp_id', 'obj_id', 'read_fp', 'update_fp']

def grp_id(rts, arg=None, config=None):
  '''
  Returns the group ID.  The argument must be a choice or variable node,
  or ID.

  Every distinct group of free variables constrained equal with (=:=) belong to
  a group with a unique group ID.  The group ID is the object ID of one
  arbitrary, distinguished member, called the representative.

  Two variables are constrained equal if and only if they share the same group
  ID (reflexivity permitted).
  '''
  config = config or rts.C
  return config.strict_constraints.read.root(rts.obj_id(arg, config))

def obj_id(rts, arg=None, config=None):
  '''
  Returns the choice or variable ID of a node.  The node argument must be a
  choice or free variable node.  For convenience, ``arg`` may be an ID, in
  which case it is simply returned.
  '''
  arg = (config or rts.C).root if arg is None else arg
  if isinstance(arg, int):
    return arg
  else:
    if arg.info.tag == T_CHOICE:
      cid, _, _ = arg.successors
      return cid
    elif arg.info.tag == T_FREE:
      vid, _ = arg.successors
      return vid

def read_fp(rts, arg=None, config=None):
  '''
  Read the fingerprint for the given argument.  The argument must be a choice
  or variable node, ID, or ChoiceState.  The group ID is always used to read a
  fingerprint.  For convenience, if a ChoiceState is provided, it is simply
  returned.
  '''
  if isinstance(arg, ChoiceState):
    return arg
  else:
    config = config or rts.C
    cid = rts.grp_id(arg, config=config)
    for cfg in rts.walk_qstack(firstconfig=config):
      if cid in cfg.fingerprint:
        return cfg.fingerprint[cid]
    else:
      return UNDETERMINED

def fork(rts, config=None):
  '''
  Fork a choice-rooted configuration.  Yields each consistent configuration
  arising from fixing the choice to the LEFT or RIGHT.
  '''
  rts.telemetry._forks += 1
  config = config or rts.C
  for idx, choicestate in [(1, LEFT), (2, RIGHT)]:
    clone = config.clone(config.root.successors[idx])
    if rts.update_fp(choicestate, config.root, config=clone):
      cid = rts.obj_id(config=config)
      gid = rts.grp_id(cid, config=clone)
      if cid in rts.vtable:
        rts.apply_binding(cid, config=clone)
        rts.apply_binding(gid, config=clone)
        if not rts.constrain_equal(*map(rts.get_freevar, [cid,gid]), config=clone):
          continue
      if any(config.fingerprint.get(i, choicestate) != choicestate
          for config in rts.walk_qstack()
          for i in [cid, gid]
        ):
        continue
      yield clone

def equate_fp(rts, arg0, arg1, config=None):
  '''
  Equate two IDs in a fingerprint.  Set both to the same value and return
  True, if that is consistent, or return False otherwise.
  '''
  return rts.update_fp(arg0, arg1, config=config) \
     and rts.update_fp(arg1, arg0, config=config)

def pull_tab(rts, root, target, realpath, rewrite=None):
  '''
  Make a choice node with ID ``cid`` whose alternatives are derived by
  replacing ``node[path]`` with the alternatives of choice-rooted
  expression``alternatives``.  If ``alternatives`` is not specified, then
  ``node[path]`` is used.  If ``rewrite`` is supplied, the specified node is
  overwritten.  Otherwise a new node is created.
  '''
  rts.telemetry._pulltabs += 1
  cid,l,r = target.successors
  lhs = graph.utility.copy_spine(root, realpath, end=l)
  rhs = graph.utility.copy_spine(root, realpath, end=r)
  return graph.Node(rts.prelude._Choice, cid, lhs, rhs, target=rewrite)

def update_fp(rts, choicestate, arg=None, config=None):
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
  config = config or rts.C
  choicestate = rts.read_fp(choicestate, config=config)
  if choicestate == UNDETERMINED:
    return True
  current = rts.read_fp(arg, config=config)
  if current == UNDETERMINED:
    config.fingerprint = copy(config.fingerprint)
    config.fingerprint[rts.obj_id(arg, config)] = choicestate
    config.fingerprint[rts.grp_id(arg, config)] = choicestate
    return True
  else:
    return current == choicestate

