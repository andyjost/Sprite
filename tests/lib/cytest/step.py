from curry import icurry
from curry.interpreter.eval import makegoal
from curry.interpreter import runtime
from curry.utility.binding import binding

def step(interp, expr, num=1):
  '''
  Takes up to the specified number of steps for the given expression, stopping
  if the root is ever replaced with a symbol or a residual is found.  This
  function is used for testing.
  '''
  if not hasattr(expr, 'info') or expr.info.tag >= runtime.T_CTOR:
    expr = makegoal(interp, expr)
  with binding(interp.__dict__, 'stepcounter', runtime.StepCounter(limit=num)):
    try:
      if isinstance(expr, icurry.BuiltinVariant):
        return
      while expr.info.tag == runtime.T_FUNC:
        interp._stepper(expr)
      if expr.info.tag >= runtime.T_CTOR:
        runtime.N(interp, expr)
      else:
        return
      # FIXME: get the termination condition right.  It needs the same
      # check as D to see whether expr is actually a value.
    except (runtime.E_CONTINUE, runtime.E_STEPLIMIT, runtime.E_RESIDUAL):
      pass

