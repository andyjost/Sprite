'''
First-order unification of type terms, with an occurs check and the rule
for the pseudo constructor ``Prelude.Apply``.

The rules (design of the typed boundary, section 3.3):

  * ``Apply f a`` against ``T a1 .. an`` with ``n >= 1`` binds ``f`` to
    ``T a1 .. a(n-1)`` and unifies ``a`` with ``an``.  A function type is the
    constructor ``(->)`` with two arguments for this rule.
  * ``Apply f a`` against ``Apply g b`` unifies pairwise.
  * A variable is bound once; the occurs check refuses an infinite type.
  * A rigid variable (of an ``exprtype`` string) unifies with itself and
    with an unbound variable alone.
  * A nested ``ForallType`` is instantiated with fresh variables when the
    unifier reaches it.

The unifier does not know the engine.  It calls ``on_bind(var, term)`` after
it binds a variable to a term that is not a variable, so that the engine can
reduce the predicates of the variable and check its holders.
'''

from ..toolchain.flat2icurry import flatcurry as fc
from . import terms
from .terms import APPLY, ARROW, Rigid, Var

__all__ = ['OccursError', 'TypeMismatch', 'UnifyError', 'unify']

class UnifyError(Exception):
  '''
  Two terms do not unify.  ``lhs`` and ``rhs`` are the terms at the point
  of failure; ``top`` the two terms the call started from.
  '''
  def __init__(self, lhs, rhs, top=None):
    Exception.__init__(self, lhs, rhs)
    self.lhs = lhs
    self.rhs = rhs
    self.top = top

class TypeMismatch(UnifyError):
  '''Two constructors differ, or a rigid variable meets another type.'''

class OccursError(UnifyError):
  '''A variable would be bound to a term that contains it.'''

def _arrow_cons(t):
  '''A function type as the constructor ``(->)`` applied to two arguments.'''
  if isinstance(t, fc.FuncType):
    return fc.TCons(ARROW, [t.domain, t.range])
  return t

def unify(lhs, rhs, arity=None, on_bind=None):
  '''
  Unifies two terms in place.

  Args:
    lhs, rhs:
        The terms.
    arity:
        A function from a qualified type name to its declared arity, or
        None; :func:`terms.whnf` folds ``Apply`` with it.
    on_bind:
        Called as ``on_bind(var, term)`` after a variable is bound to a
        term that is not a variable.

  Raises:
    TypeMismatch, OccursError
  '''
  top = (lhs, rhs)
  work = [(lhs, rhs)]
  while work:
    s, t = work.pop()
    s = terms.whnf(s, arity)
    t = terms.whnf(t, arity)
    if s is t:
      continue
    if isinstance(s, Var):
      _bind(s, t, top, on_bind)
      continue
    if isinstance(t, Var):
      _bind(t, s, top, on_bind)
      continue
    if isinstance(s, fc.ForallType) or isinstance(t, fc.ForallType):
      if isinstance(s, fc.ForallType):
        s = terms.instantiate(s, {})
      if isinstance(t, fc.ForallType):
        t = terms.instantiate(t, {})
      work.append((s, t))
      continue
    if isinstance(s, Rigid) or isinstance(t, Rigid):
      raise TypeMismatch(s, t, top)
    if isinstance(s, fc.FuncType) and isinstance(t, fc.FuncType):
      work.append((s.range, t.range))
      work.append((s.domain, t.domain))
      continue
    s_apply = isinstance(s, fc.TCons) and s.name == APPLY
    t_apply = isinstance(t, fc.TCons) and t.name == APPLY
    if s_apply and t_apply:
      work.append((s.args[1], t.args[1]))
      work.append((s.args[0], t.args[0]))
      continue
    if s_apply or t_apply:
      app, other = (s, t) if s_apply else (t, s)
      other = _arrow_cons(other)
      if not isinstance(other, fc.TCons) or not other.args:
        # A nullary constructor, or something that is no application.
        raise TypeMismatch(s, t, top)
      work.append((app.args[1], other.args[-1]))
      work.append((app.args[0], fc.TCons(other.name, list(other.args[:-1]))))
      continue
    s, t = _arrow_cons(s), _arrow_cons(t)
    if isinstance(s, fc.TCons) and isinstance(t, fc.TCons):
      if s.name != t.name or len(s.args) != len(t.args):
        raise TypeMismatch(s, t, top)
      work.extend(reversed(list(zip(s.args, t.args))))
      continue
    raise TypeMismatch(s, t, top)

def _bind(var, term, top, on_bind):
  '''Binds the unbound representative ``var`` to ``term``.'''
  if isinstance(term, Var):
    var.union(term)
    return
  if isinstance(term, fc.ForallType):
    term = terms.instantiate(term, {})
  if not isinstance(term, Rigid) and terms.occurs(var, term):
    raise OccursError(var, term, top)
  var.binding = term
  if on_bind is not None:
    on_bind(var, term)
