from ....common import T_SETGRD, T_FAIL, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from . import graph, trace
from .... import icurry, inspect
from ....utility import exprutil

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
    elif tag == T_FREE:
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
      ## FIXME
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


# The N procedure is normally called from D (with no arguments), when the root
# expression is constructor rooted.
# 
# The exceptions are the built-in # control function $!! and $##, which make
# recursive calls to N with more arguments.  The additional arguments indicate
# the position under a function symbol that needs to be normalized.

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
            var = rts.variable(rts.E, state.path)
            rts.E = rts.make_constraint(var)
          else:
            var = rts.variable(root, state.path)
            rts.make_constraint(var, rewrite=root)
          return False
        elif tag == T_FREE:
          if ground:
            # Path not relevant here.  We must clone the whole context.
            if rts.has_binding(state.cursor):
              binding = rts.get_binding(state.cursor)
              rts.E = rts.variable(rts.E, state.path).copy_spine(end=binding)
              rts.restart()
            elif rts.is_narrowed(state.cursor):
              gen = rts.get_generator(state.cursor)
              rts.E = rts.variable(rts.E, state.path).copy_spine(end=gen)
              rts.restart()
            elif rts.obj_id(state.cursor) != rts.grp_id(state.cursor):
              x = rts.get_freevar(rts.grp_id(state.cursor))
              rts.E = rts.variable(rts.E, state.path).copy_spine(end=x)
              rts.restart()
          break
        elif tag == T_FWD:
          state.spine[-1] = state.parent.getitem(state.parent, state.path[-1])
        elif tag == T_CHOICE:
          cid = state.cursor.successors[0]
          rts.update_escape_sets(sids=state.data, cid=cid)
          if path is None:
            var = rts.variable(rts.E, state.path)
            rts.E = rts.pull_tab(var)
          else:
            var = rts.variable(root, state.path)
            rts.pull_tab(var, rewrite=root)
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
    _0 = rts.variable(node)
    node.info.step(rts, _0)
    rts.stepcounter.increment()

def hnf(rts, var, typedef=None, values=None):
  '''
  Head-normalize the expression at the given variable.

  This function either succeeds and returns the updated variable or raises an
  exception.

  Parameters:
  -----------
    ``var``
      An instance of ``Variable``.

    ``typedef``
      The type of the inductive position.  Needed when ``var`` is a free
      variable.

    ``values``
      An optional list of integers, floats, or characters indicating the values
      that may occur at the inductive position.  This is only meaningful when
      ``typedef`` is Prelude.Int, Prelude.Float, or Prelude.Char.

  Returns:
  --------
    The updated variable, ``var``.
  '''
  C = rts.C
  C.search_state.append(tuple(var.fullrealpath))
  try:
    while True:
      if isinstance(var.target, icurry.ILiteral):
        return var
      tag = var.tag
      if tag == T_FAIL:
        var.root.rewrite(rts.prelude._Failure)
        rts.unwind()
      elif tag == T_CONSTR:
        rts.make_constraint(var, rewrite=var.root)
        rts.unwind()
      elif tag == T_FREE:
        if rts.has_generator(var.target):
          gen = rts.get_generator(var.target)
          var.copy_spine(end=gen, rewrite=var.root)
          var.update()
          C.search_state[-1] = tuple(var.fullrealpath)
        elif rts.has_binding(var.target):
          # FIXME: can't I get rid of this branch?  Just instantiate the
          # variable and let the fingerprint sort out the rest.  But that does
          # not work for infinite types.
          binding = rts.get_binding(var.target)
          rts.E = graph.utility.copy_spine(rts.E, tuple(rts.C.path), end=binding)
          rts.restart()
        elif typedef in rts.builtin_types:
          if values:
            bindings = rts.make_value_bindings(var, values, typedef)
            var.copy_spine(end=bindings, rewrite=var.root)
            var.update()
            C.search_state[-1] = tuple(var.fullrealpath)
          else:
            rts.suspend(var.target)
        else:
          rts.instantiate(var, typedef)
      elif tag == T_CHOICE:
        cid = inspect.get_choice_id(var.target)
        for sid in var.all_guards():
          rts.update_escape_set(sid=sid, cid=cid)
        rts.pull_tab(var, rewrite=var.root)
        rts.unwind()
      elif tag == T_FUNC:
        S(rts, var.target)
        var.update()
        C.search_state[-1] = tuple(var.fullrealpath)
      elif tag >= T_CTOR:
        return var
      else:
        # T_FWD and T_SETGRD should not occur.
        assert False
  finally:
    C.search_state.pop()

