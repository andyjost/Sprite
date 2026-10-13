import collections

__all__ = ['failure_guards', 'Queue']

def failure_guards(outside_failures):
  '''
  Rule (d3) of the failure rule F2: the set ids of the guards of the
  failure a capsule with the outside failures ``outside_failures`` (pairs
  of a level and a set of set ids) becomes.  This is the one place that
  chooses the records: the records at the least level (the failures that
  entered the chain innermost; deviation 147 of the README of the Lean
  development), and the union of their guards.  A record of level zero
  makes a plain failure, which escapes to no enclosing capsule.
  Queue.failure_guards and the checker (check_capsule_end) call it.  The
  C++ runtime has the same function (cyrt::failure_guards in
  state/queue.cpp).
  '''
  if not outside_failures:
    return []
  least = min(level for level, _ in outside_failures)
  guards = set()
  for level, sids in outside_failures:
    if level == least:
      guards.update(sids)
  return sorted(guards)

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

  The failure record of the capsule (Definition 2.94 of the note on the
  Fair Scheme, the deferred form of the failure rule F2;
  rts_setfunctions.record_failure writes it, and allValues in
  currylib/setfunctions.py reads it on the empty queue): ``produced``
  counts the values the queue gave (rule SF.3), ``inside_failure`` tells
  whether a configuration met a failure of the function's own, and
  ``outside_failures`` holds the failures that came from an argument, each
  a pair of its level (the position, in the chain of the capsules innermost
  first, of the outermost capsule whose guard the failure crossed; zero
  names the capsule itself) and the set ids of the enclosing guards it
  crossed, less the set of the capsule.  A copy of the queue, the queues of
  a split and the clones of a queue, keeps the record, as the mechanization
  does.  The C++ runtime has the same fields (Queue::produced,
  Queue::inside_failure, Queue::outside_failures).
  '''
  def __init__(self, *args, **kwds):
    sid = kwds.pop('sid', None)
    decisions = kwds.pop('decisions', None)
    absorbed = kwds.pop('absorbed', None)
    collections.deque.__init__(self, *args, **kwds)
    self.sid = sid
    self.decisions = set() if decisions is None else decisions
    self.absorbed = {} if absorbed is None else absorbed
    self.produced = 0
    self.inside_failure = False
    self.outside_failures = []

  def __copy__(self):
    cp = super(Queue, self).__copy__()
    cp.sid = self.sid
    cp.decisions = set(self.decisions)
    cp.absorbed = dict(self.absorbed)
    cp.produced = self.produced
    cp.inside_failure = self.inside_failure
    cp.outside_failures = list(self.outside_failures)
    return cp

  def fails_at_end(self):
    '''
    Rule (d2): on the empty queue the capsule is a failure when it produced
    no value, recorded no inside failure and recorded some outside failure;
    its set stands otherwise.
    '''
    return not self.produced and not self.inside_failure \
        and bool(self.outside_failures)

  def failure_guards(self):
    '''
    Rule (d3): the set ids of the guards of the failure the capsule
    becomes (the function failure_guards of this module over
    outside_failures).
    '''
    return failure_guards(self.outside_failures)

  def copy(self):
    return self.__copy__()
