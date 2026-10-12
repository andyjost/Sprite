from .....common import T_FREE
from .....exceptions import InstantiationError
from ....generic.eval.control import E_RESIDUAL
from ... import graph
from ..... import inspect
import functools

def concurrent_and(rts, _0):
  '''
  Implements Prelude.&.

  Evaluate an argument and inspect its head symbol:
    - If true, rewrite to the other argument;
    - If false, rewrite to false;
    - If it suspends:
        - if the other arg has not been inspected, work on the other arg;
        - if any step occurred, work on the other arg;
        - otherwise, suspend;

  See ``digits.curry``.
  '''
  Bool = rts.type('Prelude.Bool')
  assert rts.prelude.False_.info.tag == 0
  assert rts.prelude.True_.info.tag == 1
  errs = [None, None]
  i = 0
  while True:
    stepnumber = rts.stepcounter.count
    try:
      _1 = rts.variable(_0, i)
      _1.hnf(typedef=Bool)
    except E_RESIDUAL as err:
      errs[i] = err
      if errs[1-i] and rts.stepcounter.count == stepnumber:
        raise
    else:
      if _1.info.tag:      # True
        yield rts.Fwd
        yield _0.successors[1-i]
      else:               # False
        yield rts.prelude.False_
      return
    i = 1-i

def _decided(rts, var):
  '''
  Whether the configuration decides the variable at ``var``: the
  fingerprint decides its group and no binding holds it.  Such a variable
  reads as its instance (hnf with ``free`` writes its generator).
  '''
  return not rts.has_binding(var.target) and rts.is_narrowed(var.target)

def _expand(rts, _0, i):
  '''
  Writes the generator of the decided variable at successor ``i`` of the
  redex into its slot (rule S.x).  The pull-tab of hnf then unwinds.
  '''
  rts.variable(_0, i).hnf_or_free(free=True)
  # The pull-tab unwinds before this line.  A raise, not an assert, so
  # that the guard survives python -O.
  raise AssertionError('the pull-tab of a decided variable unwinds')

def constr_eq(rts, _0):
  '''Implements =:=.'''
  # A variable that is free in this configuration is taken as it is,
  # although another configuration may have narrowed it (issue #129), and
  # so is a variable the configuration decides until the other side is
  # known.  A decided variable is expanded to its instance against a
  # constructor, a value, or a second decided variable.  Against a variable
  # that is free in the configuration the step records the pair instead
  # (decision D25 of 2026-10-12): the constraint step unites the two
  # classes, with the occurs check, and the free variable reads the
  # instance through the class.  The values are those of the narrowing of
  # the free variable against the instance, with fewer forks, and a cyclic
  # pair fails the step where the narrowing ran without end.  The C++ step
  # has the same rule (constrEq_step in currylib/prelude/constr.cpp).
  lhs, rhs = [
      rts.variable(_0, i).hnf_or_free(free=True, decided=True) for i in (0,1)
    ]
  if lhs.is_boxed and rhs.is_boxed:
    ltag, rtag = lhs.info.tag, rhs.info.tag
    if ltag == T_FREE:
      if rtag == T_FREE:
        if inspect.get_freevar_id(lhs.target) == inspect.get_freevar_id(rhs.target):
          yield rts.prelude.True_
        elif _decided(rts, lhs) and _decided(rts, rhs):
          # Two decided variables: the left one is expanded first, and the
          # step runs again with its instance.
          _expand(rts, _0, 0)
        else:
          # Two free variables, or a free one and a decided one: the pair.
          yield rts.StrictConstraint
          yield rts.expr(True)
          # The pair holds the two variables themselves, without the guards
          # crossed on the way to them: constrain_equal reads the ids of the
          # pair, and a guard has none (issue #121).  The C++ step builds
          # the same pair (constrEq_step in currylib/prelude/constr.cpp).
          yield rts.expr((lhs.target, rhs.target))
      elif _decided(rts, lhs):
        _expand(rts, _0, 0)
      else:
        values = [rhs.unboxed_value] if rts.is_builtin_type(rhs.typedef) else None
        _1 = rts.variable(_0, 0)
        _1.hnf(rhs.typedef, values)
    else:
      if rtag == T_FREE:
        if _decided(rts, rhs):
          _expand(rts, _0, 1)
        values = [lhs.unboxed_value] if rts.is_builtin_type(lhs.typedef) else None
        _1 = rts.variable(_0, 1)
        _1.hnf(lhs.typedef, values)
      else:
        if ltag == rtag: # recurse when the comparison returns 0 or False.
          arity = lhs.info.arity
          assert arity == rhs.info.arity
          if arity:
            conj = getattr(rts.prelude, '&')
            def terms():
              for i in range(arity):
                _1 = rts.variable(lhs, i)
                _2 = rts.variable(rhs, i)
                yield graph.Node(_0.info, _1, _2)
            expr = functools.reduce((lambda a,b: graph.Node(conj, a, b)), terms())
            yield expr.info
            for succ in expr.successors:
              yield succ
          else:
            yield rts.prelude.True_
        else:
          yield rts.Failure
  elif not lhs.is_boxed and not rhs.is_boxed:
    yield rts.prelude.True_ if lhs.unboxed_value == rhs.unboxed_value \
                            else rts.Failure
  else:
    raise InstantiationError('=:= cannot bind to an unboxed value')

def nonstrict_eq(rts, _0):
  '''
  Implements =:<=.

  This follows "Declarative Programming with Function Patterns," Antoy and
  Hanus, LOPSTR 2005, pg. 16.  The left side is the pattern, the right side
  the actual argument.  A free variable on the left takes the right side as
  a non-strict binding.  A free variable on the right is bound to the
  constructor or the value on the left, as =:= binds it: a builtin type
  passes its one value to hnf, so a free Char, Int or Float gets the value
  instead of a suspension.
  '''
  lhs = rts.variable(_0, 0)
  rhs = rts.variable(_0, 1)
  if lhs.is_boxed and rhs.is_boxed:
    lhs = lhs.hnf_or_free(free=True)
    if lhs.info.tag == T_FREE:
      # Bind lhs -> rhs
      yield rts.NonStrictConstraint
      yield rts.expr(True)
      yield rts.expr((lhs, rhs))
    else:
      assert inspect.is_data(lhs.target)
      rhs = rhs.hnf_or_free(free=True)
      if rhs.info.tag == T_FREE:
        values = [lhs.unboxed_value] if rts.is_builtin_type(lhs.typedef) else None
        _1 = rts.variable(_0, 1)
        _1.hnf(lhs.typedef, values)
      else:
        assert inspect.is_data(rhs.target)
        if lhs.info.tag == rhs.info.tag:
          arity = lhs.info.arity
          assert arity == rhs.info.arity
          if arity:
            conj = getattr(rts.prelude, '&')
            def terms():
              for i in range(arity):
                _1 = rts.variable(lhs, i)
                _2 = rts.variable(rhs, i)
                yield graph.Node(_0.info, _1, _2)
            expr = functools.reduce((lambda a,b: graph.Node(conj, a, b)), terms())
            yield expr.info
            for succ in expr.successors:
              yield succ
          else:
            yield rts.prelude.True_
        else:
          yield rts.Failure
  elif not lhs.is_boxed and not rhs.is_boxed:
    yield rts.prelude.True_ if lhs.unboxed_value == rhs.unboxed_value \
                           else rts.Failure
  else:
    raise InstantiationError('=:<= cannot bind to an unboxed value')

