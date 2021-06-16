from .evaluator import Frame
from . import freevars as freevars_module
from .. import graph
from .. import trace
from ..... import icurry
from ..misc import E_CONTINUE, E_RESIDUAL, E_STEPLIMIT
from ...sprite import LEFT, RIGHT, UNDETERMINED
from .....tags import *

__all__ = ['D', 'N', 'hnf']

def D(evaluator):
  '''The dispatch (D) Fair Scheme procedure.'''
  while evaluator.queue:
    rts = evaluator.rts
    frame = evaluator.queue.popleft()
    rts.currentframe = frame
    if evaluator._handle_frame_if_blocked(frame):
      continue
    trace.activate_frame(rts)
    if isinstance(frame.expr, icurry.ILiteral):
      trace.yield_(rts, frame.expr)
      yield frame.expr
      continue
    tag = frame.expr.info.tag
    if tag == T_CHOICE:
      evaluator.queue.extend(fork(frame))
    elif tag == T_BIND:
      evaluator.queue.extend(constrain(frame))
    elif tag == T_FAIL:
      trace.failed(rts)
      # discard this frame
    elif tag == T_FREE:
      vid = frame.get_id(frame.expr)
      if vid in frame.fingerprint:
        _,(_,l,r) = frame.expr
        frame.expr = l if frame.fingerprint[vid] == LEFT else r
        evaluator.queue.append(frame)
      else:
        vids = list(frame.eq_vars(vid))
        if any(vid_ in frame.lazy_bindings.read for vid_ in vids):
          activate_implicit_constraints(rts.currentframe, vids)
          evaluator.queue.append(frame)
        else:
          for value in iter_values(rts, frame, frame.expr):
            trace.yield_(rts, value)
            yield value
    elif tag == T_FUNC:
      try:
        rts.S(rts, frame.expr)
      except E_CONTINUE:
        evaluator.queue.append(frame)
      except E_RESIDUAL as res:
        evaluator.queue.append(frame.block(blocked_by=res.ids))
      else:
        evaluator.queue.append(frame)
    elif tag >= T_CTOR:
      try:
        _, freevars = N(rts, frame.expr, frame.expr)
      except E_CONTINUE:
        evaluator.queue.append(frame)
      except E_RESIDUAL as res:
        evaluator.queue.append(frame.block(blocked_by=res.ids))
      else:
        if frame.expr.info.tag == tag:
          for value in iter_values(rts, frame, frame.expr):
            trace.yield_(rts, value)
            yield value
        else:
          evaluator.queue.append(frame)
    else:
      assert False

def N(rts, root, target=None, path=None, freevars=None):
  '''The normalize (N) Fair Scheme procedure.'''
  root = graph.Node.getitem(root)
  path = [] if path is None else path
  target = root[path] if target is None else target
  assert target.info.tag >= T_CTOR
  freevars = set() if freevars is None else freevars
  if target.info is rts.prelude._PartApplic.info:
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
          graph.Node(rts.prelude._Failure, target=root)
          raise E_CONTINUE()
        elif tag == T_CHOICE:
          graph.lift_choice(rts, root, path)
          raise E_CONTINUE()
        elif tag == T_BIND:
          graph.lift_constr(rts, root, path)
          raise E_CONTINUE()
        elif tag == T_FREE:
          frame = rts.currentframe
          vid = frame.get_id(succ)
          if vid in frame.fingerprint:
            _,(_,l,r) = succ
            replacement = l if frame.fingerprint[vid] == LEFT else r
            frame.expr = graph.replace_copy(rts, frame.expr, path, replacement)
            raise E_CONTINUE()
          vids = list(frame.eq_vars(vid))
          if any(vid_ in frame.lazy_bindings.read for vid_ in vids):
            activate_implicit_constraints(rts.currentframe, vids)
            raise E_CONTINUE()
          freevars.add(succ)
          break
        elif tag == T_FUNC:
          try:
            rts.S(rts, succ)
          except E_CONTINUE:
            pass
        elif tag >= T_CTOR:
          _,freevars2 = N(rts, root, succ, path, freevars)
          freevars.update(freevars2)
          break
        else:
          assert False
  finally:
    path.pop()
  return target, freevars

def hnf(rts, expr, path, typedef=None, values=None):
  assert path
  assert expr.info.tag == T_FUNC
  target = expr[path]
  while True:
    if isinstance(target, icurry.ILiteral):
      return target
    tag = target.info.tag
    if tag == T_FAIL:
      graph.Node(rts.prelude._Failure, target=expr)
      raise E_CONTINUE()
    elif tag == T_CHOICE:
      graph.lift_choice(rts, expr, path)
      raise E_CONTINUE()
    elif tag == T_BIND:
      graph.lift_constr(rts, expr, path)
      raise E_CONTINUE()
    elif tag == T_FREE:
      if typedef is None:
        vid = freevars_module.get_id(target)
        raise E_RESIDUAL([vid])
      else:
        target = freevars_module.instantiate(rts, expr, path, typedef)
    elif tag == T_FUNC:
      try:
        rts.S(rts, target)
      except E_CONTINUE:
        pass
    elif tag >= T_CTOR:
      return target
    elif tag == T_FWD:
      target = expr[path] # remove FWD nodes
      assert target.info.tag != T_FWD
    else:
      assert False

def _fork_updatebindings(frame, xid):
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
    for var in frame.bindings.write.pop(xid, []):
      assert var.info.tag == T_FREE
      vid = freevars_module.get_id(var)
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
          if not bind(frame, pivot, var):
            return 1
      break
  # Activate lazy bindings for this group of variables, now that a binding is
  # available.
  seen_ids.add(xid)
  return 2 if activate_implicit_constraints(frame, seen_ids, lazy=True) else 0

def fork(frame):
  '''
  Fork a choice-rooted frame into its left and right children.  Yields each
  consistent child.  Recycles ``frame``.
  '''
  assert frame.expr[()].info.tag == T_CHOICE
  cid_,lhs,rhs = frame.expr[()]
  cid = frame.constraint_store.read.root(cid_)
  if cid in frame.bindings.read or cid in frame.lazy_bindings.read:
    bindresult = _fork_updatebindings(frame, cid)
    if bindresult:
      if bindresult == 1: # inconsistent
        trace.kill(rts)
        return
      else:
        assert bindresult == 2 # new bindings: keep working
        yield frame
        return
    else:
      cid = frame.constraint_store.read.root(cid)
  if cid in frame.fingerprint: # Decided, so one child.
    lr = frame.fingerprint[cid]
    assert lr in [LEFT,RIGHT]
    frame.expr = lhs if lr==LEFT else rhs
    yield frame
  else: # Undecided, so two children.
    lchild = Frame(expr=lhs, clone=frame)
    lchild.fingerprint.set_left(cid)
    yield lchild
    frame.expr = rhs
    frame.fingerprint.set_right(cid)
    yield frame

def constrain(frame):
  '''
  Process a constraint-rooted frame.  Update the constraint store and discard
  the constraint node.
  '''
  frame.expr, (x, y) = frame.expr
  if bind(frame, x, y):
    yield frame

def bind(frame, _x, _y):
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
      x_id, y_id = map(frame.constraint_store.read.root, [x_id, y_id])
      if x_id != y_id:
        x_lr, y_lr = map(frame.fingerprint.get, [x_id, y_id])
        code = 3 * x_lr + y_lr
        acode = abs(code)
        if acode == 1:
          frame.fingerprint[x_id] = LEFT if code<0 else RIGHT
        elif acode == 2:
          return False # inconsistent
        elif acode == 3:
          frame.fingerprint[y_id] = LEFT if code<0 else RIGHT
        frame.constraint_store.write.unite(x_id, y_id)
        stack.extend([(xr, yr), (xl, yl)])
    elif x.info.tag == T_FREE:
      if y.info.tag != T_FREE:
        # This is a lazy binding.
        x_id, _ = x
        vid = frame.constraint_store.read.root(x_id)
        frame.lazy_bindings.write[vid].write.append((x,y))
      else:
        (x_id, x_gen), (y_id, y_gen) = x, y
        x_id, y_id = map(frame.constraint_store.read.root, [x_id, y_id])
        if x_id != y_id:
          # Whether x/y are NOT bound.
          x_nbnd, y_nbnd = (arg.info.tag == T_CTOR for arg in [x_gen, y_gen])
          if x_nbnd and y_nbnd:
            # Place unbound variables in the binding store.
            bnd = frame.bindings.write
            bnd[x_id].write.append(y)
            bnd[y_id].write.append(x)
            # frame.constraint_store.write.unite(x_id, y_id)
          else:
            # Continue binding recursively.
            if x_nbnd:
              freevars_module.clone_generator(frame.rts, y, x)
              x_gen = x[1]
            elif y_nbnd:
              freevars_module.clone_generator(frame.rts, x, y)
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

def iter_values(rts, frame, expr):
  # TODO
  yield expr

def activate_implicit_constraints(frame, vids, lazy=False):
  '''
  Locates newly uncovered constraints associated with ``vids`` and inserts
  necessary apllications of an equational constraint operator at the root.

  An equational constraint between free variables can imply an unbounded number
  of implicit constraints.  For example x =:= y, where x and y are lists,
  implies equality between the list spines and every element.  Obviously, such
  a constraint cannot be checked eagerly, since that would involve an infinite
  recursion.  Instead, as the rules of the program narrow x and/or y, the
  runtime must add the implicit constraints.  This function does exactly that.
  '''
  bindings = []
  for vid in vids:
    if vid in frame.lazy_bindings.read:
      # If this variable was involved in a =:= expression, then it is needed;
      # therefore, it would not be in the lazy bindings, nor would it appear
      # unbound in a constructor expression.  The only way to get a mapping
      # to a different root in the constraint store is to process =:=.
      assert frame.constraint_store.read.root(vid) == vid
      # This variable is needed.  The binding, now, is therefore effected
      # with =:=.
      bindings += frame.lazy_bindings.write.pop(vid).read
  if bindings:
    conj = getattr(frame.rts.prelude, '&')
    bindinfo = getattr(
        frame.rts.prelude, 'prim_nonstrictEq' if lazy else 'prim_constrEq'
      )
    act = lambda var: freevars_module.get_generator(frame.rts, var, None) if lazy else var
    frame.expr = graph.Node(
        getattr(frame.rts.prelude, '&>')
      , reduce(
            lambda a, b: graph.Node(conj, a, b)
          , [graph.Node(bindinfo, act(x), e) for x, e in bindings]
          )
      , frame.expr
      )
    return True
  else:
    return False

