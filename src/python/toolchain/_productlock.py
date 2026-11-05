'''
File-production locks, shared by threads and processes.

Never hold one across an interpreter import or native materialization.  Prepare
those operations first, lock only to recheck and publish files, then release
before consulting native state.  Each entry uses an RLock for thread ownership
and a file lock for process ownership; recursion belongs to the owning thread alone.
'''
from ..utility.locking import Lock as _SpriteLock, RLock as _SpriteRLock

from . import _filenames
from ..utility import locking as _locking
import contextlib, errno, logging, os, threading, time
try:
  import fcntl
except ImportError:
  fcntl = None
try:
  import msvcrt
except ImportError:
  msvcrt = None

__all__ = ['lockfile', 'locked']

logger = logging.getLogger(__name__)

SUFFIX = '.lock'

_registry_lock = _SpriteLock()
_locks = {}
_local = threading.local()
_descriptors = set()

def _after_fork():
  global _registry_lock, _locks, _local, _descriptors
  _registry_lock.release()
  # Close the child copies without unlocking the parent's open description.
  for fd in _descriptors:
    os.close(fd)
  _registry_lock = _SpriteLock()
  _locks = {}
  _local = threading.local()
  _descriptors = set()

def _before_fork():
  _registry_lock.acquire()

def _parent_after_fork():
  _registry_lock.release()

if hasattr(os, 'register_at_fork'):
  os.register_at_fork(before=_before_fork,
    after_in_parent=_parent_after_fork, after_in_child=_after_fork)

def lockfile(filename):
  '''
  The lock file of the module of ``filename``, a file of its chain (the
  source, the ICurry, the image, the generated file or the object):
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
    log(logger, logging.DEBUG, 'No lock for %r (%s)', path, exc)
    return None

@contextlib.contextmanager
def _locked(filename):
  """Hold the file-production lock. Yield whether acquiring it waited."""
  owner_pid = os.getpid()
  path = os.path.realpath(lockfile(filename))
  with _registry_lock:
    mutex, users = _locks.get(path, (_SpriteRLock(), 0))
    _locks[path] = mutex, users + 1
  waited = not mutex.acquire(blocking=False)
  if waited:
    mutex.acquire()
  try:
    held = getattr(_local, 'held', None)
    if held is None:
      held = _local.held = {}
    if path in held:
      yield False
      return
    if fcntl is None:
      if msvcrt is None:
        raise OSError('process locking is unavailable')
      fd = _open(path)
      if fd is None:
        raise OSError('cannot open product lock')
      try:
        # One byte at offset zero identifies the process lock. Closing the
        # descriptor releases it, including when the process exits early.
        while True:
          os.lseek(fd, 0, os.SEEK_SET)
          try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            break
          except OSError as exc:
            if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
              raise
            if not waited:
              log(logger, logging.INFO, 'Waiting for another process that compiles %s (the lock %s)',
                          os.path.basename(filename), path)
            waited = True
            time.sleep(0.05)
        held[path] = fd
        try:
          yield waited
        finally:
          del held[path]
      finally:
        os.close(fd)
      return
    fd = _open(path)
    if fd is None:
      raise OSError('cannot open product lock')
    with _registry_lock:
      _descriptors.add(fd)
    try:
      try:
        try:
          fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
          waited = True
          log(logger, logging.INFO, 'Waiting for another process that compiles %s (the lock %s)',
              os.path.basename(filename), path)
          fcntl.flock(fd, fcntl.LOCK_EX)
      except OSError as exc:
        log(logger, logging.DEBUG, 'No advisory lock for %r (%s)', path, exc)
        raise
      held[path] = fd
      try:
        yield waited
      finally:
        if os.getpid() == owner_pid:
          del held[path]
    finally:
      if os.getpid() == owner_pid:
        with _registry_lock:
          _descriptors.discard(fd)
          os.close(fd)
  finally:
    if os.getpid() == owner_pid:
      mutex.release()
      with _registry_lock:
        mutex, users = _locks[path]
        if users == 1:
          del _locks[path]
        else:
          _locks[path] = mutex, users - 1


def log(logger, level, message, *args):
  """Enqueue immediately in the thread's common ordered diagnostics queue."""
  _locking.log(logger, level, message, *args)


def emit_messages(messages, logger=None):
  """Emit only after all enclosing locks release; retain each source logger."""
  _locking.emit_messages(messages, logger)


@contextlib.contextmanager
def locked(filename, messages=None):
  """Collect diagnostics until the outermost product/JIT locks are released."""
  with _locking.holding():
    with _locked(filename) as waited:
      yield waited
