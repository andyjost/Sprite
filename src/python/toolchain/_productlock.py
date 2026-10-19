'''
File-production locks, shared by threads and processes.

Never hold one across an interpreter import or native materialization.  Prepare
those operations first, lock only to recheck and publish files, then release
before consulting native state.  Each entry uses an RLock for thread ownership
and flock for process ownership; recursion belongs to the owning thread alone.
'''

from . import _filenames
import contextlib, fcntl, logging, os, threading

__all__ = ['lockfile', 'locked']

logger = logging.getLogger(__name__)

SUFFIX = '.lock'

_registry_lock = threading.Lock()
_locks = {}
_local = threading.local()
_descriptors = set()

def _after_fork():
  global _registry_lock, _locks, _local, _descriptors
  # Close the child copies without unlocking the parent's open description.
  for fd in _descriptors:
    os.close(fd)
  _registry_lock = threading.Lock()
  _locks = {}
  _local = threading.local()
  _descriptors = set()

def _before_fork():
  _registry_lock.acquire()

def _parent_after_fork():
  _registry_lock.release()

os.register_at_fork(before=_before_fork,
    after_in_parent=_parent_after_fork, after_in_child=_after_fork)

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
  """Hold the file-production lock. Yield whether acquiring it waited."""
  owner_pid = os.getpid()
  path = os.path.realpath(lockfile(filename))
  with _registry_lock:
    mutex, users = _locks.get(path, (threading.RLock(), 0))
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
    fd = _open(path)
    if fd is None:
      yield waited
      return
    with _registry_lock:
      _descriptors.add(fd)
    try:
      try:
        try:
          fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
          waited = True
          logger.info('Waiting for another process that compiles %s (the lock %s)',
              os.path.basename(filename), path)
          fcntl.flock(fd, fcntl.LOCK_EX)
      except OSError as exc:
        logger.debug('No advisory lock for %r (%s)', path, exc)
        yield waited
        return
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
