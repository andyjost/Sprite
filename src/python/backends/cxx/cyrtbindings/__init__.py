'''Python bindings for libcyrt.so.'''
from ._cyrtbindings import *
from ...generic.eval import trace
from . import fingerprint
from ... import Node as _backends_Node
import logging

from .... import exceptions
exceptions.EvaluationError.register(EvaluationError)
exceptions.EvaluationSuspended.register(EvaluationSuspended)

logger = logging.getLogger(__name__)
_backends_Node.register(Node)

def make_node(info, *args, **kwds):
  info = getattr(info, 'info', info)
  partial_info = kwds.pop('partial_info', None)
  target = kwds.pop('target', None)
  target = getattr(target, 'target', target) # accept target=Variable
  args = [Arg(arg) for arg in args]
  return Node.create(info, args, target, bool(partial_info))

class RuntimeState(RuntimeStateBase):
  def __init__(self, interp, goal=None):
    istate = interp.backend.get_interpreter_state(interp)
    self.tracing = interp.flags['trace']
    RuntimeStateBase.__init__(self, istate, goal, self.tracing)

  def generate_values(self):
    while True:
      result = self.next()
      if result is None:
        return
      yield result

