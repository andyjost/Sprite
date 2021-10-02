'''
Inspect live Curry objects.
'''

from .common import T_SETGRD, T_FAIL, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from . import config, context, icurry, objects
from .utility import visitation
import collections
import os
import re

SUBDIR = config.intermediate_subdir()

def info_of(arg):
  if is_boxed(arg):
    return arg.info

def tag_of(arg):
  if is_boxed(arg):
    return arg.info.tag
  elif isa_unboxed_primitive(arg):
    return T_CTOR

def isa(arg, what):
  '''
  Checks whether the given Curry object is an instance of the given type or
  constructor.  The second argument may be a sequence to check against.
  '''
  if not is_boxed(arg):
    return False
  else:
    return _isa(id(arg.info), what)

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

def isa_curry_expr(arg):
  return is_boxed(arg) or isa_unboxed_primitive(arg)

def isa_curry_expr_or_none(arg):
  return arg is None or isa_curry_expr(arg)

def isa_boxed_primitive(arg):
  info = info_of(arg)
  return info is not None and info.is_primitive

def unboxed_value(arg):
  if isa_boxed_primitive(arg):
    return arg.successors[0]
  elif isa_unboxed_primitive(arg):
    return arg

def isa_unboxed_primitive(arg):
  return isinstance(arg, icurry.IUnboxedLiteral)

def isa_primitive(arg):
  return isa_boxed_primitive(arg) or isa_unboxed_primitive(arg)

def isa_boxed_int(arg):
  info = info_of(arg)
  return info is not None and info.is_int

def isa_unboxed_int(arg):
  return isinstance(arg, int)

def isa_int(arg):
  return isa_boxed_int(arg) or isa_unboxed_int(arg)

def isa_boxed_char(arg):
  info = info_of(arg)
  return info is not None and info.is_char

def isa_unboxed_char(arg):
  return isinstance(arg, str) and len(arg) == 1

def isa_char(arg):
  return isa_boxed_char(arg) or isa_unboxed_char(arg)

def isa_boxed_float(arg):
  info = info_of(arg)
  return info is not None and info.is_float

def isa_unboxed_float(arg):
  return isinstance(arg, float)

def isa_float(arg):
  return isa_boxed_float(arg) or isa_unboxed_float(arg)

def isa_io(arg):
  info = info_of(arg)
  return info is not None and info.is_io

def isa_bool(arg):
  info = info_of(arg)
  return info is not None and info.is_bool

def isa_true(arg):
  info = info_of(arg)
  return info is not None and info.is_bool and info.tag == 1

def isa_false(arg):
  info = info_of(arg)
  return info is not None and info.is_bool and info.tag == 0

def isa_list(arg):
  info = info_of(arg)
  return info is not None and info.is_list

def isa_cons(arg):
  info = info_of(arg)
  return info is not None and info.is_list and info.tag == 0

def cons_head(arg):
  if isa_cons(arg):
    return arg.successors[0]

def cons_tail(arg):
  if isa_cons(arg):
    return arg.successors[1]

def isa_nil(arg):
  info = info_of(arg)
  return info is not None and info.is_list and info.tag == 1

def isa_tuple(arg):
  info = info_of(arg)
  return info is not None and info.is_tuple

_TUPLE_PATTERN = re.compile(r'\(,*\)$')
def isa_tuple_name(name):
  return re.match(_TUPLE_PATTERN, name)

_OPERATOR_PATTERN = re.compile(r'([^_a-zA-Z0-9\(\)\'\"\[\]])+$')
def isa_operator_name(name):
  return re.match(_OPERATOR_PATTERN, name)

def isa_setguard(arg):
  info = info_of(arg)
  return info is not None and info.tag == T_SETGRD

def isa_failure(arg):
  info = info_of(arg)
  return info is not None and info.tag == T_FAIL

def isa_constraint(arg):
  info = info_of(arg)
  return info is not None and info.tag == T_CONSTR

def isa_freevar(arg):
  info = info_of(arg)
  return info is not None and info.tag == T_FREE

def isa_fwd(arg):
  info = info_of(arg)
  return info is not None and info.tag == T_FWD

def isa_choice(arg):
  info = info_of(arg)
  return info is not None and info.tag == T_CHOICE

def isa_func(arg):
  info = info_of(arg)
  return info is not None and info.tag == T_FUNC

def isa_ctor(arg):
  info = info_of(arg)
  return info is not None and info.tag >= T_CTOR

def is_data(arg):
  return isa_ctor(arg) or isa_unboxed_primitive(arg)

def is_boxed(node):
  return isinstance(node, context.Node)

def get_choice_id(arg):
  # Note: a variable has a choice ID (which equals its variable ID).
  if isa_choice(arg) or isa_freevar(arg):
    return arg.successors[0]

def get_choice_alternatives(arg):
  assert isa_choice(arg)
  return arg.successors[1], arg.successors[2]

def get_left_alternative(arg):
  assert isa_choice(arg)
  return arg.successors[1]

def get_right_alternative(arg):
  assert isa_choice(arg)
  return arg.successors[2]

def get_freevar_id(arg):
  if isa_freevar(arg):
    return arg.successors[0]

def get_set_id(arg):
  if isa_setguard(arg):
    return arg.successors[0]

def get_setguard_value(arg):
  if isa_setguard(arg):
    return arg.successors[1]

def fwd_target(arg):
  if isa_fwd(arg):
    return arg.successors[0]

def fwd_chain_target(arg):
  while True:
    after = fwd_target(arg)
    if after is None:
      return arg
    else:
      arg = after

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
