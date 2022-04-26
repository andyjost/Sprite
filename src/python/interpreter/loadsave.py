from .. import config, exceptions, icurry, inspect, utility
from ..utility.binding import binding
from ..utility.strings import ensure_str
from ..objects import handle
import logging, os, six
from six.moves import cStringIO as StringIO

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
      Indicates a goal to evaluate when running the module.  By default,
      running the generated code imports the module but evaluates nothing.

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
    interp.symbol('%s.%s' % (icy.fullname, goal)) # Raises SymbolLookupError on failure
  h = handle.getHandle(interp.import_(icy))
  if logger.isEnabledFor(logging.INFO):
    logger.info(
        'Saving Curry module %r to %r (%r type%s, %r symbol%s)'
      , icy.fullname, filename or '<string>'
      , len(h.types), '' if len(h.types) == 1 else 's'
      , len(h.symbols), '' if len(h.symbols) == 1 else 's'
      )
  be = interp.backend
  target_object = be.compile(interp, h.icurry)
  if isinstance(filename, six.string_types):
    with open(filename, 'w') as stream:
      be.write_module(target_object, stream, goal=goal, **kwds)
  elif not filename:
    stream = StringIO()
    be.write_module(target_object, stream, goal=goal, **kwds)
    return stream.getvalue()
  else:
    stream = filename
    be.write_module(target_object, stream, goal=goal, **kwds)

