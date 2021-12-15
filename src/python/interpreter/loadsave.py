from ..objects import handle
import logging, runpy

logger = logging.getLogger(__name__)

__all__ = ['load', 'save']

def load(interp, name):
  '''
  Load a saved Curry module.  The (Python) module file must be importable.

  Args:
    name:
      An importable Python module name or path to a Python file.

  Returns:
    An instance of object.CurryModule.
  '''
  logger.info('Loading %r', name)
  if name.endswith('.py'):
    pymodule = runpy.run_path(name)
    cymodule = pymodule['_module_']
  else:
    pymodule = __import__(name)
    cymodule = pymodule._module_
  if logger.isEnabledFor(logging.INFO):
    h = handle.getHandle(cymodule)
    logger.info(
        'Loaded Curry module %r from %r (%r types, %r symbols)'
      , h.fullname, name, len(h.types), len(h.symbols)
      )
  return cymodule

def save(interp, cymodule, filename=None):
  '''
  Save a Curry module.

  Args:
    cymodule:
      The argument to dump.  Must be a valid argument to inspect.geticurry.

    filename:
      A file name, stream, or None.  If None, a string is returned.  Otherwise,
      the file is created, if specified, and the output is written to the file
      or stream.

  Returns:
    If ``filename`` is None, the module contents are returned as a string.
    Otherwise, None.
  '''
  h = handle.getHandle(cymodule)
  if logger.isEnabledFor(logging.INFO):
    logger.info(
        'Saving Curry module %r to %r (%r types, %r symbols)'
      , h.fullname, filename, len(h.types), len(h.symbols)
      )
  cc = interp.context.compiler
  ir = cc.compile(interp, h.icurry)
  return ir.dump(filename)

