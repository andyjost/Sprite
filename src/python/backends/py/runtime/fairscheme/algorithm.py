from .....common import T_FAIL, T_CONSTR, T_VAR, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from .. import graph, trace
from ..... import icurry
from .....utility import exprutil

@trace.trace_values
def D(rts):
  while rts.ready():
    tag = graph.tag_of(rts.E)
    if tag == T_FAIL:
      rts.drop()
    elif tag == T_CONSTR:
      value, (l, r) = rts.E
      if not rts.constrain_equal(l, r, rts.constraint_type()):
        rts.drop()
      else:
        rts.E = value
    elif tag == T_VAR:
      if rts.has_binding():
        rts.E = rts.get_binding()
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
      with rts.catch_control(residual=True, restart=True):
        if tag == T_FUNC:
          S(rts, rts.E)
        elif tag >= T_CTOR:
          if N(rts):
            yield rts.E
            rts.drop()

def N(rts):
  C = rts.C
  C.search_state.append(None)
  try:
    for state in exprutil.walk(rts.E):
      rts.C.search_state[-1] = state
      while True:
        tag = graph.tag_of(state.cursor)
        if tag == T_FAIL:
          rts.drop()
          return False
        elif tag == T_CONSTR:
          rts.E = graph.make_constraint(state.cursor, rts.E, state.path)
          return False
        elif tag == T_VAR:
          if rts.has_binding(state.cursor):
            binding = rts.get_binding(state.cursor)
            rts.E = graph.replace_copy(rts, rts.E, state.path, binding)
          elif rts.is_narrowed(state.cursor):
            gen = target = rts.get_generator(state.cursor)
            rts.E = graph.make_choice(rts, gen[0], rts.E, state.path, gen)
            return False
          elif rts.obj_id(state.cursor) != rts.grp_id(state.cursor):
            x = rts.get_variable(rts.grp_id(state.cursor))
            rts.E = graph.replace_copy(rts, rts.E, state.path, x)
            return False
          break
        elif tag == T_FWD:
          state.spine[-1] = state.parent[state.path[-1]]
        elif tag == T_CHOICE:
          rts.E = graph.make_choice(rts, state.cursor[0], rts.E, state.path)
          return False
        elif tag == T_FUNC:
          S(rts, state.cursor)
        elif tag >= T_CTOR:
          if graph.info_of(state.cursor) is not rts.prelude._PartApplic.info:
            state.push()
          break
    return True
  finally:
    C.search_state.pop()

@trace.trace_steps
def S(rts, node):
  with rts.catch_control(unwind=True, nondet_io=rts.is_io(node)):
    node.info.step(rts, node)
    rts.stepcounter.increment()

def hnf(rts, func, path, typedef=None, values=None):
  '''
  Head-normalize the expression at the inductive position ``func[path],`` where
  func is a needed, function-rooted expression.

  This function either succeeds and returns the indicated subexpression or
  raises an exception.

  The compiler generates calls to this function when evaluating case
  expressions.  Built-in functions may also call this.

  Parameters:
  -----------
    ``func``
      The function-rooted subexpression nearest to this step.

    ``path``
      The path from ``func`` to the (inductive) position to normalize.

    ``typedef``
      The type of the inductive position.  Needed when a free variable occurs
      there.

    ``values``
      An instance of the Curry type Integer.ISet specifying the integers that
      may occur at the inductive position.  Only meaningful when ``typedef``
      is Prelude.Int.  Used to restrict integer narrowing.

  Returns:
  --------
    The subexpression after reducing it to a constructor-rooted expression.
  '''
  target = func[path]
  C = rts.C
  C.search_state.append(tuple(path))
  try:
    while True:
      if isinstance(target, icurry.ILiteral):
        return target
      tag = graph.tag_of(target)
      if tag == T_FAIL:
        func.rewrite(rts.prelude._Failure)
        rts.unwind()
      elif tag == T_CONSTR:
        graph.make_constraint(target, func, path, rewrite=func)
        rts.unwind()
      elif tag == T_VAR:
        if rts.has_generator(target):
          gen = rts.get_generator(target)
          graph.make_choice(rts, gen[0], func, path, gen, rewrite=func)
          rts.unwind()
        elif rts.has_binding(target):
          binding = rts.get_binding(target)
          rts.E = graph.replace_copy(rts, rts.E, tuple(rts.C.path), binding)
          rts.restart()
        elif typedef in rts.builtin_types:
          if values:
            target = graph.make_value_bindings(rts, target, values)
            graph.replace(rts, func, path, target)
          else:
            rts.suspend(target)
        else:
          target = rts.instantiate(func, path, typedef)
      elif tag == T_FWD:
        target = func[path]
      elif tag == T_CHOICE:
        graph.make_choice(rts, target[0], func, path, rewrite=func)
        rts.unwind()
      elif tag == T_FUNC:
        S(rts, target)
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
    with rts.catch_control(ground=ground):
      hnf(rts, func, state.path)
    if graph.tag_of(state.cursor) >= T_CTOR:
      if graph.info_of(state.cursor) is not rts.prelude._PartApplic.info:
        state.push()
  return func[path]

