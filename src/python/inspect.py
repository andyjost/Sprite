'''
Inspect live Curry objects.
'''

from . import config
from . import context
from . import objects
from .tags import T_FAIL, T_BIND, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from .utility import visitation
import collections
import os
import re

SUBDIR = config.intermediate_subdir()

def isa(cyobj, what):
  '''
  Checks whether the given Curry object is an instance of the given type or
  constructor.  The second argument may be a sequence to check against.
  '''
  if not isinstance(cyobj, context.Node):
    return False
  return _isa(id(cyobj[()].info), what)

@visitation.dispatch.on('what')
def _isa(addr, what):
  raise TypeError(
      'arg 2 must be an instance or sequence of %s.objects.CurryNodeLabel '
      'objects.' % __package__
    )

@_isa.when(objects.CurryNodeLabel)
def _isa(addr, nodeinfo):
  return addr == id(nodeinfo.info)

@_isa.when(objects.CurryDataType)
def _isa(addr, typedef):
  return _isa(addr, typedef.constructors)

@_isa.when(collections.Sequence, no=str)
def _isa(addr, seq):
  return any(_isa(addr, ti) for ti in seq)

def isa_primitive(interp, arg):
  '''The primitive types are Int, Char, Float.'''
  p = interp.prelude
  return isa(arg, (p.Int, p.Char, p.Float))

def isa_io(interp, arg):
  return isa(arg, interp.prelude.IO)

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
  if not isinstance(arg, context.Node):
    return False
  return is_tuple_name(arg[()].info.name)

_TUPLE_PATTERN = re.compile(r'\(,*\)$')
def is_tuple_name(name):
  return re.match(_TUPLE_PATTERN, name)

def isa_failure(interp, arg):
  if not isinstance(arg, context.Node):
    return False
  return arg[()].info.tag == T_FAIL

def isa_freevar(interp, arg):
  if not isinstance(arg, context.Node):
    return False
  return arg[()].info.tag == T_FREE

def isa_fwd(interp, arg):
  if not isinstance(arg, context.Node):
    return False
  return arg.info.tag == T_FWD

def isa_choice(interp, arg):
  if not isinstance(arg, context.Node):
    return False
  return arg[()].info.tag == T_CHOICE

def isa_func(interp, arg):
  if not isinstance(arg, context.Node):
    return False
  return arg[()].info.tag == T_FUNC

def isa_ctor(interp, arg):
  if not isinstance(arg, context.Node):
    return False
  return arg[()].info.tag >= T_CTOR

def is_boxed(interp, node):
  return isinstance(node, context.Node)

def get_id(interp, arg):
  return interp.context.runtime.get_id(arg)

def _getfile(moduleobj, suffixes):
  if moduleobj.__file__:
    for suffix in suffixes:
      filename = os.path.join(
          os.path.dirname(moduleobj.__file__)
        , '.curry'
        , SUBDIR
        , config.interactive_modname() + suffix
        )
      if os.path.exists(filename):
        return filename

def getjsonfile(moduleobj):
  '''Returns the file containing ICurry-JSON, if one exists, or None.'''
  return _getfile(moduleobj, ['.json', '.json.z'])

def geticurryfile(moduleobj):
  '''Gets the ICurry file associated with a module.'''
  return _getfile(moduleobj, ['.icy'])

def geticurry(moduleobj):
  '''Gets the ICurry associated with a module.'''
  return getattr(moduleobj, '.icurry')
