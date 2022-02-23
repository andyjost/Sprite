from curry.backends.generic.runtime import control
from curry.common import T_CTOR

def step(interp, expr, num=1):
  '''
  Takes up to the specified number of steps for the given expression, stopping
  if the root is ever replaced with a symbol or a residual is found.  This
  function is used for testing.
  '''
  if not hasattr(expr, 'info') or expr.info.tag >= T_CTOR:
    expr = interp.expr(expr)
  evaluator = interp.context.runtime.Evaluator(interp, expr)
  evaluator.set_global_step_limit(num)
  try:
    list(evaluator.evaluate())
  except control.E_TERMINATE:
    pass

