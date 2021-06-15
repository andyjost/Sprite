from curry.backends.py import runtime as pyruntime
from curry import icurry
from curry.tags import *
from curry.utility.binding import binding

def step(interp, expr, num=1):
  '''
  Takes up to the specified number of steps for the given expression, stopping
  if the root is ever replaced with a symbol or a residual is found.  This
  function is used for testing.
  '''
  if not hasattr(expr, 'info') or expr.info.tag >= T_CTOR:
    expr = interp.expr(expr)
  # rts = pyruntime.RuntimeState(interp)
  evaluator = pyruntime.Evaluator(interp, expr)
  rts = evaluator.rts
  rts.currentframe = evaluator.queue[0]
  with binding(rts.__dict__, 'stepcounter', pyruntime.StepCounter(limit=num)):
    try:
      if isinstance(expr, icurry.ILiteral):
        return
      while expr.info.tag == T_FUNC:
        rts.S(rts, expr)
      if expr.info.tag >= T_CTOR:
        pyruntime.N(rts, expr)
      else:
        return
      # FIXME: get the termination condition right.  It needs the same
      # check as D to see whether expr is actually a value.
    # except (pyruntime.E_CONTINUE, pyruntime.E_STEPLIMIT, pyruntime.E_RESIDUAL):
    except pyruntime.RuntimeFlowException:
      pass

