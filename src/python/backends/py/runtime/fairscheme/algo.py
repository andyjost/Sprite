from .evaluator import Frame
from . import freevars
from .. import graph
from .. import trace
from ..... import icurry
from ..misc import E_CONTINUE, E_RESIDUAL, E_STEPLIMIT, E_UPDATE_CONTEXT
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
    expr = frame.expr
    target = expr[()]
    trace.activate_frame(rts)
    if isinstance(target, icurry.ILiteral):
      trace.yield_(rts, target)
      yield target
      continue
    tag = target.info.tag
    if tag == T_CHOICE:
      evaluator.queue.extend(fork(frame))
    elif tag == T_BIND:
      evaluator.queue.extend(constrain(frame))
    elif tag == T_FAIL:
      trace.failed(rts)
      continue # discard
    elif tag == T_FREE:
      try:
        frame.check_freevar_bindings(target, lazy=False)
      except E_CONTINUE:
        # TODO: Maybe a property for frame.expr would be better.
        frame.expr = evaluator.add_prefix(frame.expr)
        evaluator.queue.append(frame)
      else:
        for value in iter_values(rts, frame, target):
          trace.yield_(rts, value)
          yield value
    elif tag == T_FUNC:
      try:
        rts.S(rts, target)
      except E_CONTINUE:
        # assert expr.info.tag < T_CTOR and expr.info.tag != T_FUNC
        evaluator.queue.append(frame)
      except E_RESIDUAL as res:
        evaluator.queue.append(frame.block(blocked_by=res.ids))
      except E_UPDATE_CONTEXT as cxt:
        frame.expr = cxt.expr
        evaluator.queue.append(frame)
      else:
        # TODO: The expr property was removed, so this next line does not do
        # what is says.
        frame.expr = frame.expr # insert FWD node, if needed.
        evaluator.queue.append(frame)
    elif tag >= T_CTOR:
      try:
        _, freevars = N(rts, expr, target)
      except E_CONTINUE:
        # assert expr.info.tag < T_CTOR and expr.info.tag != T_FUNC
        evaluator.queue.append(frame)
      except E_RESIDUAL as res:
        evaluator.queue.append(frame.block(blocked_by=res.ids))
      else:
        target = expr[()]
        if target.info.tag == tag:
          for value in iter_values(rts, frame, target):
            trace.yield_(rts, value)
            yield value
        else:
          evaluator.queue.append(frame)
    else:
      assert False

def N(rts, root, target=None, path=None, freevars=None):
  '''The normalize (N) Fair Scheme procedure.'''
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
          rts.currentframe.check_freevar_bindings(succ, path, lazy=False)
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
      if typedef is None or typedef is rts.type('Prelude.Int'):
        vid = freevars.get_id(target)
        if vid in rts.currentframe.lazy_bindings.read:
          bl, br = rts.currentframe.lazy_bindings.read[vid][0]
          assert bl is target
          replacement = graph.replace_copy(rts, expr, path, br)
          raise E_UPDATE_CONTEXT(replacement)
        elif values:
          values = map(int, values)
          graph.replace(rts, expr, path
            , graph.Node(rts.integer.narrowInt, expr[path], rts.expr(values))
            )
          target = expr[path]
        else:
          raise E_RESIDUAL([vid])
      else:
        target = freevars.instantiate(rts, expr, path, typedef)
    elif tag == T_FUNC:
      try:
        rts.S(rts, target)
      except E_CONTINUE:
        pass
      except E_UPDATE_CONTEXT as cxt:
        replacement = graph.replace_copy(rts, expr, path, cxt.expr)
        raise E_UPDATE_CONTEXT(replacement)
    elif tag >= T_CTOR:
      return target
    elif tag == T_FWD:
      target = expr[path]
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
      vid = freevars.get_id(var)
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
  return 2 if frame.activate_lazy_bindings(seen_ids, lazy=True) else 0

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
              freevars.clone_generator(frame.rts, y, x)
              x_gen = x[1]
            elif y_nbnd:
              freevars.clone_generator(frame.rts, x, y)
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
  yield expr
