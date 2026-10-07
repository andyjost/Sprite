'''
Implements RuntimeState methods related to bindings.  This module is not
intended to be imported except by rts.py.

A binding is private to the configuration that made it
(Configuration.bindings, a copy-on-write map keyed by the group id of the
variable).  A nested configuration, the capsule of a set function, starts
with an empty map, and a variable of its goal that an enclosing configuration
bound keeps its binding there.  So get_binding and has_binding read through
the queue stack (walk_qstack), as read_fp reads the decisions of the
enclosing configurations: the map of the configuration first, then the map
of the front configuration of each enclosing queue, under the group id of
the variable in that configuration.  Without the walk the capsule took such
a variable for unbound: it bound the variable anew, to the other side of its
comparison, or narrowed it, and the enclosing configuration then met the
generator of a variable it had bound (issue #97).  The writers (add_binding,
apply_binding, update_binding) use the map of the configuration alone.  The
C++ runtime has the same rule (RuntimeState::get_binding).
'''

from .. import graph

__all__ = [
    'add_binding', 'apply_binding', 'get_binding', 'has_binding'
  , 'make_value_bindings', 'update_binding'
  ]

def _find_binding(rts, arg, config):
  '''
  Finds the binding of ``arg``: the configuration that holds it, this one or
  the nearest enclosing one, with the key of the binding in its map.  None
  when no configuration bound the variable.
  '''
  vid = rts.obj_id(arg, config)
  for cfg in rts.walk_qstack(firstconfig=config):
    gid = rts.grp_id(vid, cfg)
    if gid in cfg.bindings:
      return cfg, gid
  return None

def add_binding(rts, arg, value, config=None):
  '''
  Create a binding from ``arg`` to ``value``.  The return value indicates
  whether the binding succeeded.
  '''
  config = config or rts.C
  gid = rts.grp_id(arg, config)
  if gid in config.bindings:
    current = config.bindings.read[gid]
    assert rts.is_builtin_type(current.info.typedef)
    return current.info is value.info and current[0] == value[0]
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
  Get the binding associated with ``arg``: the configuration's own, or that
  of the nearest enclosing configuration.
  '''
  config = config or rts.C
  found = _find_binding(rts, arg, config)
  if found is None:
    raise KeyError(rts.obj_id(arg, config))
  holder, gid = found
  return holder.bindings.read[gid]

def has_binding(rts, arg=None, config=None):
  '''
  Indicates whether ``arg`` has a binding, in this configuration or in an
  enclosing one.
  '''
  config = config or rts.C
  return _find_binding(rts, arg, config) is not None

def make_value_bindings(rts, freevar, values, typedef):
  n = len(values)
  assert n
  if n == 1:
    value = graph.Node(typedef.constructors[0], values[0])
    pair = graph.Node(rts.prelude.Pair, freevar, value)
    return graph.Node(rts.ValueBinding, value, pair)
  else:
    cid = next(rts.idfactory)
    left = make_value_bindings(rts, freevar, values[:n//2], typedef)
    right = make_value_bindings(rts, freevar, values[n//2:], typedef)
    return graph.Node(rts.Choice, cid, left, right)

def update_binding(rts, arg=None, config=None):
  '''
  Updates the bindings for a node when its group ID changes.

  This performs the following action: if node ``arg`` has a binding then let i,
  j equal its object and effective IDs, respectively, and if i!=j, move the
  binding from i to j.  The map of the configuration alone is read.
  '''
  config = config or rts.C
  arg = config.root if arg is None else arg
  i, j = rts.obj_id(arg, config), rts.grp_id(arg, config)
  if i != j:
    if i in config.bindings:
      rts.add_binding(j, config.bindings.read[i], config=config)
