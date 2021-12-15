'''
A Curry interpreter.

The Interpreter manages compilation and evaluation of Curry code.  Each
instance has a separate copy of the settings and runtime.
'''

__all__ = ['Interpreter']

from .. import config, context, exceptions, icurry, utility
from . import flags as _flagmod, import_
from ..objects.handle import getHandle
from six.moves import reload_module
from ..utility.binding import binding
from ..utility import curryname, formatDocstring
import itertools, logging, os, sys

logger = logging.getLogger(__name__)

@utility.formatDocstring(config.python_package_name())
class Interpreter(object):
  '''
  A Curry interpreter.

  Use :meth:`import_` to add modules to the system.  Use :meth:`eval` to
  evaluate expressions.

  Attributes:
      flags:
        A dict containing the configuration flags.  Modify this to change
        the behavior of the Curry system.  See :mod:`{0}.interpreter.flags`.
      modules:
        A dict containing the imported Curry modules.  This maps module names
        to :class:`CurryModule <{0}.objects.CurryModule>` objects.
      path:
        A list of strings specifying the Curry search path.  Modify this to
        adjust where to search for Curry files.

  '''
  def __new__(cls, flags={}):
    self = object.__new__(cls)
    self.flags = _flagmod.get_default_flags()
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
  from ..expressions import expr, raw_expr
  from .eval import eval
  from .import_ import import_
  from .loadsave import load, save
  from .optimize import optimize

  unbox = staticmethod(unbox)

@formatDocstring(config.python_package_name())
def reload(name, flags={}):
  '''Hard-resets the interpreter found in module ``{}``.'''
  flags = _flagmod.getflags(flags)
  envflags = ','.join('%s:%s' % (str(k), str(v)) for k,v in flags.items())
  with binding(os.environ, 'SPRITE_INTERPRETER_FLAGS', envflags):
    this = sys.modules[name]
    reload_module(this)

