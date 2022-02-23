from .... import context
from . import telemetry
import abc, importlib

class Evaluator(abc.ABC):
  '''Manages the evaluation of a Curry expression.'''

  @abc.abstractmethod
  def _make_rts(self):
    pass

  @abc.abstractmethod
  def _eval(self):
    pass

  def __init__(self, interp, goal):
    '''Initialize evaluation of ``goal`` under interpreter ``interp``.'''
    goal = getattr(goal, 'raw_expr', goal)
    self.rts = self._make_rts(interp, goal)

  def evaluate(self):
    '''Evaluate the goal.'''
    interval = self.rts.interp.flags['telemetry_interval']
    if interval is not None and interval > 0:
      return telemetry.report_telemetry(self.rts, interval, self._eval())
    else:
      return self._eval()

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


class Runtime(context.Runtime):
  def lookup_builtin_module(self, modulename):
    basepath = '...%s.runtime.currylib.' % self.BACKEND_NAME
    if modulename == 'Prelude':
      module = importlib.import_module(basepath + 'prelude', package=__package__)
      return module.PreludeSpecification
    elif modulename == 'Control.SetFunctions':
      module = importlib.import_module(basepath + 'setfunctions', package=__package__)
      return module.SetFunctionsSpecification

  def evaluate(self, interp, goal):
    return self.Evaluator(interp, goal).evaluate()

  def single_step(self, interp, expr):
    expr = getattr(expr, 'raw_expr', expr)
    evaluator = self.Evaluator(interp, expr)
    expr.info.step(evaluator.rts, expr)
    return expr


