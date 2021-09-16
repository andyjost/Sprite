'''
Implements RuntimeState methods related to bindings.  This module is not
intended to be imported except by state.py.
'''

from .. import graph

__all__ = [
    'add_binding', 'apply_binding', 'get_binding', 'has_binding'
  , 'make_value_bindings', 'update_binding'
  ]

def add_binding(self, arg, value, config=None):
  '''
  Create a binding from ``arg`` to ``value``.  The return value indicates
  whether the binding succeeded.
  '''
  config = config or self.C
  value = graph.Node.getitem(value)
  if self.has_binding(arg, config):
    current = self.get_binding(arg, config)
    assert current.info.typedef() in self.builtin_types
    return current.info is value.info and current[0] == value[0]
  else:
    vid = self.grp_id(arg)
    config.bindings.write[vid] = value
    return True

def apply_binding(self, arg=None, config=None):
  '''
  Pop a binding and apply it to the current configuration.

  The given argument must refer to a free variable with a binding in the
  bindings table.  That binding will be removed from the table.  The binding is
  applied by replacing the root expression ``e`` with ``b &> e``, where ``b``
  is the binding.

  Parameters:
  -----------
    ``arg``
        The argument whose binding to apply.  Must be a choice or free variable
        node, or ID. The associated ID must refer to a free variable.

     ``config``
        The configuration to use as context.

  '''
  config = config or self.C
  if self.has_binding(arg, config=config):
    config.root = graph.Node(
        getattr(self.prelude, '&>')
      , graph.Node(
            self.prelude.prim_nonstrictEq
          , self.get_generator(arg, config=config)
          , self.get_binding(arg, config=config)
          )
      , config.root
      )

def get_binding(self, arg=None, config=None):
  '''Get the binding associated with ``arg``.'''
  config = config or self.C
  vid = self.grp_id(arg, config)
  return config.bindings.read[vid]

def has_binding(self, arg=None, config=None):
  '''Indicates whether ``arg`` has a binding.'''
  config = config or self.C
  return self.grp_id(arg, config) in config.bindings

def make_value_bindings(rts, var, values, typedef):
  n = len(values)
  assert n
  if n == 1:
    value = graph.Node(typedef.constructors[0], values[0])
    pair = graph.Node(rts.prelude.Pair, rts.obj_id(var), value)
    return graph.Node(rts.prelude._ValueBinding, value, pair)
  else:
    cid = next(rts.idfactory)
    left = make_value_bindings(rts, var, values[:n//2], typedef)
    right = make_value_bindings(rts, var, values[n//2:], typedef)
    return graph.Node(rts.prelude._Choice, cid, left, right)

def update_binding(self, arg=None, config=None):
  '''
  Updates the bindings for a node when its group ID changes.

  This performs the following action: if node ``arg`` has a binding then let i,
  j equal its object and effective IDs, respectively, and if i!=j, move the
  binding from i to j.
  '''
  config = config or self.C
  arg = config.root if arg is None else arg
  i,j = self.obj_id(arg), self.grp_id(arg)
  if i != j:
    if i in config.bindings:
      self.add_binding(j, self.get_binding(i, config), config=config)

