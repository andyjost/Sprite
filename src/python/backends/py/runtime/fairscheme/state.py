from copy import copy
from . import stepcounter
from ...sprite import Fingerprint
from .....utility import shared, unionfind
import collections
import itertools

class DefaultDict(shared.DefaultDict):
  def __repr__(self):
    return '{%s}' % ','.join('%s:%s' % (k,v) for k,v in self.iteritems())

Bindings = lambda: shared.Shared(dict)

class Configuration(object):
  def __init__(
      self, root, fingerprint=None, strict_constraints=None, bindings=None
    ):
    self.root = root
    self.fingerprint = Fingerprint() if fingerprint is None else fingerprint
    self.strict_constraints = shared.Shared(unionfind.UnionFind) \
        if strict_constraints is None else strict_constraints
    self.bindings = Bindings() if bindings is None else bindings
    self.residuals = set()
    self.search_state = []

  @property
  def path(self):
    for state in self.search_state:
      for part in getattr(state, 'path', state):
        yield part

  def __copy__(self):
    return self.clone(self.root)

  def clone(self, root):
    state = self.fingerprint, self.strict_constraints, self.bindings
    assert not self.residuals
    return Configuration(root, *map(copy, state))

  def __repr__(self):
    return '{{fp=%s, cst=%s, bnd=%s}}' % (
        self.fingerprint, self.strict_constraints.read, self.bindings
      )


Queue = collections.deque

class InterpreterState(object):
  '''
  The part of the runtime system state that belongs to the interpreter.  Each
  interpreter keeps its own ID factory.  Storing this with the interpreter is
  necessary to ensure that all expressions built by the interpreter are
  compatible.
  '''
  def __init__(self, interp):
    self.idfactory = itertools.count()

class RuntimeState(object):
  '''
  The state of the runtime system during evaluation.  Each time a goal is
  activated an object of this type is created.

  Attributes:
  -----------
      ``C``
          The active configuration.  Equivalent to queue[0].
      ``E``
          The active expression.  Equivalent to queu[0].root.
      ``queue``
          The Fair Scheme work queue.  A sequence of Configurations comprising
          a set of disjoint paths through the non-deterministic solution
          space.
  '''
  def __init__(self, interp, goal=None):
    # Capture the interpreter state.  This includes mutable objects, such as
    # the standard file streams; system lbraries, such as the Prelude; and
    # functions that might be required by built-ins, such as the ``expr``,
    # ``type``, and ``unbox`` functions.
    self.builtin_types = tuple(map(
        interp.type, ('Prelude.Int', 'Prelude.Char', 'Prelude.Float')
      ))
    self.currypath = tuple(interp.path)
    self.expr = interp.expr
    self.integer = interp.integer
    self.prelude = interp.prelude
    self.stdin = interp.stdin
    self.stdout = interp.stdout
    self.topython = interp.topython
    self.tracing = interp.flags['trace']
    self.type = interp.type
    self.unbox = interp.unbox

    # State unique to this evaluation.
    self.idfactory = interp.context.runtime.get_interpreter_state(interp).idfactory
    self.stepcounter = stepcounter.StepCounter()

    # The Fair Scheme work queue.
    self.queue = Queue([])
    self.set_goal(goal)

    # The free variable table.  Mapping from ID to Node.
    self.vtable = {}

    # The trace object.
    from .. import trace
    self.trace = trace.Trace(self)

  def set_goal(self, goal):
    assert not self.queue
    if goal is not None:
      self.queue.append(Configuration(goal))

  @property
  def C(self):
    '''The current configuration.'''
    return self.queue[0]

  @property
  def E(self):
    '''The current root expression.'''
    return self.C.root

  @E.setter
  def E(self, node):
    self.C.root = node

  from .rts_bindings import (
      add_binding, apply_binding, get_binding, has_binding, update_binding
    )
  from .rts_constraints import constraint_type, constrain_equal
  from .rts_control import (
      append, catch_control, drop, extend, ready, restart, rotate, suspend
    , unwind
    )
  from .rts_fingerprint import (
      equate_fp, fork, grp_id, obj_id, read_fp, update_fp
    )
  from .rts_variables import (
      clone_generator, freshvar, freshvar_args, get_generator, get_variable
    , has_generator, instantiate, is_free, is_narrowed, is_nondet, is_variable
    , register_variable
    )

