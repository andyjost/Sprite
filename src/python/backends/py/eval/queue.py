import collections

__all__ = ['Queue']

class Queue(collections.deque):
  '''
  A queue of configurations.  ``sid`` names the set function the queue
  belongs to, or None for the outermost queue.  ``decisions`` holds the
  choices whose escapes made this queue (rts_setfunctions.split_queue): a
  configuration of the queue that has not made such a choice forks on it
  instead of escaping it again (rts_setfunctions.choice_escapes).
  ``absorbed`` holds the bindings of enclosing configurations that the
  nested evaluation of the queue reads, keyed by the group id of the
  variable in the configurations of the queue: a capsule whose evaluation
  reads a binding of the configuration that runs it is cloned for that
  configuration, and the clone absorbs the binding
  (rts_setfunctions.clone_queue); the readers look here after the map of
  the configuration (rts_bindings._find_binding).  A copy of the queue
  keeps both.  The C++ runtime has the same fields (Queue::decisions,
  Queue::absorbed).
  '''
  def __init__(self, *args, **kwds):
    sid = kwds.pop('sid', None)
    decisions = kwds.pop('decisions', None)
    absorbed = kwds.pop('absorbed', None)
    collections.deque.__init__(self, *args, **kwds)
    self.sid = sid
    self.decisions = set() if decisions is None else decisions
    self.absorbed = {} if absorbed is None else absorbed

  def __copy__(self):
    cp = super(Queue, self).__copy__()
    cp.sid = self.sid
    cp.decisions = set(self.decisions)
    cp.absorbed = dict(self.absorbed)
    return cp

  def copy(self):
    return self.__copy__()
