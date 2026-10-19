"""Small synchronization helpers. No Python mutex spans a native wait."""
import functools


def native_metadata(function):
  """Group native metadata and publication under the existing heap gate.

  This is for materialization/registry updates, never evaluation or waits
  for compilation jobs. Preparation that imports or produces files stays
  outside the decorated operation.
  """
  @functools.wraps(function)
  def call(*args, **kwds):
    from ..backends.cxx.cyrtbindings import _cyrtbindings
    return _cyrtbindings._metadata_call(lambda: function(*args, **kwds))
  return call


def synchronized(lock):
  def decorate(function):
    @functools.wraps(function)
    def call(*args, **kwds):
      with lock:
        return function(*args, **kwds)
    return call
  return decorate


import threading
lib_import_lock = threading.Lock()
lib_import_names = set()
