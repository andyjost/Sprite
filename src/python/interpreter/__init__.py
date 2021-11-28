'''
A Curry interpreter.

The Interpreter manages compilation and evaluation of Curry code.  Each
instance has a separate copy of the settings and runtime.
'''

__all__ = ['Interpreter']

from .. import config, context, exceptions, icurry, utility
from ..objects.handle import getHandle
from . import import_
from ..utility import curryname, flagutils
import itertools, logging, os, sys

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
          Indicates how to convert Curry results when returning to Python.
          With no conversion a list value, for example, is returned as a Curry
          list.  The 'topython' converter converts lists, tuples, strings,
          numbers, and other basic objects to their Python equivalents.
      ``trace`` (True|*False*)
          Trace computations.
      ``keep_temp_files``  (True|*False*|<str>)
          Keep temporary files and directories.  If a nonempty string is
          supplied, then it is treated as a directory name and all temporary
          files will be written there.
      ``lazycompile`` (*True*|False)
          Functions are not materialized until the first time they are needed.
      ``setfunction_strategy`` (*'lazy'*|'eager')
          Indicates how to evaluate set functions.  If 'lazy', then set guards
          are used (similar to KiCS2).  Otherwise, each argument is reduced to
          ground normal form before applying the set function (similar to
          PAKCS).
      ``telemetry_interval`` (*None*|<number>)
          Specifies the number of seconds between event reports in the log
          output.  Events provide information about the state of the runtime
          system, such as the number of nodes created or steps performed.  If
          None or non-positive, this information is not reported.
  '''
  def __new__(cls, flags={}):
    self = object.__new__(cls)
    self.flags = flagutils.get_default_flags()
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
  def setfunctions(self):
    if not hasattr(self, '__setflib'):
      self.__setflib = self.module('Control.SetFunctions')
    return self.__setflib

  def reset(self):
    '''
    Soft-resets the interpreter.

    Clears loaded modules (except for the Prelude), restores I/O streams to
    their defaults, resets the Curry path from the environment, and clears
    internal counters.  This is much faster than building a new interpreter,
    which loads the Prelude.
    '''
    self.stdin = sys.stdin
    self.stdout = sys.stdout
    self.stderr = sys.stderr
    self.automodules = config.syslibs()
    self._counter = itertools.count()
    for name, module in list(self.modules.items()):
      module = getHandle(module)
      if not module.is_package and name != 'Prelude':
        module.unlink(self)
    self.path[:] = config.currypath(reset=True)
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
    modulename, _, objname = name.partition('.')
    moduleobj = self.module(modulename)
    return getHandle(moduleobj).getsymbol(objname)

  def type(self, name):
    '''Returns the constructor info tables for the named type.'''
    modulename, _, name = name.partition('.')
    moduleobj = self.module(modulename)
    return getHandle(moduleobj).gettype(name)

  # Externally-implemented methods.
  from .compile import compile
  from .conversions import currytype, topython, unbox
  from ..expressions import expr
  from .eval import eval
  from .import_ import import_
  from .loadsave import load, save
  from .optimize import optimize

  unbox = staticmethod(unbox)

