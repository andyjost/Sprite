from ..... import icurry, utility
from .....common import T_SETGRD, T_CONSTR, T_VAR, T_FWD, T_CHOICE, T_FUNC, T_CTOR

__all__ = ['guard' , 'replace', 'replace_copy', 'rewrite', 'subexpr']

def replace(rts, context, path, replacement):
  from .replacer import Replacer
  R = Replacer(context, path, lambda _a, _b: replacement)
  replaced = R[None]
  context.successors[:] = replaced.successors

def replace_copy(rts, context, path, replacement):
  copy = context.copy()
  replace(rts, copy, path, replacement)
  return copy

def guard_args(rts, guards, node):
  from .node import Node
  guards = iter(guards)
  last_sid = next(guards)
  for sid in guards:
    node = Node(rts.setfunctions._SetGuard, sid, node)
  yield rts.setfunctions._SetGuard
  yield last_sid
  yield node

def guard(rts, guards, node, target=None):
  from .node import Node
  return Node(*guard_args(rts, guards, node), target=target)

class subexpr(object):
  def __init__(self, rts, node):
    self.rts = rts
    self.node = node
  def __getitem__(self, path):
    from .node import Node
    target, guards = Node.getitem_and_guards(self.node, path)
    if guards:
      return guard(self.rts, guards, target)
    else:
      return target
  def __setitem__(self, idx, rhs):
    self.node.successors[idx] = rhs

def rewrite(rts, target, info, *args, **kwds):
  from .node import Node
  guards = kwds.pop('guards', None)
  if guards:
    node = Node(info, *args)
    return guard(rts, guards, node, target=target, **kwds)
  else:
    return Node(info, *args, target=target, **kwds)


