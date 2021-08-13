from ..... import icurry
from .....common import T_CTOR
from .. import graph

__all__ = [
    'info_of', 'make_choice', 'make_constraint', 'make_value_bindings', 'tag_of'
  ]

def tag_of(node):
  if isinstance(node, icurry.ILiteral):
    return T_CTOR
  else:
    return node.info.tag

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
  repl = graph.Replacer(node, path, alternatives=generator)
  return graph.Node(rts.prelude._Choice, cid, repl[1], repl[2], target=rewrite)

def make_constraint(constr, node, path, rewrite=None):
  '''
  Make a new constraint object based on ``constr``, which is located at
  node[path].  If ``rewrite`` is supplied, the specified node is overwritten.
  Otherwise a new node is created.
  '''
  repl = graph.Replacer(node, path)
  value = repl[0]
  pair = constr[1]
  return graph.Node(constr.info, value, pair, target=rewrite)

def make_value_bindings(rts, var, values):
  n = len(values)
  assert n
  if n == 1:
    value = graph.Node(rts.prelude.Int, values[0])
    pair = graph.Node(rts.prelude.Pair, rts.obj_id(var), value)
    return graph.Node(rts.prelude._IntegerBinding, value, pair)
  else:
    cid = next(rts.idfactory)
    left = make_value_bindings(rts, var, values[:n//2])
    right = make_value_bindings(rts, var, values[n//2:])
    return graph.Node(rts.prelude._Choice, cid, left, right)

