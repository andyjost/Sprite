import runpy
from ... import exceptions

__all__ = ['load_module']

def load_module(interp, pyfile):
  assert pyfile.endswith('.py')
  globals_ = {'interp': interp}
  pymodule = runpy.run_path(pyfile, init_globals=globals_)
  cymodule = pymodule['_module_']
  return cymodule
