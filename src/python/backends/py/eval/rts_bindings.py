'''
Implements RuntimeState methods related to bindings.  This module is not
intended to be imported except by rts.py.

A binding is private to the configuration that made it
(Configuration.bindings, a copy-on-write map keyed by the group id of the
variable).  A nested configuration, the capsule of a set function, starts
with an empty map, and a variable of its goal that an enclosing configuration
bound keeps its binding there.  So get_binding and has_binding read through
the queue stack (walk_qstack), as read_fp reads the decisions of the
enclosing configurations: the map of the configuration first, then the
bindings its queue absorbed (Queue.absorbed), then the map of the front
configuration of each enclosing queue and the bindings of that queue, under
the group id of the variable in that configuration.  Without the walk the
capsule took such a variable for unbound: it bound the variable anew, to the
other side of its comparison, or narrowed it, and the enclosing
configuration then met the generator of a variable it had bound (issue
#97).  A binding found above the configuration's own level is private
state of the configuration there, and a capsule that reads it may be
shared by configurations with other bindings (issue #86): get_binding
raises E_DIVERGE, and allValues (currylib/setfunctions.py) clones the
capsule for that configuration, which absorbs the binding, before the read
takes effect.  The writers (add_binding, apply_binding, update_binding) use
the map of the configuration alone.  The C++ runtime has the same rule
(RuntimeState::get_binding and diverge).
'''

from ....common import T_CTOR
from ...generic.eval.control import E_DIVERGE
from .. import graph
from ..graph.node import Node
from .... import inspect

# The number of cells the comparison of two bindings reads.
SAME_BINDING_BUDGET = 1024

__all__ = [
    'add_binding', 'apply_binding', 'get_binding', 'has_binding'
  , 'make_value_bindings', 'update_binding'
  ]

def _find_binding(rts, arg, config):
  '''
  Finds the binding of ``arg``: the map that holds it (the bindings of a
  configuration, or the bindings a queue absorbed), the key of the binding
  in that map, and the level where it was found: 0 for ``config`` and its
  queue, k for the k-th enclosing level.  None when no configuration bound
  the variable.  A binding of the outermost configuration while that
  configuration is alone in its queue is absorbed into the current queue in
  place, at level 0: no other configuration reaches the capsule, and a later
  clone of the configuration starts with the same binding (the shortcut of
  _private_state in currylib/setfunctions.py, for the same reason).  The
  C++ runtime has the same walk (RuntimeState::get_binding).
  '''
  vid = rts.obj_id(arg, config)
  n = len(rts.qstack)
  key0 = None
  for level, qid in enumerate(reversed(rts.qstack)):
    Q = rts.qtable[qid]
    cfg = config if level == 0 else Q[0]
    gid = rts.grp_id(vid, cfg)
    if level == 0:
      key0 = gid
    if gid in cfg.bindings:
      holder = cfg.bindings.read
    elif gid in Q.absorbed:
      holder = Q.absorbed
    else:
      continue
    if level and level == n - 1 and len(Q) == 1:
      rts.Q.absorbed[key0] = holder[gid]
      return rts.Q.absorbed, key0, 0
    return holder, gid, level
  return None

def _divergence(rts, arg, config, level, binding):
  '''
  The arguments of E_DIVERGE for a binding found ``level`` levels up: the
  queue that the configuration there runs, and the id under which the
  configurations of that queue looked the variable up.  The C++ runtime
  has the same step (RuntimeState::diverge).
  '''
  qid = rts.qstack[-level]
  cfg = config if level == 1 else rts.qtable[qid][0]
  return qid, rts.grp_id(rts.obj_id(arg, config), cfg), binding

def _same_binding(current, value):
  '''
  Two bindings of one class are the same term when they are one cell, or
  the same constructor or literal over the same successors through forward
  nodes, read within SAME_BINDING_BUDGET cells.  Two distinct cells that
  are not constructor terms (operations, choices, variables, failures)
  count as different, and so does a pair beyond the budget: a second
  non-strict binding of a bound class to a different term fails the step
  (add_binding).  The merge of two bound classes at a union no longer
  compares the terms: it keeps one binding and guards the step with the
  strict equality of the two (update_binding; decision D26 of
  2026-10-12).  The C++ runtime has the same comparison (same_binding in
  state/rts_bindings.cpp).
  '''
  stack = [(current, value)]
  cells = 0
  while stack:
    a, b = stack.pop()
    a, b = inspect.fwd_chain_target(a), inspect.fwd_chain_target(b)
    if a is b:
      continue
    if not isinstance(a, Node) or not isinstance(b, Node):
      if isinstance(a, Node) or isinstance(b, Node) or a != b:
        return False
      continue
    if a.info is not b.info or a.info.tag < T_CTOR:
      return False
    cells += 1
    if cells > SAME_BINDING_BUDGET:
      return False
    stack.extend(zip(a.successors, b.successors))
  return True

def add_binding(rts, arg, value, config=None):
  '''
  Create a binding from ``arg`` to ``value``.  The bindings sit under the
  root of the class (update_binding keeps them there at a union).  The
  return value indicates whether the binding succeeded: False when the
  class holds a different binding.
  '''
  config = config or rts.C
  gid = rts.grp_id(arg, config)
  if gid in config.bindings:
    return _same_binding(config.bindings.read[gid], value)
  else:
    config.bindings.write[gid] = value
    return True

def apply_binding(rts, arg=None, config=None):
  '''
  Applies the binding of ``arg`` to ``config``, whose root is an alternative
  of the generator of the variable (fork): the root ``e`` becomes
  ``(generator =:<= binding) &> e``, so the side of the generator agrees
  with the binding.  The binding is consumed.  The constraint carries it
  into the variables of the generator, and a configuration that forks on
  the generator again applies nothing.  Applied at every fork, the
  constraint pull-tabbed the same generator to the root, the fork applied
  the binding once more, and so on without end (issue #97).  The C++
  runtime has the same step (RuntimeState::apply_binding).

  Args:
    arg:
        The argument whose binding to apply.  Must be a choice or free variable
        node, or ID. The associated ID must refer to a free variable.

     config:
        The configuration to use as context.

  Returns:
    Nothing.
  '''
  config = config or rts.C
  gid = rts.grp_id(arg, config)
  if gid in config.bindings:
    binding = config.bindings.read[gid]
    config.root = graph.Node(
        getattr(rts.prelude, '&>')
      , graph.Node(
            rts.symbol('Prelude.nonstrictEq')
          , rts.get_generator(arg, config=config)
          , binding
          )
      , config.root
      )
    del config.bindings.write[gid]

def get_binding(rts, arg=None, config=None):
  '''
  Get the binding associated with ``arg``: the configuration's own, the one
  its queue absorbed, or that of the nearest enclosing level.  A binding of
  an enclosing level raises E_DIVERGE: the capsule is cloned for the
  configuration that holds it, and the read runs again in the clone (see
  the module docstring).
  '''
  config = config or rts.C
  found = _find_binding(rts, arg, config)
  if found is None:
    raise KeyError(rts.obj_id(arg, config))
  holder, gid, level = found
  if level:
    raise E_DIVERGE(*_divergence(rts, arg, config, level, holder[gid]))
  return holder[gid]

def has_binding(rts, arg=None, config=None):
  '''
  Indicates whether ``arg`` has a binding, in this configuration, in its
  queue, or in an enclosing level.  A test alone; get_binding raises
  E_DIVERGE for a binding of an enclosing level.
  '''
  config = config or rts.C
  return _find_binding(rts, arg, config) is not None

def make_value_bindings(rts, freevar, values, typedef):
  '''
  Builds the value bindings of a free variable of a builtin type: one
  ValueBinding per value, under a tree of choices.  ``freevar`` is the
  Variable at the variable, or the node itself.  The pair holds the node,
  without the set guards crossed on the way to it: constrain_equal reads
  the id of the pair, and a guard has none, so a binding made through the
  box of a captured argument was dropped (the cause of issue #121).  The
  C++ step builds the same pair (make_value_bindings in
  state/rts_bindings.cpp).
  '''
  target = getattr(freevar, 'target', freevar)
  n = len(values)
  assert n
  if n == 1:
    value = graph.Node(typedef.constructors[0], values[0])
    pair = graph.Node(rts.prelude.Pair, target, value)
    return graph.Node(rts.ValueBinding, value, pair)
  else:
    cid = next(rts.idfactory)
    left = make_value_bindings(rts, freevar, values[:n//2], typedef)
    right = make_value_bindings(rts, freevar, values[n//2:], typedef)
    return graph.Node(rts.Choice, cid, left, right)

def update_binding(rts, arg=None, config=None, guards=None):
  '''
  Moves the binding of ``arg`` to the root of its class when its group ID
  changed: ``arg`` is a root of a class before a union, and the binding
  goes under the root after it, so a class keeps one binding, under its
  root (issue #128).  The map of the configuration alone is read.

  When the two roots hold distinct binding cells, the class keeps the
  binding of the new root and the pair (dropped, kept) goes into
  ``guards`` (decision D26 of 2026-10-12): the two classes were bound to
  two terms, and the strict equality of the two terms, as a guard above
  the result of the constraint step, decides the merge (fairscheme.D).
  An equality that fails drops the configuration, as the inconsistent
  merge did before the decision; one that succeeds keeps the value the
  failure lost (two equal terms not yet evaluated: eqShapeG18 of
  unit_constraints.py).  One cell under both roots is one binding: nothing
  to guard.  Without a list (a caller outside the constraint step at the
  root: the fork, the pairing of get_generator) such a merge returns False
  and fails the step, as before the decision.  No program is known to
  reach it, so the checker counts it (unguarded_merges) and the tests pin
  the count at zero.  The C++ runtime has the same step (merge_binding in
  state/rts_constraints.cpp).
  '''
  config = config or rts.C
  arg = config.root if arg is None else arg
  i, j = rts.obj_id(arg, config), rts.grp_id(arg, config)
  if i != j and i in config.bindings:
    value = config.bindings.read[i]
    if j not in config.bindings:
      config.bindings.write[j] = value
    else:
      kept = config.bindings.read[j]
      if kept is not value:
        if guards is None:
          if rts.checker is not None:
            rts.checker.unguarded_merge(config)
          return False
        guards.append((value, kept))
        if rts.checker is not None:
          rts.checker.merge_guard(config, value, kept)
    del config.bindings.write[i]
  return True
