from .. import encoding
from . import function_compiler
from .. import icurry
from .. import importer
from . import lookup
from . import runtime
from . import show
from .. import visitation
import collections
import logging
import types

logger = logging.getLogger(__name__)

class CurryModule(types.ModuleType):
  def __init__(self, *args, **kwds):
    super(CurryModule, self).__init__(*args, **kwds)
    setattr(self, '.symbols', {})
    setattr(self, '.types', {})
  def __repr__(self):
    return "<curry module '%s'>" % self.__name__
  __str__ = __repr__

# FIXME: ICurry does not tell us which symbols are private.  For now, all
# symbols are treated as public.
def insertSymbol(module, basename, nodeinfo, private=False):
  '''
  Inserts a symbol into the given module.

  All symbols are added to the module's '.symbols' dict.  Public symbols are
  also bound directly to the module itself.

  Parameters:
  -----------
  ``module``
      An instance of ``CurryModule``.
  ``basename``
      A stirng containing the unqualified symbol name.
  ``nodeinfo``
      The nodeinfo for this symbol.
  ``private``
      Whether this is a private symbol.

  Returns:
  --------
  Nothing.
  '''
  logging.debug(
      'Inserting symbol %s into module %s' % (basename, module.__name__)
    )
  getattr(module, '.symbols')[basename] = nodeinfo
  if not private and encoding.isaCurryIdentifier(basename):
    setattr(module, basename, nodeinfo)


@visitation.dispatch.on('idef')
def loadSymbols(interp, idef, moduleobj, extern=None, **kwds): #pragma: no cover
  '''
  Load symbols (i.e., constructor and functions names) from the ICurry
  definition ``idef`` into module ``moduleobj``.
  '''
  raise RuntimeError("unhandled ICurry type during symbol loading: '%s'" % type(idef))

@loadSymbols.when(collections.Sequence, no=(str,icurry.IType))
def loadSymbols(interp, seq, *args, **kwds):
  for item in seq:
    loadSymbols(interp, item, *args, **kwds)

@loadSymbols.when(icurry.IType)
def loadSymbols(interp, itype, moduleobj, extern=None):
  if itype:
    return loadSymbols(interp, list(itype), moduleobj, extern, itype=itype)
  elif extern is not None:
    try:
      itype.constructors = extern.types[itype.ident].constructors
    except KeyError:
      pass # fall through to the error
    else:
      return loadSymbols(interp, itype, moduleobj)
  raise ValueError(
      '%s has no constructors and no external definition was found.'
          % itype.ident
    )

@loadSymbols.when(collections.Mapping)
def loadSymbols(interp, mapping, moduleobj, **kwds):
  for item in mapping.itervalues():
    loadSymbols(interp, item, moduleobj, **kwds)

@loadSymbols.when(icurry.IModule)
def loadSymbols(interp, imodule, moduleobj, **kwds):
  for modulename in imodule.imports:
    import_(interp, modulename)
  loadSymbols(interp, imodule.types, moduleobj, **kwds)
  loadSymbols(interp, imodule.functions, moduleobj, **kwds)
  # Stash the type defs in the module; e.g.:
  #   .types = {'Bool': [<NodeInfo for True>, <NodeInfo for False>]}
  setattr(moduleobj, '.types'
    , { typename.basename:
          [getattr(moduleobj, ctor.ident.basename) for ctor in ctors]
          for typename,ctors in imodule.types.items()
        }
    )

@loadSymbols.when(icurry.IConstructor)
def loadSymbols(interp, icons, moduleobj, extern=None, itype=None):
  # For builtins, the 'py.tag' metadata contains the tag.
  builtin = 'py.tag' in icons.metadata
  metadata = icurry.getmd(icons, extern, itype=itype)
  info = runtime.InfoTable(
      icons.ident.basename
    , icons.arity
    , runtime.T_CTOR + icons.index if not builtin else metadata['py.tag']
    , _no_step if not builtin else _unreachable
    , show.Show(interp, getattr(metadata, 'py.format', None))
    )
  insertSymbol(
      moduleobj, icons.ident.basename, runtime.NodeInfo(icons.ident, info)
    )

@loadSymbols.when(icurry.IFunction)
def loadSymbols(interp, ifun, moduleobj, extern=None):
  metadata = icurry.getmd(ifun, extern)
  info = runtime.InfoTable(
      ifun.ident.basename
    , ifun.arity, runtime.T_FUNC, None
    , show.Show(interp, getattr(metadata, 'py.format', None))
    )
  insertSymbol(
      moduleobj, ifun.ident.basename, runtime.NodeInfo(ifun.ident, info)
    )

@visitation.dispatch.on('arg')
def import_(interp, arg, currypath=None, extern=True, export=(), alias=()):
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
def import_(interp, modulename, currypath=None, **kwds):
  try:
    return interp.modules[modulename]
  except KeyError:
    logger.debug('Importing %s' % modulename)
    currypath = interp.path if currypath is None else currypath
    icur = importer.getICurryForModule(modulename, currypath)
    return import_(interp, icur, **kwds)

@import_.when(collections.Sequence, no=str)
def import_(interp, seq, *args, **kwds):
  return [import_(interp, item, *args, **kwds) for item in seq]

@import_.when(icurry.IModule)
def import_(
    interp, imodule, currypath=None, extern=None, export=(), alias=()
  ):
  if imodule.name not in interp.modules:
    imodule.merge(extern, export)
    moduleobj = CurryModule(imodule.name)
    moduleobj.__file__ = imodule.filename
    interp.modules[imodule.name] = moduleobj
    loadSymbols(interp, imodule, moduleobj, extern=extern)
    compileICurry(interp, imodule, moduleobj, extern=extern)
    for name, target in alias:
      if hasattr(moduleobj, name):
        raise ValueError("cannot alias previously defined name '%s'" % name)
      setattr(moduleobj, name, getattr(moduleobj, target))
  return interp.modules[imodule.name]

@visitation.dispatch.on('idef')
def compileICurry(interp, idef, moduleobj, extern=None): # pragma: no cover
  '''Compile the ICurry definitions from ``idef`` into module ``moduleobj``'''
  assert False

@compileICurry.when(collections.Mapping)
def compileICurry(interp, mapping, *args, **kwds):
  for item in mapping.itervalues():
   compileICurry(interp, item, *args, **kwds)

@compileICurry.when(icurry.IModule)
def compileICurry(interp, imodule, moduleobj, extern=None):
  compileICurry(interp, imodule.functions, moduleobj, extern)

@compileICurry.when(icurry.IFunction)
def compileICurry(interp, ifun, moduleobj, extern=None):
  info = lookup._symbol(moduleobj, ifun.ident).info
  info.step = function_compiler.compile_function(interp, ifun, extern)

def _no_step(*args, **kwds): #pragma: no cover
  pass

def _unreachable(*args, **kwds): #pragma: no cover
  assert False
