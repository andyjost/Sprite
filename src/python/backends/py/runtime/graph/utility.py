from ..... import icurry, inspect, utility
from .....common import T_SETGRD, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
import itertools, numbers

__all__ = ['copy_spine', 'foldr', 'joinpath', 'rewrite']

def copy_spine(root, realpath, end=None, rewrite=None):
  '''
  Copies the spine from ``root`` along ``realpath``.

  Parameters:
  -----------
    ``root``
      The node at which to begin.

    ``realpath``
      The real path along which to copy.

    ``end``
      If supplied, this expression is placed at the end of the spine copied.

    ``rewrite``
      Specifies a node to rewrite with the result.

  Returns:
  --------
  The root of the copied expression.
  '''
  # Example:
  #      f      path=[1,0]                     f'
  #    / | \                                 / | \
  #   A  B  C   -- copy_spine(end=u) -->    A  B' C
  #      |                                     |
  #      ?                                     u
  #     / \
  #    u   v
  from .node import Node
  def construct(node, path, target=None):
    if path:
      i = path[0]
      successors = list(node.successors)
      successors[i] = construct(successors[i], path[1:])
      return Node(node.info, *successors, target=target)
    else:
      return node if end is None else end
  assert rewrite is None or inspect.isa_func(getattr(rewrite, 'target', rewrite))
  return construct(root, realpath, target=rewrite)


def foldl(f, args, initial=None):
  '''
  Builds a Curry expression by folding a binary operation over arguments.
  For example, given f=$##, args=[f, a, b], and initial=set2, this would
  build:

      (((set2 $## f) $## a) $## b)

  The result is returned as a generator producing arguments suitable for
  calling the Node constructor.
  '''
  from .node import Node
  if len(args) + (0 if initial is None else 1) < 2:
    raise TypeError('not enough args to fold')
  if initial is None:
    subexpr = reduce(lambda a, b: Node(f, a, b), args[:-1])
  else:
    subexpr = reduce(lambda a, b: Node(f, a, b), args[:-1], initial)
  yield f
  yield subexpr
  yield args[-1]


def joinpath(*parts):
  '''
  Join expression paths.  Each part should be None, an Integer, or an iterable.
  All will be chained together.  Returns a list of integers containing the
  joined path..
  '''
  parts = (
      [p] if isinstance(p, numbers.Integral) else p
          for p in parts
          if p is not None
    )
  return list(itertools.chain(*parts))

def rewrite(rts, target, info, *args, **kwds):
  from .node import Node
  return Node(info, *args, target=target, **kwds)

