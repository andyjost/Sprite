from ... import graph
from ...... import icurry
from . import state
from ... import trace
from ...misc import E_CONTINUE, E_RESIDUAL, E_RESTART
from ......tags import *
from ......utility import exprutil

@trace.trace_values
def D(rts):
  while rts.ready():
    tag = tag_of(rts.E)
    if tag == T_FAIL:
      rts.drop()
    elif tag == T_CONSTR:
      value, (l, r) = rts.E
      if not rts.constrain_equal(l, r, rts.constraint_type()):
        rts.drop()
      else:
        rts.E = value
    elif tag == T_FREE:
      if rts.has_binding():
        rts.E = rts.pop_binding()
      elif rts.is_narrowed():
        rts.E = rts.get_generator()
      else:
        yield rts.E
        rts.drop()
    elif tag == T_FWD:
      rts.E = rts.E[()]
    elif tag == T_CHOICE:
      rts.extend(rts.fork())
      rts.drop()
    else:
      try:
        if tag == T_FUNC:
          S(rts, rts.E)
        elif tag >= T_CTOR:
          if N(rts):
            yield rts.E
            rts.drop()
      except E_RESIDUAL as res:
        rts.C.residuals.update(res.ids)
        rts.rotate()
      except E_RESTART:
        pass

def N(rts):
  C = rts.C
  C.search_state.append(None)
  try:
    for state in exprutil.walk(rts.E):
      rts.C.search_state[-1] = state
      while True:
        tag = tag_of(state.cursor)
        if tag == T_FAIL:
          rts.drop()
          return False
        elif tag == T_CONSTR:
          rts.E = make_constraint(state.cursor, rts.E, state.path)
          return False
        elif tag == T_FREE:
          if rts.has_binding(state.cursor):
            binding = rts.pop_binding(state.cursor)
            rts.E = graph.replace_copy(rts, rts.E, state.path, binding)
          elif rts.is_narrowed(state.cursor):
            gen = target = rts.get_generator(state.cursor)
            rts.E = make_choice(rts, gen[0], rts.E, state.path, gen)
            return False
          elif rts.obj_id(state.cursor) != rts.grp_id(state.cursor):
            x = rts.get_freevar(rts.grp_id(state.cursor))
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
  finally:
    C.search_state.pop()

@trace.trace_steps
def S(rts, node):
  try:
    node.info.step(rts, node)
    rts.stepcounter.increment()
  except E_CONTINUE:
    pass

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

    ``E_RESIDUAL``
        If a non-narrowable free variable occurs at the inductive position.
        This can happen for infinite types (e.g., Int) and functions with
        infinite defining rules (e.g., +).

  '''
  target = func[path]
  C = rts.C
  C.search_state.append(tuple(path))
  try:
    while True:
      if isinstance(target, icurry.ILiteral):
        return target
      tag = target.info.tag
      if tag == T_FAIL:
        func.rewrite(rts.prelude._Failure)
        raise E_CONTINUE()
      elif tag == T_CONSTR:
        make_constraint(target, func, path, rewrite=func)
        raise E_CONTINUE()
      elif tag == T_FREE:
        if rts.has_generator(target):
          gen = rts.get_generator(target)
          make_choice(rts, gen[0], func, path, gen, rewrite=func)
          raise E_CONTINUE()
        elif rts.has_binding(target):
          binding = rts.get_binding(target)
          rts.E = graph.replace_copy(rts, rts.E, tuple(rts.C.path), binding)
          raise E_RESTART()
        elif typedef is None:
          raise E_RESIDUAL([rts.obj_id(target), rts.grp_id(target)])
        else:
          target = rts.instantiate(func, path, typedef)
      elif tag == T_FWD:
        target = func[path]
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
  finally:
    C.search_state.pop()

def normalize(rts, func, path, ground):
  '''
  Normalize the subexpression at ``func[path]``.  Used to implement $!! and
  $##.
  '''
  for state in exprutil.walk(func, path=path):
    try:
      hnf(rts, func, state.path)
    except E_RESIDUAL:
      if ground:
        raise
    if tag_of(state.cursor) >= T_CTOR:
      if info_of(state.cursor) is not rts.prelude._PartApplic.info:
        state.push()
  return func[path]

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

def make_constraint(constr, node, path, rewrite=None):
  '''
  Make a new constraint object based on ``constr``, which is located at
  node[path].  If ``rewrite`` is supplied, the specified node is overwritten.
  Otherwise a new node is created.
  '''
  repl = graph.Replacer(node, path)
  value = repl[0]
  pair = constr[1]
  return graph.Node(constr.info, value, pair, target=rewrite)
