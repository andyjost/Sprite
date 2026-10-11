from ....common import T_SETGRD, T_FAIL, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from ..graph import indexing
from ..graph.node import Node
from .. import graph
from ...generic.eval import control, trace
from ...generic.eval.control import E_SETFAIL
from .... import icurry, inspect
from . import callstack

@trace.trace_values
def D(rts):
  rts.telemetry._enterD += 1
  while rts.ready():
    # The root is read once per iteration.  Each read of rts.E goes through
    # the queue table.
    E = rts.E
    assert not hasattr(E, 'raw_expr')
    rts.telemetry._iterD += 1
    tag = inspect.tag_of(E)
    checker = rts.checker
    if checker is not None:
      # The root cell at the dispatch, for the discard check (checker.py).
      checker.dispatch(E)
    if tag == T_FAIL:
      # A failure under the guard of the current set at the root (escape_all)
      # is boxed: under the flag setfunction_failures it fails the set
      # function (boxed_failure; allValues catches E_SETFAIL).
      sids = rts.boxed_failure()
      if sids is not None:
        raise E_SETFAIL(sids)
      if checker is not None:
        checker.discard(E)
      rts.drop()
    elif tag == T_CONSTR:
      value, lr = E.successors
      l, r = lr.successors
      if not rts.constrain_equal(l, r, rts.constraint_type()):
        rts.drop()
      else:
        if checker is not None:
          checker.constrained(rts.C)
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
      rts.E = inspect.fwd_target(E)
    elif tag == T_SETGRD and (
        E.successors[0] == rts.sid or not rts.in_recursive_call
      ):
      # A guard of the current set at the root: the choices and the
      # failures below it escape (escape_all), and the guard goes, as
      # release_value drops the guards of the current set from a value.
      # Outside every set function a guard at the root goes the same way.
      # A guard of an enclosing set is a node of the spine like a
      # constructor: N descends into it, a choice found below it is pulled
      # up through it into the escape set of its set, and the value keeps
      # it (the C++ procD lets T_SETGRD fall to procN).  An unwind here
      # reached allValues, which expects a choice at the root (issue #130).
      if E.successors[0] == rts.sid:
        rts.C.escape_all = True
      rts.E = E.successors[1]
    elif tag == T_CHOICE:
      cid = rts.obj_id()
      if rts.choice_escapes(cid):
        rts.unwind()
      else:
        with rts.trace.fork():
          rts.extend(rts.fork())
          rts.drop(trace=False)
    else:
      with rts.catch_control(residual=True, restart=True, steplimit=True):
        if tag == T_FUNC:
          S(rts, E)
        elif tag >= T_CTOR or tag == T_SETGRD:
          if N(rts, rts.variable(E)):
            yield rts.release_value()
  # The queue is empty.  An alternative dropped at the stack limit reports its
  # error now, after the other alternatives produced their values.
  rts.raise_deferred_error()

# Note: "state" is added by the system.
@trace.trace_steps
@callstack.with_N_stackframe
def N(rts, var, state):
  rts.telemetry._enterN += 1
  for _ in state:
    while True:
      tag = inspect.tag_of(state.cursor)
      if tag == T_FAIL:
        # A failure below a set guard is boxed: under the flag
        # setfunction_failures it fails the set function (boxed_failure).
        sids = rts.boxed_failure()
        if sids is not None:
          raise E_SETFAIL(sids)
        if var.is_root:
          # Rule N.1: the configuration is dropped and no cell changes.
          if rts.checker is not None:
            rts.checker.discard(var.root)
          rts.drop()
        else:
          # The redex becomes a failure, as in hnf.  ($!!) normalizes its
          # argument this way.
          var.root.rewrite(rts.Failure)
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
        # The variable is replaced through a private copy of the spine from
        # the root of the configuration, as in hnf.  The path of the walk
        # starts at var.root: the root of the configuration when D calls N,
        # and the redex when a step normalizes its argument (($!!), ($##)).
        # The path of the call stack runs from the root in both cases.
        if rts.has_binding(state.cursor):
          rts.telemetry._copyspine += 1
          binding = rts.get_binding(state.cursor)
          old, path = rts.E, rts.C.realpath
          rts.E = graph.utility.copy_spine(old, path, end=binding)
          if rts.checker is not None:
            rts.checker.copied(old, rts.E, path, binding, 'binding')
          rts.restart()
        elif rts.is_narrowed(state.cursor):
          rts.telemetry._copyspine += 1
          gen = rts.get_generator(state.cursor)
          old, path = rts.E, rts.C.realpath
          rts.E = graph.utility.copy_spine(old, path, end=gen)
          if rts.checker is not None:
            rts.checker.copied(old, rts.E, path, gen, 'generator')
          rts.restart()
        elif rts.obj_id(state.cursor) != rts.grp_id(state.cursor):
          rts.telemetry._copyspine += 1
          x = rts.get_freevar(rts.grp_id(state.cursor))
          old, path = rts.E, rts.C.realpath
          rts.E = graph.utility.copy_spine(old, path, end=x)
          if rts.checker is not None:
            rts.checker.copied(old, rts.E, path, x, 'representative')
          rts.restart()
        break
      elif tag == T_FWD:
        # The chain of forward nodes at the cursor is spliced out of the
        # parent, as the C++ walk does (compress_fwd_chain in procN).  The
        # walk goes on at the end of the chain.  A set guard there is met on
        # the next pass.  The T_SETGRD case pushes it with its sid.  So the
        # real path and the set ids include the box, and the pull-tab of a
        # choice behind it keeps the box and inserts the choice into the
        # escape set of its set.  logical_subexpr skipped the guards with
        # the chain, and the path stayed short of them (issue #123).
        end = indexing.compress_fwd_chain(state.cursor)
        if state.parent is not None:
          state.parent.set_successor(state.realpath[-1], end)
        state.spine[-1] = end
      elif tag == T_CHOICE:
        cid = state.cursor.successors[0]
        rts.update_escape_sets(sids=state.data, cid=cid)
        if var.is_root:
          rts.E = rts.pull_tab(var.root, state.cursor, state.realpath)
        else:
          # The choice is at the cursor of the walk, below the argument the
          # step normalizes, and the path runs from the redex, var.root.
          assert inspect.isa_func(var.root)
          rts.pull_tab(
              var.root, state.cursor, state.realpath, rewrite=var.root
            )
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
    checker = rts.checker
    if checker is None:
      node.info.step(rts, _0)
    else:
      # The checker reads the symbol and the arguments the redex held before
      # the step.  The step replaces the list of successors, so the list
      # itself is kept, not copied.
      info, args = node.info, node.successors
      info.step(rts, _0)
      checker.step(node, info, args)
    # Only a completed step counts.  A step that raised a control exception
    # left its redex as it was.  The C++ procS applies the same rule.
    rts.stepcounter.increment()
    rts.count_step()

@callstack.with_hnf_stackframe
def hnf(rts, var, typedef=None, values=None, free=False):
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

    free:
      The caller takes a free variable as it is (the equality steps, through
      hnf_or_free).  A variable is bound in a configuration when the
      fingerprint of the configuration decides its group, or when a binding
      holds it; a generator that another configuration created binds nothing
      here (Def 2.57 of the note on the Fair Scheme).  So an equality step
      binds such a variable by its constraint cell or its non-strict
      binding, without a narrowing (Def 2.62, Def 2.75; issue #129).
      Without the flag a variable with a generator is narrowed by it (rule
      S.x).  The C++ runtime has the same rule (FREE_IN_CONFIGURATION in
      currylib/prelude/constr.cpp).

  Returns:
    The updated variable, ``var``.
  '''
  rts.telemetry._enterhnf += 1
  if rts.checker is not None:
    rts.checker.hnf(var, typedef, values)
  while True:
    rts.telemetry._iterhnf += 1
    target = var.target
    if isinstance(target, Node):
      tag = target.info.tag
    elif isinstance(target, icurry.ILiteral):
      return var
    else:
      tag = var.tag
    if tag == T_SETGRD:
      var.extend()
    elif tag == T_FAIL:
      # A failure below a set guard is boxed: under the flag
      # setfunction_failures it fails the set function (boxed_failure).
      sids = rts.boxed_failure(var.guards)
      if sids is not None:
        raise E_SETFAIL(sids)
      var.root.rewrite(rts.Failure)
      rts.unwind()
    elif tag == T_CONSTR:
      rts.lift_constraint(var, rewrite=var.root)
      rts.unwind()
    elif tag == T_FREE:
      if free:
        narrow = not rts.has_binding(var.target) \
            and rts.is_narrowed(var.target)
      else:
        narrow = rts.has_generator(var.target)
      if narrow:
        # A variable of a decided class without a generator of its own gets
        # one here (get_generator).  The checker tests the equality rule at
        # every slot write.
        gen = rts.get_generator(var.target)
        if rts.checker is not None:
          rts.checker.slot_write(var)
        var.replace_target(replacement=gen)
      elif rts.has_binding(var.target):
        binding = rts.get_binding(var.target)
        old, path = rts.E, rts.C.realpath
        rts.E = graph.utility.copy_spine(old, path, end=binding)
        if rts.checker is not None:
          rts.checker.copied(old, rts.E, path, binding, 'binding')
        rts.restart()
      elif rts.is_builtin_type(typedef):
        if values:
          value_bindings = rts.make_value_bindings(var, values, typedef)
          if rts.checker is not None:
            rts.checker.value_bindings(var.target, value_bindings)
          var.replace_target(replacement=value_bindings)
        else:
          rts.suspend(var.target)
      elif free:
        # Free in this configuration: hnf_or_free reports the variable.
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

def hnf_or_free(rts, var, typedef=None, free=False):
  '''
  Reduce the expression to head normal form or a free variable.  With
  ``free`` a variable that is free in the configuration is reported as it
  is, although a generator may exist (see ``free`` of hnf).
  '''
  try:
    return hnf(rts, var, typedef, free=free)
  except control.E_RESIDUAL:
    # The argument could be a free variable or an expression containing a free
    # variable that cannot be narrowed, such as "ensureNotFree x".
    if inspect.isa_freevar(var.target):
      return var
    else:
      raise

