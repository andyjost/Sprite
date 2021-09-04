from ..... import icurry, utility
from .....common import T_SETGRD, T_CONSTR, T_VAR, T_FWD, T_CHOICE, T_FUNC, T_CTOR

__all__ = [
    'info_of', 'guard', 'make_choice', 'make_constraint', 'make_value_bindings'
  , 'replace', 'replace_copy', 'rewrite', 'subexpr', 'tag_of'
  ]

def info_of(node):
  if isinstance(node, icurry.ILiteral):
    return None
  else:
    return node.info

def make_choice(rts, cid, node, path, generator=None, rewrite=None):
  '''
  Make a choice node with ID ``cid`` whose alternatives are derived by
  replacing ``node[path]`` with the alternatives of choice-rooted
  expression``alternatives``.  If ``alternatives`` is not specified, then
  ``node[path]`` is used.  If ``rewrite`` is supplied, the specified node is
  overwritten.  Otherwise a new node is created.
  '''
  from .node import Node
  from .replacer import Replacer
  R = Replacer(node, path, alternatives=generator)
  return Node(rts.prelude._Choice, cid, R[1], R[2], target=rewrite)

def make_constraint(constr, node, path, rewrite=None):
  '''
  Make a new constraint object based on ``constr``, which is located at
  node[path].  If ``rewrite`` is supplied, the specified node is overwritten.
  Otherwise a new node is created.
  '''
  from .node import Node
  from .replacer import Replacer
  R = Replacer(node, path)
  value = R[0]
  pair = constr[1]
  return Node(constr.info, value, pair, target=rewrite)

def make_value_bindings(rts, var, values, typedef):
  from .node import Node
  n = len(values)
  assert n
  if n == 1:
    value = Node(typedef.constructors[0], values[0])
    pair = Node(rts.prelude.Pair, rts.obj_id(var), value)
    return Node(rts.prelude._ValueBinding, value, pair)
  else:
    cid = next(rts.idfactory)
    left = make_value_bindings(rts, var, values[:n//2], typedef)
    right = make_value_bindings(rts, var, values[n//2:], typedef)
    return Node(rts.prelude._Choice, cid, left, right)

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
  def __setitem__(self, path, rhs):
    self.node[path] = rhs

def rewrite(rts, target, info, *args, **kwds):
  from .node import Node
  guards = kwds.pop('guards', None)
  if guards:
    node = Node(info, *args)
    return guard(rts, guards, node, target=target, **kwds)
  else:
    return Node(info, *args, target=target, **kwds)

def tag_of(node):
  if isinstance(node, icurry.ILiteral):
    return T_CTOR
  else:
    return node.info.tag

