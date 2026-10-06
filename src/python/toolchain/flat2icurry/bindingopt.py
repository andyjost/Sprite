'''
The binding optimization, a FlatCurry-to-FlatCurry pass over the FlatCurry
file of a module.

PAKCS and KiCS2 run the tool ``transbooleq`` over every FlatCurry file they
compile (the property ``bindingoptimization`` of PAKCS, ``fast`` by
default).  This module is a port of its fast mode.  The ideas are in "From
Boolean Equalities to Constraints" (Antoy and Hanus, LOPSTR 2015) and
"Transforming Boolean equalities into constraints" (Formal Aspects of
Computing, 2017).

A Boolean equality whose value is required to be True is replaced by the
equational constraint, which binds free variables where the Boolean
equality on a primitive type suspends:

  - ``e1 == e2`` and ``e1 === e2`` become ``constrEq e1 e2``.
  - ``e1 /= e2`` and ``e1 /== e2`` with required value False become
    ``not (constrEq e1 e2)``.

The required value comes from the context.  The condition of a rule is
required True: the front end writes a guard as ``case c of True -> e;
False -> failed``.  The scrutinee of a case with one branch that does not
fail is required to be the constructor of that branch.  The fast mode
knows the required values of the arguments of a few Prelude operations and
no others (``PRELUDE_REQUIRED_VALUES``): the arguments of ``&&`` and ``&``
required True are required True, the argument of ``not`` required False is
required True, and so on.  An operation outside the table requires nothing
of its arguments.  So ``f x | x == 3 = x`` and ``f x | x == 1 && y == 2``
bind, while ``if x == 3 then a else b`` and a guard with an ``otherwise``
branch keep the Boolean equality, as under PAKCS.

The pass changes the semantics of a program in the same way PAKCS does.
``(1 == 2) & True`` is False under the plain semantics and fails after the
pass, because ``&`` requires both arguments True whatever its result is
required to be.  An equivalence ``==`` is replaced on the assumption that
the ``Eq`` instance defines equality; the tool of PAKCS makes the same
assumption.

:func:`optimize_file` applies the pass to a FlatCurry file in place, as
PAKCS does before any compiler reads the file (``preprocessFcyFile`` of its
compiler): the file is written again when the pass replaced an equality, and
left as it is otherwise.  Both routes from Curry to ICurry
(:mod:`curry.toolchain._frontend` and the ``icurry`` program, see
:mod:`curry.toolchain._curry2icurry`) run it after the front end and before
the translation, so the ``.fcy`` file on disk is the optimized program and
the two routes translate the same text.  The pass is idempotent: over an
optimized program it replaces nothing and writes nothing.
:func:`optimize_bindings` is the pass on a program in memory; the oracle
tests of the translation never apply it, because the files ``icurry`` wrote
for the oracle come from the FlatCurry as the front end wrote it.

The command line of :mod:`rewrite` rewrites FlatCurry files by hand::

    python -m curry.toolchain.flat2icurry.rewrite [-q] M.fcy...

The products made from the file before (the ICurry and what follows it)
are not touched by it; ``sprite-make --rewrite-flat`` runs the step of a
module again and makes them from the rewritten file.
'''

from . import flatcurry as fc
import functools

__all__ = [
    'ANY', 'ANYC', 'FAILED', 'PRELUDE_REQUIRED_VALUES', 'case_arg_type'
  , 'constructors', 'contains_equality', 'equality_operands', 'lub'
  , 'optimize_bindings', 'optimize_file', 'required_argument_values'
  , 'transform_exp', 'transform_func', 'transform_prog'
  ]

# The abstract values of the required-values analysis (AType of the
# analysis RequiredValues of CASS).  A constructor is its qualified name; a
# set of constructors, the join of two different ones, is a frozenset of
# names.  ANY is no requirement; ANYC is any constructor.
ANY = 'Any'
ANYC = 'AnyC'

TRUE = fc.prelude('True')
FALSE = fc.prelude('False')
FAILED = fc.Comb(fc.FuncCall, fc.prelude('failed'), [])

# The required values of the arguments of the Prelude operations the fast
# mode knows, by the required value of the result: a list of pairs of the
# argument values and the result value.  This is preludeBoolReqValues of
# transbooleq.
PRELUDE_REQUIRED_VALUES = {
    fc.prelude('&&')   : [([ANY, ANY], FALSE), ([TRUE, TRUE], TRUE)]
  , fc.prelude('not')  : [([TRUE], FALSE), ([FALSE], TRUE)]
  , fc.prelude('||')   : [([FALSE, FALSE], FALSE), ([ANY, ANY], TRUE)]
  , fc.prelude('&')    : [([TRUE, TRUE], TRUE)]
  , fc.prelude('solve'): [([TRUE], TRUE)]
  , fc.prelude('&&>')  : [([TRUE, ANY], ANYC)]
  }

def constructors(a):
  '''The constructor set of a constructor value.'''
  return a if isinstance(a, frozenset) else frozenset([a])

def lub(a, b):
  '''
  The least upper bound of two abstract values, lubAType of the analysis.
  ANY absorbs every value, ANYC absorbs a constructor value, and two
  constructor values join to the set of their constructors: a single name
  when both name the same constructor, else a frozenset.  The join of True
  and False is such a set, not ANYC: it is the required value of the
  argument of ``not`` as a value, and it requires nothing of the arguments
  of a call below it (see ``required_argument_values``).
  '''
  if a == ANY or b == ANY:
    return ANY
  if a == ANYC or b == ANYC:
    return ANYC
  joined = constructors(a) | constructors(b)
  return next(iter(joined)) if len(joined) == 1 else joined

def required_argument_values(qname, reqval, nargs):
  '''
  The required values of the ``nargs`` arguments of a call of ``qname``
  whose result is required to be ``reqval``: argumentTypesFor of
  transbooleq.  The table gives the arguments of the entry with that
  result, else of an entry with an unrequired result, else the join of all
  entries when ``reqval`` is ANY or ANYC.  An operation outside the table,
  and any other case, requires nothing.  A set of constructors is such a
  case: ``not`` as a value requires True or False of its argument, so
  ``not ((x == 1) & (y == 2))`` and ``not (solve (x == 3))`` keep their
  equalities and suspend, as under PAKCS, while ``not (not e)`` requires
  nothing of ``e``, and the join path transforms ``&`` and ``solve`` in it.
  '''
  entries = PRELUDE_REQUIRED_VALUES.get(qname)
  values = None
  if entries is not None:
    for args, result in entries:
      if result == reqval:
        values = args
        break
    else:
      for args, result in entries:
        if result in (ANY, ANYC):
          values = args
          break
      else:
        if reqval in (ANY, ANYC):
          columns = zip(*[args for args, _ in entries])
          values = [functools.reduce(lub, column) for column in columns]
  if values is None:
    return [ANY] * nargs
  values = list(values[:nargs])
  return values + [ANY] * (nargs - len(values))

def is_equality_name(qname, eq, equivalence=True):
  '''
  Whether ``qname`` is a Boolean equality (``eq``) or disequality (not
  ``eq``): the class method of the Prelude or an instance method, whose
  name starts with ``_impl#`` in any module.  With ``equivalence`` the
  methods of ``Eq`` count as well as those of ``Data``.
  '''
  name = qname[1]
  if eq:
    if qname == fc.prelude('===') or name.startswith('_impl#===#Prelude.Data#'):
      return True
    return equivalence and (
        qname == fc.prelude('==') or name.startswith('_impl#==#Prelude.Eq#')
      )
  else:
    if qname == fc.prelude('/=='):
      return True
    return equivalence and (
        qname == fc.prelude('/=') or name.startswith('_impl#/=#Prelude.Eq#')
      )

def equality_operands(e, eq, equivalence=True):
  '''
  The two operands of a call of a Boolean equality (``eq``) or disequality
  (not ``eq``), or None.  Three shapes count: a saturated call of the
  method with the operands last, after any dictionaries; a method applied
  to a dictionary and then to the operands through ``apply``; and a
  default instance method without a dictionary, applied the same way.
  '''
  if not isinstance(e, fc.Comb) or e.combtype != fc.FuncCall:
    return None
  if is_equality_name(e.name, eq, equivalence) and len(e.args) > 1:
    return list(e.args[-2:])
  if e.name == fc.prelude('apply') and len(e.args) == 2:
    inner, e2 = e.args
    if isinstance(inner, fc.Comb) and inner.combtype == fc.FuncCall \
        and inner.name == fc.prelude('apply') and len(inner.args) == 2:
      method, e1 = inner.args
      if isinstance(method, fc.Comb) and method.combtype == fc.FuncCall \
          and len(method.args) <= 1 \
          and is_equality_name(method.name, eq, equivalence):
        return [e1, e2]
  return None

def reduce_dollar(args):
  '''Turns ``f $ x`` with a partial application ``f`` into the call.'''
  head, arg = args
  ct = head.combtype
  if isinstance(ct, fc.FuncPartCall):
    newct = fc.FuncCall if ct.missing == 1 else fc.FuncPartCall(ct.missing - 1)
  else:
    newct = fc.ConsCall if ct.missing == 1 else fc.ConsPartCall(ct.missing - 1)
  return fc.Comb(newct, head.name, list(head.args) + [arg])

def case_arg_type(branches):
  '''
  The required value of the scrutinee of a case.  True when the second
  branch is ``False -> failed``, the translation of a guard.  Otherwise the
  constructor of the one branch that does not fail, or ANY.
  '''
  if len(branches) > 1 and branches[1] == fc.Branch(fc.Pattern(FALSE, []), FAILED):
    return TRUE
  alive = [br for br in branches if br.body != FAILED]
  if len(alive) != 1:
    return ANY
  pattern = alive[0].pattern
  return pattern.name if isinstance(pattern, fc.Pattern) else ANY

def transform_exp(e, reqval, equivalence=True):
  '''
  Transforms an expression whose value is required to be ``reqval``.
  Returns the new expression and the number of equalities replaced.
  '''
  def rec(e, reqval):
    if isinstance(e, (fc.Var, fc.Lit)):
      return e, 0
    elif isinstance(e, fc.Comb):
      return comb(e, reqval)
    elif isinstance(e, fc.Free):
      body, n = rec(e.body, reqval)
      return fc.Free(e.vars, body), n
    elif isinstance(e, fc.Or):
      lhs, n1 = rec(e.lhs, reqval)
      rhs, n2 = rec(e.rhs, reqval)
      return fc.Or(lhs, rhs), n1 + n2
    elif isinstance(e, fc.Typed):
      expr, n = rec(e.expr, reqval)
      return fc.Typed(expr, e.typeexpr), n
    elif isinstance(e, fc.Case):
      scrutinee, n = rec(e.scrutinee, case_arg_type(e.branches))
      branches = []
      for br in e.branches:
        body, m = rec(br.body, reqval)
        branches.append(fc.Branch(br.pattern, body))
        n += m
      return fc.Case(e.casetype, scrutinee, branches), n
    elif isinstance(e, fc.Let):
      n = 0
      bindings = []
      for v, b in e.bindings:
        b, m = rec(b, ANY)
        bindings.append((v, b))
        n += m
      body, m = rec(e.body, reqval)
      return fc.Let(bindings, body), n + m
    raise TypeError('not an expression: %r' % (e,))

  def comb(e, reqval):
    if reqval == TRUE:
      operands = equality_operands(e, True, equivalence)
      if operands is not None:
        args, n = many(operands, [ANY, ANY])
        return fc.Comb(fc.FuncCall, fc.prelude('constrEq'), args), n + 1
    if reqval == FALSE:
      operands = equality_operands(e, False, equivalence)
      if operands is not None:
        args, n = many(operands, [ANY, ANY])
        constraint = fc.Comb(fc.FuncCall, fc.prelude('constrEq'), args)
        return fc.Comb(fc.FuncCall, fc.prelude('not'), [constraint]), n + 1
    if e.name == fc.prelude('$') and len(e.args) == 2 \
        and isinstance(e.args[0], fc.Comb) \
        and isinstance(e.args[0].combtype, (fc.FuncPartCall, fc.ConsPartCall)):
      return rec(reduce_dollar(e.args), reqval)
    values = required_argument_values(e.name, reqval, len(e.args))
    args, n = many(e.args, values)
    return fc.Comb(e.combtype, e.name, args), n

  def many(exprs, values):
    out = []
    n = 0
    for expr, value in zip(exprs, values):
      expr, m = rec(expr, value)
      out.append(expr)
      n += m
    return out, n

  return rec(e, reqval)

def contains_equality(e, equivalence=True):
  '''Whether an expression holds a Boolean equality or disequality call.'''
  if isinstance(e, (fc.Var, fc.Lit)):
    return False
  elif isinstance(e, fc.Comb):
    return equality_operands(e, True, equivalence) is not None \
        or equality_operands(e, False, equivalence) is not None \
        or any(contains_equality(arg, equivalence) for arg in e.args)
  elif isinstance(e, fc.Free):
    return contains_equality(e.body, equivalence)
  elif isinstance(e, fc.Typed):
    return contains_equality(e.expr, equivalence)
  elif isinstance(e, fc.Or):
    return contains_equality(e.lhs, equivalence) or contains_equality(e.rhs, equivalence)
  elif isinstance(e, fc.Case):
    return contains_equality(e.scrutinee, equivalence) \
        or any(contains_equality(br.body, equivalence) for br in e.branches)
  elif isinstance(e, fc.Let):
    return contains_equality(e.body, equivalence) \
        or any(contains_equality(b, equivalence) for _, b in e.bindings)
  raise TypeError('not an expression: %r' % (e,))

def transform_func(fd, equivalence=True):
  '''
  Transforms a function declaration.  Returns it with the count.  As in
  transbooleq, a rule without a Boolean equality is returned as it is, and
  a rule with one is rebuilt, so its applications of ``$`` to a partial
  application are reduced to calls whether or not an equality is replaced.
  '''
  if isinstance(fd.rule, fc.External) \
      or not contains_equality(fd.rule.body, equivalence):
    return fd, 0
  body, n = transform_exp(fd.rule.body, ANY, equivalence)
  return fc.Func(
      fd.name, fd.arity, fd.visibility, fd.typeexpr, fc.Rule(fd.rule.args, body)
    ), n

def transform_prog(prog, equivalence=True):
  '''
  Transforms a FlatCurry program.  Returns the new program and the number of
  equalities replaced.  Without ``equivalence`` only ``===`` and ``/==`` are
  replaced, as under the option ``-s`` of transbooleq.
  '''
  functions = []
  total = 0
  for fd in prog.functions:
    fd, n = transform_func(fd, equivalence)
    functions.append(fd)
    total += n
  if all(a is b for a, b in zip(functions, prog.functions)):
    return prog, 0
  return fc.Prog(
      prog.name, prog.imports, prog.types, functions, prog.operators
    ), total

def optimize_bindings(prog, equivalence=True):
  '''
  Applies the binding optimization to a FlatCurry program.  Returns the
  transformed program when an equality was replaced, else ``prog`` itself:
  transbooleq writes a file only then, so a rule whose equalities all stay
  is rebuilt (its ``$`` reduced) only in a program that is transformed.
  '''
  newprog, n = transform_prog(prog, equivalence)
  return newprog if n else prog

def optimize_file(fcyfile, equivalence=True):
  '''
  Applies the binding optimization to the FlatCurry file ``fcyfile`` in
  place.  The file is written again, in the format of the front end, when
  the pass replaced an equality; else it is left as it is, with its time.
  Returns the number of equalities replaced.
  '''
  prog = fc.load(fcyfile)
  newprog, n = transform_prog(prog, equivalence)
  if n:
    fc.write(newprog, fcyfile)
  return n
