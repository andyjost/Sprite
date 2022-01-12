from .... import context

__all__ = ['Runtime']

class Runtime(context.Runtime):
  '''
  Implementation of the runtime system interface for the Python backend.  Used
  by the Interpreter object.
  '''
  @property
  def Node(self):
    from .pybindings import Node
    return Node

  @property
  def InfoTable(self):
    from .pybindings import InfoTable
    return InfoTable

  @property
  def evaluate(self):
    assert False
    # from .evaluator import Evaluator
    # return lambda *args, **kwds: Evaluator(*args, **kwds).evaluate()

  def get_interpreter_state(self, interp):
    return interp._its

  def init_interpreter_state(self, interp):
    # from .state import InterpreterState
    # interp._its = InterpreterState(interp)
    interp._its = None

  @property
  def lookup_builtin_module(self):
    assert False
    # from .currylib import index
    # return index.lookup

  def single_step(self, interp, expr):
    assert False
    # from .evaluator import Evaluator
    # expr = getattr(expr, 'raw_expr', expr)
    # evaluator = Evaluator(interp, expr)
    # expr.info.step(evaluator.rts, expr)
    # return expr
