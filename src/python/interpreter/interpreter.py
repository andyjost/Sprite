'''
A pure-Python Curry interpreter.
'''
from .. import config
from . import import_
from . import runtime
from .. import utility
import itertools
import logging
import os
import sys

logger = logging.getLogger(__name__)

class Interpreter(object):
  '''
  A Curry interpreter.

  Use ``import_`` to add modules to the system.  Then use ``eval`` to evaluate
  expressions.

  Supported flags:
  ----------------
      ``debug`` (True|*False*)
          Sacrifice speed to add more consistency checks and enable debugging
          with PDB.
      ``defaultconverter`` ('topython'|*None*)
          Indicates the conversion to apply to results of eval.
      ``trace`` (True|*False*)
          Shows the effect of each step in a computation.
      ``lazycompile`` (*True*|False)
          Delays compilation of functions until they are needed.
      ``keep_temp_files``  (True|*False*|<str>)
          Indicates whether temporary files (and directories) should be
          deleted.  If a non-null string is passed, then it is treated as a
          directory name and all temporary files will be written there.
      ``direct_var_binding`` (True|*False*)
          [Experimental] Implements constraints by directly binding variables
          to expressions.
  '''
  def __new__(cls, flags={}):
    self = object.__new__(cls)
    self.flags = {
        'debug':False, 'defaultconverter':None, 'trace':False, 'lazycompile':True
      , 'keep_temp_files':False, 'direct_var_binding':False
      }
    self.flags.update(flags)
    self._stepper = runtime.get_stepper(self)
    self.stepcounter = runtime.StepCounter()
    self.modules = {}
    self.path = []
    self.reset() # set remaining attributes.
    return self

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
    self.automodules = ['Integer', 'Prelude']
    for name in self.modules.keys():
      if name not in self.automodules:
        del self.modules[name]
    self.path[:] = config.currypath([]) # re-read it from the environment

  # Externally-implemented methods.
  from .compile import compile
  from .conversions import currytype, expr, topython, unbox
  from .eval import eval
  from .import_ import import_
  from .lookup import module, symbol, type
  from .runtime import N, S, hnf, nextid, freshvar

