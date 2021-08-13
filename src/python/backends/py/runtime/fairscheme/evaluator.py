'''
Code for evaluating Curry expressions.
'''

from . import algorithm, state

class Evaluator(object):
  '''Manages the evaluation of a Curry expression.'''

  def __init__(self, interp, goal):
    '''Initialize evaluation of ``goal`` under interpreter ``interp``.'''
    self.rts = state.RuntimeState(interp, goal)

  def evaluate(self):
    '''Evaluate the goal.'''
    return algorithm.D(self.rts)

  def set_global_step_limit(self, limit=None, reset=True):
    '''
    Sets the step limit after which E_TERMINATE is raised.
    '''
    if reset:
      self.rts.stepcounter.reset_global()
    self.rts.stepcounter.global_limit = limit

