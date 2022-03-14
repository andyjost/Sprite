from .. import config, utility
from ..utility.binding import binding
from ..objects import handle
import logging, os, runpy, six
from six.moves import cStringIO as StringIO

logger = logging.getLogger(__name__)

__all__ = ['load', 'save']

@utility.formatDocstring(config.python_package_name())
def load(interp, name):
  '''
  Loads a Curry module saved with :func:`save`.

  Aside from how the file is located, this follows the import protocol, so the
  module is added to the interpreter's ``modules`` dict.

  Args:
    name:
      An importable Python module name or a path to a Python file.  If this
      ends with ``.py``, it is assumed to be a file name.  If a module name is
      given, ``sys.path`` (as opposed to ``{0}.path``) is searched.

  Returns:
    A :class:`CurryModule <{0}.objects.CurryModule>`.
  '''
  logger.info('Loading %r', name)
  globals_ = {'interp':interp}
  if name.endswith('.py'):
    pymodule = runpy.run_path(name, init_globals=globals_)
    cymodule = pymodule['_module_']
  else:
    pymodule = __import__(name, globals=globals_)
    cymodule = pymodule._module_
  if logger.isEnabledFor(logging.INFO):
    h = handle.getHandle(cymodule)
    logger.info(
        'Loaded Curry module %r from %r (%r types, %r symbols)'
      , h.fullname, name, len(h.types), len(h.symbols)
      )
  return cymodule

def save(interp, cymodule, filename=None, goal=None):
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

  Returns:
    If ``filename`` is None, the module contents are returned as a string.
    Otherwise, None.
  '''
  h = handle.getHandle(cymodule)
  if goal is not None:
    h.getsymbol(goal) # Raises SymbolLookupError on failure
  if logger.isEnabledFor(logging.INFO):
    logger.info(
        'Saving Curry module %r to %r (%r types, %r symbols)'
      , h.fullname, filename or '<string>', len(h.types), len(h.symbols)
      )
  be = interp.backend
  target_object = be.compile(interp, h.icurry)
  if isinstance(filename, six.string_types):
    with open(filename, 'w') as stream:
      be.write_module(target_object, stream, goal=goal)
  elif not filename:
    stream = StringIO()
    be.write_module(target_object, stream, goal=goal)
    return stream.getvalue()
  else:
    stream = filename
    be.write_module(target_object, stream, goal=goal)

