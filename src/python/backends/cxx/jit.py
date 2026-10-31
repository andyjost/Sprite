"""Selection of the compiled backend for interpreted functions."""
from ... import config
from ...exceptions import FlagError
import importlib, logging, sys

logger = logging.getLogger(__name__)
_warned = False
_logged = set()

def select(interp):
  """Validate forced backends and select auto once for this interpreter."""
  global _warned
  requested = interp.flags['jit_backend']
  try:
    llvm = importlib.import_module('llvmlite')
  except ImportError:
    llvm = None
  cxx = None if sys.platform == 'win32' else config.cxx_tool()
  backend = requested
  if requested == 'auto':
    backend = 'llvm' if llvm is not None else 'cxx' if cxx else None
  if backend == 'llvm' and llvm is None:
    raise FlagError('jit_backend:llvm needs llvmlite; pip install curry[jit]')
  if backend == 'cxx' and sys.platform == 'win32':
    raise FlagError(
        'jit_backend:cxx is unavailable on Windows; use jit_backend:llvm '
        'and pip install curry[jit]'
      )
  if backend == 'cxx' and cxx is None:
    raise FlagError('jit_backend:cxx needs a C++ compiler; install a C++ compiler')
  if requested == 'llvm':
    from . import llvmjit
    try:
      llvmjit._get()
    except llvmjit.Unavailable as exc:
      raise FlagError(
          'jit_backend:llvm is unavailable: %s; pip install curry[jit] '
          'and use an installation built with the clang JIT helpers' % exc
        ) from None
  interp._jit_backend = backend
  if backend is None:
    reason = 'llvmlite and a C++ compiler are unavailable; pip install curry[jit] or install a C++ compiler'
    if not _warned:
      _warned = True
      logger.warning('jit: no backend, interpreter only (%s)', reason)
    return None
  detail = 'llvmlite %s' % llvm.__version__ if backend == 'llvm' else str(cxx)
  if (backend, detail) not in _logged:
    _logged.add((backend, detail))
    logger.info('jit: backend %s (%s)', backend, detail)
  return backend

def backend(interp):
  # The internal Interpreter flag dictionary also supports direct changes.
  key = interp.flags['jit_backend']
  if getattr(interp, '_jit_selection', None) != key:
    select(interp)
    interp._jit_selection = key
  return interp._jit_backend
