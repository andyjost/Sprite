from copy import copy
from ..graph.copy import copygraph
from ..... import inspect
from .. import stepcounter, trace
from ...sprite import Fingerprint
from .....utility import shared, unionfind
import collections, contextlib, itertools

__all__ = ['Configuration', 'InterpreterState', 'Queue', 'RuntimeState']

class DefaultDict(shared.DefaultDict):
  def __repr__(self):
    return '{%s}' % ','.join('%s:%s' % (k,v) for k,v in self.iteritems())

Bindings = lambda: shared.Shared(dict)

class Configuration(object):
  def __init__(
      self, root, fingerprint=None, strict_constraints=None, bindings=None
    , escape_all=False
    ):
    self.root = root
    self.fingerprint = Fingerprint() if fingerprint is None else fingerprint
    self.strict_constraints = shared.Shared(unionfind.UnionFind) \
        if strict_constraints is None else strict_constraints
    self.bindings = Bindings() if bindings is None else bindings
    self.residuals = set()
    self.search_state = []
    self.escape_all = escape_all

  @property
  def path(self):
    for state in self.search_state:
      for part in getattr(state, 'path', state):
        yield part

  def __copy__(self):
    return self.clone(self.root)

  def clone(self, root):
    state = self.fingerprint, self.strict_constraints, self.bindings, self.escape_all
    assert not self.residuals
    return Configuration(root, *map(copy, state))

  def __repr__(self):
    return '{{fp=%s, cst=%s, bnd=%s}}' % (
        self.fingerprint, self.strict_constraints.read, self.bindings
      )


class SetFunctionEval(object):
  '''
  An object representing the evaluation of a set function.  There is a separate
  queue for each instance of this under a distinct fingerprint.  The queues
  share their elements, so steps applied in one queue take effect in them all.
  The purpose of having multiple queues is to filter out configurations that
  are inconsistent from the perspective of the outer context.
  '''
  def __init__(self):
    self.escape_set = set()


class Queue(collections.deque):
  def __init__(self, *args, **kwds):
    sid = kwds.pop('sid', None)
    collections.deque.__init__(self, *args, **kwds)
    self.sid = sid

  def __copy__(self):
    cp = super(Queue, self).__copy__()
    cp.sid = self.sid
    return cp

  def copy(self):
    return self.__copy__()


class InterpreterState(object):
  '''
  The part of the runtime system state that belongs to the interpreter.  Each
  interpreter keeps its own ID factory.  Storing this with the interpreter is
  necessary to ensure that all expressions built by the interpreter are
  compatible.
  '''
  def __init__(self, interp):
    self.idfactory = itertools.count()
    self.setfactory = itertools.count()

class RuntimeState(object):
  '''
  The state of the runtime system during evaluation.  Each time a goal is
  activated an object of this type is created.

  Attributes:
  -----------
      ``C``
          The active configuration.  Equivalent to Q[0].
      ``E``
          The active expression.  Equivalent to Q[0].root.
      ``Q``
          The active work queue.  A sequence of Configurations comprising
          a set of disjoint paths through the non-deterministic solution
          space.  Set functions are implemented with by using multiple queues.  This
          attribute returns the current one.
  '''
  def __init__(self, interp, goal=None):
    # Capture the interpreter state.  This includes mutable objects, such as
    # the standard file streams; system lbraries, such as the Prelude; and
    # functions that might be required by built-ins, such as ``expr``,
    # ``type``, or ``unbox``.
    self.builtin_types = tuple(map(
        interp.type, ('Prelude.Int', 'Prelude.Char', 'Prelude.Float')
      ))
    self.currypath = tuple(interp.path)
    self.expr = interp.expr
    self.integer = interp.integer
    self.prelude = interp.prelude
    self.setfunctions = interp.setfunctions
    self.stdin = interp.stdin
    self.stdout = interp.stdout
    self.topython = interp.topython
    self.tracing = interp.flags['trace']
    self.type = interp.type
    self.unbox = interp.unbox

    # State unique to this evaluation.
    self.idfactory = interp.context.runtime.get_interpreter_state(interp).idfactory
    self.setfactory = interp.context.runtime.get_interpreter_state(interp).setfactory
    self.stepcounter = stepcounter.StepCounter()

    # The Fair Scheme work queues.
    self.qstack = []
    self.qtable = {}
    self.push_queue()
    self.set_goal(goal)

    # The free variable table.  Mapping from ID to Node.
    self.vtable = {}

    # The table of setfunction evaluations.
    self.sftable = {}

    # The trace object.
    self.trace = trace.Trace(self)

  def push_queue(self, sid=None, qid=None):
    if qid is None:
      qid = next(self.setfactory)
      self.qtable[qid] = Queue([], sid=sid)
    self.qstack.append(qid)

  def pop_queue(self):
    self.qstack.pop()

  def create_setfunction(self):
    sid = next(self.setfactory)
    self.sftable[sid] = SetFunctionEval()
    return sid

  @contextlib.contextmanager
  def queue_scope(self, sid=None, qid=None):
    self.push_queue(sid, qid)
    try:
      yield
    finally:
      self.pop_queue()

  def get_sid(self, qid=None):
    qid = self.qid if qid is None else qid
    return self.qtable[qid].sid

  def update_escape_set(self, sid, cid):
    setf = self.sftable[sid]
    setf.escape_set.add(cid)

  def update_escape_sets(self, sids, cid):
    for sid in sids:
      if sid is not None:
        self.update_escape_set(sid=sid, cid=cid)

  def walk_configs(self):
    for qid in self.qstack[::-1]:
      yield self.qtable[qid][0]

  def set_goal(self, goal):
    assert not self.Q
    if goal is not None:
      self.Q.append(Configuration(goal))

  @property
  def in_recursive_call(self):
    return len(self.qstack) > 1

  def make_value(self, arg=None, config=None):
    config = config or self.C
    arg = config.root if arg is None else arg
    if inspect.isa(arg, self.prelude.IO):
      return arg.successors[0]
    skipgrds = set([] if self.sid is None else [self.sid])
    return copygraph(arg, skipfwd=True, skipgrds=skipgrds)

  def release_value(self):
    '''
    Makes a value from the first configuration, detaches that configuration
    from the computation state, and then returns the value.
    '''
    value = self.make_value()
    self.drop()
    return value

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
    '''Reeplaces the current queue.'''
    self.qtable[self.qid] = queue

  @property
  def S(self):
    return self.sftable.get(self.Q.sid, None)

  @property
  def qid(self):
    '''The ID of the current queue.'''
    return self.qstack[-1]

  @property
  def sid(self):
    '''The ID of the current set.'''
    return self.Q.sid

  from .rts_bindings import (
      add_binding, apply_binding, get_binding, has_binding
    , make_value_bindings, update_binding
    )
  from .rts_constraints import (
      constraint_type, constrain_equal, make_constraint
    )
  from .rts_control import (
      append, catch_control, drop, extend, is_io, ready, restart, rotate
    , suspend, unwind
    )
  from .rts_fingerprint import (
      equate_fp, fork, grp_id, obj_id, pull_tab, read_fp, update_fp
    )
  from .rts_setfunctions import guard
  from .rts_freevars import (
      clone_generator, freshvar, freshvar_args, get_freevar, get_generator
    , has_generator, instantiate, is_narrowed, is_nondet, is_void
    , register_freevar
    )
  from ..graph.variable import variable

