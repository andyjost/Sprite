'''
Case lifting, the third pass.  It follows ``FlatCurry.CaseLifting`` of the
Curry package ``icurry`` with the default options: nested cases, lets, and
free declarations are lifted, and so is a case whose scrutinee is not a
variable.

The state carries the module name, the names of the original top-level
functions, the functions made so far for the current top-level function,
the name of that function, and one counter shared by all four kinds of
generated functions.  A generated name that collides with an original
top-level name is skipped, and the counter still advances.  A generated
function is lifted itself before it is added, and it is added at the front
of the list, so the output order is the reverse of the order of creation.
'''

from . import flatcurry as fc
from ...utility.trampoline import trampoline

__all__ = ['lift_prog', 'unbound_vars', 'union', 'unionmap']

NONE_TYPE = fc.TCons(fc.prelude('None'), [])

def union(xs, ys):
  '''``Data.List.union`` of the Curry library: xs not in ys, then ys.'''
  return [x for x in xs if x not in ys] + list(ys)

def unionmap(f, items):
  '''``foldr union [] (map f items)``.'''
  return unions([f(item) for item in items])

def unions(lists):
  '''``foldr union []`` of a list of lists.'''
  acc = []
  for item in reversed(lists):
    acc = union(item, acc)
  return acc

class LiftState:
  def __init__(self, modname, topfuncs):
    self.modname = modname
    self.topfuncs = topfuncs   # local names of the original top-level functions
    self.liftfuncs = []        # functions made for the current top-level function
    self.currfunc = ''         # local name of the current top-level function
    self.index = 0             # counter for generated names

  def gen_func_name(self, suffix):
    while True:
      newfn = '%s_%s%d' % (self.currfunc, suffix, self.index)
      self.index += 1
      if newfn not in self.topfuncs:
        return (self.modname, newfn)

  def add_fun(self, fd):
    self.liftfuncs.insert(0, fd)

def lift_prog(prog):
  '''Lifts the nested cases, lets, and free declarations of a program.'''
  topfuncs = set(fd.name[1] for fd in prog.functions)
  state = LiftState(prog.name, topfuncs)
  functions = []
  for fd in prog.functions:
    state.currfunc = fd.name[1]
    state.index = 0
    nrule = lift_rule(state, fd.rule)
    functions.append(fc.Func(fd.name, fd.arity, fd.visibility, fd.typeexpr, nrule))
    functions.extend(state.liftfuncs)
    state.liftfuncs = []
  return fc.Prog(prog.name, prog.imports, prog.types, functions, prog.operators)

def lift_new_fun(state, fd):
  return trampoline(_lift_new_fun(state, fd))

def lift_rule(state, rule):
  if isinstance(rule, fc.External):
    return rule
  return fc.Rule(rule.args, lift_exp(state, False, rule.body))

def lift_exp(state, nested, e):
  '''
  Lifts an expression.  ``nested`` is true inside an expression where a
  case, let, or free declaration must be lifted, such as a call argument.
  The walk runs on a stack of its own (:func:`utility.trampoline.trampoline`),
  so a nested application of any depth needs no recursion (issue #125); a
  function the walk makes is lifted in turn on the same stack, before it
  is added, as the recursion did.
  '''
  return trampoline(_lift(state, nested, e))

def _lift(state, nested, e):
  if isinstance(e, (fc.Var, fc.Lit)):
    return e
  elif isinstance(e, fc.Comb):
    args = []
    for arg in e.args:
      arg = yield _lift(state, True, arg)
      args.append(arg)
    return fc.Comb(e.combtype, e.name, args)
  elif isinstance(e, fc.Case):
    if isinstance(e.scrutinee, fc.Var):
      return (yield from _lift_case_exp(state, nested, e))
    return (yield from _lift_case_arg(state, e))
  elif isinstance(e, fc.Let):
    if nested:
      return (yield from _lift_to_function(state, 'LET', e))
    bindings = []
    for v, b in e.bindings:
      b = yield _lift(state, True, b)
      bindings.append((v, b))
    body = yield _lift(state, True, e.body)
    return fc.Let(bindings, body)
  elif isinstance(e, fc.Free):
    if nested:
      return (yield from _lift_to_function(state, 'FREE', e))
    body = yield _lift(state, True, e.body)
    return fc.Free(e.vars, body)
  elif isinstance(e, fc.Or):
    lhs = yield _lift(state, True, e.lhs)
    rhs = yield _lift(state, True, e.rhs)
    return fc.Or(lhs, rhs)
  elif isinstance(e, fc.Typed):
    expr = yield _lift(state, nested, e.expr)
    return fc.Typed(expr, e.typeexpr)
  raise TypeError('not an expression: %r' % (e,))

def _lift_new_fun(state, fd):
  rule = fd.rule
  if not isinstance(rule, fc.External):
    body = yield _lift(state, False, rule.body)
    rule = fc.Rule(rule.args, body)
  return fc.Func(fd.name, fd.arity, fd.visibility, fd.typeexpr, rule)

def _lift_to_function(state, suffix, e):
  '''Moves ``e`` into a new function of its unbound variables.'''
  cfn = state.gen_func_name(suffix)
  vs = unbound_vars(e)
  newfun = fc.Func(cfn, len(vs), fc.Private, NONE_TYPE, fc.Rule(vs, e))
  newfun = yield _lift_new_fun(state, newfun)
  state.add_fun(newfun)
  return fc.Comb(fc.FuncCall, cfn, [fc.Var(v) for v in vs])

def _lift_case_exp(state, nested, e):
  if nested:
    return (yield from _lift_to_function(state, 'CASE', e))
  ne = yield _lift(state, True, e.scrutinee)
  nbrs = []
  for br in e.branches:
    body = yield _lift(state, True, br.body)
    nbrs.append(fc.Branch(br.pattern, body))
  return fc.Case(e.casetype, ne, nbrs)

def _lift_case_arg(state, e):
  '''Lifts a case whose scrutinee is not a variable.'''
  ne = yield _lift(state, True, e.scrutinee)
  cfn = state.gen_func_name('COMPLEXCASE')
  casevar = max([0] + fc.all_vars(e)) + 1
  vs = unionmap(unbound_vars_in_branch, e.branches)
  newfun = fc.Func(
      cfn, len(vs) + 1, fc.Private, NONE_TYPE
    , fc.Rule(vs + [casevar], fc.Case(e.casetype, fc.Var(casevar), e.branches))
    )
  newfun = yield _lift_new_fun(state, newfun)
  state.add_fun(newfun)
  return fc.Comb(fc.FuncCall, cfn, [fc.Var(v) for v in vs] + [ne])

def unbound_vars(e):
  '''
  The variables an expression does not bind, as the Curry ``unboundVars``.
  The walk runs on a stack of its own (:func:`utility.trampoline.trampoline`).
  '''
  return trampoline(_unbound_vars(e))

def _unbound_vars(e):
  if isinstance(e, fc.Var):
    return [e.index]
  elif isinstance(e, fc.Lit):
    return []
  elif isinstance(e, fc.Comb):
    parts = []
    for arg in e.args:
      part = yield _unbound_vars(arg)
      parts.append(part)
    return unions(parts)
  elif isinstance(e, fc.Or):
    lhs = yield _unbound_vars(e.lhs)
    rhs = yield _unbound_vars(e.rhs)
    return union(lhs, rhs)
  elif isinstance(e, fc.Typed):
    return (yield _unbound_vars(e.expr))
  elif isinstance(e, fc.Free):
    body = yield _unbound_vars(e.body)
    return [v for v in body if v not in e.vars]
  elif isinstance(e, fc.Let):
    parts = []
    for sub in [e.body] + [b for _, b in e.bindings]:
      part = yield _unbound_vars(sub)
      parts.append(part)
    bounds = [v for v, _ in e.bindings]
    return [v for v in unions(parts) if v not in bounds]
  elif isinstance(e, fc.Case):
    scrutinee = yield _unbound_vars(e.scrutinee)
    parts = []
    for br in e.branches:
      part = yield _unbound_vars_in_branch(br)
      parts.append(part)
    return union(scrutinee, unions(parts))
  raise TypeError('not an expression: %r' % (e,))

def unbound_vars_in_branch(br):
  return trampoline(_unbound_vars_in_branch(br))

def _unbound_vars_in_branch(br):
  body = yield _unbound_vars(br.body)
  if isinstance(br.pattern, fc.Pattern):
    return [v for v in body if v not in br.pattern.vars]
  return body
