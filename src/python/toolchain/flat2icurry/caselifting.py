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

__all__ = ['lift_prog', 'unbound_vars', 'union', 'unionmap']

NONE_TYPE = fc.TCons(fc.prelude('None'), [])

def union(xs, ys):
  '''``Data.List.union`` of the Curry library: xs not in ys, then ys.'''
  return [x for x in xs if x not in ys] + list(ys)

def unionmap(f, items):
  '''``foldr union [] (map f items)``.'''
  acc = []
  for item in reversed(items):
    acc = union(f(item), acc)
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
  return fc.Func(fd.name, fd.arity, fd.visibility, fd.typeexpr, lift_rule(state, fd.rule))

def lift_rule(state, rule):
  if isinstance(rule, fc.External):
    return rule
  return fc.Rule(rule.args, lift_exp(state, False, rule.body))

def lift_exp(state, nested, e):
  '''
  Lifts an expression.  ``nested`` is true inside an expression where a
  case, let, or free declaration must be lifted, such as a call argument.
  '''
  if isinstance(e, (fc.Var, fc.Lit)):
    return e
  elif isinstance(e, fc.Comb):
    return fc.Comb(e.combtype, e.name, [lift_exp(state, True, arg) for arg in e.args])
  elif isinstance(e, fc.Case):
    if isinstance(e.scrutinee, fc.Var):
      return lift_case_exp(state, nested, e)
    return lift_case_arg(state, e)
  elif isinstance(e, fc.Let):
    if nested:
      return lift_to_function(state, 'LET', e)
    bindings = [(v, lift_exp(state, True, b)) for v, b in e.bindings]
    return fc.Let(bindings, lift_exp(state, True, e.body))
  elif isinstance(e, fc.Free):
    if nested:
      return lift_to_function(state, 'FREE', e)
    return fc.Free(e.vars, lift_exp(state, True, e.body))
  elif isinstance(e, fc.Or):
    return fc.Or(lift_exp(state, True, e.lhs), lift_exp(state, True, e.rhs))
  elif isinstance(e, fc.Typed):
    return fc.Typed(lift_exp(state, nested, e.expr), e.typeexpr)
  raise TypeError('not an expression: %r' % (e,))

def lift_to_function(state, suffix, e):
  '''Moves ``e`` into a new function of its unbound variables.'''
  cfn = state.gen_func_name(suffix)
  vs = unbound_vars(e)
  newfun = fc.Func(cfn, len(vs), fc.Private, NONE_TYPE, fc.Rule(vs, e))
  state.add_fun(lift_new_fun(state, newfun))
  return fc.Comb(fc.FuncCall, cfn, [fc.Var(v) for v in vs])

def lift_case_exp(state, nested, e):
  if nested:
    return lift_to_function(state, 'CASE', e)
  ne = lift_exp(state, True, e.scrutinee)
  nbrs = [fc.Branch(br.pattern, lift_exp(state, True, br.body)) for br in e.branches]
  return fc.Case(e.casetype, ne, nbrs)

def lift_case_arg(state, e):
  '''Lifts a case whose scrutinee is not a variable.'''
  ne = lift_exp(state, True, e.scrutinee)
  cfn = state.gen_func_name('COMPLEXCASE')
  casevar = max([0] + fc.all_vars(e)) + 1
  vs = unionmap(unbound_vars_in_branch, e.branches)
  newfun = fc.Func(
      cfn, len(vs) + 1, fc.Private, NONE_TYPE
    , fc.Rule(vs + [casevar], fc.Case(e.casetype, fc.Var(casevar), e.branches))
    )
  state.add_fun(lift_new_fun(state, newfun))
  return fc.Comb(fc.FuncCall, cfn, [fc.Var(v) for v in vs] + [ne])

def unbound_vars(e):
  '''The variables an expression does not bind, as the Curry ``unboundVars``.'''
  if isinstance(e, fc.Var):
    return [e.index]
  elif isinstance(e, fc.Lit):
    return []
  elif isinstance(e, fc.Comb):
    return unionmap(unbound_vars, e.args)
  elif isinstance(e, fc.Or):
    return union(unbound_vars(e.lhs), unbound_vars(e.rhs))
  elif isinstance(e, fc.Typed):
    return unbound_vars(e.expr)
  elif isinstance(e, fc.Free):
    return [v for v in unbound_vars(e.body) if v not in e.vars]
  elif isinstance(e, fc.Let):
    unbounds = unionmap(unbound_vars, [e.body] + [b for _, b in e.bindings])
    bounds = [v for v, _ in e.bindings]
    return [v for v in unbounds if v not in bounds]
  elif isinstance(e, fc.Case):
    return union(unbound_vars(e.scrutinee), unionmap(unbound_vars_in_branch, e.branches))
  raise TypeError('not an expression: %r' % (e,))

def unbound_vars_in_branch(br):
  if isinstance(br.pattern, fc.Pattern):
    return [v for v in unbound_vars(br.body) if v not in br.pattern.vars]
  return unbound_vars(br.body)
