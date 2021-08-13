'''
Implements RuntimeState methods related to free variables.  This module is not
intended to be imported except by state.py.
'''

from .....common import T_VAR, T_CHOICE
from . import common
from . import freevars
from .. import graph
from ...sprite import Fingerprint, LEFT, RIGHT, UNDETERMINED, ChoiceState

__all__ = [
    'get_generator', 'get_variable', 'has_generator', 'instantiate'
  , 'is_free', 'is_nondet', 'is_variable', 'is_narrowed', 'register_variable'
  ]

def get_generator(self, arg=None, config=None):
  '''
  Returns the generator for the given free variable. The first argument must
  be a choice or free variable node, or ID.
  '''
  vid = self.obj_id(arg, config)
  x = self.get_variable(vid)
  if not self.has_generator(x):
    self.constrain_equal(x, self.get_variable(self.grp_id(vid, config)))
    assert self.has_generator(x)
  _, gen = x
  return gen

def get_variable(self, arg=None, config=None):
  try:
    if arg.info.tag == T_VAR:
      return arg
  except:
    vid = self.obj_id(arg, config)
    return self.vtable[vid]

def has_generator(self, arg=None, config=None):
  x = self.get_variable(arg, config)
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

def is_free(self, arg=None, config=None):
  '''
  Indicates whether a free variable is missing any information that would allow
  a computation needing it to proceed.  Used to implement
  Prelude.ensureNotFree.
  '''
  return self.is_variable(arg) and not any(
      prop(arg, config) for prop in [
          self.has_generator, self.has_binding, self.is_narrowed
        ]
    )

def is_narrowed(self, arg=None, config=None):
  '''
  Indicates whether the given free varaible was narrowed in this
  configuration.  The argument must be a free variable node or ID.
  '''
  return self.read_fp(arg, config=config) != UNDETERMINED

def is_nondet(self, arg=None, config=None):
  '''
  Returns True if the argument is a choice or variable.
  '''
  arg = (config or self.C).root if arg is None else arg
  return common.tag_of(arg) in [T_CHOICE, T_VAR]

def is_variable(self, node):
  '''Indicates whether the given argument is a free variable.'''
  try:
    return node.info.tag == T_VAR
  except AttributeError:
    return False

def register_variable(self, var):
  '''
  Update the vtable for variable ``var``.  The variable is added to the
  table so that it can be found later, if needed.
  '''
  self.vtable[self.obj_id(var)] = var

