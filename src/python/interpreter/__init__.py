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
import contextlib, contextvars, logging, os, sys, threading

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
    # The flags start from the environment, as the flags of the global
    # interpreter do: SPRITE_ROTATION, then SPRITE_INTERPRETER_FLAGS, then
    # the argument (flags.getflags).  So a fresh interpreter runs as the
    # process does unless its argument says otherwise.
    self._flags.update(_flagmod.getflags(flags))
    _flagmod.check_flags(self._flags)
    self._backend = backends.IBackend(self._flags['backend'])
    self._modules = {}
    self._module_view = contextvars.ContextVar('sprite_module_view', default=None)
    self._path_view = contextvars.ContextVar('sprite_path_view', default=None)
    self._state_lock = threading.RLock()
    self._path = list(config.currypath(reset=True))
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
    view = self._module_view.get()
    return self._modules if view is None else view

  @property
  def path(self):
    '''
    A list of strings specifying the Curry search path.  Change it in
    place to adjust where to search for Curry files.  An assignment to the
    attribute replaces the entries of the same list.
    '''
    view = self._path_view.get()
    return self._path if view is None else view

  @path.setter
  def path(self, values):
    self.path[:] = [str(x) for x in values]

  @property
  def backend(self):
    '''The backend object associated with this interpreter.'''
    return self._backend

  @property
  def prelude(self):
    '''The built-in module Prelude.'''
    if not hasattr(self, '_Interpreter__preludelib'):
      self.__preludelib = self.module('Prelude')
    return self.__preludelib

  @property
  def setfunctions(self):
    '''The built-in module Control.SetFunctions.'''
    if not hasattr(self, '_Interpreter__setflib'):
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

  def reset(self, flags=None):
    '''
    Soft-resets the interpreter.

    Starts a new session and clears the loaded modules.
    A loaded Prelude is replaced too, so held module objects become stale.
    Restores I/O streams to their defaults, keeps the Curry path, releases
    the expression modules, and clears the signature
    table.  The names of anonymous modules are not reused; see compile.py.
    This is much faster than building a new interpreter, which loads the
    Prelude.
    '''
    from ..backends.cxx import tiered
    tiered.cancel()
    tiered.wait(interp=self)
    from ..utility.locking import native_metadata
    return native_metadata(self._reset_state)(flags)
    return self._reset_state(flags)

  def _reset_state(self, flags):
    self._session = object()
    self.stdin = sys.stdin
    self.stdout = sys.stdout
    self.stderr = sys.stderr
    self.automodules = config.syslibs()
    self._expression_modules = [] # see compile.py
    self._unlink_modules()
    prelude = self.modules.pop('Prelude', None)
    if prelude is not None:
      self.backend.module_unlinked(self, prelude)
    for cached in ('_Interpreter__preludelib', '_Interpreter__setflib'):
      self.__dict__.pop(cached, None)

    for name in list(self._modules):
      if getHandle(self._modules[name]).is_package:
        del self._modules[name]
    if flags is not None:
      self._flags = dict(flags)
      self._backend = backends.IBackend(self._flags['backend'])
    self.backend.init_interpreter_state(self)
    self._sigtable.clear()
    if prelude is not None:
      self.import_('Prelude')

  def _unlink_modules(self):
    '''
    Unlinks the loaded modules, except the Prelude and the packages.  The
    backend hands the tables of each module to the runtime
    (IBackend.module_unlinked), so a module of the same name made later
    runs its own code while an object of the old module is alive (issue
    #114).  ``reset`` and ``reload`` call this.
    '''
    for name, module in self.modules.copy().items():
      module = getHandle(module)
      if not module.is_package and name != 'Prelude':
        module.unlink(self)

  @contextlib.contextmanager
  def _using_path(self, values):
    token = self._path_view.set(list(values))
    try:
      yield
    finally:
      self._path_view.reset(token)

  @contextlib.contextmanager
  def _private_modules(self):
    token = self._module_view.set(self.modules.copy())
    try:
      yield
    finally:
      self._module_view.reset(token)

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
    longest loaded module prefix identifies the module, so a module may
    also be the namespace of another module. The second parameter has no
    effect.
    '''
    moduleobj, objname = self._qualified_name(name)
    return getHandle(moduleobj).getsymbol(objname)

  def type(self, name):
    '''Returns the constructor info tables for the named type.'''
    moduleobj, name = self._qualified_name(name)
    return getHandle(moduleobj).gettype(name)

  def _qualified_name(self, name):
    for prefix in reversed(list(curryname.prefixes(name))[:-1]):
      if prefix in self.modules:
        return self.modules[prefix], name[len(prefix) + 1:]
    modulename, _, local = name.partition('.')
    return self.module(modulename), local

  # Externally-implemented methods.
  from .compile import compile
  from .conversions import currytype, topython, unbox
  from ..expressions import describe, expr, raw_expr, typeof
  from .eval import eval, eval_nodes, solve, stream
  from .import_ import import_
  from .loadsave import load, save
  from .optimize import optimize
  from .stats import stats

  unbox = staticmethod(unbox)

@formatDocstring(config.python_package_name())
def reload(name, flags={}):
  '''Hard-resets the interpreter found in module ``{}``.'''
  flags = _flagmod.getflags(flags)
  this = sys.modules[name]
  def replace():
    this._reload_flags = flags
    old = getattr(this, '_interpreter_', None)
    if isinstance(old, Interpreter):
      # The modules of the interpreter replaced leave it as a reset
      # unlinks them, before the new interpreter imports: a module of the
      # same name then takes its tables back and runs its own code while
      # an object of the old module is alive (issue #114).
      old._unlink_modules()
    importlib.reload(this)
  old = getattr(this, '_interpreter_', None)
  if old is not None and old.flags['backend'] == 'cxx':
    from ..utility.locking import native_metadata
    return native_metadata(replace)()
  return replace()
