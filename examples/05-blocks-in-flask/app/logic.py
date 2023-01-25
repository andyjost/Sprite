import curry
from curry.lib import solver

def get_solution(form):
  initial = build_config(form['i1'] or 'AB', form['i2'], form['i3'])
  final   = build_config(form['f1'], form['f2'], form['f3'] or 'AB')
  goal = curry.expr(solver.solve, initial, final)
  trace = next(curry.eval(goal, converter='topython'))
  return show_trace(trace)

def get_block(label):
  symbol = getattr(solver, label)
  return curry.expr(symbol)

def build_config(*stacks):
  return tuple(
      curry.expr([get_block(label) for label in stack])
          for stack in stacks
    )

def show_trace(trace):
  return '\n'.join(map(show_config, trace))

def show_config(config):
  return ' '.join(map(show_stack, config))

def show_stack(stack):
  return '[' + ''.join(str(block) for block in stack) + ']'

