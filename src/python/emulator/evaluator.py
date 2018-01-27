from .node import Node

NORMALIZE = 0
HEADNORMALIZE = 1

class RewriteStepTaken(Exception):
  '''
  Raised after a rewrite step is taken.  Used to return control to the main
  evaluator loop.
  '''
  pass

class UnhandledChoice(Exception):
  '''Raised when a choice is encountered.  The parent must handle it.'''
  pass

class Evaluator(object):
  def __new__(cls, emulator, goal, sink):
    self = object.__new__(cls)
    self.emulator = emulator
    self.sink = sink
    self.queue = [goal]
    return self

  def run(self):
    while self.queue:
      expr = self.queue.pop(0)
      try:
        is_value = expr.info.step(expr, self.emulator, NORMALIZE, self.sink)
        if is_value:
          self.sink(str(expr))
          self.sink('\n')
        # else expr is a failure, so discard it.
      except UnhandledChoice:
        assert self.emulator.is_choice(expr)
        self.queue += expr.successors
      except RewriteStepTaken:
        self.queue.append(expr)

def ctor_step(ctor, emulator, mode, sink):
  '''Step function for constructors.'''
  args = iter(enumerate(expr for expr in ctor.successors if isinstance(expr, Node)))
  try:
    return all(expr.info.step(expr, emulator, mode, sink) for _,expr in args)
  except UnhandledChoice:
    i,_ = next(args, (0,None))
    # expr = ctor.successors[i-1]
    # assert emulator.is_choice(expr)
    pull_tab(ctor, [i])
    raise RewriteStepTaken()

def choice_step(choice, *args, **kwds):
  assert choice.info.name == 'Choice'
  raise UnhandledChoice()

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
  target = source.successors[i]
  assert target.info.name == 'Choice'
  #
  lsucc = source.successors
  lsucc[i] = target.successors[0]
  lhs = Node(source.info, lsucc)
  #
  rsucc = source.successors
  rsucc[i] = target.successors[1]
  rhs = Node(source.info, rsucc)
  #
  source.replace(target.info, [lhs, rhs])



