from . import telemetry
import weakref

class EvaluationTotals(object):
  '''
  Sums the rewrite steps and the forks of the evaluations of one interpreter.
  The runtime state of an evaluation counts its own steps (``steps_total``)
  and forks (``forks_total``).  A running evaluation is held by a weak
  reference, so the totals include its counts so far.  An evaluation that
  ended is added once, when its value generator is exhausted or closed.
  ``Interpreter.stats`` reports the totals.
  '''
  def __init__(self):
    self._steps = 0
    self._forks = 0
    self._running = weakref.WeakSet()

  @property
  def steps(self):
    '''The rewrite steps taken, running evaluations included.'''
    return self._steps + sum(rts.steps_total for rts in self._running)

  @property
  def forks(self):
    '''The forks taken, running evaluations included.'''
    return self._forks + sum(rts.forks_total for rts in self._running)

  def add(self, rts):
    '''Adds the counts of a runtime state that takes no more steps.'''
    self._running.discard(rts)
    self._steps += rts.steps_total
    self._forks += rts.forks_total

  def track(self, rts, values):
    '''
    Yields the values of ``values``, the value generator of the evaluation
    under ``rts``, and adds the counts of ``rts`` when the generator ends or
    is closed.
    '''
    self._running.add(rts)
    try:
      yield from values
    finally:
      self.add(rts)

class Evaluator(object):
  '''Manages the evaluation of a Curry expression.'''

  def __init__(self, interp, goal):
    '''Initialize evaluation of ``goal`` under interpreter ``interp``.'''
    goal = getattr(goal, 'raw_expr', goal)
    self.interp = interp
    self.rts = interp.backend.create_evaluation_rts(interp, goal)

  def evaluate(self):
    '''Evaluate the goal.'''
    interval = self.interp.flags['telemetry_interval']
    value_generator = self.rts.generate_values()
    if interval is not None and interval > 0:
      value_generator = telemetry.report_telemetry(
          self.rts, interval, value_generator
        )
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
  returns ``expr``.  The runtime state of either backend counts the step as
  the step loop would (``RuntimeState.single_step``), and the totals of the
  interpreter take it up like the steps of an evaluation.
  '''
  expr = getattr(expr, 'raw_expr', expr)
  evaluator = Evaluator(interp, expr)
  evaluator.rts.single_step(expr)
  interp._evaluation_totals.add(evaluator.rts)
  return expr

