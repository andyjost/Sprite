from ......common import T_FREE
from ......exceptions import InstantiationError
from .....generic.runtime.control import E_RESIDUAL
from ... import graph
from ...... import inspect
import six

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
        yield rts.prelude._Fwd
        yield _0.successors[1-i]
      else:               # False
        yield rts.prelude.False_
      return
    i = 1-i

def constr_eq(rts, _0):
  '''Implements =:=.'''
  lhs, rhs = [rts.variable(_0, i).hnf_or_free() for i in (0,1)]
  if lhs.is_boxed and rhs.is_boxed:
    ltag, rtag = lhs.info.tag, rhs.info.tag
    if ltag == T_FREE:
      if rtag == T_FREE:
        if inspect.get_freevar_id(lhs.target) != inspect.get_freevar_id(rhs.target):
          yield rts.prelude._StrictConstraint.info
          yield rts.expr(True)
          yield rts.expr((lhs, rhs))
        else:
          yield rts.prelude.True_
      else:
        values = [rhs.unboxed_value] if rhs.typedef in rts.builtin_types else None
        _1 = rts.variable(_0, 0)
        _1.hnf(rhs.typedef, values)
    else:
      if rtag == T_FREE:
        values = [lhs.unboxed_value] if lhs.typedef in rts.builtin_types else None
        _1 = rts.variable(_0, 1)
        _1.hnf(lhs.typedef, values)
      else:
        if ltag == rtag: # recurse when the comparison returns 0 or False.
          arity = lhs.info.arity
          assert arity == rhs.info.arity
          if arity:
            conj = getattr(rts.prelude, '&')
            def terms():
              for i in six.moves.range(arity):
                _1 = rts.variable(lhs, i)
                _2 = rts.variable(rhs, i)
                yield graph.Node(_0.info, _1, _2)
            expr = six.moves.reduce((lambda a,b: graph.Node(conj, a, b)), terms())
            yield expr.info
            for succ in expr.successors:
              yield succ
          else:
            yield rts.prelude.True_
        else:
          yield rts.prelude._Failure
  elif not lhs.is_boxed and not rhs.is_boxed:
    yield rts.prelude.True_ if lhs.unboxed_value == rhs.unboxed_value \
                            else rts.prelude._Failure
  else:
    raise InstantiationError('=:= cannot bind to an unboxed value')

def nonstrict_eq(rts, _0):
  '''
  Implements =:<=.

  This follows "Declarative Programming with Function Patterns," Antoy and
  Hanus, LOPSTR 2005, pg. 16.
  '''
  lhs = rts.variable(_0, 0)
  rhs = rts.variable(_0, 1)
  if lhs.is_boxed and rhs.is_boxed:
    lhs = lhs.hnf_or_free()
    if lhs.info.tag == T_FREE:
      # Bind lhs -> rhs
      yield rts.prelude._NonStrictConstraint.info
      yield rts.expr(True)
      yield rts.expr((lhs, rhs))
    else:
      assert inspect.is_data(lhs.target)
      rhs = rhs.hnf_or_free()
      if rhs.info.tag == T_FREE:
        rhs.hnf(typedef=lhs.typedef)
      else:
        assert inspect.is_data(rhs.target)
        if lhs.info.tag == rhs.info.tag:
          arity = lhs.info.arity
          assert arity == rhs.info.arity
          if arity:
            conj = getattr(rts.prelude, '&')
            def terms():
              for i in six.moves.range(arity):
                _1 = rts.variable(lhs, i)
                _2 = rts.variable(rhs, i)
                yield graph.Node(_0.info, _1, _2)
            expr = six.moves.reduce((lambda a,b: graph.Node(conj, a, b)), terms())
            yield expr.info
            for succ in expr.successors:
              yield succ
          else:
            yield rts.prelude.True_
        else:
          yield rts.prelude._Failure
  elif not lhs.is_boxed and not rhs.is_boxed:
    yield rts.prelude.True_ if lhs.unboxed_value == rhs.unboxed_value \
                           else rts.prelude._Failure
  else:
    raise InstantiationError('=:<= cannot bind to an unboxed value')

