from .... import context

__all__ = ['Runtime']

class Runtime(context.Runtime):
  '''
  Implementation of the abstract runtime system for the Python backend.  This
  interface is used by the Interpreter object.
  '''
  @property
  def Node(self):
    from .graph import Node
    return Node

  @property
  def InfoTable(self):
    from .graph import InfoTable
    return InfoTable

  def init_interpreter_state(self, interp):
    from .fairscheme.state import InterpreterState
    interp._its = InterpreterState(interp)

  def get_interpreter_state(self, interp):
    return interp._its

  @property
  def prelude(self):
    from . import prelude
    return prelude

  @property
  def setfunctions(self):
    from . import setfunctions
    return setfunctions

  @property
  def evaluate(self):
    from .fairscheme.evaluator import Evaluator
    return lambda *args, **kwds: Evaluator(*args, **kwds).evaluate()

  def single_step(self, interp, expr):
    from .fairscheme.evaluator import Evaluator
    evaluator = Evaluator(interp, expr)
    expr.info.step(evaluator.rts, expr)
    return expr

