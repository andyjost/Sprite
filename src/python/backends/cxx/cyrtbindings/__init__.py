'''Python bindings for libcyrt.so.'''
from ._cyrtbindings import *
from ...generic.eval import control, trace
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

_SETF_FAILURES = {
    'encapsulate': SETF_FAILURES_ENCAPSULATE
  , 'escape': SETF_FAILURES_ESCAPE
  }

class StepCounter(object):
  '''
  The step counter of the generic evaluator over a C++ runtime state.

  Evaluator.set_global_step_limit and the telemetry read the counter of the
  Python backend (generic.eval.stepcounter.StepCounter) as
  ``rts.stepcounter``; this object answers for the C++ state through its
  fields ``steps_total`` and ``step_limit``.  The count and the limit are
  relative to the last reset (``_step_base`` of the state), and the totals
  of the state keep every step.  A limit at or below the count raises
  E_TERMINATE at once, as the counter of the Python backend does; else the
  scheduler returns E_TERMINATE after the step that reaches the limit
  (cyrt/state/rts.hpp), and generate_values raises it.

  A view: ``rts.stepcounter`` makes one per access, and the state holds no
  counter.  A counter kept by the state made a reference cycle, which
  delayed the destruction of the state of evaluator.single_step until the
  cyclic collector ran; a live state is a root of the collector, so the
  history of a search stayed reachable (test_repl_eval_under_stress of
  unit_goals.py grew with the square of its length).
  '''
  def __init__(self, rts):
    self._rts = rts

  @property
  def global_count(self):
    '''The steps taken since the last reset.'''
    return self._rts.steps_total - self._rts._step_base

  @property
  def global_limit(self):
    limit = self._rts.step_limit
    return float('inf') if limit == NOLIMIT else limit - self._rts._step_base

  @global_limit.setter
  def global_limit(self, limit):
    if limit is None:
      self._rts.step_limit = NOLIMIT
      return
    limit = int(limit)
    if self.global_count >= limit:
      raise control.E_TERMINATE()
    self._rts.step_limit = self._rts._step_base + limit

  def reset_global(self):
    self._rts._step_base = self._rts.steps_total


class RuntimeState(RuntimeStateBase):
  def __init__(self, interp, goal=None):
    istate = interp.backend.get_interpreter_state(interp)
    self.tracing = interp.flags['trace']
    self.setfunction_strategy = \
        _SETF_STRATEGY[interp.flags['setfunction_strategy']]
    self.setfunction_failures = \
        _SETF_FAILURES[interp.flags['setfunction_failures']]
    limit = interp.flags['stack_limit']
    self.stack_limit = NOLIMIT if limit is None else int(limit)
    # The rotation cadence (see cyrt/ticker.hpp): zero steps select time
    # mode with the quantum in nanoseconds.
    mode, value = _flags.parse_rotation(interp.flags['rotation'])
    self.rotation_steps = value if mode == 'steps' else 0
    self.rotation_quantum_ns = value if mode == 'time' else 0
    RuntimeStateBase.__init__(
        self, istate, goal, self.tracing, self.setfunction_strategy
      , self.setfunction_failures, self.stack_limit, self.rotation_steps
      , self.rotation_quantum_ns
      )
    # The count of the stepper starts here (StepCounter.reset_global).
    self._step_base = 0

  @property
  def stepcounter(self):
    '''The step counter of the generic evaluator: a view of this state.'''
    return StepCounter(self)

  def single_step(self, node):
    '''
    One rewrite step at the root of ``node`` (see evaluator.single_step).
    A step that reports an error raises it as the evaluation would.
    '''
    try:
      RuntimeStateBase.single_step(self, node)
    except EvaluationError as err:
      raise exceptions.EvaluationError(str(err))

  def generate_values(self):
    '''
    Generates the values of the goal.

    The Curry program writes to the C standard output, and Python writes to
    ``sys.stdout``.  Both buffers share one file descriptor.  Python's buffer
    is flushed before the scheduler runs, and the C buffer when the scheduler
    returns (see the ``next`` binding), so the output keeps its order.

    The step limit of the stepper (``stepcounter``) ends the evaluation with
    E_TERMINATE, the flow-control exception of the generic evaluator, as on
    the Python backend.
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
    except StepLimitReached:
      raise control.E_TERMINATE()

def _flush_stdout():
  # A closed or missing stdout is legal: some IO tests close it to provoke an
  # error from the program.
  try:
    sys.stdout.flush()
  except (AttributeError, OSError, ValueError):
    pass

