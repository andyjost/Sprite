'''
A pure-Python Curry interpreter.
'''

from ..icurry import *
from . import conversions
from . import function_compiler
from .. import importer
from . import symbols
from .prelude import Prelude, System
from .runtime import InfoTable, Node, T_FAIL, T_FUNC, T_CHOICE, T_CTOR
from .show import Show
from ..visitation import dispatch
import collections
import logging
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

class CurryModule(types.ModuleType):
  def __init__(self, *args, **kwds):
    super(CurryModule, self).__init__(*args, **kwds)
    setattr(self, '.symbols', {})
    setattr(self, '.types', {})
  def __repr__(self):
    return "<curry module '%s'>" % self.__name__
  __str__ = __repr__

SymbolLookupError = symbols.SymbolLookupError

class ModuleLookupError(AttributeError):
  '''Raised when a Curry module is not found.'''

class TypeLookupError(AttributeError):
  '''Raised when a Curry type is not found.'''

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
          Sacrifice speed to add more consistency checks and enable debugging
          with PDB.
      ``defaultconverter`` (*'topython'*|None)
          Indicates the conversion to apply to results of eval.
      ``trace`` (True|*False*)
          Shows the effect of each step in a computation.
  '''
  def __new__(cls, flags={}):
    self = object.__new__(cls)
    self.modules = {}
    self.flags = {}
    self.flags.setdefault('debug', True)
    self.flags.setdefault('defaultconverter', None)
    self.flags.setdefault('trace', False)
    self.flags.update(flags)
    self.path = filter(lambda x:x, os.environ.get('CURRYPATH', '').split(':'))
    return self

  def __init__(self, flags={}):
    self.import_(System)
    self.prelude = self.import_(Prelude)
    self.it_Failure = self.symbol('_System.Failure').info
    self.it_Choice = self.symbol('_System.Choice').info
    self.it_Fwd = self.symbol('_System.Fwd').info
    self.ni_PartApplic = self.symbol('_System.PartApplic')
    self.step = runtime.get_stepper(self)

  # Importing.
  # ==========
  @dispatch.on('arg')
  def import_(self, arg, currypath=None):
    raise TypeError('cannot import type "%s"' % type(arg).__name__)

  @import_.when(str)
  def import_(self, modulename, currypath=None):
    try:
      return self.modules[modulename]
    except KeyError:
      currypath = self.path if currypath is None else currypath
      icur = importer.getICurryForModule(modulename, currypath)
      return self.import_(icur)

  @import_.when(collections.Sequence, no=str)
  def import_(self, seq, currypath=None):
    return [self.import_(item, currypath=currypath) for item in seq]

  @import_.when(IModule)
  def import_(self, imodule, currypath=None):
    if imodule.name not in self.modules:
      moduleobj = CurryModule(imodule.name)
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

  @_loadsymbols.when(collections.Sequence, no=str)
  def _loadsymbols(self, seq, *args, **kwds):
    for item in seq:
      self._loadsymbols(item, *args, **kwds)

  @_loadsymbols.when(collections.Mapping)
  def _loadsymbols(self, mapping, *args, **kwds):
    for item in mapping.itervalues():
     self._loadsymbols(item, *args, **kwds)

  @_loadsymbols.when(IModule)
  def _loadsymbols(self, imodule, moduleobj):
    for modulename in imodule.imports:
      self.import_(modulename)
    self._loadsymbols(imodule.types, moduleobj)
    self._loadsymbols(imodule.functions, moduleobj)
    # Stash the type tables in the module; e.g.:
    #   .types = {'Bool': [<NodeInfo for True>, <NodeInfo for False>]}
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
      , Show(
            # Note: this is called once when loading _System, i.e., before
            # it_Fwd exists.
            getattr(self, 'it_Fwd', None)
          , getattr(icons.metadata, 'py.format', None)
          )
      )
    symbols.insert(
        moduleobj, icons.ident.basename, runtime.NodeInfo(icons.ident, info)
      )

  @_loadsymbols.when(IFunction)
  def _loadsymbols(self, ifun, moduleobj):
    info = InfoTable(
        ifun.ident.basename
      , ifun.arity, T_FUNC, None, Show(getattr(self, 'it_Fwd', None))
      )
    symbols.insert(
        moduleobj, ifun.ident.basename, runtime.NodeInfo(ifun.ident, info)
      )

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
    info = symbols.lookupSymbol(moduleobj, ifun.ident).info
    info.step = function_compiler.compile_function(self, ifun)

  # Conversions.
  # ============
  expr = conversions.expr
  box = conversions.box
  unbox = conversions.unbox
  tocurry = conversions.tocurry
  topython = conversions.topython

  # Symbol/type lookup.
  # ===================
  def module(self, name):
    iname = IName(name)
    try:
      return self.modules[iname.module]
    except KeyError:
      raise ModuleLookupError('module "%s" not found' % iname.module)

  def symbol(self, name):
    return symbols.lookupSymbol(self.module(name), IName(name))

  def type(self, name):
    '''Returns the constructor info tables for the named type.'''
    module = self.module(name)
    iname = IName(name)
    types = getattr(module, '.types')
    try:
      return types[iname.basename]
    except KeyError:
      raise TypeLookupError(
          'module "%s" has no type "%s"' % (iname.module, iname.basename)
        )

  # Compiling.
  # ==========
  def compile(
      self, string, mode='module', imports=None, modulename='_interactive_'
    ):
    '''
    Compile a string containing Curry code.  In mode "module", the string is
    interpreted as a Curry module.  In mode "expr", the string is interpreted
    as a Curry expression.

    Parameters:
    -----------
    ``string``
        A string containing Curry code.
    ``mode``
        Indicates how to interpret the string (see above).
    ``imports``
        Names the modules to import when compiling an expresion.  Unused in
        "module" mode.  By default, all modules loaded in the current
        interpreter are imported.
    ``modulename``
        Specifies the module name.  Used only in "module" mode.  If the name
        begins with an underscore, then it will not be placed in
        ``Interpreter.modules``.

    Returns:
    --------
    In "module" mode, a Curry module.  In "expr" mode, a Curry expression.
    '''
    if mode == 'module':
      if modulename in self.modules:
        raise RuntimeError("module %s is already defined" % modulename)
      icur = importer.str2icurry(string, self.path, modulename=modulename)
      try:
        module = self.import_(icur)
        module.__file__ = icur.__file__
        module._tmpd_ = icur._tmpd_
        return module
      finally:
        if icur.name.startswith('_') and icur.name in self.modules:
          del self.modules[icur.name]
    elif mode == 'expr':
      stmts, currypath = importer.getImportSpecForExpr(
          self
        , self.modules.keys() if imports is None else imports
        )
      stmts += ['expression = ' + string]
      string = '\n'.join(stmts)
      icur = importer.str2icurry(string, currypath)
      module = self.import_(icur)
      del self.modules[icur.name]
      expr = self.expr(module.expression)
      self.step(expr)
      return expr
    else:
      raise TypeError('expected mode "module" or "expr"')

  # Evaluating.
  # ===========
  def eval(self, goal, converter='default'):
    '''
    Evaluate a Curry goal.

    The first argument may be a Curry expression or a list of arguments
    used to construct one (as ``expr`` would).

    A converter may be specified to control the way results are returned.
    '''
    if not isinstance(goal, Node):
      goal = self.expr(goal)
    convert = conversions.getconverter(
        converter if converter != 'default'
                  else self.flags['defaultconverter']
      )
    results = runtime.Evaluator(self, goal).eval()
    if convert is None:
      return results
    else:
      return (convert(self, result) for result in results)

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

