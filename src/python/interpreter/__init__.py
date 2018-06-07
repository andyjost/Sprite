'''
A pure-Python Curry interpreter.
'''

from ..icurry import *
from . import analysis
from . import conversions
from . import function_compiler
from .. import importer
from . import symbols
from . import prelude
from .runtime import InfoTable, Node, T_FAIL, T_FUNC, T_CHOICE, T_CTOR
from .show import Show
from ..visitation import dispatch
import collections
import logging
import os
import re
import sys
import types

# Logging setup.
# ==============
logger = logging.getLogger(__name__)
LOG_LEVELS = {k:getattr(logging, k)
    for k in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
  }
DEFAULT_LOG_LEVEL = 'ERROR'
LOG_FILE = os.environ.get('SPRITE_LOG_FILE', '-')
logging.basicConfig(
    level=LOG_LEVELS[
        os.environ.get('SPRITE_LOG_LEVEL', DEFAULT_LOG_LEVEL).upper()
      ]
  , format='%(asctime)s [%(levelname)s] %(message)s'
  , datefmt='%m/%d/%Y %H:%M:%S'
  , **({'filename': LOG_FILE} if LOG_FILE not in ['-', ''] else {})
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
      ``defaultconverter`` ('topython'|*None*)
          Indicates the conversion to apply to results of eval.
      ``trace`` (True|*False*)
          Shows the effect of each step in a computation.
  '''
  def __new__(cls, flags={}):
    self = object.__new__(cls)
    self.stdin = sys.stdin
    self.stdout = sys.stdout
    self.stderr = sys.stderr
    self.modules = {}
    self.flags = {'debug':True, 'defaultconverter':None, 'trace':False}
    envflags = os.environ.get('SPRITE_INTERPRETER_FLAGS')
    if envflags is not None:
      self.flags.update({
          k:_flagval(v) for e in envflags.split(',') for k,v in [e.split(':')]
        })
    self.flags.update(flags)
    self.path = filter(lambda x:x, os.environ.get('CURRYPATH', '').split(':'))
    setattr(self, '.cache', {})
    return self

  def __init__(self, flags={}):
    self.prelude = self.import_(
        "Prelude", extern=prelude.Prelude, export=prelude.exports()
      , alias=prelude.aliases()
      )
    self.step = runtime.get_stepper(self)

  # Importing.
  # ==========
  @dispatch.on('arg')
  def import_(self, arg, currypath=None, extern=True, export=(), alias=()):
    '''
    Import one or more Curry modules.

    Parameters:
    -----------
    ``arg``
        A module descriptor indicating what to import.  A module descriptor is
        a module name (string), ``curry.icurry.IModule`` object, or a sequence
        of module descriptors.
    ``currypath``
        The search path for Curry files.  By default, ``self.path`` is used.
    ``extern``
        An instance of ``curry.icurry.IModule`` used to resolve external
        declarations.
    ``export``
        A set of symbols exported unconditionally from ``extern``.  These will
        be copied into the imported module.
    ``alias``
        A set of name-target pairs specifying aliases.  For each alias, the
        module produced will have a binding called ``name`` referring to
        ``target``.

    Returns:
    --------
    A ``CurryModule`` or sequence thereof.
    '''
    raise TypeError('cannot import type "%s"' % type(arg).__name__)

  @import_.when(str)
  def import_(self, modulename, currypath=None, **kwds):
    try:
      return self.modules[modulename]
    except KeyError:
      logger.debug('Importing %s' % modulename)
      currypath = self.path if currypath is None else currypath
      icur = importer.getICurryForModule(modulename, currypath)
      return self.import_(icur, **kwds)

  @import_.when(collections.Sequence, no=str)
  def import_(self, seq, *args, **kwds):
    return [self.import_(item, *args, **kwds) for item in seq]

  @import_.when(IModule)
  def import_(
      self, imodule, currypath=None, extern=None, export=(), alias=()
    ):
    if imodule.name not in self.modules:
      imodule.merge(extern, export)
      moduleobj = CurryModule(imodule.name)
      moduleobj.__file__ = imodule.filename
      self.modules[imodule.name] = moduleobj
      self._loadsymbols(imodule, moduleobj, extern=extern)
      self._compile(imodule, moduleobj, extern=extern)
      for name, target in alias:
        if hasattr(moduleobj, name):
          raise ValueError("cannot alias previously defined name '%s'" % name)
        setattr(moduleobj, name, getattr(moduleobj, target))
    return self.modules[imodule.name]

  # Loading Symbols.
  # ================
  @dispatch.on('idef')
  def _loadsymbols(self, idef, moduleobj, extern=None): #pragma: no cover
    '''
    Load symbols (i.e., constructor and functions names) from the ICurry
    definition ``idef`` into module ``moduleobj``.
    '''
    raise RuntimeError("unhandled ICurry type during symbol loading: '%s'" % type(idef))

  @_loadsymbols.when(collections.Sequence, no=(str,IType))
  def _loadsymbols(self, seq, *args, **kwds):
    for item in seq:
      self._loadsymbols(item, *args, **kwds)

  @_loadsymbols.when(IType)
  def _loadsymbols(self, itype, moduleobj, extern=None):
    if itype:
      return self._loadsymbols(list(itype), moduleobj, extern)
    elif extern is not None:
      try:
        itype.constructors = extern.types[itype.ident].constructors
      except KeyError:
        pass
      else:
        return self._loadsymbols(itype, moduleobj)
    logging.warn(
        '%s has no constructors and no external definition was found.'
            % itype.ident
      )

  @_loadsymbols.when(collections.Mapping)
  def _loadsymbols(self, mapping, moduleobj, extern=None):
    for item in mapping.itervalues():
      self._loadsymbols(item, moduleobj, extern)

  @_loadsymbols.when(IModule)
  def _loadsymbols(self, imodule, moduleobj, extern=None):
    for modulename in imodule.imports:
      self.import_(modulename)
    self._loadsymbols(imodule.types, moduleobj, extern)
    self._loadsymbols(imodule.functions, moduleobj, extern)
    # Stash the type defs in the module; e.g.:
    #   .types = {'Bool': [<NodeInfo for True>, <NodeInfo for False>]}
    setattr(moduleobj, '.types'
      , { typename.basename:
            [getattr(moduleobj, ctor.ident.basename) for ctor in ctors]
            for typename,ctors in imodule.types.items()
          }
      )

  @_loadsymbols.when(IConstructor)
  def _loadsymbols(self, icons, moduleobj, extern=None):
    # For builtins, the 'py.tag' metadata contains the tag.
    builtin = 'py.tag' in icons.metadata
    info = InfoTable(
        icons.ident.basename
      , icons.arity
      , T_CTOR + icons.index if not builtin else icons.metadata['py.tag']
      , _no_step if not builtin else _unreachable
      , Show(self, getattr(icons.metadata, 'py.format', None))
      )
    symbols.insert(
        moduleobj, icons.ident.basename, runtime.NodeInfo(icons.ident, info)
      )

  @_loadsymbols.when(IFunction)
  def _loadsymbols(self, ifun, moduleobj, extern=None):
    info = InfoTable(
        ifun.ident.basename
      , ifun.arity, T_FUNC, None, Show(self)
      )
    symbols.insert(
        moduleobj, ifun.ident.basename, runtime.NodeInfo(ifun.ident, info)
      )

  # Compiling.
  # ==========
  @dispatch.on('idef')
  def _compile(self, idef, moduleobj, extern=None): # pragma: no cover
    '''Compile the ICurry definitions from ``idef`` into module ``moduleobj``'''
    assert False

  @_compile.when(collections.Mapping)
  def _compile(self, mapping, *args, **kwds):
    for item in mapping.itervalues():
     self._compile(item, *args, **kwds)

  @_compile.when(IModule)
  def _compile(self, imodule, moduleobj, extern=None):
    self._compile(imodule.functions, moduleobj, extern)

  @_compile.when(IFunction)
  def _compile(self, ifun, moduleobj, extern=None):
    info = symbols.lookupSymbol(moduleobj, ifun.ident).info
    info.step = function_compiler.compile_function(self, ifun, extern)

  # Conversions.
  # ============
  box = conversions.box
  currytype = conversions.currytype
  expr = conversions.expr
  topython = conversions.topython
  unbox = conversions.unbox

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
  def eval(self, *args, **kwds):
    '''
    Evaluate a Curry goal.

    Parameters:
    -----------
    ``*args``
        Positional arguments that specify the goal.  These are passed to
        ``Interpreter.expr``.
    ``converter``
        Keyword-only argument specifying the converter to use when returning
        results.  The default is 'default'.  See ``conversions.getconverter``.

    Returns:
    --------
    A generator producing the values of the specified Curry program.
    '''
    converter = kwds.pop('converter', 'default')
    convert = conversions.getconverter(
        converter if converter != 'default' else self.flags['defaultconverter']
      )
    goal = self.expr(*args)
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

def _flagval(v):
  '''Try to interpret the string ``v`` as a flag value.'''
  try:
    return {'True':True, 'False':False}[v]
  except KeyError:
    pass
  try:
    return int(v)
  except ValueError:
    pass
  return v

