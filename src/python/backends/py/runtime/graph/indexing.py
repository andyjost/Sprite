'''
Code related to expression indexing.
'''

from .....common import T_SETGRD, T_FWD
from .....exceptions import CurryIndexError, CurryTypeError
from ..... import icurry, inspect
from . import node
from .....utility import visitation
import collections
import numbers

@visitation.dispatch.on('path')
def index(root, path):
  '''
  Performs straightforward indexing into a Curry expression.  Returns the
  subexpression at ``root[path]``.  No special handling of any kind is
  performed.  More specifically, neither forward nodes nor set guards are
  skipped, and boxed fundamental types can be indexed to find their unboxed
  contents.

  Parameters:
  -----------
    ``root``
      The expression at which to begin indexing.  This is usually an instance
      of ``Node``, though unboxed values are accepted if the path is empty.

    ``path``
      An integral number or sequence of such numbers specifying the path.

  Raises:
  -------
    ``CurryTypeError``
      When ``root`` is not a Curry expression.

    ``CurryIndexError``
      When a path component is invalid.

  Returns:
  --------
  The subexpression at ``root[path]``.
  '''
  raise CurryIndexError('invalid path %r' % path)

@index.when(numbers.Integral)
def index(root, path):
  if not inspect.isa_curry_expr(root):
    raise CurryTypeError('invalid Curry expression %r' % root)
  try:
    successors = root.successors
  except AttributeError:
    raise CurryIndexError('invalid index into unboxed Curry value %r' % root)
  try:
    return successors[path]
  except IndexError:
    raise CurryIndexError('node index out of range')

@index.when((collections.Sequence, collections.Iterator), no=(str,))
def index(root, path):
  target = root
  for i in path:
    try:
      i = int(i)
    except:
      raise CurryIndexError('invalid index %r' % i)
    target = index(target, i)
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
