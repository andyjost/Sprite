'''
Implements RuntimeState methods related to bindings.  This module is not
intended to be imported except by state.py.
'''
from ... import graph

__all__ = [
    'add_binding', 'apply_binding', 'get_binding', 'has_binding'
  , 'pop_binding', 'update_binding'
  ]

def add_binding(self, vid, node, config=None):
  '''
  Create a binding from the given variable ID to ``node``.  Returns a Boolean
  indicating whether the binding succeeded.  If the variable is already bound
  to a different node, then this fails.
  '''
  config = config or self.C
  node = graph.Node.getitem(node)
  vid = self.grp_id(vid)
  if vid in config.bindings:
    return config.bindings.read[vid] is node
  else:
    config.bindings.write[vid] = node
    return True

def apply_binding(self, arg=None, config=None):
  '''
  Pop a binding and apply it to the current configuration.

  The given argument must refer to a free variale with a binding in the
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
          , self.pop_binding(arg, config=config)
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

def pop_binding(self, arg=None, config=None):
  '''
  Get the binding associated with ``arg`` and remove it from the binding table.
  '''
  config = config or self.C
  vid = self.grp_id(arg, config)
  return config.bindings.write.pop(vid)

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
  if i in config.bindings and i != j:
    self.add_binding(j, config.bindings.write.pop(i), config=config)

