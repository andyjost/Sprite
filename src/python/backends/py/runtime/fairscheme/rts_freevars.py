'''
Implements RuntimeState methods related to free variables.  This module is not
intended to be imported except by state.py.
'''

from .....common import T_FREE, T_CHOICE
from ..control import E_RESIDUAL
from . import freevars
from .. import graph
from ...sprite import Fingerprint, LEFT, RIGHT, UNDETERMINED, ChoiceState

from . import integer

__all__ = [
    'get_freevar', 'get_generator', 'has_generator', 'instantiate'
  , 'is_choice_or_freevar_node', 'is_free', 'is_freevar_node', 'is_narrowed'
  , 'register_freevar'
  ]

def get_freevar(self, arg=None, config=None):
  try:
    if arg.info.tag == T_FREE:
      return arg
  except:
    vid = self.obj_id(arg, config)
    return self.vtable[vid]

def get_generator(self, arg=None, config=None):
  '''
  Returns the generator for the given free variable. The first argument must
  be a choice or free variable node, or ID.
  '''
  vid = self.obj_id(arg, config)
  x = self.get_freevar(vid)
  if not self.has_generator(x):
    self.constrain_equal(x, self.get_freevar(self.grp_id(vid, config)))
    assert self.has_generator(x)
  _, gen = x
  return gen

def has_generator(self, arg=None, config=None):
  x = self.get_freevar(arg, config)
  return freevars.has_generator(self, x)

def instantiate(self, func, path, typedef, config=None):
  '''
  Instantiates a needed free variable, which occurs at ``func[path]`` and has
  type ``typedef``.  The subexpression ``func`` will be rewritten such that the
  specified occurrence is replaced.

  See algorithm.hnf for a description of the arguments.

  Returns:
  --------
    The expression the free variable was replaced with.
  '''
  config = config or self.C
  if typedef is None:
    self.suspend(func[path], config)
  else:
    return freevars.instantiate(self, func, path, typedef)

def is_choice_or_freevar_node(self, node):
  '''Indicates whether the given argument is a choice or free variable.'''
  try:
    return node.info.tag in [T_CHOICE, T_FREE]
  except AttributeError:
    return False

def is_free(self, arg=None, config=None):
  '''
  Indicates whether a free variable is missing any information that would allow
  a computation needing it to proceed.  Used to implement
  Prelude.ensureNotFree.
  '''
  return self.is_freevar_node(arg) and not any(
      prop(arg, config) for prop in [
          self.has_generator, self.has_binding, self.is_narrowed
        ]
    )

def is_freevar_node(self, node):
  '''Indicates whether the given argument is a free variable.'''
  try:
    return node.info.tag == T_FREE
  except AttributeError:
    return False

def is_narrowed(self, arg=None, config=None):
  '''
  Indicates whether the given free varaible was narrowed in this
  configuration.  The argument must be a free variable node or ID.
  '''
  return self.read_fp(arg, config=config) != UNDETERMINED

def register_freevar(self, var):
  '''
  Update the vtable for variable ``var``.  The variable is added to the
  table so that it can be found later, if needed.
  '''
  self.vtable[self.obj_id(var)] = var

