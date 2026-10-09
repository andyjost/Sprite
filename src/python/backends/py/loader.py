'''
Loads a generated Python module into an interpreter.

The module is loaded through importlib, so CPython's bytecode cache applies:
a valid cache beside the file (``__pycache__``) is read instead of the source.
The cache is a product of the toolchain, like the file itself, not a by-product
of an import.  The toolchain writes it when it writes the file (see
``Json2Py``), and the loader writes it when it finds none or a stale one, with
or without ``-B``.  So a generated module is compiled from source at most once
per change, not in every process.  Compiling the generated Prelude from source
costs about 0.2 s; reading its cache costs a few milliseconds.
'''
from ... import exceptions
from . import toolchain
import importlib.machinery, os

__all__ = ['load_module']

def load_module(interp, pyfile, from_plan=False):
  assert pyfile.endswith('.py')
  name = os.path.splitext(os.path.basename(pyfile))[0]
  # A file from an older installation, or one whose cache was removed, gets
  # its cache here.  importlib itself writes none under -B, which the test
  # drivers use.
  toolchain.ensure_bytecode(pyfile)
  loader = importlib.machinery.SourceFileLoader(name, pyfile)
  code = loader.get_code(name)
  globals_ = {'__name__': name, '__file__': pyfile, 'interp': interp}
  exec(code, globals_)
  return globals_['_module_']
