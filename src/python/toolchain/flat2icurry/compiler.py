'''
The name-to-index maps and the ICurry generation, the last two passes.  They
follow ``ICurry.Compiler`` and the map functions of ``ICurry.Options`` of
the Curry package ``icurry``.

Each ICurry name is a triple ``(module, name, index)``.  A constructor's
index is its position in its data type.  A data type's index is its position
in the type list of its module, type synonyms counted.  The public functions
of a module are numbered from 0 in order of appearance.  The private ones,
the lifted functions included, continue the numbering in the order of the
lifted program.
'''

from . import flatcurry as fc, icurrytypes as ic
from .errors import Flat2ICurryError
from ...utility import maxrecursion

__all__ = ['NameMaps', 'flat2icurry', 'demand_of', 'strip_typed', 'var_pos']

class NameMaps:
  '''Maps qualified names to their ICurry indices.'''

  def __init__(self):
    self.cons = {}  # (module, name) -> (arity, position)
    self.funs = {}  # (module, name) -> index

  @classmethod
  def build(cls, prog, impprogs, liftedprog):
    '''
    Builds the maps for ``prog`` (after newtype elimination), its imports,
    and the lifted program, whose private functions follow the public ones.
    '''
    maps = cls()
    for p in [prog] + list(impprogs):
      maps.add_constructors(p)
    pubfuns = [fd.name for fd in prog.functions if fd.visibility == fc.Public]
    for fd in prog.functions:
      if fd.visibility == fc.Public:
        maps.funs.setdefault(fd.name, len(maps.funs))
    pubset = set(pubfuns)
    index = len(pubfuns)
    for fd in liftedprog.functions:
      if fd.name not in pubset:
        if fd.name not in maps.funs:
          maps.funs[fd.name] = index
        index += 1
    for p in impprogs:
      maps.add_public_functions(p)
    return maps

  def add_constructors(self, prog):
    for _, cars in fc.data_decls_of(prog):
      for pos, (cname, arity) in enumerate(cars):
        self.cons.setdefault(cname, (arity, pos))

  def add_public_functions(self, prog):
    index = 0
    for fd in prog.functions:
      if fd.visibility == fc.Public:
        self.funs.setdefault(fd.name, index)
        index += 1

  def arity_pos_of_cons(self, qn, fun=''):
    try:
      return self.cons[qn]
    except KeyError:
      raise Flat2ICurryError(
          "Function '%s': Internal error in ICurry.Compiler:\n"
          "arity of constructor %s.%s is unknown" % (fun, qn[0], qn[1])
        )

  def pos_of_cons(self, qn, fun=''):
    return self.arity_pos_of_cons(qn, fun)[1]

  def pos_of_fun(self, qn, fun=''):
    try:
      return self.funs[qn]
    except KeyError:
      raise Flat2ICurryError(
          "Function '%s': Internal error in ICurry.Compiler:\n"
          "arity of operation %s.%s is unknown" % (fun, qn[0], qn[1])
        )

def flat2icurry(maps, prog, icurry_compat=True):
  '''
  Translates a completed and lifted FlatCurry program to ICurry.

  ``icurry_compat`` keeps the output of icurry 3.1.0 for a type annotation
  at the root of a rule.  See :func:`to_iblock`.
  '''
  types = []
  for ti, td in enumerate(prog.types):
    if isinstance(td, fc.TypeSyn):
      continue
    if isinstance(td, fc.TypeNew):
      raise Flat2ICurryError('ICurry.Compiler: newtype occurred!')
    mn, tn = td.name
    types.append(ic.IDataType(
        (mn, tn, ti)
      , [((c.name[0], c.name[1], i), c.arity) for i, c in enumerate(td.constructors)]
      ))
  with maxrecursion():
    functions = [tr_func(maps, fd, icurry_compat) for fd in prog.functions]
  return ic.IProg(prog.name, list(prog.imports), types, functions)

def tr_vis(vis):
  return ic.Public if vis == fc.Public else ic.Private

def tr_func(maps, fd, icurry_compat=True):
  mn, fn = fd.name
  ctx = Context(maps, fd.name, icurry_compat)
  return ic.IFunction(
      (mn, fn, maps.pos_of_fun(fd.name, fn)), fd.arity, tr_vis(fd.visibility)
    , demand_of(fd.rule, icurry_compat), tr_rule(ctx, fd.rule)
    )

def strip_typed(e):
  '''The expression under any type annotations.'''
  while isinstance(e, fc.Typed):
    e = e.expr
  return e

def demand_of(rule, icurry_compat=True):
  '''
  The argument a rule demands: the one its root case scrutinizes.  icurry
  3.1.0 does not look through a type annotation around the case.  Without
  ``icurry_compat`` the annotation is removed first.
  '''
  if isinstance(rule, fc.Rule):
    body = rule.body if icurry_compat else strip_typed(rule.body)
    if isinstance(body, fc.Case) and isinstance(body.scrutinee, fc.Var):
      v = body.scrutinee.index
      if v in rule.args:
        return [rule.args.index(v)]
  return []

def tr_rule(ctx, rule):
  if isinstance(rule, fc.External):
    return ic.IExternal(rule.name)
  return ic.IFuncBody(to_iblock(ctx, rule.args, rule.body, 0))

class Context:
  '''
  The maps, the name of the function under translation, and the
  compatibility flag.
  '''

  def __init__(self, maps, qname, icurry_compat=True):
    self.maps = maps
    self.qname = qname
    self.icurry_compat = icurry_compat

  def error(self, msg):
    return Flat2ICurryError("Function '%s': %s" % (self.qname[1], msg))

def is_failed(e):
  return isinstance(e, fc.Comb) and e.combtype == fc.FuncCall \
      and e.name == fc.prelude('failed') and not e.args

def to_iblock(ctx, vs, e, root):
  '''
  A block for the rule arguments ``vs`` and body ``e``.  ``root`` is the
  variable that holds the node whose successors are the arguments.

  A type annotation at the root of a rule, as in ``f x = (e :: t)``, is a
  defect of icurry 3.1.0.  It does not look through the annotation: a case
  under it is an error, and the bindings of a let or free declaration under
  it are lost, so the block refers to variables it never declares.  With
  ``ctx.icurry_compat`` the block is built the same way and the output stays
  byte-identical to icurry.  Without it the annotation is removed first.
  Annotations in nested positions are not affected: lifting moves the
  expression under them into a new function.
  '''
  if not ctx.icurry_compat:
    e = strip_typed(e)
  evars = fc.all_vars(e)
  evarset = set(evars)
  casevar = max([0] + evars) + 1  # fresh variable for a complex case argument

  decls = [ic.IVarDecl(v) for v in vs if v in evarset]
  if isinstance(e, fc.Free):
    decls.extend(ic.IFreeDecl(v) for v in e.vars)
  elif isinstance(e, fc.Let):
    decls.extend(ic.IVarDecl(v) for v, _ in e.bindings)
  elif isinstance(e, fc.Case) and not isinstance(e.scrutinee, fc.Var):
    decls.append(ic.IVarDecl(casevar))

  assigns = [
      ic.IVarAssign(v, ic.IVarAccess(root, [p]))
          for p, v in enumerate(vs) if v in evarset
    ]
  if isinstance(e, fc.Let):
    bindings = [(v, to_iexpr(ctx, b)) for v, b in e.bindings]
    assigns.extend(ic.IVarAssign(v, be) for v, be in bindings)
    assigns.extend(recursive_assigns(bindings))
  elif isinstance(e, fc.Case) and not isinstance(e.scrutinee, fc.Var):
    assigns.append(ic.IVarAssign(casevar, to_iexpr(ctx, e.scrutinee)))

  if isinstance(e, fc.Case) and e.branches:
    carg = e.scrutinee.index if isinstance(e.scrutinee, fc.Var) else casevar
    if isinstance(e.branches[0].pattern, fc.Pattern):
      statement = ic.ICaseCons(carg, [tr_pbranch(ctx, carg, br) for br in e.branches])
    else:
      statement = ic.ICaseLit(carg, [tr_lbranch(ctx, carg, br) for br in e.branches])
  elif is_failed(e):
    statement = ic.IExempt
  else:
    statement = ic.IReturn(to_iexpr(ctx, e))
  return ic.IBlock(decls, assigns, statement)

def recursive_assigns(bindings):
  '''
  The node assignments that close the cycles of a recursive let.  For each
  binding, every variable in its expression that names this binding or a
  later one is assigned after the fact.
  '''
  out = []
  for i, (v, be) in enumerate(bindings):
    later = set(w for w, _ in bindings[i:])
    for w, path in var_pos([], be):
      if w in later:
        out.append(ic.INodeAssign(v, path, ic.IVar(w)))
  return out

def tr_pbranch(ctx, carg, br):
  pat = br.pattern
  if not isinstance(pat, fc.Pattern):
    raise ctx.error('trPBranch with LPattern')
  mn, cn = pat.name
  ar, pos = ctx.maps.arity_pos_of_cons(pat.name, ctx.qname[1])
  return ic.IConsBranch((mn, cn, pos), ar, to_iblock(ctx, pat.vars, br.body, carg))

def tr_lbranch(ctx, carg, br):
  pat = br.pattern
  if not isinstance(pat, fc.LPattern):
    raise ctx.error('trLBranch with Pattern')
  return ic.ILitBranch(tr_lit(pat.literal), to_iblock(ctx, [], br.body, carg))

def to_iexpr(ctx, e):
  if isinstance(e, fc.Var):
    return ic.IVar(e.index)
  elif isinstance(e, fc.Lit):
    return ic.ILit(tr_lit(e.literal))
  elif isinstance(e, fc.Comb):
    if e.name == fc.prelude('?') and len(e.args) == 2:
      return to_iexpr(ctx, fc.Or(e.args[0], e.args[1]))
    mn, fn = e.name
    args = [to_iexpr(ctx, arg) for arg in e.args]
    ct = e.combtype
    maps, cur = ctx.maps, ctx.qname[1]
    if ct == fc.FuncCall:
      return ic.IFCall((mn, fn, maps.pos_of_fun(e.name, cur)), args)
    elif ct == fc.ConsCall:
      return ic.ICCall((mn, fn, maps.pos_of_cons(e.name, cur)), args)
    elif isinstance(ct, fc.FuncPartCall):
      return ic.IFPCall((mn, fn, maps.pos_of_fun(e.name, cur)), ct.missing, args)
    else:
      return ic.ICPCall((mn, fn, maps.pos_of_cons(e.name, cur)), ct.missing, args)
  elif isinstance(e, fc.Or):
    return ic.IOr(to_iexpr(ctx, e.lhs), to_iexpr(ctx, e.rhs))
  elif isinstance(e, fc.Typed):
    return to_iexpr(ctx, e.expr)
  elif isinstance(e, fc.Let):
    return to_iexpr(ctx, e.body)
  elif isinstance(e, fc.Free):
    return to_iexpr(ctx, e.body)
  elif isinstance(e, fc.Case):
    raise ctx.error('toIExpr: Case occurred')
  raise TypeError('not an expression: %r' % (e,))

def tr_lit(lit):
  if isinstance(lit, fc.Intc):
    return ic.IInt(lit.value)
  elif isinstance(lit, fc.Floatc):
    return ic.IFloat(lit.value)
  elif isinstance(lit, fc.Charc):
    return ic.IChar(lit.value)
  raise TypeError('not a literal: %r' % (lit,))

def var_pos(rpos, e):
  '''The variables of an ICurry expression with their positions.'''
  if isinstance(e, ic.IVar):
    return [(e.var, list(rpos))]
  elif isinstance(e, (ic.IVarAccess, ic.ILit)):
    return []
  elif isinstance(e, (ic.IFCall, ic.ICCall, ic.IFPCall, ic.ICPCall)):
    out = []
    for i, arg in enumerate(e.args):
      out.extend(var_pos(rpos + [i], arg))
    return out
  elif isinstance(e, ic.IOr):
    return var_pos(rpos + [0], e.lhs) + var_pos(rpos + [1], e.rhs)
  raise TypeError('not an ICurry expression: %r' % (e,))
