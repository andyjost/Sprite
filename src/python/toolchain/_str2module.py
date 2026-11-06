from ..utility.locking import Lock as _SpriteLock
from .. import config
from . import makecurry
from ..objects import handle
from ..toolchain import plans
from ..utility import filesys
from ..utility import filesys, formatDocstring
import logging, os, shutil, tempfile, weakref, threading

__all__ = ['is_temporary', 'str2module']
logger = logging.getLogger(__name__)

# The directories this module made for the modules compiled from strings in
# this process.  Tiered execution leaves such a module interpreted (see
# backends.cxx.tiered).
_TEMPORARY_DIRS = set()
# Finalizers append only. Purge before traversing, and log after unlocking.
_pending_removals = []
_dirs_lock = _SpriteLock()

def _purge_dirs():
  removed = []
  while _pending_removals:
    directory = _pending_removals.pop()
    _TEMPORARY_DIRS.discard(directory)
    removed.append(directory)
  return removed

def _log_removals(directories):
  for directory in directories:
    logger.debug('Removing Curry module directory: %r', directory)

def is_temporary(filename):
  '''Tells whether ``filename`` lies in a directory str2module made.'''
  filename = os.path.realpath(filename)
  with _dirs_lock:
    removed = _purge_dirs()
    directories = tuple(_TEMPORARY_DIRS)
  _log_removals(removed)
  return any(filename.startswith(os.path.realpath(directory) + os.sep)
      for directory in directories)

@formatDocstring(config.python_package_name())
def str2module(
    interp
  , moduletext
  , currypath=None
  , modulename=config.interactive_modname()
  , keep_temp_files=False
  , postmortem=False
  ):
  '''
  Load a Curry module from a string.

  This generates new Curry code in a temporary directory.  The ICurry object
  stores the name of that directory in the 'all.tmpd' metadata.  A hook is
  created to delete the temporary directory when the ICurry object is
  destroyed.

  Args:
    interp:
        The interpreter in charge of this compilation.
    moduletext:
        A string containing a Curry module definition to compile.
    currypath:
        A sequence of paths to search (i.e., CURRYPATH split on ':').  By default,
        ``{0}.path`` is used.
    modulename:
        The module name.
    keep_temp_files:
        Whether to keep intermediate files.
    postmoretem:
        Whether to copy intermediate files to the current working directory upon
        failure.

  Returns:
    A pair of the imported module and ICurry object.
  '''
  if keep_temp_files and isinstance(keep_temp_files, str):
    parentdir = filesys.getdir(keep_temp_files)
  else:
    parentdir = tempfile.gettempdir()
  moduledir = tempfile.mkdtemp(prefix='sprite-', dir=parentdir)
  logger.debug('Created directory %r for a dynamic Curry module', moduledir)
  with _dirs_lock:
    removed = _purge_dirs()
    _TEMPORARY_DIRS.add(moduledir)
  _log_removals(removed)
  try:
    curryfile = os.path.join(moduledir, modulename.replace('.', os.sep) + '.curry')
    os.makedirs(os.path.dirname(curryfile), exist_ok=True)
    with open(curryfile, 'w', encoding='utf-8') as ostream:
      ostream.write(moduletext)
    moduleobj = interp._import_(modulename, currypath=[moduledir] + currypath)
    moduleobj.__file__ = curryfile
    h = handle.Handle(moduleobj)
    icur = h.icurry
    icur.__file__ = curryfile
    icur.update_metadata({'all.tmpd': moduledir})
    if not keep_temp_files:
      icur._finalizer_ = weakref.finalize(icur, _rmdir, moduledir)
    return moduleobj, icur
  except:
    if postmortem:
      dst = os.path.basename(moduledir)
      try:
        shutil.copytree(moduledir, dst)
      except Exception as e:
        logger.error('Failed to copy %r to %r: %r', moduledir, dst, e)
      else:
        logger.info('****** Copied %r to %r for postmortem', moduledir, dst)
    _rmdir(moduledir)
    raise

def _rmdir(moduledir):
  # Even an enclosing registry section must never enter logging here:
  # a logging handler may call is_temporary while holding its own lock.
  _pending_removals.append(moduledir)
  shutil.rmtree(moduledir, ignore_errors=os.name == 'nt')
