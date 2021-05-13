'''
A pure-Python Curry interpreter.
'''

from .. import config
from .. import context
from .. import exceptions
from .. import icurry
from . import import_
from .. import objects
from .. import utility
import itertools
import logging
import os
import sys

logger = logging.getLogger(__name__)

@utility.formatDocstring(config.default_backend())
class Interpreter(object):
  '''
  A Curry interpreter.

  Use ``import_`` to add modules to the system.  Then use ``eval`` to evaluate
  expressions.

  Supported flags:
  ----------------
      ``backend`` ({0!r})
          The name of the backend used to compile and run Curry.
      ``debug`` (True|*False*)
          Sacrifice speed to add more consistency checks and enable debugging
          with PDB.
      ``defaultconverter`` ('topython'|*None*)
          Indicates the conversion to apply to results of eval.
      ``trace`` (True|*False*)
          Shows the effect of each step in a computation.
      ``keep_temp_files``  (True|*False*|<str>)
          Indicates whether temporary files (and directories) should be
          deleted.  If a non-null string is passed, then it is treated as a
          directory name and all temporary files will be written there.
      ``lazycompile`` (*True*|False)
          Delays compilation of functions until they are needed.
      ``algebraic_substitution`` (True|*False*)
          [Experimantal] Implements narrowing of fundamental types by
          substituting an algebraic type.
      ``direct_var_binding`` (True|*False*)
          [Experimental] Implements constraints by directly binding variables
          to expressions.
  '''
  def __new__(cls, flags={}):
    self = object.__new__(cls)
    self.flags = {
        'backend':config.default_backend(), 'debug':False
      , 'defaultconverter':None, 'trace':False, 'lazycompile':True
      , 'keep_temp_files':False, 'direct_var_binding':False
      , 'algebraic_substitution':False
      }
    self.flags.update(flags)
    self._context = context.Context(self.flags['backend'])
    self._stepper = self.context.runtime.get_stepper(self)
    self.stepcounter = self.context.runtime.get_step_counter()
    self.modules = {}
    self.path = []
    self.reset() # set remaining attributes.
    return self

  @property
  def context(self):
    return self._context

  @property
  def prelude(self):
    if not hasattr(self, '__preludelib'):
      self.__preludelib = self.module('Prelude')
    return self.__preludelib

  @property
  def integer(self):
    if not hasattr(self, '__integerlib'):
      self.__integerlib = self.module('Integer')
    return self.__integerlib

  def reset(self):
    '''
    Soft-resets the interpreter.

    Clears loaded modules (except for built-in ones), restores I/O streams to
    their defaults, resets ``path`` from the environment, and clears internal
    counters.  This is much faster than building a new interpreter, which
    loads the Prelude.
    '''
    self.stdin = sys.stdin
    self.stdout = sys.stdout
    self.stderr = sys.stderr
    self._idfactory_ = itertools.count()
    self.stepcounter.reset()
    self.automodules = config.syslibs()
    for name in self.modules.keys():
      if name not in self.automodules:
        del self.modules[name]
    self.path[:] = config.currypath([]) # re-read it from the environment

  def module(self, name):
    '''Look up a module by name.'''
    try:
      return self.modules[name]
    except KeyError:
      if name in self.automodules:
        return self.import_(name)
      raise exceptions.ModuleLookupError('Curry module %r not found' % name)

  def symbol(self, name, modulename=None):
    '''
    Look up a symbol by its fully-qualified name or by its name relative to a
    module.
    '''
    if modulename is None:
      modulename, name = icurry.splitname(name)
    moduleobj = self.module(modulename)
    symbolgetter = getattr(moduleobj, '.getsymbol')
    return symbolgetter(name)

  def type(self, name):
    '''Returns the constructor info tables for the named type.'''
    modulename, name = icurry.splitname(name)
    moduleobj = self.module(modulename)
    typegetter = getattr(moduleobj, '.gettype')
    return typegetter(name)

  def nextid(self):
    '''Generates the next available choice/variable ID.'''
    return next(self._idfactory_)

  # Externally-implemented methods.
  from .compile import compile
  from .conversions import currytype, expr, topython, unbox
  from .eval import eval
  from .import_ import import_
  from ..backends.py.runtime import N, S, hnf, freshvar

