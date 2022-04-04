from ....common import T_SETGRD, T_FAIL, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from ..graph import indexing
from .. import graph
from ...generic.eval import control, trace
from .... import icurry, inspect
from . import callstack

@trace.trace_values
def D(rts):
  rts.telemetry._enterD += 1
  while rts.ready():
    assert not hasattr(rts.E, 'raw_expr')
    rts.telemetry._iterD += 1
    tag = inspect.tag_of(rts.E)
    if tag == T_FAIL:
      rts.drop()
    elif tag == T_CONSTR:
      value, lr = rts.E.successors
      l, r = lr.successors
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
        yield rts.release_value()
    elif tag == T_FWD:
      rts.E = inspect.fwd_target(rts.E)
    elif tag == T_SETGRD:
      sid = rts.E.successors[0]
      if sid == rts.sid:
        rts.C.escape_all = True
      elif rts.in_recursive_call:
        rts.unwind()
      rts.E = rts.E.successors[1]
    elif tag == T_CHOICE:
      cid = rts.obj_id()
      if rts.choice_escapes(cid):
        rts.unwind()
      else:
        with rts.trace.fork():
          rts.extend(rts.fork())
          rts.drop(trace=False)
    else:
      with rts.catch_control(residual=True, restart=True):
        if tag == T_FUNC:
          S(rts, rts.E)
        elif tag >= T_CTOR:
          if N(rts, rts.variable(rts.E)):
            yield rts.release_value()

# Note: "state" is added by the system.
@trace.trace_steps
@callstack.with_N_stackframe
def N(rts, var, state):
  rts.telemetry._enterN += 1
  for _ in state:
    while True:
      tag = inspect.tag_of(state.cursor)
      if tag == T_FAIL:
        if var.is_root:
          rts.drop()
        else:
          var.rewrite(rts.prelude._Failure)
        return False
      elif tag == T_CONSTR:
        if var.is_root:
          var = rts.variable(rts.E, state.realpath)
          rts.E = rts.lift_constraint(var)
        else:
          var = rts.variable(var.root, state.realpath)
          rts.lift_constraint(var, rewrite=var.root)
        return False
      elif tag == T_FREE:
        # Path not relevant here.  We must clone the whole context.
        if rts.has_binding(state.cursor):
          rts.telemetry._copyspine += 1
          binding = rts.get_binding(state.cursor)
          rts.E = graph.utility.copy_spine(rts.E, state.realpath, end=binding)
          rts.restart()
        elif rts.is_narrowed(state.cursor):
          rts.telemetry._copyspine += 1
          gen = rts.get_generator(state.cursor)
          rts.E = graph.utility.copy_spine(rts.E, state.realpath, end=gen)
          rts.restart()
        elif rts.obj_id(state.cursor) != rts.grp_id(state.cursor):
          rts.telemetry._copyspine += 1
          x = rts.get_freevar(rts.grp_id(state.cursor))
          rts.E = graph.utility.copy_spine(rts.E, state.realpath, end=x)
          rts.restart()
        break
      elif tag == T_FWD:
        state.spine[-1] = indexing.logical_subexpr(
            state.parent, state.realpath[-1], update_fwd_nodes=True
          )
      elif tag == T_CHOICE:
        cid = state.cursor.successors[0]
        rts.update_escape_sets(sids=state.data, cid=cid)
        if var.is_root:
          rts.E = rts.pull_tab(var.root, state.cursor, state.realpath)
        else:
          assert inspect.isa_func(var.root)
          rts.pull_tab(var.root, var.target, var.realpath, rewrite=var.root)
        return False
      elif tag == T_SETGRD:
        sid = state.cursor.successors[0]
        state.push(data=sid)
        break
      elif tag == T_FUNC:
        with rts.trace.position(rts.E, state.realpath):
          S(rts, state.cursor)
      elif tag >= T_CTOR:
        if not getattr(inspect.info_of(state.cursor), 'is_partial', False):
          state.push()
        break
      else:
        assert False
  return True

@trace.trace_steps
def S(rts, node):
  rts.telemetry._enterS += 1
  with rts.catch_control(unwind=True, nondet=rts.is_io(node)):
    _0 = rts.variable(node)
    node.info.step(rts, _0)
    rts.stepcounter.increment()

@callstack.with_hnf_stackframe
def hnf(rts, var, typedef=None, values=None):
  '''
  Head-normalize the expression at the given variable.

  This function either succeeds and returns the updated variable or raises an
  exception.

  Args:
    var:
      An instance of ``Variable``.

    typedef:
      The type of the inductive position.  Needed when ``var`` is a free
      variable.

    values:
      An optional list of integers, floats, or characters indicating the values
      that may occur at the inductive position.  This is only meaningful when
      ``typedef`` is Prelude.Int, Prelude.Float, or Prelude.Char.

  Returns:
    The updated variable, ``var``.
  '''
  rts.telemetry._enterhnf += 1
  while True:
    rts.telemetry._iterhnf += 1
    if isinstance(var.target, icurry.ILiteral):
      return var
    tag = var.tag
    if tag == T_SETGRD:
      var.extend()
    elif tag == T_FAIL:
      var.root.rewrite(rts.prelude._Failure)
      rts.unwind()
    elif tag == T_CONSTR:
      rts.lift_constraint(var, rewrite=var.root)
      rts.unwind()
    elif tag == T_FREE:
      if rts.has_generator(var.target):
        gen = rts.get_generator(var.target)
        var.replace_target(replacement=gen)
      elif rts.has_binding(var.target):
        binding = rts.get_binding(var.target)
        rts.E = graph.utility.copy_spine(rts.E, rts.C.realpath, end=binding)
        rts.restart()
      elif rts.is_builtin_type(typedef):
        if values:
          value_bindings = rts.make_value_bindings(var, values, typedef)
          var.replace_target(replacement=value_bindings)
        else:
          rts.suspend(var.target)
      else:
        rts.instantiate(var, typedef)
    elif tag == T_FWD:
      var.extend()
    elif tag == T_CHOICE:
      cid = inspect.get_choice_id(var.target)
      for sid in var.guards:
        rts.update_escape_set(sid=sid, cid=cid)
      rts.pull_tab(var.root, var.target, var.realpath, rewrite=var.root)
      rts.unwind()
    elif tag == T_FUNC:
      S(rts, var.target)
    elif tag >= T_CTOR:
      return var
    else:
      assert False

def hnf_or_free(rts, var, typedef=None):
  '''Reduce the expression to head normal form or a free variable.'''
  try:
    return var.hnf(typedef)
  except control.E_RESIDUAL:
    # The argument could be a free variable or an expression containing a free
    # variable that cannot be narrowed, such as "ensureNotFree x".
    if inspect.isa_freevar(var.target):
      return var
    else:
      raise

