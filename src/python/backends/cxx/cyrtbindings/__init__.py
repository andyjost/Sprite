'''Python bindings for libcyrt.so.'''
from ._cyrtbindings import *
from ...generic.eval import trace
from .... import exceptions
from . import fingerprint
from ... import InfoTable as _backends_InfoTable
from ... import Node as _backends_Node
import logging

logger = logging.getLogger(__name__)
_backends_Node.register(Node)
_backends_InfoTable.register(InfoTable)

def make_node(info, *args, **kwds):
  info = getattr(info, 'info', info)
  partial_info = kwds.pop('partial_info', None)
  target = kwds.pop('target', None)
  target = getattr(target, 'target', target)
  args = [Arg(arg) for arg in args]
  return Node.create(info, args, target, bool(partial_info))

_SETF_STRATEGY = {
    'lazy': SETF_LAZY
  , 'eager': SETF_EAGER
  }

class RuntimeState(RuntimeStateBase):
  def __init__(self, interp, goal=None):
    istate = interp.backend.get_interpreter_state(interp)
    self.tracing = interp.flags['trace']
    self.setfunction_strategy = \
        _SETF_STRATEGY[interp.flags['setfunction_strategy']]
    RuntimeStateBase.__init__(self, istate, goal, self.tracing, self.setfunction_strategy)

  def generate_values(self):
    try:
      while True:
        result = self.next()
        if result is None:
          return
        yield result
    except EvaluationError as err:
      raise exceptions.EvaluationError(str(err))
    except EvaluationSuspended:
      raise exceptions.EvaluationSuspended()

