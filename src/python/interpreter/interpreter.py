'''
A pure-Python Curry interpreter.
'''
from . import import_
from . import prelude
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
  '''
  def __new__(cls, flags={}):
    self = object.__new__(cls)
    self.flags = {
        'debug':False, 'defaultconverter':None, 'trace':False, 'lazycompile':True
      , 'keep_temp_files':False
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
    if not hasattr(self, '__prelude'):
      self.__prelude = self.import_(
          "Prelude", extern=prelude.Prelude, export=prelude.exports()
        , alias=prelude.aliases()
        )
    return self.__prelude

  def reset(self):
    '''
    Soft-resets the interpreter.

    Clears loaded modules (except for the Prelude), restores I/O streams to
    their defaults, resets ``path`` from the environment, and clears internal
    counters.  This is much faster than reloading the Prelude.
    '''
    self.stdin = sys.stdin
    self.stdout = sys.stdout
    self.stderr = sys.stderr
    self._idfactory_ = itertools.count()
    self.stepcounter.reset()
    for name in self.modules.keys():
      if name != 'Prelude':
        del self.modules[name]
    self.path[:] = utility.readCurryPathFromEnviron()

  # Externally-implemented methods.
  from .compile import compile
  from .conversions import currytype, expr, topython, unbox
  from .eval import eval
  from .import_ import import_
  from .lookup import module, symbol, type
  from .runtime import N, S, hnf, nextid

