from ..... import icurry, inspect, utility
from .....common import T_FUNC, T_CTOR
import itertools, numbers

__all__ = ['copy_spine', 'curry', 'joinpath', 'rewrite', 'shallow_copy']
  
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

def curry(rts, f, *args, **kwds):
  '''
  Curries a function with a list of arguments.

  Parameters:
  -----------
    ``f``
      The expression to apply.  If this is a Node, it is simply used.
      Otherwise, it must have an 'info' attribute with information about a
      function or constructor node.  That will be used to create a partial
      application object or expression, in the case of a nullary symbol.

    ``args``
      The arguments that ``f`` shall be applied to.

    ``fapply``
      A keyword-only argument indicating which function to use for
      applications.  By default, Prelude.apply is used.  If a string
      is provided, it is used to look up a symbol in the Prelude.  Otherwise,
      the supplied argument should be node info.

  Examples:
  ---------

  1. ``curry(f, a, b)`` returns the expression ``apply(apply(f, a), b)``.
  2. ``curry(prelude.Nil)`` creates the empty list.
  3. ``curry(prelude.Cons)`` creates the partial application ``(:)``; i.e., the
     list constructor applied to no arguments.
  4. ``curry(prelude.Cons, 1)`` creates the partial list ``(1:)``. ; i.e., the
     list constructor applied to 1.
  5. ``curry(f, a, fapply='$##')`` returns the expression ``f $## a``.
  '''
  from .node import Node
  fapply = kwds.pop('fapply', 'apply')
  assert not kwds
  if isinstance(fapply, str):
    fapply = getattr(rts.prelude, fapply)
  if not isinstance(f, Node):
    info = f.info
    assert info.tag == T_FUNC or info.tag > T_CTOR
    partial = (info.arity > 0)
    f = Node(info, partial=partial)
    if partial:
      f = Node(rts.prelude._PartApplic, info.arity, f)
  return reduce(lambda a, b: Node(fapply, a, b), args, f)

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

def shallow_copy(node):
  yield node.info
  for succ in node.successors:
    yield succ

