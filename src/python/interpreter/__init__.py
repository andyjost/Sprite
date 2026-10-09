'''
A Curry interpreter.

The Interpreter manages compilation and evaluation of Curry code.  Each
instance has a separate copy of the settings and runtime.
'''

__all__ = ['Interpreter']

from .. import backends, config, exceptions, icurry, typecheck, utility
from ..backends.generic.eval import evaluator as _evaluator
from . import flags as _flagmod, import_
from ..objects.handle import getHandle
import importlib
from ..utility.binding import binding
from ..utility import curryname, formatDocstring
import logging, os, sys

logger = logging.getLogger(__name__)

@utility.formatDocstring(config.python_package_name())
class Interpreter(object):
  '''
  Represents one instance of a Curry system.

  Key data and methods are as follows:

    Data:
      :data:`flags`
          Configuration flags.
      :data:`modules`
          Imported Curry modules.
      :data:`path`
          The Curry search path.
      :data:`prelude`
          The built-in Curry module ``Prelude``.
      :data:`setfunctions`
          The built-in Curry module ``Control.SetFunctions``.
      :data:`sigtable`
          The signature table: the type schemes of the loaded symbols.

    Methods:
      :meth:`compile`
          Compile a string containing Curry code.
      :meth:`eval`
          Evaluate a Curry expression.
      :meth:`expr`
          Build a Curry expression.
      :meth:`import_`
          Import a Curry module.
      :meth:`load`
          Load compiled Curry.
      :meth:`module`
          Look up a module by name.
      :meth:`reset`
          Soft-reset the interpreter.
      :meth:`save`
          Save compiled Curry.
      :meth:`stats`
          Report the statistics of the run.
      :meth:`symbol`
          Look up a symbol by name.
      :meth:`topython`
          Convert Curry data to Python.
      :meth:`type`
          Look up a data type by name.
  '''
  def __new__(cls, flags={}):
    self = object.__new__(cls)
    self._flags = _flagmod.get_default_flags()
    bad_flags = set(flags) - set(self._flags)
    if bad_flags:
      raise ValueError('unknown flag%s: %s' % (
          's' if len(bad_flags) > 1 else ''
        , ', '.join(map(repr, bad_flags))
        ))
    # The flags start from the environment, as the flags of the global
    # interpreter do: SPRITE_ROTATION, then SPRITE_INTERPRETER_FLAGS, then
    # the argument (flags.getflags).  So a fresh interpreter runs as the
    # process does unless its argument says otherwise.
    self._flags.update(_flagmod.getflags(flags))
    _flagmod.check_flags(self._flags)
    self._backend = backends.IBackend(self._flags['backend'])
    self._modules = {}
    self._path = []
    # The steps and forks of the evaluations of this interpreter; see stats.
    self._evaluation_totals = _evaluator.EvaluationTotals()
    self._sigtable = typecheck.SignatureTable(self)
    self.reset() # set remaining attributes.
    return self

  @property
  @utility.formatDocstring(config.python_package_name())
  def flags(self):
    '''
    A dict containing the configuration flags.  Change its entries in
    place to change the behavior of the Curry system; the attribute cannot
    be assigned.  The flag ``backend`` is read when the interpreter is
    made, so a later change of it has no effect.  See
    :mod:`{0}.interpreter.flags`.
    '''
    return self._flags

  @property
  @utility.formatDocstring(config.python_package_name())
  def modules(self):
    '''
    A dict containing the imported Curry modules.  Maps module names
    to :class:`CurryModule <{0}.objects.CurryModule>` objects.
    '''
    return self._modules

  @property
  def path(self):
    '''
    A list of strings specifying the Curry search path.  Change it in
    place to adjust where to search for Curry files.  An assignment to the
    attribute replaces the entries of the same list.
    '''
    return self._path

  @path.setter
  def path(self, values):
    self._path[:] = [str(x) for x in values]

  @property
  def backend(self):
    '''The backend object associated with this interpreter.'''
    return self._backend

  @property
  def prelude(self):
    '''The built-in module Prelude.'''
    if not hasattr(self, '__preludelib'):
      self.__preludelib = self.module('Prelude')
    return self.__preludelib

  @property
  def setfunctions(self):
    '''The built-in module Control.SetFunctions.'''
    if not hasattr(self, '__setflib'):
      self.__setflib = self.module('Control.SetFunctions')
    return self.__setflib

  @property
  @utility.formatDocstring(config.python_package_name())
  def sigtable(self):
    '''
    The signature table, a :class:`SignatureTable
    <{0}.typecheck.SignatureTable>`: the type schemes of the loaded symbols,
    read on demand from the FlatCurry interfaces.  :meth:`reset` clears it.
    '''
    return self._sigtable

  def reset(self):
    '''
    Soft-resets the interpreter.

    Clears the loaded modules, except the Prelude and the packages.
    Restores I/O streams to their defaults, resets the Curry path from the
    environment, releases the expression modules, and clears the signature
    table.  The names of anonymous modules are not reused; see compile.py.
    This is much faster than building a new interpreter, which loads the
    Prelude.
    '''
    self.stdin = sys.stdin
    self.stdout = sys.stdout
    self.stderr = sys.stderr
    self.automodules = config.syslibs()
    self._expression_modules = [] # see compile.py, mode 'expr'
    self._lifted_goals = {} # see typecheck.goals.register_lifted
    for name, module in list(self.modules.items()):
      module = getHandle(module)
      if not module.is_package and name != 'Prelude':
        module.unlink(self)
    self.path[:] = config.currypath(reset=True)
    self.backend.init_interpreter_state(self)
    self._sigtable.clear()

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
    Look up a symbol by its fully-qualified name, ``'Prelude.+'``.  The
    name splits at its first dot into a module and a name in it, so
    ``'Data.List.nub'`` needs the package ``Data`` loaded, as an import of
    ``Data.List`` leaves it.  The second parameter has no effect.
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
  from ..expressions import describe, expr, raw_expr, typeof
  from .eval import eval
  from .import_ import import_
  from .loadsave import load, save
  from .optimize import optimize
  from .stats import stats

  unbox = staticmethod(unbox)

@formatDocstring(config.python_package_name())
def reload(name, flags={}):
  '''Hard-resets the interpreter found in module ``{}``.'''
  flags = _flagmod.getflags(flags)
  envflags = ','.join('%s:%s' % (str(k), str(v)) for k,v in flags.items())
  with binding(os.environ, 'SPRITE_INTERPRETER_FLAGS', envflags):
    this = sys.modules[name]
    importlib.reload(this)

