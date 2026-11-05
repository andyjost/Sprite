"""Small synchronization helpers. No Python mutex spans a native wait."""
import functools
import contextlib
import os
import sys
import threading

_local = threading.local()
_native = None
_bootstrap_locks = []


def _held():
  return bool(getattr(_local, 'depth', 0))


def check_entry():
  """Bootstrap only; registration replaces this with the native predicate."""


def _set_logs_pending(pending):
  """Bootstrap only; registration installs the native thread-local flag."""


def entry(function):
  @functools.wraps(function)
  def call(*args, **kwds):
    check_entry()
    return function(*args, **kwds)
  return call


def log(logger, level, message, *args):
  """Keep diagnostics unformatted until the enclosing locks release."""
  if getattr(_local, 'draining', False):
    _local.suppressed.append(None)
  elif _held():
    if not hasattr(_local, 'messages'):
      _local.messages = []
    # Mark first: a signal exception after append must still drain the record.
    _set_logs_pending(True)
    _local.messages.append((logger, level, message, args))
  else:
    logger.log(level, message, *args)


def emit_messages(messages, logger=None):
  if not hasattr(_local, 'messages'):
    _local.messages = []
  for record in messages:
    target, level, message, args = (logger, *record) if len(record) == 3 else record
    if getattr(_local, 'draining', False):
      _local.suppressed.append(None)
    else:
      _set_logs_pending(True)
      _local.messages.append((target, level, message, args))
  if not _held():
    _drain()


def _drain():
  # Bootstrap records stay queued until native tracking becomes available.
  # Snapshot, progress and cleanup must not have Python signal windows.
  if _native is not None:
    _native._drain_logs(_local, os.write)


@contextlib.contextmanager
def holding():
  """Mark acquisition through release, including signal-dispatch windows."""
  depth = getattr(_local, 'depth', 0)
  if not depth:
    _local.messages = []
  _local.depth = depth + 1
  try:
    yield
  finally:
    if not depth:
      messages, _local.messages = _local.messages, []
    _local.depth = depth
    if not depth:
      emit_messages(messages)


class Lock:
  """An ordinary mutex whose ownership participates in the host boundary.

  Internal nested acquisitions preserve the established lock order. API
  entries use check_entry before they can enter that order a second time.
  The Python methods below serve package bootstrap only; the runtime binding
  replaces them with native methods before any public entry becomes available.
  """
  def __init__(self, recursive=False):
    self._recursive = recursive
    if _native is not None:
      self._native_state = _native._HostLock(recursive)
      return
    _bootstrap_locks.append(self)
    self._mutex = threading.RLock() if recursive else threading.Lock()
    self._scopes = threading.local()

  def acquire(self, blocking=True, timeout=-1):
    scope = holding()
    scope.__enter__()
    try:
      acquired = self._mutex.acquire(blocking, timeout)
    except BaseException:
      scope.__exit__(*sys.exc_info())
      raise
    if acquired:
      scopes = getattr(self._scopes, 'held', None)
      if scopes is None:
        scopes = self._scopes.held = []
      scopes.append(scope)
    else:
      scope.__exit__(None, None, None)
    return acquired

  def release(self):
    self._mutex.release()
    self._scopes.held.pop().__exit__(None, None, None)

  def __enter__(self):
    self.acquire()
    return self

  def __exit__(self, *exc):
    self.release()

  def locked(self):
    return self._mutex.locked()


def RLock():
  return Lock(recursive=True)


def native_metadata(function):
  """Group native metadata and publication under the existing heap gate.

  This is for materialization/registry updates, never evaluation or waits
  for compilation jobs. Preparation that imports or produces files stays
  outside the decorated operation.
  """
  @functools.wraps(function)
  def call(*args, **kwds):
    from ..backends.cxx.curryrtbindings import _curryrtbindings
    return _curryrtbindings._metadata_call(lambda: function(*args, **kwds))
  return call


def synchronized(lock):
  def decorate(function):
    @functools.wraps(function)
    def call(*args, **kwds):
      with lock:
        return function(*args, **kwds)
    return call
  return decorate


lib_import_lock = Lock()
lib_import_names = set()
