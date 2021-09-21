'''
Code for evaluating Curry expressions.
'''

from . import fairscheme
from . import state, trace

class Evaluator(object):
  '''Manages the evaluation of a Curry expression.'''

  def __init__(self, interp, goal):
    '''Initialize evaluation of ``goal`` under interpreter ``interp``.'''
    self.rts = state.RuntimeState(interp, goal)

  def evaluate(self):
    '''Evaluate the goal.'''
    D = trace.trace_values(fairscheme.D)
    return D(self.rts)

  def set_global_step_limit(self, limit=None, reset=True):
    '''
    Sets the step limit after which E_TERMINATE is raised.  By default there is
    no limit.  This can be used to apply no more than a set number of steps,
    which is useful for debugging and perhaps in other situations.

    Parameters:
    -----------
      ``limit``
        The new global step limit.  Supply ``None`` to indicate no limit.

      ``reset``
        Indicates whether to reset the global step count to zero.
    '''
    if reset:
      self.rts.stepcounter.reset_global()
    self.rts.stepcounter.global_limit = limit

