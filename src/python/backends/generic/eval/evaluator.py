# from ...generic.eval import telemetry
# from . import fairscheme, rts
from . import telemetry

class Evaluator(object):
  '''Manages the evaluation of a Curry expression.'''

  def __init__(self, interp, goal):
    '''Initialize evaluation of ``goal`` under interpreter ``interp``.'''
    goal = getattr(goal, 'raw_expr', goal)
    self.interp = interp
    self.rts = interp.backend.make_evaluation_state(interp, goal)

  def evaluate(self):
    '''Evaluate the goal.'''
    interval = self.interp.flags['telemetry_interval']
    value_generator = self.rts.generate_values()
    if interval is not None and interval > 0:
      return telemetry.report_telemetry(self.rts, interval, value_generator)
    else:
      return value_generator

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
  expr = getattr(expr, 'raw_expr', expr)
  evaluator = Evaluator(interp, expr)
  expr.info.step(evaluator.rts, expr)
  return expr

