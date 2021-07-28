from .... import context

__all__ = ['Runtime']

class Runtime(context.Runtime):
  '''Implementation of the abstract runtime system for the Python backend.'''
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
  def evaluate(self):
    from .fairscheme.evaluator import Evaluator
    return lambda *args, **kwds: Evaluator(*args, **kwds).evaluate()

