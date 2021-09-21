from ..... import icurry, inspect, utility
from .....common import T_SETGRD, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR

__all__ = ['copy_spine', 'rewrite']

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


def rewrite(rts, target, info, *args, **kwds):
  from .node import Node
  guards = kwds.pop('guards', None)
  if guards:
    node = Node(info, *args)
    return rts.guard(guards, node, target=target, **kwds)
  else:
    return Node(info, *args, target=target, **kwds)

class subexpr(object):
  def __init__(self, rts, node):
    self.rts = rts
    self.node = node
  def __getitem__(self, path):
    from .node import Node
    target, guards = Node.getitem_and_guards(self.node, path)
    if guards:
      return self.rts.guard(guards, target)
    else:
      return target
  def __setitem__(self, idx, rhs):
    self.node.successors[idx] = rhs


