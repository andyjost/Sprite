'''Code for indexing to subexpressions.'''

from ....common import T_SETGRD, T_FWD
from ....exceptions import CurryIndexError, CurryTypeError
from .... import icurry, inspect
from . import node
from ....utility import visitation
import collections, numbers

__all__ = ['compress_fwd_chain', 'logical_subexpr', 'realpath', 'subexpr']

def logical_subexpr(root, path, update_fwd_nodes=True):
  '''
  Like subexpr, but assumes a logical path.  That is, steps through forward
  nodes and set guards do not appear in the path.
  '''
  return realpath(root, path, update_fwd_nodes)[0]

def compress_fwd_chain(end):
  '''Compresses a chain of forward nodes.'''
  chain = []
  while inspect.tag_of(end) == T_FWD:
    chain.append(end)
    end = inspect.fwd_target(end)
  for node in chain:
    node.successors[0] = end
  return end

# The result of a call to ``realpath``.
Realpath = collections.namedtuple('Realpath', ['target', 'realpath', 'guards'])

class RealPathIndexer(object):
  '''See ``realpath``.'''
  def __init__(self, root, update_fwd_nodes):
    if not inspect.isa_curry_expr(root):
      raise CurryTypeError('invalid Curry expression %r' % root)
    self.target = root
    self.realpath = []
    self.guards = set()
    self.parent = None
    self.update_fwd_nodes = update_fwd_nodes
    self.skip()

  @property
  def result(self):
    return Realpath(self.target, self.realpath, self.guards)

  def skip(self):
    '''
    Skips over forward nodes and set guards.  Updates the indexer state
    accordingly.
    '''
    while True:
      tag = inspect.tag_of(self.target)
      if tag == T_FWD:
        if self.update_fwd_nodes and self.realpath:
          end = compress_fwd_chain(self.target)
          self.parent.successors[self.realpath[-1]] = end
          self.target = end
        else:
          self.parent = self.target
          self.realpath.append(0)
          self.target = inspect.fwd_target(self.target)
      elif tag == T_SETGRD:
        self.guards.add(inspect.get_set_id(self.target))
        self.parent = self.target
        self.realpath.append(1)
        self.target = inspect.get_setguard_value(self.target)
      else:
        break

  @visitation.dispatch.on('path')
  def advance(self, path):
    raise CurryIndexError(
        'path must be an integer or sequence of integers, not %r'
            % type(path).__name__
      )

  @advance.when(numbers.Integral)
  def advance(self, i):
    parent = self.target
    try:
      self.target = parent.successors[i]
    except (IndexError, AttributeError):
      raise CurryIndexError('node index out of range')
    self.parent = parent
    self.realpath.append(i)
    self.skip()

  @advance.when((collections.Sequence, collections.Iterator), no=(str,))
  def advance(self, path):
    for i in path:
      self.advance(i)


def realpath(root, path, update_fwd_nodes=True):
  '''
  Gets the real path from ``root`` to the subexpression along the logical path
  ``path``.  The real path is formed by skipping over forward nodes and set
  guards.  These implicit steps are inserted into the path so that the result
  can be passed to ``index``.  Optionally, forward nodes can be spliced out
  instead of added to the real path.

  Args:
    root:
      A Curry expression.  Can be an instance of graph.Node or a built-in such
      as an ``int``, ``str``, or ``float``.

    path:
      A sequence of integers specifying the logical path to the intended
      subexpression.

    update_fwd_nodes:
      When True, forward nodes are spliced out, where possible, and chains of
      forward nodes are short-cut to their end.

  Returns:
    A ``namedtuple`` (target, realpath, guards), where ``target`` is the
    subexpression at ``root[path]``; ``realpath`` is the actual path used to
    reach the target, including entries for any forward nodes or set guards
    skipped over; and ``guards`` is a set containing the IDs for each guard
    crossed.
  '''
  indexer = RealPathIndexer(root, update_fwd_nodes)
  indexer.advance(path)
  return indexer.result


@visitation.dispatch.on('path')
def subexpr(root, path):
  '''
  Performs straightforward indexing into a Curry expression.  Returns the
  subexpression at ``root[path]``.  No special handling of any kind is
  performed.  More specifically, neither forward nodes nor set guards are
  skipped, and boxed fundamental types can be indexed to find their unboxed
  contents.

  Args:
    root:
      The expression at which to begin indexing.  This is usually an instance
      of ``Node``, though unboxed values are accepted if the path is empty.

    path:
      An integral number or sequence of such numbers specifying the path.

  Raises:
    CurryTypeError:
      ``root`` is not a Curry expression.

    CurryIndexError:
      A path component is invalid.

  Returns:
    The subexpression at ``root[path]``.
  '''
  raise CurryIndexError(
      'node index must be an integer or sequence of integers, not %r'
          % type(path).__name__
    )

@subexpr.when(numbers.Integral)
def subexpr(root, path):
  if not inspect.isa_curry_expr(root):
    raise CurryTypeError('invalid Curry expression %r' % root)
  try:
    return root.successors[path]
  except (IndexError, AttributeError):
    raise CurryIndexError('node index out of range')

@subexpr.when((collections.Sequence, collections.Iterator), no=(str,))
def subexpr(root, path):
  target = root
  for i in path:
    target = subexpr(target, i)
  return target

