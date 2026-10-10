'''
The lock of the products of a module.

Two processes may compile one module into one product directory at once:
the background child of the tiered compile and a foreground ``sprite-make
--so`` (the sequence of the Quickstart, which saves, compiles and loads a
module the import compiles in the background), two sessions over one tree,
or two test processes that import one stale module.  Both would write
``<Module>.cpp`` and ``<Module>.so`` in place: the code generator writes
the generated file in place, so one compiler could read a torn file, and a
failed background compile turns a later load into a refusal.

So the steps of the plan for a module run under a lock: an advisory lock
(``flock``) on a lock file beside the products, ``<Module>.lock`` in the
product directory, held from the first step that must run to the end of
the plan (``_makecurry.Maker.make``), and by the compile on first use
(``backends.cxx.materialize.compile_pending``), which writes the same
files outside the plan.  The loser waits; once it holds the lock it looks
at the files of the module again, and when the winner wrote a current
object it skips its compile.  The lock dies with its process, so a killed
compile leaves no stale lock, and the lock file itself is empty and may
stay.  A product directory that cannot be made or written gets no lock:
nothing can be compiled into it, and the steps report that themselves.  A
file system that refuses ``flock`` gives no lock either, and the compile
runs unlocked, as before the lock.

The lock is per module, so ``sprite-make --jobs`` compiles different
modules at once as before, and a compile that imports the modules of its
imports takes their locks in the order of the import graph, which is
acyclic.  Within a process the lock is re-entrant: a nested plan of the
same module (none is known) finds the lock held and goes on.
'''
from . import _filenames
import contextlib, fcntl, logging, os

__all__ = ['lockfile', 'locked']

logger = logging.getLogger(__name__)

SUFFIX = '.lock'

# The locks this process holds: the lock file to its descriptor.
_held = {}

def lockfile(filename):
  '''
  The lock file of the module of ``filename``, a file of its chain (the
  source, the ICurry, the JSON, the generated file or the object):
  ``<Module>.lock`` in the product directory beside them.
  '''
  return _filenames.replacesuffix(filename, SUFFIX)

def _open(path):
  '''
  Opens the lock file, making the product directory when it is missing.
  None when neither can be done: the directory cannot be written.
  '''
  try:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return os.open(path, os.O_RDWR | os.O_CREAT, 0o666)
  except OSError as exc:
    logger.debug('No lock for %r (%s)', path, exc)
    return None

@contextlib.contextmanager
def locked(filename):
  '''
  Holds the lock of the module of ``filename`` for the duration of the
  context.  Yields True when another process held the lock and this one
  waited for it: the files of the module may have changed, and the caller
  looks at them again before it writes.  Yields False when the lock was
  free, is held by this process already, or cannot be made.
  '''
  path = lockfile(filename)
  if path in _held:
    yield False
    return
  fd = _open(path)
  if fd is None:
    yield False
    return
  waited = False
  try:
    try:
      fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
      waited = True
      logger.info(
          'Waiting for another process that compiles %s (the lock %s)'
        , os.path.basename(filename), path
        )
      fcntl.flock(fd, fcntl.LOCK_EX)
  except OSError as exc:
    # A file system without flock (ENOLCK on a network file system
    # without a lock service, ENOSYS, EINVAL): no lock, as in an
    # unwritable directory, and the compile runs as it did before the
    # lock.
    logger.debug('No lock for %r (%s)', path, exc)
    os.close(fd)
    yield False
    return
  _held[path] = fd
  try:
    yield waited
  finally:
    del _held[path]
    # The close releases the lock.
    os.close(fd)
