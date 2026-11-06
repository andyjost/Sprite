'''The process-fork boundary, shared by Python and native work.'''
import functools, os


def _native():
  from ..backends.cxx import curryrtbindings
  return curryrtbindings._curryrtbindings


def check():
  _native()._fork_check()


def poisoned():
  return _native()._fork_poisoned()


def work(function):
  '''Count an operation before it can enter a Python or native lock.'''
  @functools.wraps(function)
  def call(*args, **kwds):
    native = _native()
    owner = native._fork_work_begin()
    try:
      result = function(*args, **kwds)
      native._fork_check() # A Python callback may have forked and returned.
      return result
    finally:
      native._fork_work_end(owner)
  return call


if hasattr(os, 'register_at_fork'):
  os.register_at_fork(before=lambda: _native()._fork_prepare())
