from .....common import T_FREE
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
  # A partial application reached through set guards (a function value that
  # is an argument of a set function, or that such an argument holds) keeps
  # its arguments boxed: each goes under the guards crossed on the way to it
  # (the box rule of the dissertation, chapter 4: a reference to a boxed
  # expression is boxed).  The application itself is not boxed, and neither
  # is ``arg``, a successor of the redex.  The C++ runtime has the same step
  # (apply_step).
  held = [rts.guard_held(t, partapplic.guards) for t in term.successors]
  if missing == 1:
    yield term.info
    for t in held:
      yield t
    yield arg
  else:
    yield partapplic.info
    yield missing-1
    yield graph.Node(term, *(held+[arg]), partial=True)

def apply_gnf(rts, _0):
  '''
  Implements ($##).  The argument is normalized as by ($!!).  When the
  normalization completed, the step suspends on the free variables of the
  normal form that have no generator, as the C++ runtime does
  (applygnf_step in currylib/prelude/apply.cpp).  A variable with a binding
  is gone from the normal form, because N put the binding into the
  expression; a variable with a generator carries information.  So a
  configuration suspended here waits for a variable that another one can
  still bind, and ready() releases it then (show x after x =:= (3 ? 4)).

  The check runs over the normal form and enters no generator.  A check
  over the argument before its normalization walked the generators of the
  narrowed variables as well, where the fresh variables of the branches
  this configuration did not take have no information and never get any,
  so the step suspended for good on them: scenario (d) of example 21 on
  the Python backend.
  '''
  replacement = list(_applyspecial(rts, _0, _normalize)) # Apply ($!!).
  unbound = [
      node for node in _nodes_outside_generators(replacement[2].target)
          if inspect.isa_freevar(node) and not rts.has_generator(node)
    ]
  if unbound:
    rts.suspend(unbound)
  else:
    return replacement

def _nodes_outside_generators(root):
  '''
  The nodes of an expression, each once, without the generators of its free
  variables.  The successors of a free variable are its id and its
  generator; the walk reads neither.
  '''
  stack = [root]
  seen = set()
  while stack:
    node = stack.pop()
    if not isinstance(node, graph.Node) or id(node) in seen:
      continue
    seen.add(id(node))
    yield node
    if node.info.tag != T_FREE:
      stack.extend(node.successors)

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
    yield rts.Fwd
    yield _0.successors[1]
  else:
    yield rts.Failure

def ensureNotFree(rts, _0):
  _1 = fairscheme.hnf_or_free(rts, rts.variable(_0, 0))
  if rts.is_void(_1.target):
    rts.suspend(_1.target)
  else:
    yield rts.Fwd
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
  # The function and the argument keep the guards crossed on the way to
  # them (rvalue), so the box rule reaches the application (apply).
  yield rts.prelude.apply
  yield partapplic.rvalue
  yield transformed_arg

def _normalize(rts, var, **kwds):
  if not fairscheme.N(rts, var, **kwds):
    rts.unwind()
  else:
    return var

