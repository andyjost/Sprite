from ..control import E_STEPLIMIT, E_TERMINATE

class StepCounter(object):
  '''
  Counts the number of steps taken.  If a limit is provided, raises E_STEPLIMIT
  when the limit is reached.

  A global limit on the number of steps may be optionally specified.  This is
  used primarily for testing and debugging.  Raises E_TERMINATE after the
  specified number of steps.
  '''
  def __init__(self, limit=None, global_limit=None):
    assert limit > 0 or limit is None
    self.reset_global()
    self.reset()
    self._limit = float('inf') if limit is None else limit
    self.global_limit = global_limit

  @property
  def count(self):
    return self._count

  @property
  def global_count(self):
    return self._global_count

  @property
  def limit(self):
    return self._limit

  @property
  def global_limit(self):
    return self._global_limit

  @global_limit.setter
  def global_limit(self, limit):
    self._global_limit = float('inf') if limit is None else int(limit)
    if self._global_count >= self.global_limit:
      raise E_TERMINATE()

  def increment(self):
    self._global_count += 1
    if self._global_count == self.global_limit:
      raise E_TERMINATE()

    self._count += 1
    if self._count >= self.limit:
      raise E_STEPLIMIT()

  def reset(self):
    self._count = 0

  def reset_global(self):
    self._global_count = 0

