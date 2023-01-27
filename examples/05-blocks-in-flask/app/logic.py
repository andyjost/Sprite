import curry
from curry.lib import solver

FORM = ('i1','i2','i3'),('f1','f2','f3')

def get_solution(data):
  configs = (
      tuple(build_stack(data[fld]) for fld in fields)
          for fields in FORM
    )
  goal = curry.expr(solver.solve, *configs)
  trace = next(curry.eval(goal))
  return show_trace(trace)

def build_stack(stk):
  return [curry.expr(getattr(solver, c)) for c in stk]

def show_trace(trace):
  return '\n'.join(show_config(cfg) for cfg in trace)

def show_config(cfg):
  return ' '.join(show_stack(stk) for stk in cfg)

def show_stack(stk):
  return '[%s]' % ''.join(str(blk) for blk in stk)

