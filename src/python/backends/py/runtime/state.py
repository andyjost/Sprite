from __future__ import absolute_import
from copy import copy
from .... import exceptions
from .... import runtime
from ..sprite import Fingerprint, LEFT, RIGHT, UNDETERMINED
from ....utility import unionfind
from ....utility.shared import Shared, compose, DefaultDict
import collections

from .graph import *
from .misc import *
from .transforms import *

__all__ = ['Evaluator', 'Frame', 'Fingerprint', 'LEFT', 'RIGHT', 'UNDETERMINED']

class Evaluator(object):
  '''Evaluates Curry expressions.'''
  def __new__(cls, interp, goal):
    self = object.__new__(cls)
    self.interp = interp
    goal = self.add_prefix(goal)
    self.queue = collections.deque([Frame(interp, goal)])
    # The number of consecutive blocked frames handled.  If this ever equals
    # the queue length, then the computation fails.
    self.n_consecutive_blocked_seen = 0
    return self

  def add_prefix(self, goal):
    '''Adds the prefix needed for top-level expressions.'''
    return self.interp.expr(
        getattr(self.interp.prelude, '$!!')
      , self.interp.prelude.id
      , goal
      )

  def D(self, *args, **kwds):
    from .fairscheme import D
    return D(self, *args, **kwds)

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
  def __init__(self, interp=None, expr=None, clone=None):
    if clone is None:
      assert expr is not None
      self.interp = interp
      self.expr = expr
      self.fingerprint = Fingerprint()
      self.constraint_store = Shared(unionfind.UnionFind)
      self.bindings = Bindings()
      self.lazy_bindings = Bindings()
      self.blocked_by = None
    else:
      assert interp is None or interp is clone.interp
      self.interp = clone.interp
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
    xid = get_id(e)
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
      conj = getattr(self.interp.prelude, '&')
      bindinfo = getattr(
          self.interp.prelude, 'prim_nonstrictEq' if lazy else 'prim_constrEq'
        )
      act = lambda var: get_generator(self.interp, var, None) if lazy else var
      self.expr = Node(
          getattr(self.interp.prelude, '&>')
        , reduce(
              lambda a, b: Node(conj, a, b)
            , [Node(bindinfo, act(x), e) for x, e in bindings]
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
    vid = get_id(freevar)
    vid = self.constraint_store.read.root(vid)
    if vid in self.fingerprint:
      assert vid not in self.lazy_bindings.read
      _a,(_b,l,r) = freevar
      replacement = l if self.fingerprint[vid] == LEFT else r
      if path:
        replace(self.interp, self.expr[()], path, replacement)
      else:
        self.expr = get_generator(self.interp, freevar, None)
      raise E_CONTINUE()
    vids = list(self.eq_vars(vid))
    if any(vid_ in self.lazy_bindings.read for vid_ in vids):
      self.activate_lazy_bindings(vids, lazy=lazy)
      raise E_CONTINUE()

  def eq_vars(self, vid):
    yield vid
    if vid in self.bindings.read:
      for vid_ in map(get_id, self.bindings.read[vid].read):
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

