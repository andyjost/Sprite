from __future__ import absolute_import
from copy import copy
from .... import exceptions
from .... import icurry
from ..sprite import Fingerprint, LEFT, RIGHT, UNDETERMINED
from ....utility import unionfind
from ....utility.shared import Shared, compose, DefaultDict
import collections

from .exceptions import *
from .graph import *
from .misc import *
from .transforms import *

__all__ = ['Evaluator', 'Frame', 'hnf', 'N', 'S', 'LEFT', 'RIGHT', 'UNDETERMINED']

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

  def D(self):
    '''The dispatch (D) Fair Scheme procedure.'''
    while self.queue:
      frame = self.queue.popleft()
      self.interp.currentframe = frame
      if self._handle_frame_if_blocked(frame):
        continue
      expr = frame.expr
      target = expr[()]
      if self.interp.flags['trace']:
        print 'F :::', target, frame
      if isinstance(target, icurry.ILiteral):
        if self.interp.flags['trace']:
          print 'Y :::', target, frame
        yield target
        continue
      tag = target.info.tag
      if tag == T_CHOICE:
        self.queue.extend(frame.fork())
      elif tag == T_BIND:
        self.queue.extend(frame.constrain())
      elif tag == T_FAIL:
        if self.interp.flags['trace']:
          print 'X :::', frame
        continue # discard
      elif tag == T_FREE:
        try:
          frame.check_freevar_bindings(target, lazy=False)
        except E_CONTINUE:
          # TODO: Maybe a property for frame.expr would be better.
          frame.expr = self.add_prefix(frame.expr)
          self.queue.append(frame)
        else:
          if self.interp.flags['trace']:
            print 'Y :::', target, frame
          yield target
      elif tag == T_FUNC:
        try:
          S(self.interp, target)
        except E_CONTINUE:
          # assert expr.info.tag < T_CTOR and expr.info.tag != T_FUNC
          self.queue.append(frame)
        except E_RESIDUAL as res:
          self.queue.append(frame.block(blocked_by=res.ids))
        except E_UPDATE_CONTEXT as cxt:
          frame.expr = cxt.expr
          self.queue.append(frame)
        else:
          # TODO: The expr property was removed, so this next line does not do
          # what is says.
          frame.expr = frame.expr # insert FWD node, if needed.
          self.queue.append(frame)
      elif tag >= T_CTOR:
        try:
          _, freevars = N(self.interp, expr, target)
        except E_CONTINUE:
          # assert expr.info.tag < T_CTOR and expr.info.tag != T_FUNC
          self.queue.append(frame)
        except E_RESIDUAL as res:
          self.queue.append(frame.block(blocked_by=res.ids))
        else:
          target = expr[()]
          if target.info.tag == tag:
            if self.interp.flags['trace']:
              print 'Y :::', target, frame
            yield target
          else:
            self.queue.append(frame)
      else:
        assert False

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

  def _fork_updatebindings(self, xid):
    '''
    Updates the bindings and lazy_bindings based on a new choice with id xid
    reaching the root.

    Returns:
    --------
      0: on success;
      1: on failure (inconsistent);
      2: if new lazy bindings were activated.
    '''
    # Collect all variables in the equivalence set of xid.  Clear the bindings
    # as we go.
    seen_ids = set()
    equiv_vars = []
    queue = [xid]
    while queue:
      xid = queue.pop()
      for var in self.bindings.write.pop(xid, []):
        assert var.info.tag == T_FREE
        vid = get_id(var)
        if vid not in seen_ids:
          seen_ids.add(vid)
          equiv_vars.append(var)
          queue.append(vid)
    # Look for a variable, the pivot, with a bound generator.  If it is found,
    # equate all variables to it.
    for pivot in equiv_vars:
      if pivot[1].info.tag == T_CHOICE:
        for var in equiv_vars:
          if var is not pivot:
            if not self.bind(pivot, var):
              return 1
        break
    # Activate lazy bindings for this group of variables, now that a binding is
    # available.
    seen_ids.add(xid)
    return 2 if self.activate_lazy_bindings(seen_ids, lazy=True) else 0

  def fork(self):
    '''
    Fork a choice-rooted frame into its left and right children.  Yields each
    consistent child.  Recycles ``self``.
    '''
    assert self.expr[()].info.tag == T_CHOICE
    cid_,lhs,rhs = self.expr[()]
    cid = self.constraint_store.read.root(cid_)
    if cid in self.bindings.read or cid in self.lazy_bindings.read:
      bindresult = self._fork_updatebindings(cid)
      if bindresult:
        if bindresult == 1: # inconsistent
          if self.interp.flags['trace']:
            print '? ::: %x inconsistent at %s' % (id(self), self.show_cid(cid_, cid))
          return
        else:
          assert bindresult == 2 # new bindings: keep working
          yield self
          return
      else:
        cid = self.constraint_store.read.root(cid)
    if cid in self.fingerprint: # Decided, so one child.
      lr = self.fingerprint[cid]
      assert lr in [LEFT,RIGHT]
      self.expr = lhs if lr==LEFT else rhs
      if self.interp.flags['trace']:
        print '? ::: %s, %s%s >> %x' % (
            self.show_cid(cid_, cid), cid, 'L' if lr==LEFT else 'R', id(self)
          )
      yield self
    else: # Undecided, so two children.
      lchild = Frame(expr=lhs, clone=self)
      if self.interp.flags['trace']:
        print '? ::: %s, %sL >> %x, %sR >> %x' % (
            self.show_cid(cid_, cid), cid, id(lchild), cid, id(self)
          )
      lchild.fingerprint.set_left(cid)
      yield lchild
      self.expr = rhs
      self.fingerprint.set_right(cid)
      yield self

  def show_cid(self, cid_orig, cid_root):
    if cid_orig == cid_root:
      return str(cid_orig)
    else:
      return '%s->%s' % (cid_orig, cid_root)

  def constrain(self):
    '''
    Process a constraint-rooted frame.  Update the constraint store and discard
    the constraint node.
    '''
    self.expr, (x, y) = self.expr
    if self.bind(x, y):
      yield self

  def bind(self, _x, _y):
    '''
    Bind matching shallow constructor expressions.  If the first argument is
    free and the second is an expression, then a lazy binding is created.  The
    return value indicates whether the binding is consistent.
    '''
    assert _x.info.tag == _y.info.tag or _x.info.tag == T_FREE
    stack = [(_x, _y)]
    while stack:
      x, y = stack.pop()
      x, y = x[()], y[()]
      if x.info.tag == T_CHOICE:
        (x_id, xl, xr), (y_id, yl, yr) = x, y
        x_id, y_id = map(self.constraint_store.read.root, [x_id, y_id])
        if x_id != y_id:
          x_lr, y_lr = map(self.fingerprint.get, [x_id, y_id])
          code = 3 * x_lr + y_lr
          acode = abs(code)
          if acode == 1:
            self.fingerprint[x_id] = LEFT if code<0 else RIGHT
          elif acode == 2:
            return False # inconsistent
          elif acode == 3:
            self.fingerprint[y_id] = LEFT if code<0 else RIGHT
          self.constraint_store.write.unite(x_id, y_id)
          stack.extend([(xr, yr), (xl, yl)])
      elif x.info.tag == T_FREE:
        if y.info.tag != T_FREE:
          # This is a lazy binding.
          x_id, _ = x
          vid = self.constraint_store.read.root(x_id)
          self.lazy_bindings.write[vid].write.append((x,y))
        else:
          (x_id, x_gen), (y_id, y_gen) = x, y
          x_id, y_id = map(self.constraint_store.read.root, [x_id, y_id])
          if x_id != y_id:
            # Whether x/y are NOT bound.
            x_nbnd, y_nbnd = (arg.info.tag == T_CTOR for arg in [x_gen, y_gen])
            if x_nbnd and y_nbnd:
              # Place unbound variables in the binding store.
              bnd = self.bindings.write
              bnd[x_id].write.append(y)
              bnd[y_id].write.append(x)
            else:
              # Continue binding recursively.
              if x_nbnd:
                clone_generator(self.interp, y, x)
                x_gen = x[1]
              elif y_nbnd:
                clone_generator(self.interp, x, y)
                y_gen = y[1]
              stack.append((x_gen, y_gen))
      elif x.info.tag >= T_CTOR:
        assert x.info is y.info
        stack.extend(zip(x, y))
      elif x.info.tag == T_FAIL:
        continue
      else:
        raise TypeError('unexpected tag %s' % x.info.tag)
    return True

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
      bindinfo = getattr(self.interp.prelude, '=:<=' if lazy else '=:=')
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

def N(interp, root, target=None, path=None, freevars=None):
  '''The normalize (N) Fair Scheme procedure.'''
  path = [] if path is None else path
  target = root[path] if target is None else target
  assert target.info.tag >= T_CTOR
  freevars = set() if freevars is None else freevars
  if target.info is interp.prelude._PartApplic.info:
    # A partial application is a value even through it may contain a function
    # symbol.  The first successor (# of arguments remaining) is unboxed, so there
    # is nothing to normalize.
    return target, freevars
  path.append(None)
  try:
    for path[-1], succ in enumerate(target):
      while True:
        if isinstance(succ, icurry.ILiteral):
          break
        succ = succ[()]
        tag = succ.info.tag
        if tag == T_FAIL:
          Node(interp.prelude._Failure, target=root)
          raise E_CONTINUE()
        elif tag == T_CHOICE:
          lift_choice(interp, root, path)
          raise E_CONTINUE()
        elif tag == T_BIND:
          lift_constr(interp, root, path)
          raise E_CONTINUE()
        elif tag == T_FREE:
          interp.currentframe.check_freevar_bindings(succ, path, lazy=False)
          freevars.add(succ)
          break
        elif tag == T_FUNC:
          try:
            S(interp, succ)
          except E_CONTINUE:
            pass
        elif tag >= T_CTOR:
          _,freevars2 = N(interp, root, succ, path, freevars)
          freevars.update(freevars2)
          break
        else:
          assert False
  finally:
    path.pop()
  return target, freevars

def hnf(interp, expr, path, typedef=None, values=None):
  assert path
  assert expr.info.tag == T_FUNC
  target = expr[path]
  while True:
    if isinstance(target, icurry.ILiteral):
      return target
    tag = target.info.tag
    if tag == T_FAIL:
      Node(interp.prelude._Failure, target=expr)
      raise E_CONTINUE()
    elif tag == T_CHOICE:
      lift_choice(interp, expr, path)
      raise E_CONTINUE()
    elif tag == T_BIND:
      lift_constr(interp, expr, path)
      raise E_CONTINUE()
    elif tag == T_FREE:
      if typedef is None or typedef is interp.type('Prelude.Int'):
        vid = get_id(target)
        if vid in interp.currentframe.lazy_bindings.read:
          bl, br = interp.currentframe.lazy_bindings.read[vid][0]
          assert bl is target
          replacement = replace_copy(interp, expr, path, br)
          raise E_UPDATE_CONTEXT(replacement)
        elif values:
          values = map(int, values)
          replace(interp, expr, path
            , Node(interp.integer.narrowInt, expr[path], interp.expr(values))
            )
          target = expr[path]
        else:
          raise E_RESIDUAL([vid])
      else:
        target = instantiate(interp, expr, path, typedef)
    elif tag == T_FUNC:
      try:
        S(interp, target)
      except E_CONTINUE:
        pass
      except E_UPDATE_CONTEXT as cxt:
        replacement = replace_copy(interp, expr, path, cxt.expr)
        raise E_UPDATE_CONTEXT(replacement)
    elif tag >= T_CTOR:
      return target
    elif tag == T_FWD:
      target = expr[path]
    else:
      assert False

def S(interp, target):
  '''The step (S) Fair Scheme procedure.'''
  interp._stepper(target)

