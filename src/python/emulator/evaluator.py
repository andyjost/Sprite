from .node import Node, T_FAIL, T_CHOICE, E_SYMBOL
from ..compiler import icurry
from ..visitation import dispatch

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
        yield expr
      elif expr.info.tag == T_CHOICE:
        self.queue += expr.successors
        continue
      elif expr.info.tag == T_FAIL:
        continue # discard
      else:
        try:
          is_value = expr.info.step(expr)
        except E_SYMBOL:
          self.queue.append(expr)
        else:
          if is_value:
            yield expr
          else:
            self.queue.append(expr)

def ctor_step(emulator):
  def step_function(ctor):
    '''
    Step function for constructors.  Corresponds to applying the Fair Scheme N
    procedure.
    '''
    is_value = True
    for i,expr in enumerate(ctor.successors):
      if not isinstance(expr, Node):
        assert isinstance(expr, icurry.BuiltinVariant)
        continue
      tag = expr.info.tag
      if tag == T_CHOICE:
        pull_tab(ctor, [i])
        return False
      elif tag == T_FAIL:
        ctor.rewrite(emulator.ti_Failure)
        return False
      else:
        is_value = is_value and expr.info.step(expr)
    return is_value
  return step_function

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

def hnf(emulator):
  def hnf(lhs, target):
    '''
    Attempts to reduce the target node to head-normal form.
  
    If a needed failure or choice symbol is encountered, the lhs is overwritten
    with failure or via a pull-tab, respectively, and E_SYMBOL is raised.
    '''
    while True:
      tag = target.info.tag
      if tag == T_FAIL:
        return lhs.rewrite(emulator.ti_Failure)
        raise E_SYMBOL
      elif tag == T_CHOICE:
        pull_tab(lhs, target)
        raise E_SYMBOL
      elif tag == T_OPER:
        try:
          target.info.step(target)
        except E_SYMBOL:
          pass
      else:
        assert tag != T_FWD
        return target
  return hnf
