from .... import icurry, inspect, utility
from ....common import T_FUNC, T_CTOR
from .node import Node
import functools, itertools, numbers

__all__ = ['copy_spine', 'curry', 'joinpath', 'rewrite', 'shallow_copy']

def copy_spine(root, realpath, end=None, rewrite=None):
  r'''
  Copies the spine from ``root`` along ``realpath``.

  Args:
    root:
      The node at which to begin.

    realpath:
      The real path along which to copy.

    end:
      The expression to place at the end of the copied spine.

    rewrite:
      A node to rewrite with the result.

  Returns:
    The root of the copied expression.

  Example:

    The following command could perform the transformation shown after:

      >>> copy_spine(root=f, path=[1,0], end=u)

    ::

             f                f'
           / | \   ---->    / | \ 
          A  B  C          A  B' C
             |                |
             ?                u
            / \ 
           u   v

    Supplying ``rewrite=f`` would overwrite ``f`` rather than create a new
    node, ``f'``.

  '''
  assert rewrite is None or inspect.isa_func(getattr(rewrite, 'target', rewrite))
  target = getattr(rewrite, 'target', rewrite) # accept rewrite=Variable
  end = getattr(end, 'rvalue', end)            # accept end=Variable
  return _copy_spine(root, realpath, 0, end, target)

def _copy_spine(node, realpath, i, end, target):
  '''Copies the spine of ``node`` from position ``i`` of ``realpath``.'''
  if i < len(realpath):
    j = realpath[i]
    successors = list(node.successors)
    successors[j] = _copy_spine(successors[j], realpath, i + 1, end, None)
    # The copy of a valid node needs no check of its arity or its successors,
    # so the node is built directly, as the graph copier does.
    if target is None:
      target = object.__new__(Node)
    target.info = node.info
    target.successors = successors
    return target
  else:
    return node if end is None else end

def curry(rts, f, *args, **kwds):
  '''
  Curries a function with a list of arguments.

  Args:
    f:
      The expression to apply.  If this is a Node, it is simply used.
      Otherwise, it must have an 'info' attribute with information about a
      function or constructor node.  That will be used to create a partial
      application object or expression, in the case of a nullary symbol.

    args:
      The arguments that ``f`` shall be applied to.

    fapply:
      A keyword-only argument indicating which function to use for
      applications.  By default, ``Prelude.apply`` is used.  If a string is
      provided, it is used to look up a symbol in the Prelude.  Otherwise, the
      supplied argument should be node info.

  Returns:
    A Curry expression.

  Examples:
    1. ``curry(f, a, b)`` returns the expression ``apply(apply(f, a), b)``.
    2. ``curry(prelude.Nil)`` creates the empty list.
    3. ``curry(prelude.Cons)`` creates the partial application ``(:)``; i.e., the
       list constructor applied to no arguments.
    4. ``curry(prelude.Cons, 1)`` creates the partial list ``(1:)``. ; i.e., the
       list constructor applied to 1.
    5. ``curry(f, a, fapply='$##')`` returns the expression ``f $## a``.
  '''
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
      f = Node(rts.PartApplic, info.arity, f)
  return functools.reduce(lambda a, b: Node(fapply, a, b), args, f)

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
  return Node(info, *args, target=target, **kwds)

def shallow_copy(node):
  yield node.info
  for succ in node.successors:
    yield succ

