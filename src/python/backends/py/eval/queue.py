import collections

__all__ = ['Queue']

class Queue(collections.deque):
  def __init__(self, *args, **kwds):
    sid = kwds.pop('sid', None)
    collections.deque.__init__(self, *args, **kwds)
    self.sid = sid

  def __copy__(self):
    cp = super(Queue, self).__copy__()
    cp.sid = self.sid
    return cp

  def copy(self):
    return self.__copy__()
