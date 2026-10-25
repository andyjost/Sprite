'''
Case completion, the second pass.  It follows ``FlatCurry.CaseCompletion``
of the Curry package ``icurry``.

Every case over constructors is rewritten so that its branches follow the
constructor order of the data declaration.  A missing constructor ``c`` of
arity ``n`` gets the branch ``c 101 .. 100+n -> Prelude.failed``.  A case
over literals is left as it is. Cases completed by the new front end with
explicit failure branches retain their order. The data declarations come from the module
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

def complete_prog(datadecls, prog, preserve_completed=False):
  '''Completes every case in a program.'''
  return fc.Prog(
      prog.name, prog.imports, prog.types
    , [complete_fun(datadecls, fd, preserve_completed) for fd in prog.functions], prog.operators
    )

def complete_fun(datadecls, fd, preserve_completed=False):
  return fc.Func(
      fd.name, fd.arity, fd.visibility, fd.typeexpr, complete_rule(datadecls, fd.rule, preserve_completed)
    )

def complete_rule(datadecls, rule, preserve_completed=False):
  if isinstance(rule, fc.External):
    return rule
  return fc.Rule(rule.args, complete_exp(datadecls, rule.body, preserve_completed))

def complete_exp(datadecls, e, preserve_completed=False):
  '''
  Completes every case in an expression.  The walk runs on a stack of its
  own (:func:`utility.trampoline.trampoline`), so a nested application of
  any depth needs no recursion (issue #125).
  '''
  return trampoline(_complete(datadecls, e, preserve_completed))

def _complete(datadecls, e, preserve_completed=False):
  if isinstance(e, (fc.Var, fc.Lit)):
    return e
  elif isinstance(e, fc.Comb):
    args = []
    for arg in e.args:
      arg = yield _complete(datadecls, arg, preserve_completed)
      args.append(arg)
    return fc.Comb(e.combtype, e.name, args)
  elif isinstance(e, fc.Let):
    bindings = []
    for binding in e.bindings:
      v, b = binding[0], binding[-1]
      b = yield _complete(datadecls, b, preserve_completed)
      bindings.append(fc.binding_expr(binding, b))
    body = yield _complete(datadecls, e.body, preserve_completed)
    return fc.Let(bindings, body)
  elif isinstance(e, fc.Free):
    body = yield _complete(datadecls, e.body, preserve_completed)
    return fc.Free(e.vars, body)
  elif isinstance(e, fc.Or):
    lhs = yield _complete(datadecls, e.lhs, preserve_completed)
    rhs = yield _complete(datadecls, e.rhs, preserve_completed)
    return fc.Or(lhs, rhs)
  elif isinstance(e, fc.Typed):
    expr = yield _complete(datadecls, e.expr, preserve_completed)
    return fc.Typed(expr, e.typeexpr)
  elif isinstance(e, fc.Case):
    ce = yield _complete(datadecls, e.scrutinee, preserve_completed)
    cbrs = []
    for br in e.branches:
      body = yield _complete(datadecls, br.body, preserve_completed)
      cbrs.append(fc.Branch(br.pattern, body))
    if not cbrs or isinstance(cbrs[0].pattern, fc.LPattern):
      return fc.Case(e.casetype, ce, cbrs)
    _, consdecls = type_of_constructor(datadecls, cbrs[0].pattern.name)
    # Front end 3.1 completes a case itself, appending failed branches.
    # Keep that order (including the original successful branches).
    present = {br.pattern.name for br in cbrs}
    if preserve_completed and all(c in present for c, _ in consdecls) and any(
        br.body == fc.Comb(fc.FuncCall, fc.prelude('failed'), []) for br in cbrs):
      return fc.Case(e.casetype, ce, cbrs)
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
