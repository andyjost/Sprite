import collections

__all__ = ['Queue']

class Queue(collections.deque):
  '''
  A queue of configurations.  ``sid`` names the set function the queue
  belongs to, or None for the outermost queue.  ``decisions`` holds the
  choices whose escapes made this queue (rts_setfunctions.split_queue): a
  configuration of the queue that has not made such a choice forks on it
  instead of escaping it again (rts_setfunctions.choice_escapes).
  '''
  def __init__(self, *args, **kwds):
    sid = kwds.pop('sid', None)
    decisions = kwds.pop('decisions', None)
    collections.deque.__init__(self, *args, **kwds)
    self.sid = sid
    self.decisions = set() if decisions is None else decisions

  def __copy__(self):
    cp = super(Queue, self).__copy__()
    cp.sid = self.sid
    cp.decisions = set(self.decisions)
    return cp

  def copy(self):
    return self.__copy__()
