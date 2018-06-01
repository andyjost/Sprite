from . import runtime
from ..visitation import dispatch
import collections
import re

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
      'arg 2 must be an instance or sequence of curry.interpreter.NodeInfo '
      'objects.'
    )

@_isa.when(runtime.NodeInfo)
def _isa(addr, nodeinfo):
  return addr == id(nodeinfo.info)

@_isa.when(collections.Sequence, no=str)
def _isa(addr, seq):
  return any(_isa(addr, ti) for ti in seq)

def isa_primitive(interp, arg):
  '''The primitive types are Int, Char, Float.'''
  p = interp.prelude
  return isa(arg, (p.Int, p.Char, p.Float))

def isa_bool(interp, arg):
  p = interp.prelude
  return isa(arg, (p.True, p.False))

def isa_true(interp, arg):
  return isa(arg, interp.prelude.True)

def isa_false(interp, arg):
  return isa(arg, interp.prelude.False)

def isa_list(interp, arg):
  return isa(arg, interp.type('Prelude.[]'))

def isa_tuple(interp, arg):
  if not isinstance(arg, runtime.Node):
    return False
  return is_tuple_name(arg[()].info.name)

_TUPLE_PATTERN = re.compile(r'\(,*\)$')
def is_tuple_name(name):
  return re.match(_TUPLE_PATTERN, name)

