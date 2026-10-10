'''
Case completion, the second pass.  It follows ``FlatCurry.CaseCompletion``
of the Curry package ``icurry``.

Every case over constructors is rewritten so that its branches follow the
constructor order of the data declaration.  A missing constructor ``c`` of
arity ``n`` gets the branch ``c 101 .. 100+n -> Prelude.failed``.  A case
over literals is left as it is.  The data declarations come from the module
and from the interfaces of its imports.
'''

from . import flatcurry as fc
from .errors import Flat2ICurryError
from ...utility.trampoline import trampoline

__all__ = ['complete_prog', 'complete_exp', 'failed_branch', 'type_of_constructor']

def type_of_constructor(datadecls, qn):
  '''The first data declaration that holds the constructor ``qn``.'''
  for decl in datadecls:
    for cname, _ in decl[1]:
      if cname == qn:
        return decl
  raise Flat2ICurryError("Type of constructor '%s' not found!" % qn[1])

def complete_prog(datadecls, prog):
  '''Completes every case in a program.'''
  return fc.Prog(
      prog.name, prog.imports, prog.types
    , [complete_fun(datadecls, fd) for fd in prog.functions], prog.operators
    )

def complete_fun(datadecls, fd):
  return fc.Func(
      fd.name, fd.arity, fd.visibility, fd.typeexpr, complete_rule(datadecls, fd.rule)
    )

def complete_rule(datadecls, rule):
  if isinstance(rule, fc.External):
    return rule
  return fc.Rule(rule.args, complete_exp(datadecls, rule.body))

def complete_exp(datadecls, e):
  '''
  Completes every case in an expression.  The walk runs on a stack of its
  own (:func:`utility.trampoline.trampoline`), so a nested application of
  any depth needs no recursion (issue #125).
  '''
  return trampoline(_complete(datadecls, e))

def _complete(datadecls, e):
  if isinstance(e, (fc.Var, fc.Lit)):
    return e
  elif isinstance(e, fc.Comb):
    args = []
    for arg in e.args:
      arg = yield _complete(datadecls, arg)
      args.append(arg)
    return fc.Comb(e.combtype, e.name, args)
  elif isinstance(e, fc.Let):
    bindings = []
    for v, b in e.bindings:
      b = yield _complete(datadecls, b)
      bindings.append((v, b))
    body = yield _complete(datadecls, e.body)
    return fc.Let(bindings, body)
  elif isinstance(e, fc.Free):
    body = yield _complete(datadecls, e.body)
    return fc.Free(e.vars, body)
  elif isinstance(e, fc.Or):
    lhs = yield _complete(datadecls, e.lhs)
    rhs = yield _complete(datadecls, e.rhs)
    return fc.Or(lhs, rhs)
  elif isinstance(e, fc.Typed):
    expr = yield _complete(datadecls, e.expr)
    return fc.Typed(expr, e.typeexpr)
  elif isinstance(e, fc.Case):
    ce = yield _complete(datadecls, e.scrutinee)
    cbrs = []
    for br in e.branches:
      body = yield _complete(datadecls, br.body)
      cbrs.append(fc.Branch(br.pattern, body))
    if not cbrs or isinstance(cbrs[0].pattern, fc.LPattern):
      return fc.Case(e.casetype, ce, cbrs)
    _, consdecls = type_of_constructor(datadecls, cbrs[0].pattern.name)
    sbrs = [branch_for_cons(cbrs, c, ar) for c, ar in consdecls]
    return fc.Case(e.casetype, ce, sbrs)
  raise TypeError('not an expression: %r' % (e,))

def branch_for_cons(branches, c, ar):
  for br in branches:
    if isinstance(br.pattern, fc.Pattern) and br.pattern.name == c:
      return br
  return failed_branch(c, ar)

def failed_branch(c, ar):
  '''The branch for a constructor the case does not mention.'''
  return fc.Branch(
      fc.Pattern(c, list(range(101, 101 + ar)))
    , fc.Comb(fc.FuncCall, fc.prelude('failed'), [])
    )
