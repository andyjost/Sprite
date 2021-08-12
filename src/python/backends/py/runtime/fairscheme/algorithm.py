from .....common import T_FAIL, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from ..control import E_CONTINUE, E_RESIDUAL, E_RESTART
from . import freevars
from .. import graph
from ..... import icurry
from . import state
from .. import trace
from .....utility import exprutil
from . import common

@trace.trace_values
def D(rts):
  while rts.ready():
    tag = common.tag_of(rts.E)
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
        tag = common.tag_of(state.cursor)
        if tag == T_FAIL:
          rts.drop()
          return False
        elif tag == T_CONSTR:
          rts.E = common.make_constraint(state.cursor, rts.E, state.path)
          return False
        elif tag == T_FREE:
          if rts.has_binding(state.cursor):
            binding = rts.get_binding(state.cursor)
            rts.E = graph.replace_copy(rts, rts.E, state.path, binding)
          elif rts.is_narrowed(state.cursor):
            gen = target = rts.get_generator(state.cursor)
            rts.E = common.make_choice(rts, gen[0], rts.E, state.path, gen)
            return False
          elif rts.obj_id(state.cursor) != rts.grp_id(state.cursor):
            x = rts.get_freevar(rts.grp_id(state.cursor))
            rts.E = graph.replace_copy(rts, rts.E, state.path, x)
            return False
          break
        elif tag == T_FWD:
          state.spine[-1] = state.parent[state.path[-1]]
        elif tag == T_CHOICE:
          rts.E = common.make_choice(rts, state.cursor[0], rts.E, state.path)
          return False
        elif tag == T_FUNC:
          S(rts, state.cursor)
        elif tag >= T_CTOR:
          if common.info_of(state.cursor) is not rts.prelude._PartApplic.info:
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
      tag = common.tag_of(target)
      if tag == T_FAIL:
        func.rewrite(rts.prelude._Failure)
        raise E_CONTINUE()
      elif tag == T_CONSTR:
        common.make_constraint(target, func, path, rewrite=func)
        raise E_CONTINUE()
      elif tag == T_FREE:
        if rts.has_generator(target):
          gen = rts.get_generator(target)
          common.make_choice(rts, gen[0], func, path, gen, rewrite=func)
          raise E_CONTINUE()
        elif rts.has_binding(target):
          binding = rts.get_binding(target)
          rts.E = graph.replace_copy(rts, rts.E, tuple(rts.C.path), binding)
          raise E_RESTART()
        elif typedef is None or typedef in rts.builtin_types:
          vid = target[0]
          if values:
            target = common.make_value_bindings(rts, vid, values)
            graph.replace(rts, func, path, target)
          else:
            raise E_RESIDUAL([rts.obj_id(target), rts.grp_id(target)])
        else:
          target = rts.instantiate(func, path, typedef)
      elif tag == T_FWD:
        target = func[path]
      elif tag == T_CHOICE:
        common.make_choice(rts, target[0], func, path, rewrite=func)
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
    if common.tag_of(state.cursor) >= T_CTOR:
      if common.info_of(state.cursor) is not rts.prelude._PartApplic.info:
        state.push()
  return func[path]

