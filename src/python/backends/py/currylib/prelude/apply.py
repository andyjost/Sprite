from ..... import inspect
from ... import graph
from ...eval import fairscheme

__all__ = [
    'apply', 'apply_gnf', 'apply_hnf', 'apply_nf', 'cond', 'ensureNotFree'
  ]

def apply(rts, _0):
  # _0 (_Partapplic #missing term) arg
  #
  # The term is a function symbol followed zero or more arguments.
  # No forward nodes or set guards may appear around the term.
  partapplic = rts.variable(_0, 0)
  partapplic.hnf()
  missing, term = partapplic.target.successors
  assert inspect.isa_unboxed_int(missing)
  assert inspect.isa_func(term) or inspect.isa_ctor(term)
  arg = _0.target.successors[1]
  assert missing >= 1
  if missing == 1:
    yield term.info
    for t in term.successors:
      yield t
    yield arg
  else:
    yield partapplic.info
    yield missing-1
    yield graph.Node(term, *(term.successors+[arg]), partial=True)

def apply_gnf(rts, _0):
  '''Implements ($##).'''
  rv = _applyspecial(rts, _0, _normalize) # Apply ($!!).
  unbound = [
      y for y in (x.target for x in graph.iterexpr(_0))
          if inspect.isa_freevar(y) and not rts.has_generator(y)
    ]
  if unbound:
    rts.suspend(unbound)
  else:
    return rv

def apply_hnf(rts, _0):
  '''Implements ($!).'''
  return _applyspecial(rts, _0, fairscheme.hnf)

def apply_nf(rts, _0):
  '''Implements ($!!).'''
  return _applyspecial(rts, _0, _normalize)

def cond(rts, _0):
  Bool = rts.type('Prelude.Bool')
  _1 = rts.variable(_0, 0)
  _1.hnf(typedef=Bool)
  if _1.info.tag:
    yield rts.prelude._Fwd
    yield _0.successors[1]
  else:
    yield rts.prelude._Failure

def ensureNotFree(rts, _0):
  _1 = fairscheme.hnf_or_free(rts, rts.variable(_0, 0))
  if rts.is_void(_1.target):
    rts.suspend(_1.target)
  else:
    yield rts.prelude._Fwd
    yield _1

def _applyspecial(rts, _0, action, **kwds):
  '''Apply a function with a special action on the argument.'''
  partapplic = rts.variable(_0, 0)
  partapplic.hnf()
  term = partapplic.successors[1]
  assert inspect.isa_func(term) # not a forward node or set guard
  with rts.catch_control(nondet=rts.is_io(term)):
    _1 = rts.variable(_0, 1)
    transformed_arg = action(rts, _1, **kwds)
  yield rts.prelude.apply
  yield _0.successors[0]
  yield transformed_arg

def _normalize(rts, var, **kwds):
  if not fairscheme.N(rts, var, **kwds):
    rts.unwind()
  else:
    return var

