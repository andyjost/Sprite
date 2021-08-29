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
from ..utility import curryname
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
  '''
  def __new__(cls, flags={}):
    self = object.__new__(cls)
    self.flags = {
        'backend':config.default_backend(), 'debug':False
      , 'defaultconverter':None, 'trace':False, 'lazycompile':True
      , 'keep_temp_files':False
      }
    bad_flags = set(flags) - set(self.flags)
    if bad_flags:
      raise ValueError('unknown flag%s: %s' % (
          's' if len(bad_flags) > 1 else ''
        , ', '.join(map(repr, bad_flags))
        ))
    self.flags.update(flags)
    self._context = context.Context(self.flags['backend'])
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

  @property
  def setfunctions(self):
    if not hasattr(self, '__setflib'):
      self.__setflib = self.module('Control.SetFunctions')
    return self.__setflib

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
    self.automodules = config.syslibs()
    for name in self.modules.keys():
      if name not in self.automodules:
        del self.modules[name]
    self.path[:] = config.currypath([]) # re-read it from the environment
    self.context.runtime.init_interpreter_state(self)

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
    # modulename, objname = curryname.split(name, self.modules, modulename)
    modulename, objname = icurry.splitname(name)
    moduleobj = self.module(modulename)
    symbolgetter = getattr(moduleobj, '.getsymbol')
    return symbolgetter(objname)

  def type(self, name):
    '''Returns the constructor info tables for the named type.'''
    modulename, name = icurry.splitname(name)
    moduleobj = self.module(modulename)
    typegetter = getattr(moduleobj, '.gettype')
    return typegetter(name)

  # Externally-implemented methods.
  from .compile import compile
  from .conversions import currytype, expr, topython, unbox
  from .eval import eval
  from .import_ import import_

