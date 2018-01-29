'''
A pure-Python Curry emulator.
'''

from ..compiler.icurry import *
from . import evaluator
from . import prelude
from .node import InfoTable, TypeInfo, Node
from .show import Show
from ..visitation import dispatch
import collections
import logging
import numbers
import types

# For export.
Prelude = prelude.Prelude

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG
  , format='%(asctime)s [%(levelname)s] %(message)s'
  , datefmt='%m/%d/%Y %H:%M:%S'
  )

class SymbolLookupError(AttributeError):
  pass
  
# Emulation.
# ==========
class Emulator(object):
  '''
  Implements a Curry emulator.

  Use ``import_`` to add modules to the system.  Then use ``eval`` to evaluate
  expressions.
  '''
  def __new__(cls):
    self = object.__new__(cls)
    self.modules = {}
    self.prelude = self.import_(Prelude)
    return self

  # Importing.
  # ==========
  @dispatch.on('arg')
  def import_(self, arg):
    raise RuntimeError('unhandled argument type')

  @import_.when(collections.Sequence)
  def import_(self, seq):
    return [self.import_(item) for item in seq]

  @import_.when(IModule)
  def import_(self, imodule):
    if imodule.name not in self.modules:
      moduleobj = types.ModuleType(imodule.name)
      self.modules[imodule.name] = moduleobj
      self._loadsymbols(imodule, moduleobj)
      self._compile(imodule, moduleobj)
    return self.modules[imodule.name]

  # Loading Symbols.
  # ================
  @dispatch.on('idef')
  def _loadsymbols(self, idef, moduleobj):
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

  @_loadsymbols.when(IConstructor)
  def _loadsymbols(self, icons, moduleobj):
    info = InfoTable(
        icons.ident.basename
      , icons.arity
      , _unreachable if icons.noexec else evaluator.ctor_step
      , Show(icons.format)
      )
    setattr(moduleobj, icons.ident.basename, TypeInfo(icons.ident, info))

  @_loadsymbols.when(IFunction)
  def _loadsymbols(self, ifun, moduleobj):
    info = InfoTable(ifun.ident.basename, ifun.arity, None, Show('{0}'))
    setattr(moduleobj, ifun.ident.basename, TypeInfo(ifun.ident, info))

  # Compiling.
  # ==========
  @dispatch.on('idef')
  def _compile(self, idef, moduleobj):
    '''Compile the ICurry definitions from ``idef`` into module ``moduleobj``'''
    raise RuntimeError("unhandled ICurry type during compilation: '%s'" % type(idef))

  @_compile.when(collections.Sequence)
  def _compile(self, seq, *args, **kwds):
    for item in seq:
      self._compile(item, *args, **kwds)

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
    info.step = evaluator.compile_function(self, ifun)

  # Expression building.
  # ====================
  @dispatch.on('arg')
  def expr(self, arg, *args):
    raise RuntimeError('unhandled argument type')

  @expr.when(collections.Sequence)
  def expr(self, arg):
    # Supports nested structures, e.g., Cons 0 [Cons 1 Nil].
    return self.expr(*arg)

  @expr.when(numbers.Integral)
  def expr(self, arg, *args):
    args = (int(arg),) + args
    self.prelude.Int._check_call(args)
    return Node(self.prelude.Int.info, args)

  @expr.when(numbers.Real)
  def expr(self, arg, *args):
    args = (float(arg),) + args
    self.prelude.Float._check_call(args)
    return Node(self.prelude.Float.info, args)

  @expr.when(TypeInfo)
  def expr(self, info, *args):
    return info(*map(self.expr, args))

  @expr.when(Node)
  def expr(self, node):
    return node

  # Symbol lookup.
  # ==============
  @dispatch.on('key')
  def __getitem__(self, key):
    return self[IName(key)]

  @__getitem__.when(IName)
  def __getitem__(self, iname):
    try:
      module = self.modules[iname.module]
    except KeyError:
      raise SymbolLookupError("module '%s' not found" % iname.module)

    try:
      return getattr(module, iname.basename)
    except AttributeError:
      raise SymbolLookupError(
          "module '%s' has no symbol '%s'" % (iname.module, iname.basename)
        )

  # Evaluating.
  # ===========
  def eval(self, goal):
    return evaluator.Evaluator(self, goal).run()

  # Queries.
  # ========
  def is_choice(self, node):
    return node.info is self.prelude.Choice.info

  def is_failure(self, node):
    return node.info is self.prelude.Failure.info

# Misc.
# =====
def _unreachable(*args, **kwds):
  raise RuntimeError('Unreachable')

