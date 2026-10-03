'''Code for indexing to subexpressions.'''

from ....common import T_SETGRD, T_FWD
from ....exceptions import CurryIndexError, CurryTypeError
from .... import inspect
from .node import Node
import collections, collections.abc, itertools, numbers

__all__ = ['compress_fwd_chain', 'logical_subexpr', 'realpath', 'subexpr']

def logical_subexpr(root, path, update_fwd_nodes=True):
  '''
  Like subexpr, but assumes a logical path.  That is, steps through forward
  nodes and set guards do not appear in the path.
  '''
  return realpath_parts(root, path, update_fwd_nodes)[0]

def compress_fwd_chain(end):
  '''Compresses a chain of forward nodes.'''
  chain = []
  while inspect.tag_of(end) == T_FWD:
    chain.append(end)
    end = inspect.fwd_target(end)
  for node in chain:
    # set_successor writes through on both backends; on the C++ backend
    # ``successors`` is a fresh list, so assigning into it would be lost.
    node.set_successor(0, end)
  return end

def _is_path_sequence(path):
  '''Tells whether ``path`` is a sequence or iterator of path components.'''
  return isinstance(path, (list, tuple)) or (
      isinstance(path, (collections.abc.Sequence, collections.abc.Iterator))
      and not isinstance(path, str)
    )

def _components(path):
  '''
  Generates the integer components of ``path``.  A nested sequence is
  flattened.  A component that is neither an integer nor a sequence raises
  CurryIndexError when it is reached.
  '''
  if isinstance(path, int) or isinstance(path, numbers.Integral):
    yield path
  elif _is_path_sequence(path):
    for part in path:
      yield from _components(part)
  else:
    raise CurryIndexError(
        'path must be an integer or sequence of integers, not %r'
            % type(path).__name__
      )

# Marks the end of a path.
_END = object()

# The result of a call to ``realpath``.
Realpath = collections.namedtuple('Realpath', ['target', 'realpath', 'guards'])

def realpath_parts(root, path, update_fwd_nodes):
  '''
  Implements ``realpath``.  Returns the target, the real path, and the guards
  as a plain tuple.  The evaluator creates a variable with this function for
  every inductive position, so it runs as one loop without helper objects.
  '''
  if not inspect.isa_curry_expr(root):
    raise CurryTypeError('invalid Curry expression %r' % root)
  if type(path) is int:
    components = iter((path,))
  elif type(path) is list or type(path) is tuple:
    components = iter(path)
  else:
    components = _components(path)
  target = root
  parent = None
  realpath = []
  guards = set()
  while True:
    # Skip over forward nodes and set guards.
    while True:
      if isinstance(target, Node):
        tag = target.info.tag
      else:
        tag = inspect.tag_of(target)
      if tag == T_FWD:
        if update_fwd_nodes and realpath:
          end = compress_fwd_chain(target)
          parent.set_successor(realpath[-1], end)
          target = end
        else:
          parent = target
          realpath.append(0)
          target = target.successors[0]
      elif tag == T_SETGRD:
        guards.add(target.successors[0])
        parent = target
        realpath.append(1)
        target = target.successors[1]
      else:
        break
    # Step to the next successor.
    i = next(components, _END)
    if i is _END:
      return target, realpath, guards
    if type(i) is not int:
      if _is_path_sequence(i):
        components = itertools.chain(_components(i), components)
        continue
      if not isinstance(i, numbers.Integral):
        raise CurryIndexError(
            'path must be an integer or sequence of integers, not %r'
                % type(i).__name__
          )
    parent = target
    try:
      target = parent.successors[i]
    except (IndexError, AttributeError):
      raise CurryIndexError('node index out of range')
    realpath.append(i)


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
  return Realpath(*realpath_parts(root, path, update_fwd_nodes))


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
  if isinstance(path, int) or isinstance(path, numbers.Integral):
    if not inspect.isa_curry_expr(root):
      raise CurryTypeError('invalid Curry expression %r' % root)
    try:
      return root.successors[path]
    except (IndexError, AttributeError):
      raise CurryIndexError('node index out of range')
  elif _is_path_sequence(path):
    target = root
    for i in path:
      target = subexpr(target, i)
    return target
  else:
    raise CurryIndexError(
        'node index must be an integer or sequence of integers, not %r'
            % type(path).__name__
      )
