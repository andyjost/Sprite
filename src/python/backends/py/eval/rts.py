from ...generic.eval import stepcounter, telemetry, trace
from ..graph import infotable
from . import configuration
from .. import graph
from .... import inspect
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

  def set_goal(self, goal):
    assert not self.Q
    if goal is not None:
      self.append(configuration.Configuration(goal))

  def generate_values(self):
    from .fairscheme import D
    return D(self)

  @property
  def C(self):
    '''The current configuration.'''
    return self.Q[0]

  @C.setter
  def C(self, config):
    self.Q[0] = config

  @property
  def E(self):
    '''The current root expression.'''
    return self.C.root

  @E.setter
  def E(self, node):
    self.C.root = node

  @property
  def Q(self):
    '''The current queue.'''
    return self.qtable[self.qid]

  @Q.setter
  def Q(self, queue):
    '''Replaces the current queue.'''
    self.qtable[self.qid] = queue

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
      append, catch_control, drop, extend, is_io, make_value, ready
    , release_value, restart, rotate, suspend, unwind
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

