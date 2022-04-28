'''Python bindings for libcyrt.so.'''
from ._cyrtbindings import *
from . import fingerprint
import logging
from ... import Node as _backends_Node

logger = logging.getLogger(__name__)

_backends_Node.register(Node)

def make_node(info, *args, **kwds):
  info = getattr(info, 'info', info)
  partial_info = kwds.pop('partial_info', None)
  target = kwds.pop('target', None)
  target = getattr(target, 'target', target) # accept target=Variable
  args = [Arg(arg) for arg in args]
  return Node.create(info, args, target, bool(partial_info))

def evaluate(interp, goal, steplimit=None):
  state = interp.backend.get_interpreter_state(interp)
  evaluator = Evaluator(state, goal)
  def result_generator():
    while True:
      result = evaluator.next()
      if result is None:
        return
      yield result
  return result_generator()
