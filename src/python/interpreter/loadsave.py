from .. import config, exceptions, icurry, inspect, toolchain, utility
from ..typecheck import defaulting, goals
from ..utility.binding import binding
from ..utility.strings import ensure_str
from ..objects import handle
import io, logging, os

logger = logging.getLogger(__name__)

__all__ = ['load', 'save']

def load(interp, filename):
  '''
  Loads a Curry module saved with :func:`save`.

  Aside from how the file is located, this follows the import protocol, so the
  module is added to the interpreter's ``modules`` dict.

  Args:
    filename:
      The path to a file to load.  The file type and suffix must match the
      interpreter.

  Returns:
    A :class:`CurryModule <{0}.objects.CurryModule>`.
  '''
  logger.info('Loading %r', filename)
  be = interp.backend
  if not filename.endswith(be.object_file_extension):
    raise exceptions.PrerequisiteError(
        'Cannot load %r into the %r backend.  Expecting extension %r.'
            % (filename, be.backend_name, be.object_file_extension)
      )
  cymodule = be.load_module(interp, filename)
  if logger.isEnabledFor(logging.INFO):
    h = handle.getHandle(cymodule)
    logger.info(
        'Loaded Curry module %r from %r (%r type%s, %r symbol%s)'
      , h.fullname, filename
      , len(h.types), '' if len(h.types) == 1 else 's'
      , len(h.symbols), '' if len(h.symbols) == 1 else 's'
      )
  return cymodule

def save(interp, cymodule, filename=None, goal=None, **kwds):
  '''
  Saves a Curry module.

  Args:
    cymodule:
      The argument to dump.  Must be a valid argument to inspect.geticurry.

    filename:
      A file name, stream, or None.  If None, a string is returned.  Otherwise,
      the file is created, if specified, and the output is written to the file
      or stream.

    goal:
      The goal the saved program evaluates when it runs, unless ``-g`` on
      its command line names another.  A program needs one: without
      ``goal`` the call raises ``ValueError`` (issue #35).  To save a module
      without a main program, for :func:`load`, pass ``module_main=False``.
      A goal with class constraints and no signature is defaulted with the
      table of the PAKCS REPL at run time; the file records its type, so it
      runs from any directory.  A goal the table cannot default raises
      here, at save time.  On the C++ backend the saved file is C++ source,
      and its record names the source of the module relative to the
      directory of the object (the product directory beside the source,
      ``.curry/<subdir>/``).  Compile the file in that directory, as
      ``sprite-make --so`` does; an object compiled elsewhere loads, but
      its module has no source file (``backends.cxx.loader.source_file``).

    kwds:
      Additional keyword arguments passed to ``IBackend.write_module``.
      Possibly specific to the backend.
  Returns:
    If ``filename`` is None, the module contents are returned as a string.
    Otherwise, None.
  '''
  icy = inspect.geticurry(cymodule)
  if not isinstance(icy, icurry.IModule):
    raise exceptions.ModuleLookupError(
        'Cannot get ICurry for %r object' % type(cymodule).__name__
      )
  if goal is not None:
    goal = ensure_str(goal)
    symbol = interp.symbol('%s.%s' % (icy.fullname, goal)) # Raises SymbolLookupError on failure
    goalscheme = goal_scheme_text(interp, symbol)
    if goalscheme is not None:
      kwds['goalscheme'] = goalscheme
  elif kwds.get('module_main', True):
    raise ValueError(
        'curry.save needs a goal: pass goal=NAME to name the goal the saved '
        'program evaluates, or module_main=False to save a module without a '
        'main program'
      )
  h = handle.getHandle(interp.import_(icy))
  icy = compilable_icurry(cymodule, h.icurry)
  if logger.isEnabledFor(logging.INFO):
    logger.info(
        'Saving Curry module %r to %r (%r type%s, %r symbol%s)'
      , icy.fullname, filename or '<string>'
      , len(h.types), '' if len(h.types) == 1 else 's'
      , len(h.symbols), '' if len(h.symbols) == 1 else 's'
      )
  be = interp.backend
  target_object = be.compile(interp, icy)
  if isinstance(filename, str):
    with open(filename, 'w', encoding='utf-8') as stream:
      be.write_module(target_object, stream, goal=goal, **kwds)
  elif not filename:
    stream = io.StringIO()
    be.write_module(target_object, stream, goal=goal, **kwds)
    return stream.getvalue()
  else:
    stream = filename
    be.write_module(target_object, stream, goal=goal, **kwds)


def goal_scheme_text(interp, symbol):
  '''
  The FlatCurry type of a goal as text for the footer of a saved module, or
  None for a goal without dictionary parameters.  Applies the table of the
  PAKCS REPL once, so that a goal the table cannot default fails here.

  Raises:
    CurryTypeError:
        The goal has parameters but no type, or the table cannot default
        its constraints.
  '''
  if symbol.info.arity == 0:
    return None
  scheme = interp.sigtable.lookup(symbol, required=True)
  if not scheme.ndicts:
    return None
  defaulting.default_scheme(
      scheme, type_arity=goals.type_arity(interp)
    , hint='add a type signature to the goal'
    )
  return goals.flat_type_text(scheme)

def compilable_icurry(cymodule, icy):
  '''
  The ICurry to compile for a saved module.  A module loaded from generated
  code holds its bill of materials: every function body is ``IExempt`` and
  the code lives in the metadata, so compiling it again would write a
  failing stub for every function.  The ICurry with the bodies is read from
  the JSON file of the module in that case.
  '''
  functions = list(icy.functions.values())
  exempt = [
      f for f in functions
        if isinstance(getattr(f.body, 'block', None), icurry.IExempt)
    ]
  if not exempt:
    return icy
  jsonfile = inspect.getjsonfile(cymodule)
  if jsonfile is None:
    raise exceptions.CompileError(
        'cannot save %s: %d of its %d functions have no ICurry body and no '
        'ICurry-JSON file is found beside %r'
            % (icy.fullname, len(exempt), len(functions), icy.filename)
      )
  logger.info('Reading the ICurry of %s from %s', icy.fullname, jsonfile)
  return toolchain.loadjson(jsonfile)
