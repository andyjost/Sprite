from .. import inspect
import runpy

def load(interp, name):
  '''
  Load a saved Curry module.  The (Python) module file must be importable.

  Parameters:
  -----------
    ``name``
      An importable Python module name or path to a Python file.

  Returns:
  --------
    An instance of object.CurryModule.
  '''
  if name.endswith('.py'):
    pymodule = runpy.run_path(name)
    return pymodule['_module_']
  else:
    pymodule = __import__(name)
    return pymodule._module_

def save(interp, cymodule, filename=None):
  '''
  Save a Curry module.

  Parameters:
  -----------
    ``cymodule``
      The argument to dump.  Must be a valid argument to inspect.geticurry.

    ``filename``
      A file name, stream, or None.  If None, a string is returned.  Otherwise,
      the file is created, if specified, and the output is written to the file
      or stream.

  Returns:
  --------
    If ``filename`` is None, the module contents are returned as a string.
    Otherwise, None.
  '''
  cc = interp.context.compiler
  icy = inspect.geticurry(cymodule)
  ir = cc.compile(interp, icy)
  return ir.dump(filename)

