from .node import Node

NORMALIZE = 0
HEADNORMALIZE = 1

class RewriteStepTaken(Exception):
  '''
  Raised after a rewrite step is taken.  Used to return control to the main
  evaluator loop.
  '''
  pass

class Evaluator(object):
  def __new__(cls, goal, sink):
    self = object.__new__(cls)
    self.sink = sink
    self.queue = [goal]
    return self

  def run(self):
    while self.queue:
      expr = self.queue.pop(0)
      try:
        is_value = expr.info.step(expr, NORMALIZE, self.sink)
        if is_value:
          self.sink(str(expr))
          self.sink('\n')
        # TODO: choice handled here?
        # else expr is a failure, so discard it.
      except RewriteStepTaken:
        self.queue.append(expr)

def ctor_step(node, mode, sink):
  '''Step function for constructors.'''
  return all(
      arg.info.step(arg, mode, sink)
          for arg in node.args
          if isinstance(arg, Node)
    )

