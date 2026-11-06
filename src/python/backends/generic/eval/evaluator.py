from ....utility.locking import Lock as _SpriteLock
import weakref, threading

# The keys of the scheduler counters that hold a largest value.  Over several
# evaluations the largest of them counts; every other number adds.
MAX_KEYS = ('max', 'queue_max')

def merge_counters(total, part):
  '''
  Adds the counters of ``part`` to ``total`` and returns ``total``: numbers
  add (a largest value, see MAX_KEYS, takes the maximum), lists add element
  by element, dicts merge key by key.  ``total`` may be None, which stands
  for nothing counted yet.
  '''
  if total is None:
    return _copy_counters(part)
  for key, value in part.items():
    if isinstance(value, dict):
      total[key] = merge_counters(total.get(key), value)
    elif isinstance(value, list):
      old = total.get(key)
      total[key] = list(value) if old is None \
                   else [a + b for a, b in zip(old, value)]
    elif key in MAX_KEYS:
      total[key] = max(total.get(key, 0), value)
    else:
      total[key] = total.get(key, 0) + value
  return total

def _copy_counters(part):
  return {
      key: _copy_counters(value) if isinstance(value, dict)
           else list(value) if isinstance(value, list) else value
        for key, value in part.items()
    }

class EvaluationTotals(object):
  '''
  Sums the rewrite steps and the forks of the evaluations of one interpreter.
  The runtime state of an evaluation counts its own steps (``steps_total``)
  and forks (``forks_total``).  A running evaluation is held by a weak
  reference, so the totals include its counts so far.  An evaluation that
  ended is added once, when its value generator is exhausted or closed.
  ``Interpreter.stats`` reports the totals.

  The scheduler counters of an instrumented C++ runtime (make COUNTERS=1)
  are summed the same way: ``rts.scheduler_counters()`` gives a dict of
  numbers, lists, and dicts, or None when the runtime has none.
  '''
  def __init__(self):
    self._steps = 0
    self._forks = 0
    self._scheduler = None
    self._running_refs = {}
    # Callbacks only append; owner sections purge before using the map.
    self._pending_removals = []
    self._lock = _SpriteLock()
    self._version = 0

  def _purge(self):
    # Called only under _lock, before a traversal starts. Never replace the
    # pending list: callbacks in other threads may be appending to it.
    while self._pending_removals:
      key, ref = self._pending_removals.pop()
      if self._running_refs.get(key) is ref:
        del self._running_refs[key]
        self._version += 1

  @property
  def _running(self):
    # Keep the inspection view used by diagnostics; resolve weakrefs only
    # after releasing the metadata lock, just as the counter snapshots do.
    with self._lock:
      self._purge()
      refs = tuple(self._running_refs.values())
    return tuple(rts for ref in refs if (rts := ref()) is not None)

  @property
  def steps(self):
    '''The rewrite steps taken, running evaluations included.'''
    return self._snapshot()[0]

  @property
  def forks(self):
    '''The forks taken, running evaluations included.'''
    return self._snapshot()[1]

  @property
  def scheduler(self):
    '''
    The scheduler counters summed, running evaluations included; None when
    the runtime has no counters or no evaluation reported any.
    '''
    return self._snapshot()[2]

  def _snapshot(self):
    while True:
      with self._lock:
        self._purge()
        version = self._version
        steps, forks = self._steps, self._forks
        refs = tuple(self._running_refs.values())
        total = _copy_counters(self._scheduler) if self._scheduler else None
      running = tuple(rts for ref in refs if (rts := ref()) is not None)
      for rts in running:
        steps += rts.steps_total
        forks += rts.forks_total
        counters = rts.scheduler_counters()
        if counters is not None:
          total = merge_counters(total, counters)
      with self._lock:
        self._purge()
        if version == self._version:
          return steps, forks, total

  def add(self, rts):
    '''Adds the counts of a runtime state that takes no more steps.'''
    # Native reads may wait for the heap with the GIL released.  Read them
    # before changing the Python totals, so another finishing evaluation
    # cannot overwrite a partial update or disappear from a snapshot.
    steps = rts.steps_total
    forks = rts.forks_total
    counters = rts.scheduler_counters()
    self._add_counts(rts, steps, forks, counters)

  def _add_counts(self, rts, steps, forks, counters):
    with self._lock:
      self._purge()
      self._running_refs.pop(id(rts), None)
      self._steps += steps
      self._forks += forks
      if counters is not None:
        self._scheduler = merge_counters(self._scheduler, counters)
      self._version += 1

  def track(self, rts, values):
    '''
    Yields the values of ``values``, the value generator of the evaluation
    under ``rts``, and adds the counts of ``rts`` when the generator ends or
    is closed.
    '''
    key = id(rts)
    def forget(ref):
      self._pending_removals.append((key, ref))
    with self._lock:
      self._purge()
      self._running_refs[key] = weakref.ref(rts, forget)
      self._version += 1
    if hasattr(rts, '_counts'):
      # The native pull saves these under its existing heap section, also
      # on errors and exhaustion. Delegation adds no per-value heap call.
      try:
        yield from values
      finally:
        self._add_counts(rts, *rts._counts)
        close = getattr(values, 'close', None)
        if close is not None:
          close()
      return
    # Snapshot while consuming, before suspending at a yield. Closing a
    # suspended generator (including cyclic GC) must not enter the heap.
    counts = (0, 0, None)
    def snapshot():
      return rts.steps_total, rts.forks_total, rts.scheduler_counters()
    try:
      try:
        for value in values:
          counts = snapshot()
          yield value
      except GeneratorExit:
        raise
      except BaseException:
        counts = snapshot()
        raise
      else:
        counts = snapshot()
    finally:
      self._add_counts(rts, *counts)
      close = getattr(values, 'close', None)
      if close is not None:
        close()

class Evaluator(object):
  '''Manages the evaluation of a Curry expression.'''

  def __init__(self, interp, goal):
    '''Initialize evaluation of ``goal`` under interpreter ``interp``.'''
    goal = getattr(goal, 'raw_expr', goal)
    self.interp = interp
    self.rts = interp.backend.create_evaluation_rts(interp, goal)

  def evaluate(self):
    '''Evaluate the goal.'''
    value_generator = self.rts.generate_values()
    return self.interp._evaluation_totals.track(self.rts, value_generator)

  def set_global_step_limit(self, limit=None, reset=True):
    '''
    Sets the step limit after which E_TERMINATE is raised.  By default there is
    no limit.  This can be used to apply no more than a set number of steps,
    which is useful for debugging and perhaps in other situations.

    Args:
      limit:
        The new global step limit.  Pass None to indicate no limit.

      reset:
        Indicates whether to reset the global step count to zero.
    '''
    if reset:
      self.rts.stepcounter.reset_global()
    self.rts.stepcounter.global_limit = limit


def evaluate(interp, goal, steplimit=None):
  evaluator = Evaluator(interp, goal)
  if steplimit is not None:
    evaluator.set_global_step_limit(steplimit)
  return evaluator.evaluate()

def single_step(interp, expr):
  '''
  Takes one rewrite step at the root of ``expr``, outside an evaluation, and
  returns ``expr``.  The runtime state of the runtime counts the step as
  the step loop would (``RuntimeState.single_step``), and the totals of the
  interpreter take it up like the steps of an evaluation.  A free variable
  the step creates (``let x free`` in a compiled expression) outlives the
  state: the state counts it, so that ``set_goal`` of a later evaluation
  registers it (``InterpreterState.external_freevars``).
  '''
  expr = getattr(expr, 'raw_expr', expr)
  evaluator = Evaluator(interp, expr)
  evaluator.rts.single_step(expr)
  interp._evaluation_totals.add(evaluator.rts)
  return expr

