from .. import graph

__all__ = ['guard_args', 'guard', 'subexpr']

def guard_args(rts, guards, node):
  guards = iter(guards)
  last_sid = next(guards)
  for sid in guards:
    node = graph.Node(rts.setfunctions._SetGuard, sid, node)
  yield rts.setfunctions._SetGuard
  yield last_sid
  yield node

def guard(rts, guards, node, target=None):
  if not guards:
    return node
  else:
    return graph.Node(*guard_args(rts, guards, node), target=target)
