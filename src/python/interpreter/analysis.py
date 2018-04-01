from . import runtime
from ..visitation import dispatch
import collections

# def is_value(iexpr):
#   '''Indicates whether the ICurry expression is a value.'''
#   return False # TODO

# def is_det(iexpr):
#   '''Indicates whether the ICurry expression is deterministic.'''
#   return is_value(iexpr) # TODO

def isa(cyobj, what):
  '''
  Checks whether the given Curry object is an instance of the given type or
  constructor.  The second argument may be a sequence to check against.
  '''
  if not isinstance(cyobj, runtime.Node):
    return False
  return _isa(id(cyobj[()].info), what)

@dispatch.on('what')
def _isa(addr, what):
  raise TypeError(
      'arg 2 must be an instance or sequence of curry.interpreter.TypeInfo '
      'objects.')

@_isa.when(runtime.TypeInfo)
def _isa(addr, typeinfo):
  return addr == id(typeinfo.info)

@_isa.when(collections.Sequence, no=str)
def _isa(addr, seq):
  if not all(isinstance(ti, runtime.TypeInfo) for ti in seq):
    _isa(None, None) # raise error
  return addr in (id(ti.info) for ti in seq)

