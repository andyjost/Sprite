from .node import Node

NORMALIZE = 0
HEADNORMALIZE = 1

class Evaluator(object):
  def __new__(cls, emulator, goal):
    self = object.__new__(cls)
    self.emulator = emulator
    self.queue = [goal]
    return self

  def run(self):
    while self.queue:
      expr = self.queue.pop(0)
      is_value = False
      if not isinstance(expr, Node):
        is_value = True
      elif self.emulator.is_choice(expr):
        self.queue += expr.successors
        continue
      elif self.emulator.is_failure(expr):
        continue
      else:
        is_value = expr.info.step(expr, self.emulator, NORMALIZE)
      if is_value:
        yield expr
      else:
        self.queue.append(expr)

def ctor_step(ctor, emulator, mode):
  '''Step function for constructors.'''
  is_value = True
  for i,expr in enumerate(ctor.successors):
    if not isinstance(expr, Node):
      continue
    if emulator.is_choice(expr):
      pull_tab(ctor, [i])
      return False
    elif emulator.is_failure(expr):
      ctor.rewrite(emulator.prelude.Failure)
      return False
    else:
      is_value = is_value and expr.info.step(expr, emulator, mode)
  return is_value

def pull_tab(source, targetpath):
  '''
  Executes a pull-tab step.

  Parameters:
  -----------
    ``source``
      The ancestor, which will be overwritten.

    ``targetpath``
      A sequence of integers giving the path from ``source`` to the target
      (descendent).
  '''
  assert targetpath
  i, = targetpath # temporary
  target = source[i]
  assert target.info.name == 'Choice'
  #
  lsucc = source.successors
  lsucc[i] = target[0]
  lhs = Node(source.info, lsucc)
  #
  rsucc = source.successors
  rsucc[i] = target[1]
  rhs = Node(source.info, rsucc)
  #
  source.rewrite(target.info, [lhs, rhs])

def hnf(node):
  '''Reduce a node to head-normal form.'''
  pass

