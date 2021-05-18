from copy import copy
from ..... import exceptions
from . import freevars
from .. import graph
from ..misc import E_CONTINUE, E_RESIDUAL, E_STEPLIMIT, E_UPDATE_CONTEXT
from ...sprite import Fingerprint, LEFT, RIGHT, UNDETERMINED
from .....tags import *
from .....utility.exprutil import iterexpr
from .....utility import unionfind
from .....utility.shared import Shared, compose, DefaultDict
import collections
import itertools

__all__ = [
    'Evaluator', 'Fingerprint', 'Frame', 'InterpreterState', 'RuntimeState'
  , 'StepCounter', 'LEFT', 'RIGHT', 'UNDETERMINED'
  ]

class InterpreterState(object):
  '''
  The part of the runtime system state the belongs to the interpreter.  Each
  interpreter keeps its own ID factory.  Storing this with the interpreter is
  necessary to ensures that all expressions built by the interpreter are
  compatible.
  '''
  def __init__(self, interp):
    self.idfactory = itertools.count()


class RuntimeState(object):
  '''
  The state of the runtime system during evaluation.  Each time a goal is
  activated an object of this type is created.
  '''
  def __init__(self, interp):
    # Set up flags first.
    self.tracing = interp.flags['trace']
    self.algebraic_substitution = interp.flags['algebraic_substitution']
    self.direct_var_binding = interp.flags['direct_var_binding']

    self.idfactory = interp.context.runtime.get_interpreter_state(interp).idfactory

    self.currypath = tuple(interp.path)
    self.integer = interp.integer
    self.prelude = interp.prelude
    self.S = get_stepper(self)
    self.stepcounter = StepCounter()
    self.currentframe = None

    self.stdout = interp.stdout
    self.stdin = interp.stdin
    self.expr = interp.expr
    self.topython = interp.topython
    self.type = interp.type
    self.unbox = interp.unbox


class Evaluator(object):
  '''
  Evaluates Curry expressions.
  '''
  def __init__(self, interp, goal):
    self.rts = RuntimeState(interp)
    self.queue = collections.deque([Frame(self.rts, self.add_prefix(goal))])

    # The number of consecutive blocked frames handled.  If this ever equals
    # the queue length, then the computation fails.
    self.n_consecutive_blocked_seen = 0

  def add_prefix(self, goal):
    '''Adds the prefix needed for top-level expressions.'''
    rts = self.rts
    return rts.expr(getattr(rts.prelude, '$!!'), rts.prelude.id, goal)

  def evaluate(self):
    from .algo import D
    return D(self)

  def _handle_frame_if_blocked(self, frame):
    '''
    Process a blocked frame, if applicable.  Returns true if the frame was
    indeed blocked, unless the computation suspends.
    '''
    if frame.blocked:
      self.queue.append(frame)
      if frame.unblock():
        self.n_consecutive_blocked_seen = 0
      else:
        self.n_consecutive_blocked_seen += 1
        if self.n_consecutive_blocked_seen == len(self.queue):
          raise exceptions.EvaluationSuspended()
      return True
    else:
      self.n_consecutive_blocked_seen = 0
      return False


Bindings = compose(Shared, compose(DefaultDict, compose(Shared, list)))

class Frame(object):
  '''
  A computation frame.

  One element of the work queue managed by an ``Evaluator``.  Represents an
  expression "activated" for evaluation.
  '''
  def __init__(self, rts=None, expr=None, clone=None):
    if clone is None:
      assert expr is not None
      assert isinstance(rts, RuntimeState)
      self.rts = rts
      self.expr = expr
      self.fingerprint = Fingerprint()
      self.constraint_store = Shared(unionfind.UnionFind)
      self.bindings = Bindings()
      self.lazy_bindings = Bindings()
      self.blocked_by = None
    else:
      assert rts is None or rts is clone.rts
      self.rts = clone.rts
      self.expr = clone.expr if expr is None else expr
      self.fingerprint = copy(clone.fingerprint)
      self.constraint_store = copy(clone.constraint_store)
      self.bindings = copy(clone.bindings)
      self.lazy_bindings = copy(clone.lazy_bindings)
      # sharing is OK; this is only iterated and replaced.
      self.blocked_by = clone.blocked_by

  def __copy__(self): # pragma: no cover
    return Frame(clone=self)

  def __repr__(self):
    e = self.expr[()]
    xid = freevars.get_id(e)
    return '{{id=%x, hd=%s, fp=%s, cst=%s, bnd=%s, lzy=%s, bl=%s}}' % (
        id(self)
      , self.expr[()].info.name + ('' if xid is None else '(%s)' % xid)
      , self.fingerprint
      , self.constraint_store.read
      , dict(self.bindings.read)
      , dict(self.lazy_bindings.read)
      , self.blocked_by
      )

  def show_cid(self, cid_orig, cid_root):
    if cid_orig == cid_root:
      return str(cid_orig)
    else:
      return '%s->%s' % (cid_orig, cid_root)

  def activate_lazy_bindings(self, vids, lazy):
    bindings = []
    for vid in vids:
      if vid in self.lazy_bindings.read:
        # If this variable was involved in a =:= expression, then it is needed;
        # therefore, it would not be in the lazy bindings, nor would it appear
        # unbound in a constructor expression.  The only way to get a mapping
        # to a different root in the constraint store is to process =:=.
        assert self.constraint_store.read.root(vid) == vid
        # This variable is needed.  The binding, now, is therefore effected
        # with =:=.
        bindings += self.lazy_bindings.write.pop(vid).read
    if bindings:
      conj = getattr(self.rts.prelude, '&')
      bindinfo = getattr(
          self.rts.prelude, 'prim_nonstrictEq' if lazy else 'prim_constrEq'
        )
      act = lambda var: freevars.get_generator(self.rts, var, None) if lazy else var
      self.expr = graph.Node(
          getattr(self.rts.prelude, '&>')
        , reduce(
              lambda a, b: graph.Node(conj, a, b)
            , [graph.Node(bindinfo, act(x), e) for x, e in bindings]
            )
        , self.expr
        )
      return True
    else:
      return False

  # When a free variable is needed, check the fingerprint for an existing
  # binding and use it if found.  Otherwise, if there is a lazy binding,
  # activate it.  If only the hnf is needed, use =:<=, otherwise, if the nf is
  # needed, use =:=.
  def check_freevar_bindings(self, freevar, path=(), lazy=False):
    vid = freevars.get_id(freevar)
    vid = self.constraint_store.read.root(vid)
    if vid in self.fingerprint:
      assert vid not in self.lazy_bindings.read
      _a,(_b,l,r) = freevar
      replacement = l if self.fingerprint[vid] == LEFT else r
      if path:
        graph.replace(self.rts, self.expr[()], path, replacement)
      else:
        self.expr = freevars.get_generator(self.rts, freevar, None)
      raise E_CONTINUE()
    vids = list(self.eq_vars(vid))
    if any(vid_ in self.lazy_bindings.read for vid_ in vids):
      self.activate_lazy_bindings(vids, lazy=lazy)
      raise E_CONTINUE()

  def eq_vars(self, vid):
    yield vid
    if vid in self.bindings.read:
      for vid_ in map(freevars.get_id, self.bindings.read[vid].read):
        yield vid_

  @property
  def blocked(self):
    '''Indicates whether the frame is blocked.'''
    return bool(self.blocked_by)


  def block(self, blocked_by):
    '''Block this frame, waiting for any of the free variables.'''
    assert blocked_by
    assert not self.blocked_by
    self.blocked_by = blocked_by
    return self

  def unblock(self):
    '''Try to unblock a blocked frame.'''
    assert self.blocked
    root = self.constraint_store.read.root
    if any(root(x) in self.fingerprint for x in self.blocked_by):
      self.blocked_by = None
      return True
    else:
      return False


class StepCounter(object):
  '''
  Counts the number of steps taken.  If a limit is provided, raises E_STEPLIMIT
  when the limit is reached.
  '''
  def __init__(self, limit=None):
    assert limit > 0 or limit is None
    self._limit = -1 if limit is None else limit
    self.reset()
  @property
  def count(self):
    return self._count
  @property
  def limit(self):
    return self._limit
  def increment(self):
    self._count += 1
    if self._count == self.limit:
      raise E_STEPLIMIT()
  def reset(self):
    self._count = 0


def get_stepper(rts):
  '''
  Returns a function to apply steps, according to the configuration.
  '''
  if rts.tracing:
    indent = [0]
    def step(rts, _0): # pragma: no cover
      print 'S <<<' + '  ' * indent[0], str(_0), getattr(rts, 'currentframe', '')
      indent[0] += 1
      try:
        _0.info.step(rts, _0)
        rts.stepcounter.increment()
      finally:
        indent[0] -= 1
        print 'S >>>' + '  ' * indent[0], str(_0), getattr(rts, 'currentframe', '')
  else:
    def step(rts, _0):
      _0.info.step(rts, _0)
      rts.stepcounter.increment()
  return step

