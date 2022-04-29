from curry.backends.generic.eval import control, evaluator
from curry.common import T_CTOR

def step(interp, expr, num=1):
  '''
  Takes up to the specified number of steps for the given expression, stopping
  if the root is ever replaced with a symbol or a residual is found.  This
  function is used for testing.
  '''
  if not hasattr(expr, 'info') or expr.info.tag >= T_CTOR:
    expr = interp.expr(expr)
  value_generator = evaluator.evaluate(interp, expr, num)
  try:
    next(value_generator)
  except control.E_TERMINATE:
    pass

