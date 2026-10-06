'''Python bindings for libcyrt.so.'''
from ._cyrtbindings import *
from ...generic.eval import trace
from ....interpreter import flags as _flags
from .... import exceptions
from . import fingerprint
from ... import InfoTable as _backends_InfoTable
from ... import Node as _backends_Node
import logging, sys

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
    limit = interp.flags['stack_limit']
    self.stack_limit = NOLIMIT if limit is None else int(limit)
    # The rotation cadence (see cyrt/ticker.hpp): zero steps select time
    # mode with the quantum in nanoseconds.
    mode, value = _flags.parse_rotation(interp.flags['rotation'])
    self.rotation_steps = value if mode == 'steps' else 0
    self.rotation_quantum_ns = value if mode == 'time' else 0
    RuntimeStateBase.__init__(
        self, istate, goal, self.tracing, self.setfunction_strategy
      , self.stack_limit, self.rotation_steps, self.rotation_quantum_ns
      )

  def generate_values(self):
    '''
    Generates the values of the goal.

    The Curry program writes to the C standard output, and Python writes to
    ``sys.stdout``.  Both buffers share one file descriptor.  Python's buffer
    is flushed before the scheduler runs, and the C buffer when the scheduler
    returns (see the ``next`` binding), so the output keeps its order.
    '''
    try:
      while True:
        _flush_stdout()
        result = self.next()
        if result is None:
          return
        yield result
    except EvaluationError as err:
      raise exceptions.EvaluationError(str(err))
    except EvaluationSuspended:
      raise exceptions.EvaluationSuspended()

def _flush_stdout():
  # A closed or missing stdout is legal: some IO tests close it to provoke an
  # error from the program.
  try:
    sys.stdout.flush()
  except (AttributeError, OSError, ValueError):
    pass

