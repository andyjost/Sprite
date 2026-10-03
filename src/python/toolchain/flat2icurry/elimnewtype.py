'''
Newtype elimination, the first pass.  It follows ``FlatCurry.ElimNewtype``
of the Curry package ``flatcurry``.

For a declaration ``newtype T a = C te``:

  - The declaration becomes a data declaration with one unary constructor.
  - A type ``T t`` becomes ``te`` with ``a`` replaced by ``t``.  Operations
    named ``_inst#...`` keep their types.
  - A constructor application ``C e`` becomes ``e``.
  - A partial application ``C`` becomes the partial ``Prelude.id``.
  - A case ``case x of C y -> e`` becomes ``e`` with ``y`` replaced by ``x``,
    or a ``Let`` when the scrutinee is not a variable.

The newtypes come from the module and from the interfaces of its imports.
'''

from . import flatcurry as fc

__all__ = ['elim_newtype', 'newtypes_of', 'subst_var']

def newtypes_of(typedecls):
  '''
  Maps the name of each newtype to ``(typevars, consname, typeexpr)``.  The
  first declaration of a name wins, as the Curry ``lookup`` does.
  '''
  nti = {}
  for td in typedecls:
    if isinstance(td, fc.TypeNew):
      nc = td.constructor
      nti.setdefault(td.name, ([tv for tv, _ in td.typevars], nc.name, nc.typeexpr))
  return nti

def elim_newtype(impprogs, prog):
  '''Eliminates the newtypes of ``prog``.  ``impprogs`` are its imports.'''
  typedecls = list(prog.types)
  for imp in impprogs:
    typedecls.extend(imp.types)
  nti = newtypes_of(typedecls)
  if not nti:
    return prog
  newcons = {consname for _, consname, _ in nti.values()}
  return fc.Prog(
      prog.name, prog.imports
    , [replace_newtype_decl(td) for td in prog.types]
    , [elim_newtype_in_func(nti, newcons, fd) for fd in prog.functions]
    , prog.operators
    )

def replace_newtype_decl(td):
  if isinstance(td, fc.TypeNew):
    nc = td.constructor
    return fc.Type(
        td.name, td.visibility, td.typevars
      , [fc.Cons(nc.name, 1, nc.visibility, [nc.typeexpr])]
      )
  return td

def is_class_instance_op(qname):
  return qname[1].startswith('_inst#')

def elim_newtype_in_func(nti, newcons, fd):
  if isinstance(fd.rule, fc.External) or is_class_instance_op(fd.name):
    return fd
  return fc.Func(
      fd.name, fd.arity, fd.visibility, elim_type(nti, fd.typeexpr)
    , fc.Rule(fd.rule.args, elim_exp(newcons, fd.rule.body))
    )

def elim_type(nti, te):
  if isinstance(te, fc.TVar):
    return te
  elif isinstance(te, fc.FuncType):
    return fc.FuncType(elim_type(nti, te.domain), elim_type(nti, te.range))
  elif isinstance(te, fc.TCons):
    args = [elim_type(nti, arg) for arg in te.args]
    if te.name in nti:
      tvs, _, ntexp = nti[te.name]
      return subst_tvars(list(zip(tvs, args)), ntexp)
    return fc.TCons(te.name, args)
  elif isinstance(te, fc.ForallType):
    return fc.ForallType(te.typevars, elim_type(nti, te.typeexpr))
  raise TypeError('not a type expression: %r' % (te,))

def subst_tvars(mapping, te):
  '''Applies a type substitution, a list of pairs, to a type expression.'''
  def subst(texp):
    if isinstance(texp, fc.TVar):
      for tv, replacement in mapping:
        if tv == texp.index:
          return replacement
      return texp
    elif isinstance(texp, fc.FuncType):
      return fc.FuncType(subst(texp.domain), subst(texp.range))
    elif isinstance(texp, fc.TCons):
      return fc.TCons(texp.name, [subst(arg) for arg in texp.args])
    elif isinstance(texp, fc.ForallType):
      return fc.ForallType(texp.typevars, subst(texp.typeexpr))
    raise TypeError('not a type expression: %r' % (texp,))
  return subst(te)

def elim_exp(newcons, e):
  if isinstance(e, (fc.Var, fc.Lit)):
    return e
  elif isinstance(e, fc.Comb):
    args = [elim_exp(newcons, arg) for arg in e.args]
    return elim_comb(newcons, e.combtype, e.name, args)
  elif isinstance(e, fc.Let):
    return fc.Let(
        [(v, elim_exp(newcons, b)) for v, b in e.bindings], elim_exp(newcons, e.body)
      )
  elif isinstance(e, fc.Free):
    return fc.Free(e.vars, elim_exp(newcons, e.body))
  elif isinstance(e, fc.Or):
    return fc.Or(elim_exp(newcons, e.lhs), elim_exp(newcons, e.rhs))
  elif isinstance(e, fc.Case):
    return elim_case(
        newcons, e.casetype, elim_exp(newcons, e.scrutinee)
      , [fc.Branch(br.pattern, elim_exp(newcons, br.body)) for br in e.branches]
      )
  elif isinstance(e, fc.Typed):
    return fc.Typed(elim_exp(newcons, e.expr), e.typeexpr)
  raise TypeError('not an expression: %r' % (e,))

def elim_comb(newcons, ct, qn, es):
  if ct == fc.ConsCall and len(es) == 1 and qn in newcons:
    return es[0]
  if isinstance(ct, fc.ConsPartCall) and ct.missing == 1 and not es and qn in newcons:
    return fc.Comb(fc.FuncPartCall(1), fc.prelude('id'), [])
  return fc.Comb(ct, qn, es)

def elim_case(newcons, ct, ce, bs):
  if len(bs) == 1:
    pat, be = bs[0].pattern, bs[0].body
    if isinstance(pat, fc.Pattern) and len(pat.vars) == 1 and pat.name in newcons:
      v, = pat.vars
      if isinstance(ce, fc.Var):
        return subst_var(v, ce.index, be)
      return fc.Let([(v, ce)], be)
  return fc.Case(ct, ce, bs)

def subst_var(x, y, e0):
  '''Replaces the variable ``x`` by the variable ``y`` in an expression.'''
  def subst(e):
    if isinstance(e, fc.Var):
      return fc.Var(y) if e.index == x else e
    elif isinstance(e, fc.Lit):
      return e
    elif isinstance(e, fc.Comb):
      return fc.Comb(e.combtype, e.name, [subst(arg) for arg in e.args])
    elif isinstance(e, fc.Let):
      return fc.Let([(v, subst(b)) for v, b in e.bindings], subst(e.body))
    elif isinstance(e, fc.Free):
      return fc.Free(e.vars, subst(e.body))
    elif isinstance(e, fc.Or):
      return fc.Or(subst(e.lhs), subst(e.rhs))
    elif isinstance(e, fc.Case):
      return fc.Case(
          e.casetype, subst(e.scrutinee)
        , [fc.Branch(br.pattern, subst(br.body)) for br in e.branches]
        )
    elif isinstance(e, fc.Typed):
      return fc.Typed(subst(e.expr), e.typeexpr)
    raise TypeError('not an expression: %r' % (e,))
  return subst(e0)
