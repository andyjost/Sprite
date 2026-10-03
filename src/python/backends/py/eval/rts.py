from ...generic.eval import stepcounter, telemetry, trace
from ..graph import infotable
from . import configuration
from .. import graph
from .... import inspect
from ....utility import maxrecursion
import itertools

__all__ = ['InterpreterState', 'RuntimeState']

class InterpreterState(object):
  '''
  The part of the runtime system state that belongs to the interpreter.  Each
  interpreter keeps its own ID factory.  Storing this with the interpreter is
  necessary to ensure that all expressions built by the interpreter are
  compatible.
  '''
  def __init__(self):
    self.idfactory = itertools.count()
    self.setfactory = itertools.count()

class RuntimeState(object):
  # Fundamental symbols.
  from ..currylib.fundamental import (
      Choice, Failure, Free, Fwd, NonStrictConstraint
    , PartApplic, SetGuard, StrictConstraint, ValueBinding
    )
  '''
  The state of the runtime system during evaluation.  Each time a goal is
  activated an object of this type is created.

  Attributes:
    ``C``
      The active configuration.  Equivalent to Q[0].
    ``E``
      The active expression.  Equivalent to Q[0].root.
    ``Q``
      The active work queue.  A sequence of Configurations comprising a set of
      disjoint paths through the non-deterministic solution space.  Set
      functions are implemented with by using multiple queues.  This attribute
      returns the current one.
  '''
  def __init__(self, interp, goal=None):
    # Capture the interpreter state.  This includes mutable objects, such as
    # the standard file streams; system lbraries, such as the Prelude; and
    # functions that might be required by built-ins, such as ``expr``,
    # ``type``, or ``unbox``.
    self.interp = interp
    self.__builtin_types = tuple(
        interp.type(typename).datatype
            for typename in ('Prelude.Int', 'Prelude.Char', 'Prelude.Float')
      )
    self.currypath = tuple(interp.path)
    self.expr = interp.raw_expr
    self.setfunction_strategy = interp.flags['setfunction_strategy']
    self.prelude = interp.prelude
    self.stdin = interp.stdin
    self.stdout = interp.stdout
    self.symbol = interp.symbol
    self.topython = interp.topython
    self.tracing = interp.flags['trace']
    self.type = interp.type
    self.unbox = interp.unbox

    # Other runtime objects.
    self.Node = graph.Node

    # State unique to this evaluation.
    self.idfactory = interp.backend.get_interpreter_state(interp).idfactory
    self.setfactory = interp.backend.get_interpreter_state(interp).setfactory
    self.stepcounter = stepcounter.StepCounter()
    # The step budget of a configuration.  See rts_control.count_step.
    self.step_budget = interp.flags['step_budget']
    # The error of an alternative dropped at the stack limit.  D raises it
    # when the outermost queue is empty.  See rts_control.overflow.
    self.deferred_error = None

    self.trace = trace.Trace(self)
    self.telemetry = telemetry.TelemetryData(self)

    # The Fair Scheme work queues.
    self.qstack = []
    self.qtable = {}
    self.push_queue(trace=False)
    self.set_goal(goal)

    # The free variable table.  Mapping from ID to Node.
    self.vtable = {}

    # The table of setfunction evaluations.
    self.sftable = {}

  @property
  def setfunctions(self):
    return self.interp.setfunctions

  # The C++ runtime state has the same two attributes.  The evaluator reads
  # them for the statistics of a run (Interpreter.stats).
  @property
  def steps_total(self):
    '''The number of rewrite steps taken in this evaluation.'''
    return self.stepcounter.global_count

  @property
  def forks_total(self):
    '''The number of times a configuration forked in this evaluation.'''
    return self.telemetry._forks

  def single_step(self, node):
    '''
    Takes one rewrite step at the root of ``node``, outside the step loop
    (see evaluator.single_step).  The step function takes the root as a
    variable, as in S.  A completed step counts as in S: the step counter and
    the current configuration take it up.  A step that raises left its redex
    as it was and counts nothing.
    '''
    node.info.step(self, self.variable(node))
    self.stepcounter.increment()
    self.count_step()

  def set_goal(self, goal):
    assert not self.Q
    if goal is not None:
      self.append(configuration.Configuration(goal))

  def generate_values(self):
    '''
    Generate the values of the goal.

    The evaluator nests one Python call per level of a deep expression, so
    each value is computed under a raised recursion limit (see
    utility.maxrecursion).  The limit is restored between values.
    '''
    from .fairscheme import D
    values = D(self)
    while True:
      with maxrecursion():
        try:
          value = next(values)
        except StopIteration:
          return
      yield value

  # The evaluator reads these properties on every iteration, so each one
  # reads the queue table directly rather than through the other properties.
  @property
  def C(self):
    '''The current configuration.  Equivalent to Q[0].'''
    return self.qtable[self.qstack[-1]][0]

  @C.setter
  def C(self, config):
    self.qtable[self.qstack[-1]][0] = config

  @property
  def E(self):
    '''The current root expression.  Equivalent to C.root.'''
    return self.qtable[self.qstack[-1]][0].root

  @E.setter
  def E(self, node):
    self.qtable[self.qstack[-1]][0].root = node

  @property
  def Q(self):
    '''The current queue.  Equivalent to qtable[qid].'''
    return self.qtable[self.qstack[-1]]

  @Q.setter
  def Q(self, queue):
    '''Replaces the current queue.'''
    self.qtable[self.qstack[-1]] = queue

  @property
  def S(self):
    '''The current set evaluation.'''
    return self.sftable.get(self.Q.sid, None)

  def is_builtin_type(self, ty):
    assert ty is None or isinstance(ty, infotable.DataType)
    return ty in self.__builtin_types

  from ..graph.variable import variable
  from .rts_bindings import (
      add_binding, apply_binding, get_binding, has_binding
    , make_value_bindings, update_binding
    )
  from .rts_constraints import (
      constraint_type, constrain_equal, lift_constraint
    )
  from .rts_control import (
      append, catch_control, count_step, drop, extend, is_io, make_value
    , overflow, raise_deferred_error, ready, release_value, restart, rotate
    , suspend, unwind
    )
  from .rts_fingerprint import (
      equate_fp, fork, grp_id, obj_id, pull_tab, read_fp, update_fp
    )
  from .rts_freevars import (
      clone_generator, freshvar, freshvar_args, get_freevar, get_generator
    , has_generator, instantiate, is_narrowed, is_nondet, is_void
    , register_freevar
    )
  from .rts_setfunctions import (
      create_queue, create_setfunction, choice_escapes, filter_queue, guard_args
    , guard, in_recursive_call, pop_queue, push_queue, qid, queue_scope, qid
    , SetFunctionEval, sid, update_escape_set, update_escape_sets, walk_qstack
    )

  in_recursive_call = property(in_recursive_call)
  qid = property(qid)
  sid = property(sid)

