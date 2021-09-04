'''
Code related to expression indexing.
'''

from . import node
from .....common import T_SETGRD, T_FWD

def index(root, path):
  '''
  Returns the subexpression at ``root[path]``. There is no special treatment
  for forward nodes or set guards.
  '''
  target = root
  for i in path:
    target = target.successors[i]
  return target

def realpath(root, path):
  '''
  Get the real path to subexpression ``root[path]``.  The real path is formed
  by skipping over forward nodes and set guards.  These implicit steps are
  inserted into the path.

  Parameters:
  -----------
    ``root``
      A Curry expression.  Can be an instance of graph.Node or a built-in such
      as an ``int``, ``str``, or ``float``.

    ``path``
      A sequence of integers specifying the logical path to the intended
      subexpression.

  Returns:
  --------
  A triple of (target, realpath, guards) where ``target`` is the subexpression
  at ``root[path]``; ``realpath`` is the actual path used to reach the target,
  including entries for any forward nodes or set guards skipped over; and
  guards is a set containing the IDs for each guard crossed.
  '''
  target = root
  realpath = []
  guards = set()
  target = _skip(target, realpath, guards)
  for i in path:
    realpath.append(i)
    target = target.successors[i]
    target = _skip(target, realpath, guards)
  return target, realpath, guards

def _skip(target, realpath, guards):
  if isinstance(target, node.Node):
    while hasattr(target, 'info') and target.info.tag in [T_FWD, T_SETGRD]:
      if target.info.tag == T_FWD:
        realpath.append(0)
        target = target.successors[0]
      elif target.info.tag == T_SETGRD:
        guards.add(target[0])
        realpath.append(1)
        target = target.successors[1]
  return target
