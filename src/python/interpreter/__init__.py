'''
A pure-Python Curry interpreter.
'''

from .function_compiler import compile_function
from ..icurry import *
from .. import importer
from .prelude import Prelude, System
from .runtime import InfoTable, Node, T_FAIL, T_FUNC, T_CHOICE, T_CTOR
from .show import Show
from ..visitation import dispatch
import collections
import logging
import numbers
import os
import types

# Logging setup.
# ==============
logger = logging.getLogger(__name__)
LOG_LEVELS = {k:getattr(logging, k)
    for k in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
  }
DEFAULT_LOG_LEVEL = 'INFO'
logging.basicConfig(
    level=LOG_LEVELS[
        os.environ.get('SPRITE_LOG_LEVEL', DEFAULT_LOG_LEVEL).upper()
      ]
  , format='%(asctime)s [%(levelname)s] %(message)s'
  , datefmt='%m/%d/%Y %H:%M:%S'
  )

class SymbolLookupError(AttributeError):
  pass

class TypeInfo(object):
  '''Compile-time type info.'''
  def __init__(self, ident, info):
    self.ident = ident
    self.info = info

  def _check_call(self, *args):
    if len(args) != self.info.arity:
      raise TypeError(
          'cannot construct "%s" (arity=%d), with %d arg%s' % (
              self.info.name
            , self.info.arity
            , len(args)
            , '' if len(args) == 1 else 's'
            )
        )

  def __call__(self, *args):
    '''Constructs an object of this type.'''
    self._check_call(*args)
    return Node(self.info, *args)

  def __str__(self):
    return 'TypeInfo for "%s"' % self.ident

# Inpterpretation.
# ================
class Interpreter(object):
  '''
  A Curry interpreter.

  Use ``import_`` to add modules to the system.  Then use ``eval`` to evaluate
  expressions.

  Supported flags:
  ----------------
      ``debug`` (*True*|False)
          Sacrifice speed to add more consistency checks.
  '''
  def __new__(cls, flags={}):
    self = object.__new__(cls)
    self.modules = {}
    self.flags = {}
    self.flags.setdefault('debug', True)
    self.flags.update(flags)
    self.path = os.environ.get('CURRYPATH', '')
    return self

  def __init__(self, flags={}):
    self.prelude = self.import_(Prelude)
    self.import_(System)
    self.ti_Failure = self.symbol('_System.Failure').info

  # Importing.
  # ==========
  @dispatch.on('arg')
  def import_(self, arg):
    raise TypeError('cannot import type "%s"' % type(arg).__name__)

  @import_.when(str)
  def import_(self, module_name):
    breakpoint()

  @import_.when(collections.Sequence)
  def import_(self, seq):
    return [self.import_(item) for item in seq]

  @import_.when(IModule)
  def import_(self, imodule):
    if imodule.name not in self.modules:
      moduleobj = types.ModuleType(imodule.name)
      setattr(moduleobj, '.types', {})
      self.modules[imodule.name] = moduleobj
      self._loadsymbols(imodule, moduleobj)
      self._compile(imodule, moduleobj)
    return self.modules[imodule.name]

  # Loading Symbols.
  # ================
  @dispatch.on('idef')
  def _loadsymbols(self, idef, moduleobj): #pragma: no cover
    '''
    Load symbols (i.e., constructor and functions names) from the ICurry
    definition ``idef`` into module ``moduleobj``.
    '''
    raise RuntimeError("unhandled ICurry type during symbol loading: '%s'" % type(idef))

  @_loadsymbols.when(collections.Sequence)
  def _loadsymbols(self, seq, *args, **kwds):
    for item in seq:
      self._loadsymbols(item, *args, **kwds)

  @_loadsymbols.when(collections.Mapping)
  def _loadsymbols(self, mapping, *args, **kwds):
    for item in mapping.itervalues():
     self._loadsymbols(item, *args, **kwds)

  @_loadsymbols.when(IModule)
  def _loadsymbols(self, imodule, moduleobj):
    # TODO: imports
    self._loadsymbols(imodule.types, moduleobj)
    self._loadsymbols(imodule.functions, moduleobj)
    # Stash the type tables in the module; e.g.:
    #   .types = {'Bool': [<TypeInfo for True>, <TypeInfo for False>]}
    setattr(moduleobj, '.types'
      , { typename.basename:
            [getattr(moduleobj, ctor.ident.basename) for ctor in ctors]
            for typename,ctors in imodule.types.items()
          }
      )

  @_loadsymbols.when(IConstructor)
  def _loadsymbols(self, icons, moduleobj):
    # For builtins, the 'py.tag' metadata contains the tag.
    builtin = 'py.tag' in icons.metadata
    info = InfoTable(
        icons.ident.basename
      , icons.arity
      , T_CTOR + icons.index if not builtin else icons.metadata['py.tag']
      , _no_step if not builtin else _unreachable
      , Show(getattr(icons.metadata, 'py.format', None))
      )
    setattr(moduleobj, icons.ident.basename, TypeInfo(icons.ident, info))

  @_loadsymbols.when(IFunction)
  def _loadsymbols(self, ifun, moduleobj):
    info = InfoTable(
        ifun.ident.basename, ifun.arity, T_FUNC, None, Show()
      )
    setattr(moduleobj, ifun.ident.basename, TypeInfo(ifun.ident, info))

  # Compiling.
  # ==========
  @dispatch.on('idef')
  def _compile(self, idef, moduleobj): # pragma: no cover
    '''Compile the ICurry definitions from ``idef`` into module ``moduleobj``'''
    assert False

  @_compile.when(collections.Mapping)
  def _compile(self, mapping, *args, **kwds):
    for item in mapping.itervalues():
     self._compile(item, *args, **kwds)

  @_compile.when(IModule)
  def _compile(self, imodule, moduleobj):
    self._compile(imodule.functions, moduleobj)

  @_compile.when(IFunction)
  def _compile(self, ifun, moduleobj):
    info = getattr(moduleobj, ifun.ident.basename).info
    info.step = compile_function(self, ifun)

  # Expression building.
  # ====================
  @dispatch.on('arg')
  def expr(self, arg, *args):
    raise TypeError(
        'cannot build a Curry expression from type "%s"' % type(arg).__name__
      )

  @expr.when(str) # Char or [Char].
  def expr(self, arg, *args):
    if len(arg) == 1:
      args = (arg,) + args
      self.prelude.Char._check_call(*args)
      return Node(self.prelude.Char.info, *args)
    else:
      raise RuntimeError('multi-char strings not supported yet.')

  @expr.when(collections.Sequence)
  def expr(self, arg):
    # Supports nested structures, e.g., Cons 0 [Cons 1 Nil].
    return self.expr(*arg)

  @expr.when(numbers.Integral)
  def expr(self, arg, *args):
    args = (int(arg),) + args
    self.prelude.Int._check_call(*args)
    return Node(self.prelude.Int.info, *args)

  @expr.when(numbers.Real)
  def expr(self, arg, *args):
    args = (float(arg),) + args
    self.prelude.Float._check_call(*args)
    return Node(self.prelude.Float.info, *args)

  @expr.when(TypeInfo)
  def expr(self, info, *args):
    return info(*map(self.expr, args))

  @expr.when(Node)
  def expr(self, node):
    return node

  # Symbol/type lookup.
  # ===================
  def module(self, name):
    iname = IName(name)
    try:
      return self.modules[iname.module]
    except KeyError:
      raise SymbolLookupError('module "%s" not found' % iname.module)

  def symbol(self, name):
    module = self.module(name)
    iname = IName(name)
    try:
      return getattr(module, iname.basename)
    except AttributeError:
      raise SymbolLookupError(
          'module "%s" has no symbol "%s"' % (iname.module, iname.basename)
        )

  def type(self, name):
    '''Returns the constructor info tables for the named type.'''
    module = self.module(name)
    iname = IName(name)
    try:
      return getattr(module, '.types')[iname.basename]
    except KeyError:
      raise SymbolLookupError(
          'module "%s" has no type "%s"' % (iname.module, iname.basename)
        )

  # Evaluating.
  # ===========
  def eval(self, goal):
    if not isinstance(goal, Node):
      goal = self.expr(goal)
    return runtime.Evaluator(self, goal).eval()

  # Head-normalizing function.
  hnf = runtime.hnf

  # Normalizing function.
  nf = runtime.nf


# Misc.
# =====
def _unreachable(*args, **kwds): #pragma: no cover
  assert False

def _no_step(*args, **kwds): #pragma: no cover
  pass

