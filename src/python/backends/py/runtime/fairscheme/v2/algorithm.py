from ... import graph
from ...... import icurry
from . import state
from ... import trace
from ...misc import E_CONTINUE, E_RESIDUAL, E_STEPLIMIT
from ......tags import *
from ......utility import exprutil

def D(rts):
  while rts.queue:
    tag = tag_of(rts.E)
    if tag == T_FAIL:
      rts.drop()
    elif tag == T_BIND:
      value, (l, r) = rts.E
      if not rts.constrain_equal(l, r, strict=rts.is_strict_binding()):
        rts.drop()
      else:
        rts.E = value
    elif tag == T_FREE:
      if rts.has_binding():
        rts.E = rts.pop_binding()
      elif rts.is_narrowed():
        rts.E = rts.generator()
      else:
        rts.trace.yield_(rts.E)
        yield rts.E
        rts.drop()
    elif tag == T_FWD:
      rts.E = rts.E[()]
    elif tag == T_CHOICE:
      l, r = rts.left(), rts.right()
      if l: rts.queue.append(l)
      if r: rts.queue.append(r)
      rts.drop()
    elif tag == T_FUNC:
      S(rts, rts.E)
    elif tag >= T_CTOR:
      if N(rts):
        rts.trace.yield_(rts.E)
        yield rts.E
        rts.drop()

def N(rts):
  walk = exprutil.walk(rts.E)
  # walk = exprutil.unique(walk, exprutil.node_identity)
  for state in walk:
    while True:
      tag = tag_of(state.cursor)
      if tag == T_FAIL:
        rts.drop()
        return False
      elif tag == T_BIND:
        rts.E = make_binding(state.cursor, rts.E, state.path)
        return False
      elif tag == T_FREE:
        if rts.has_binding(state.cursor):
          binding = rts.pop_binding(state.cursor)
          rts.E = graph.replace_copy(rts, rts.E, state.path, binding)
        elif rts.is_narrowed(state.cursor):
          gen = target=rts.generator(state.cursor)
          rts.E = make_choice(rts, gen[0], rts.E, state.path, gen)
          return False
        elif rts.real_id(state.cursor) != rts.eff_id(state.cursor):
          x = rts.freevar(rts.eff_id(state.cursor))
          rts.E = graph.replace_copy(rts, rts.E, state.path, x)
        break
      elif tag == T_FWD:
        state.spine[-1] = state.parent[state.path[-1]]
      elif tag == T_CHOICE:
        rts.E = make_choice(rts, state.cursor[0], rts.E, state.path)
        return False
      elif tag == T_FUNC:
        S(rts, state.cursor)
      elif tag >= T_CTOR:
        if info_of(state.cursor) is not rts.prelude._PartApplic.info:
          state.push()
        break
  return True

def S(rts, node):
  rts.trace.enter_rewrite(node)
  try:
    node.info.step(rts, node)
    rts.stepcounter.increment()
  except E_CONTINUE:
    pass
  finally:
    rts.trace.exit_rewrite(node)

def hnf(rts, func, path, typedef=None, values=None):
  '''
  Head-normalize the expression at the inductive position ``func[path],`` where
  func is a needed, function-rooted expression.

  This function either succeeds and returns the indicated subexpression or
  raises an exception.

  The compiler generates calls to this function when evaluating case
  expressions.  Built-in functions may also call this.

  Returns:
  --------
    The subexpression after reducing it to a constructor-rooted expression.

  Raises:
  -------
    ``E_CONTINUE``
        If the func was overwritten due to a pull-tab step or failure.

    ``E_REDISUAL``
        If a non-narrowable free variable occurs at the inductive position.
        This can happen for infinite types (e.g., Int) and functions with
        infinite defining rules (e.g., +).

  '''
  assert path
  assert func.info.tag == T_FUNC
  target = func[path]
  while True:
    if isinstance(target, icurry.ILiteral):
      return target
    tag = target.info.tag
    if tag == T_FAIL:
      func.rewrite(rts.prelude._Failure)
      raise E_CONTINUE()
    elif tag == T_BIND:
      make_binding(target, func, path, rewrite=func)
      raise E_CONTINUE()
    elif tag == T_FREE:
      if typedef is None:
        vid = rts.eff_id(target)
        raise E_RESIDUAL([vid])
      else:
        target = rts.instantiate(func, path, typedef)
    elif tag == T_FWD:
      target = func[path]
      assert target.info.tag != T_FWD
    elif tag == T_CHOICE:
      make_choice(rts, target[0], func, path, rewrite=func)
      raise E_CONTINUE()
    elif tag == T_FUNC:
      try:
        S(rts, target)
      except E_CONTINUE:
        pass
    elif tag >= T_CTOR:
      return target

def normalize(rts, func, path, ground):
  '''
  Normalize the subexpression at ``func[path]``.  Used to implement $!! and
  $##.
  '''
  assert path
  assert func.info.tag == T_FUNC
  walk = exprutil.walk(func, path=path)
  # walk = exprutil.unique(walk, key=lambda st: id(st.cursor))
  for state in walk:
    try:
      hnf(rts, func, state.path)
    except E_RESIDUAL:
      if ground:
        raise
    if tag_of(state.cursor) >= T_CTOR:
      if info_of(state.cursor) is not rts.prelude._PartApplic.info:
        state.push()

def tag_of(node):
  if isinstance(node, icurry.ILiteral):
    return T_CTOR
  else:
    return node.info.tag

def info_of(node):
  if isinstance(node, icurry.ILiteral):
    return None
  else:
    return node.info

def make_choice(rts, cid, node, path, generator=None, rewrite=None):
  '''
  Make a choice node with ID ``cid`` whose alternatives are derived by
  replacing ``node[path]`` with the alternatives of choice-rooted
  expression``alternatives``.  If ``alternatives`` is not specified, then
  ``node[path]`` is used.  If ``rewrite`` is supplied, the specified node is
  overwritten.  Otherwise a new node is created.
  '''
  repl = graph.Replacer(node, path, alternatives=generator)
  return graph.Node(rts.prelude._Choice, cid, repl[1], repl[2], target=rewrite)

def make_binding(binding, node, path, rewrite=None):
  '''
  Make a new binding object based on ``binding``, which is located at
  node[path].  If ``rewrite`` is supplied, the specified node is overwritten.
  Otherwise a new node is created.
  '''
  repl = graph.Replacer(node, path)
  bindvalue = repl[0]
  bindspec = binding[1]
  return graph.Node(binding.info, bindvalue, bindspec, target=rewrite)
