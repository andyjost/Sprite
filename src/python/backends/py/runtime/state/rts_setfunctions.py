from .. import graph

__all__ = ['guard_args', 'guard', 'subexpr']

def guard_args(rts, expr, guards):
  guards = iter(guards)
  last_sid = next(guards)
  for sid in guards:
    expr = graph.Node(rts.setfunctions._SetGuard, sid, expr)
  yield rts.setfunctions._SetGuard
  yield last_sid
  yield expr

def guard(rts, expr, guards, target=None):
  if not guards:
    return expr
  else:
    return graph.Node(*guard_args(rts, expr, guards), target=target)
