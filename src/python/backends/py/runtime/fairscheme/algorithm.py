from .....common import T_SETGRD, T_FAIL, T_CONSTR, T_VAR, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from .. import graph, trace
from ..... import icurry, inspect
from .....utility import exprutil

def D(rts):
  while rts.ready():
    tag = inspect.tag_of(rts.E)
    if tag == T_FAIL:
      rts.drop()
    elif tag == T_CONSTR:
      value, (l, r) = rts.E
      if not rts.constrain_equal(l, r, rts.constraint_type()):
        rts.drop()
      else:
        rts.E = value
        del value
    elif tag == T_VAR:
      if rts.has_binding():
        rts.E = rts.get_binding()
      elif rts.is_narrowed():
        rts.E = rts.get_generator()
      else:
        yield rts.make_value()
        rts.drop()
    elif tag == T_FWD:
      rts.E = rts.E.fwd
    elif tag == T_SETGRD:
      sid = rts.E.successors[0]
      if sid == rts.get_sid():
        rts.C.escape_all = True
      elif rts.in_recursive_call:
        rts.unwind()
      rts.E = rts.E.successors[1]
    elif tag == T_CHOICE:
      cid = rts.obj_id()
      if (cid in getattr(rts.S, 'escape_set', []) or rts.C.escape_all) and not any(
          cid in config.fingerprint for config in rts.walk_configs()
        ):
        rts.unwind()
      else:
        configs = rts.walk_configs()
        next(configs)
        configs = list(configs)
        for child in rts.fork():
          for config in configs:
            if cid in config.fingerprint:
              if child.fingerprint[cid] == config.fingerprint[cid]:
                rts.append(child)
              break
          else:
            rts.append(child)
        rts.drop()
        # rts.extend(rts.fork())
        # rts.drop()
    else:
      with rts.catch_control(residual=True, restart=True):
        if tag == T_FUNC:
          S(rts, rts.E)
        elif tag >= T_CTOR:
          if N(rts):
            value = rts.make_value()
            rts.drop()
            yield value
            del value


def N(rts, root=None, path=None, ground=True):
  C = rts.C
  C.search_state.append(None)
  root = rts.E if root is None else root
  try:
    for state in exprutil.walk(root, path=path):
      rts.C.search_state[-1] = state
      while True:
        tag = inspect.tag_of(state.cursor)
        if tag == T_FAIL:
          if path is None:
            rts.drop()
          else:
            root.rewrite(rts.prelude._Failure)
          return False
        elif tag == T_CONSTR:
          if path is None:
            rts.E = rts.make_constraint(state.cursor, rts.E, state.path)
          else:
            rts.make_constraint(state.cursor, root, state.path, rewrite=root)
          return False
        elif tag == T_VAR:
          if ground:
            if rts.has_binding(state.cursor):
              binding = rts.get_binding(state.cursor)
              rts.E = graph.utility.replace_copy(rts, rts.E, state.path, binding)
              rts.restart()
            elif rts.is_narrowed(state.cursor):
              gen = target = rts.get_generator(state.cursor)
              rts.E = rts.make_choice(gen[0], rts.E, state.path, gen)
              rts.restart()
            elif rts.obj_id(state.cursor) != rts.grp_id(state.cursor):
              x = rts.get_variable(rts.grp_id(state.cursor))
              rts.E = graph.utility.replace_copy(rts, rts.E, state.path, x)
              rts.restart()
          break
        elif tag == T_FWD:
          state.spine[-1] = state.parent.getitem(state.parent, state.path[-1])
        elif tag == T_CHOICE:
          cid = state.cursor.successors[0]
          rts.update_escape_sets(sids=state.data, cid=cid)
          if path is None:
            rts.E = rts.make_choice(cid, rts.E, state.path)
          else:
            rts.make_choice(cid, root, state.path, rewrite=root)
          return False
        elif tag == T_SETGRD:
          sid = state.cursor.successors[0]
          state.push(data=sid)
          break
        elif tag == T_FUNC:
          S(rts, state.cursor)
        elif tag >= T_CTOR:
          if inspect.info_of(state.cursor) is not rts.prelude._PartApplic.info:
            state.push()
          break
        else:
          assert False
    return True
  finally:
    C.search_state.pop()


@trace.trace_steps
def S(rts, node):
  with rts.catch_control(unwind=True, nondet=rts.is_io(node)):
    node.info.step(rts, node)
    rts.stepcounter.increment()


def hnf(rts, func, path, typedef=None, values=None, guards=None):
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
      A list of integers, float, or characters indicating the values that may
      occur at the inductive position.  Only meaningful when ``typedef`` is
      Prelude.Int, Prelude.Float, or Prelude.Char.

  Returns:
  --------
    The subexpression after reducing it to a constructor-rooted expression.
  '''
  guards = set() if guards is None else guards
  target = graph.Node.getitem(func, path, guards)
  C = rts.C
  C.search_state.append(tuple(path))
  try:
    while True:
      if isinstance(target, icurry.ILiteral):
        return target, guards
      tag = inspect.tag_of(target)
      if tag == T_FAIL:
        func.rewrite(rts.prelude._Failure)
        rts.unwind()
      elif tag == T_CONSTR:
        rts.make_constraint(target, func, path, rewrite=func)
        rts.unwind()
      elif tag == T_VAR:
        if rts.has_generator(target):
          gen = rts.get_generator(target)
          rts.make_choice(gen.successors[0], func, path, gen, rewrite=func)
          rts.unwind()
        elif rts.has_binding(target):
          binding = rts.get_binding(target)
          rts.E = graph.utility.replace_copy(rts, rts.E, tuple(rts.C.path), binding)
          rts.restart()
        elif typedef in rts.builtin_types:
          if values:
            target = rts.make_value_bindings(target, values, typedef)
            graph.utility.replace(rts, func, path, target)
          else:
            rts.suspend(target)
        else:
          target = rts.instantiate(func, path, typedef)
      elif tag == T_FWD:
        target = graph.Node.getitem(func, path, guards)
      elif tag == T_CHOICE:
        cid = target.successors[0]
        for sid in guards:
          rts.update_escape_set(sid=sid, cid=cid)
        rts.make_choice(cid, func, path, rewrite=func)
        rts.unwind()
      elif tag == T_SETGRD:
        sid, expr = target
        guards.add(sid)
        target = expr
      elif tag == T_FUNC:
        S(rts, target)
      elif tag >= T_CTOR:
        return target, guards
      else:
        assert False
  finally:
    C.search_state.pop()

