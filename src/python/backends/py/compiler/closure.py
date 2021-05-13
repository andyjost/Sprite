'''
Defines a closure to use in dynamic code.  A closure associates compile-time objects
with name at run-time.
'''

from .... import objects
from ....utility import encoding

__all__ = ['Closure']

class Closure(object):
  '''
  The closure in which a step function is compiled.  Contains symbols looked up
  at compile time.

  This is a mapping from names to Python identifiers with associated objects.
  During compilation, the closure translates a name to an identifier that can
  appear in generated code as a reference to the corresponding object.  The
  mapping from identifiers to objects is exported to the runtime.

  The closure is automatically populated: the first time a symbol is looked up,
  it is added to the closure.  The value must be set once, of course, for the
  lookup to succeed at runtime.

  See ``FunctionCompiler`` for naming conventions.
  '''
  def __init__(self, interp):
    self.interp = interp
    self.context = {}

  def __getitem__(self, key):
    if isinstance(key, objects.CurryDataType):
      obj = key
      key = encoding.encode(obj.fullname, 'ty_', self.context)
    else:
      obj = None
    rv = self.context.get(key, None)
    if rv is not None:
      return rv
    else:
      if obj is None:
        obj = self.interp.symbol(key).info
      for k,v in self.context.iteritems():
        if v is obj:
          return k
      else:
        if not isinstance(obj, objects.CurryDataType):
          key = encoding.encode(key, 'ni_', self.context)
        self.context[key] = obj
        return key

  def __setitem__(self, key, obj):
    '''Add a non-symbol, such as a system function, to the closure.'''
    assert not (key.startswith('ni_') or key.startswith('_') or '.' in key)
    if key not in self.context:
      self.context[key] = obj
    else: # pragma: no cover
      assert self.context[key] is obj or self.context[key] == obj

  def findpath(self, path):
    path = tuple(path)
    for k,v in self.context.items():
      if k.startswith('p_') and v == path:
        return k
    else:
      assert False

