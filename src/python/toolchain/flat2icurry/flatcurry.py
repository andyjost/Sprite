'''
The FlatCurry data types, a reader for .fcy and .fint files, and a writer.

The types follow ``FlatCurry.Types`` of the Curry package ``flatcurry``.  A
qualified name is a pair ``(module, name)``.  Lists stay Python lists.  The
reader decodes the output of :func:`curry.utility.readcurry.parse`.  The
writer prints a program as the Curry front end does (:func:`terms.showhaskell`),
so a program read from a file of the front end and written again gives the
same bytes.
'''

from .errors import Flat2ICurryError
from .terms import Char, Term, constructor, showhaskell
from ...utility import readcurry as rc
from ...utility.trampoline import trampoline
import os

__all__ = [
    'Prog', 'Type', 'TypeSyn', 'TypeNew', 'Cons', 'NewCons'
  , 'TVar', 'FuncType', 'TCons', 'ForallType', 'KStar', 'KArrow'
  , 'Op', 'InfixOp', 'InfixlOp', 'InfixrOp'
  , 'Func', 'Rule', 'External', 'Rigid', 'Flex'
  , 'FuncCall', 'ConsCall', 'FuncPartCall', 'ConsPartCall'
  , 'Var', 'Lit', 'Comb', 'Let', 'Free', 'Or', 'Case', 'Typed'
  , 'Branch', 'Pattern', 'LPattern', 'Intc', 'Floatc', 'Charc'
  , 'Public', 'Private'
  , 'Expr', 'Literal', 'TypeDecl', 'TypeExpr', 'RuleDecl', 'PatternDecl'
  , 'CombType', 'CaseType', 'Visibility', 'Kind', 'Fixity'
  , 'CONSTRUCTORS', 'all_vars', 'data_decls_of', 'decode', 'load', 'prelude'
  , 'read', 'show', 'write', 'let_bindings', 'free_vars', 'binding_expr'
  , 'has_typed_locals', 'type_signatures', 'LocalTypes', 'typed_format', 'quantify_type'
  ]

CONSTRUCTORS = {}

def _cons(name, fields='', base=Term):
  '''Makes a term class and registers it for the reader.'''
  cls = constructor(name, fields, base)
  entry = cls if fields else cls()
  CONSTRUCTORS[name] = entry
  return entry

class TypeDecl(Term)   : __slots__ = ()
class ConsDecl(Term)   : __slots__ = ()
class TypeExpr(Term)   : __slots__ = ()
class Kind(Term)       : __slots__ = ()
class OpDecl(Term)     : __slots__ = ()
class Fixity(Term)     : __slots__ = ()
class FuncDecl(Term)   : __slots__ = ()
class RuleDecl(Term)   : __slots__ = ()
class CaseType(Term)   : __slots__ = ()
class CombType(Term)   : __slots__ = ()
class Expr(Term)       : __slots__ = ()
class BranchExpr(Term) : __slots__ = ()
class PatternDecl(Term): __slots__ = ()
class Literal(Term)    : __slots__ = ()
class Visibility(Term) : __slots__ = ()

Prog         = _cons('Prog', 'name imports types functions operators')
Public       = _cons('Public', base=Visibility)
Private      = _cons('Private', base=Visibility)
Type         = _cons('Type', 'name visibility typevars constructors', TypeDecl)
TypeSyn      = _cons('TypeSyn', 'name visibility typevars typeexpr', TypeDecl)
TypeNew      = _cons('TypeNew', 'name visibility typevars constructor', TypeDecl)
Cons         = _cons('Cons', 'name arity visibility argtypes', ConsDecl)
NewCons      = _cons('NewCons', 'name visibility typeexpr', ConsDecl)
TVar         = _cons('TVar', 'index', TypeExpr)
FuncType     = _cons('FuncType', 'domain range', TypeExpr)
TCons        = _cons('TCons', 'name args', TypeExpr)
ForallType   = _cons('ForallType', 'typevars typeexpr', TypeExpr)
KStar        = _cons('KStar', base=Kind)
KArrow       = _cons('KArrow', 'domain range', Kind)
Op           = _cons('Op', 'name fixity precedence', OpDecl)
InfixOp      = _cons('InfixOp', base=Fixity)
InfixlOp     = _cons('InfixlOp', base=Fixity)
InfixrOp     = _cons('InfixrOp', base=Fixity)
Func         = _cons('Func', 'name arity visibility typeexpr rule', FuncDecl)
Rule         = _cons('Rule', 'args body', RuleDecl)
External     = _cons('External', 'name', RuleDecl)
Rigid        = _cons('Rigid', base=CaseType)
Flex         = _cons('Flex', base=CaseType)
FuncCall     = _cons('FuncCall', base=CombType)
ConsCall     = _cons('ConsCall', base=CombType)
FuncPartCall = _cons('FuncPartCall', 'missing', CombType)
ConsPartCall = _cons('ConsPartCall', 'missing', CombType)
Var          = _cons('Var', 'index', Expr)
Lit          = _cons('Lit', 'literal', Expr)
Comb         = _cons('Comb', 'combtype name args', Expr)
# Retain the wire form: Let pairs / Free indices in FlatCurry 3,
# Let (index, type, expression) / Free (index, type) in FlatCurry 5.
Let          = _cons('Let', 'bindings body', Expr)
Free         = _cons('Free', 'vars body', Expr)
Or           = _cons('Or', 'lhs rhs', Expr)
Case         = _cons('Case', 'casetype scrutinee branches', Expr)
Typed        = _cons('Typed', 'expr typeexpr', Expr)
Branch       = _cons('Branch', 'pattern body', BranchExpr)
Pattern      = _cons('Pattern', 'name vars', PatternDecl)
LPattern     = _cons('LPattern', 'literal', PatternDecl)
Intc         = _cons('Intc', 'value', Literal)
Floatc       = _cons('Floatc', 'value', Literal)
Charc        = _cons('Charc', 'value', Literal)

def let_bindings(bindings):
  """The (index, expression) pairs of old pairs or typed triples."""
  return [(b[0], b[-1]) for b in bindings]

def binding_expr(binding, expr):
  """Replace a binding's expression, retaining its optional type slot."""
  return binding[:-1] + (expr,)

def free_vars(variables):
  """The indices of old free declarations or typed (index, type) pairs."""
  return [v if isinstance(v, int) else v[0] for v in variables]

def prelude(name):
  '''The qualified name of a Prelude symbol.'''
  return ('Prelude', name)

# The reader
# ==========
def read(text):
  '''Reads a FlatCurry program (or interface) from .fcy text.'''
  return decode(rc.parse(text))

def load(filename):
  '''Reads a FlatCurry program (or interface) from a file.'''
  with open(filename, 'r', encoding='utf-8') as istream:
    return read(istream.read())

def show(prog):
  '''
  The text of a FlatCurry program (or interface) as the front end writes it:
  the ``show`` of Haskell, on one line, without a newline at the end.
  '''
  return showhaskell(prog)

def write(prog, filename):
  '''
  Writes a FlatCurry program to a file in the format of the front end.  The
  text goes to a file beside the target first, which then takes the place of
  the target, so a reader never sees a partial file.
  '''
  text = show(prog)
  tmpname = filename + '.tmp%d' % os.getpid()
  with open(tmpname, 'w', encoding='utf-8', newline='') as ostream:
    ostream.write(text)
  os.replace(tmpname, filename)

def decode(rcdata):
  '''
  Converts the ``readcurry`` representation into FlatCurry terms.  The walk
  runs on a stack of its own (:func:`utility.trampoline.trampoline`), so a
  term of any depth needs no recursion (issue #125).
  '''
  return trampoline(_decode(rcdata))

def _lookup(name):
  try:
    return CONSTRUCTORS[name]
  except KeyError:
    raise Flat2ICurryError('unknown FlatCurry constructor %r' % name)

def _decode(x):
  if isinstance(x, rc.Applic):
    # The parser gives a nullary constructor in argument position as an
    # application without arguments.
    entry = _lookup(x.f.name)
    if isinstance(entry, Term):
      if x.args:
        raise Flat2ICurryError('%s takes no arguments' % x.f.name)
      return entry
    if len(x.args) != len(entry._fields_):
      raise Flat2ICurryError(
          '%s takes %d arguments, got %d'
              % (x.f.name, len(entry._fields_), len(x.args))
        )
    args = []
    for arg in x.args:
      arg = yield _decode(arg)
      args.append(arg)
    return entry(*args)
  elif isinstance(x, rc.Identifier):
    entry = _lookup(x.name)
    if not isinstance(entry, Term):
      raise Flat2ICurryError('%s needs %d arguments' % (x.name, len(entry._fields_)))
    return entry
  elif isinstance(x, (list, tuple)):
    out = []
    for arg in x:
      arg = yield _decode(arg)
      out.append(arg)
    return type(x)(out)
  elif isinstance(x, rc.Char):
    return Char(x)
  elif isinstance(x, rc.String):
    return str(x)
  elif isinstance(x, rc.Int):
    return int(x)
  elif isinstance(x, rc.Float):
    return float(x)
  else:
    raise Flat2ICurryError('cannot decode %r' % (x,))

# Selectors from FlatCurry.Goodies and FlatCurry.CaseCompletion
# ============================================================
def all_vars(expr):
  '''
  All variables of an expression, pattern variables included, in the order
  of ``FlatCurry.Goodies.allVars``.  The list may repeat a variable.  The
  walk keeps its own stack, so a nested application of any depth needs no
  recursion: an item of the stack is an expression to visit, or a list of
  variables to record as they are.
  '''
  out = []
  stack = [expr]
  while stack:
    e = stack.pop()
    if isinstance(e, list):
      out.extend(e)
    elif isinstance(e, Var):
      out.append(e.index)
    elif isinstance(e, Lit):
      pass
    elif isinstance(e, Comb):
      stack.extend(reversed(e.args))
    elif isinstance(e, Let):
      items = [e.body]
      for v, b in let_bindings(e.bindings):
        items.append([v])
        items.append(b)
      stack.extend(reversed(items))
    elif isinstance(e, Free):
      stack.append(e.body)
      stack.append(free_vars(e.vars))
    elif isinstance(e, Or):
      stack.append(e.rhs)
      stack.append(e.lhs)
    elif isinstance(e, Case):
      items = [e.scrutinee]
      for branch in e.branches:
        if isinstance(branch.pattern, Pattern):
          items.append(list(branch.pattern.vars))
        items.append(branch.body)
      stack.extend(reversed(items))
    elif isinstance(e, Typed):
      stack.append(e.expr)
    else:
      raise TypeError('not an expression: %r' % (e,))
  return out

def data_decls_of(prog):
  '''
  The data declarations of a program: a list of pairs of a type name and the
  constructor names with their arities.  A type synonym contributes nothing.
  A newtype contributes its one unary constructor.
  '''
  decls = []
  for td in prog.types:
    if isinstance(td, Type):
      decls.append((td.name, [(c.name, c.arity) for c in td.constructors]))
    elif isinstance(td, TypeNew):
      decls.append((td.name, [(td.constructor.name, 1)]))
  return decls

def has_typed_locals(term):
  '''Whether a term contains typed Free or Let declarations.'''
  stack = [term]
  while stack:
    x = stack.pop()
    if isinstance(x, Free) and any(isinstance(v, tuple) for v in x.vars):
      return True
    if isinstance(x, Let) and any(len(b) == 3 for b in x.bindings):
      return True
    if isinstance(x, Term):
      stack.extend(x._args_)
    elif isinstance(x, (list, tuple)):
      stack.extend(x)
  return False

def type_signatures(progs):
  '''Function and constructor schemes for local annotation propagation.'''
  schemes = {}
  for prog in progs:
    schemes.update((fd.name, fd.typeexpr) for fd in prog.functions)
    for td in prog.types:
      if isinstance(td, (Type, TypeNew)):
        result = TCons(td.name, [TVar(v) for v, _ in td.typevars])
        constructors = td.constructors if isinstance(td, Type) else [td.constructor]
        for c in constructors:
          args = c.argtypes if isinstance(c, Cons) else [c.typeexpr]
          te = result
          for arg in reversed(args):
            te = FuncType(arg, te)
          schemes[c.name] = ForallType(td.typevars, te) if td.typevars else te
  return schemes

class LocalTypes:
  '''Propagate the front end's types when a rewrite synthesizes a binding.

  This is an annotation helper for already typed FlatCurry, not the Python
  API type checker.  Its variables use the enclosing rule's type indices;
  instantiations of called schemes have fresh indices.
  '''
  def __init__(self, fd, schemes):
    self.schemes = schemes
    self.variables = {}
    self.substitution = {}
    self.nextvar = -1
    self.kinds = dict(fd.typeexpr.typevars) if isinstance(fd.typeexpr, ForallType) else {}
    te = self.body_type(fd.typeexpr)
    for v in fd.rule.args:
      self.variables[v], te = te.domain, te.range
    stack = [fd.rule.body]
    while stack:
      e = stack.pop()
      if isinstance(e, Free):
        self.variables.update(v for v in e.vars if isinstance(v, tuple))
        stack.append(e.body)
      elif isinstance(e, Let):
        self.variables.update((b[0], b[1]) for b in e.bindings if len(b) == 3)
        stack.extend(b[-1] for b in e.bindings)
        stack.append(e.body)
      elif isinstance(e, Case):
        stack.append(e.scrutinee)
        for br in e.branches:
          if isinstance(br.pattern, Pattern):
            if br.pattern.name not in self.schemes:
              stack.append(br.body)
              continue
            ct = self.instantiate(self.schemes[br.pattern.name])
            args = []
            for v in br.pattern.vars:
              args.append((v, ct.domain))
              ct = ct.range
            self.match(ct, self.expression(e.scrutinee))
            self.variables.update((v, self.resolve(t)) for v, t in args)
          stack.append(br.body)
      elif isinstance(e, Comb):
        stack.extend(e.args)
      elif isinstance(e, Or):
        stack.extend([e.lhs, e.rhs])
      elif isinstance(e, Typed):
        stack.append(e.expr)

  @staticmethod
  def body_type(te):
    return te.typeexpr if isinstance(te, ForallType) else te

  def fresh(self):
    te = TVar(self.nextvar)
    self.nextvar -= 1
    return te

  def resolve(self, te):
    if isinstance(te, TVar):
      if te.index in self.substitution:
        return self.resolve(self.substitution[te.index])
      return te
    if isinstance(te, FuncType):
      return FuncType(self.resolve(te.domain), self.resolve(te.range))
    if isinstance(te, TCons):
      return TCons(te.name, [self.resolve(t) for t in te.args])
    return te

  def instantiate(self, te):
    variables = {}
    kinds = dict(te.typevars) if isinstance(te, ForallType) else {}
    def rec(t):
      if isinstance(t, TVar):
        if t.index not in variables:
          variables[t.index] = self.fresh()
          self.kinds[variables[t.index].index] = kinds.get(t.index, KStar)
        return variables[t.index]
      if isinstance(t, FuncType):
        return FuncType(rec(t.domain), rec(t.range))
      if isinstance(t, TCons):
        return TCons(t.name, [rec(a) for a in t.args])
      return t
    return rec(self.body_type(te))

  def match(self, formal, actual):
    formal, actual = self.resolve(formal), self.resolve(actual)
    if formal == actual:
      return
    if isinstance(formal, TVar) and formal.index < 0:
      self.substitution[formal.index] = actual
    elif isinstance(actual, TVar) and actual.index < 0:
      self.substitution[actual.index] = formal
    elif isinstance(formal, FuncType) and isinstance(actual, FuncType):
      self.match(formal.domain, actual.domain)
      self.match(formal.range, actual.range)
    elif isinstance(formal, TCons) and isinstance(actual, TCons) \
        and formal.name == actual.name:
      for a, b in zip(formal.args, actual.args):
        self.match(a, b)

  def expression(self, expr):
    def rec(e):
      if isinstance(e, Var):
        if e.index not in self.variables:
          self.variables[e.index] = self.fresh()
        return self.resolve(self.variables[e.index])
      if isinstance(e, Typed):
        return e.typeexpr
      if isinstance(e, Lit):
        name = 'Int' if isinstance(e.literal, Intc) else \
               'Float' if isinstance(e.literal, Floatc) else 'Char'
        return TCons(prelude(name), [])
      if isinstance(e, (Free, Let)):
        return (yield rec(e.body))
      if isinstance(e, Or):
        return (yield rec(e.lhs))
      if isinstance(e, Case):
        return (yield rec(e.branches[0].body)) if e.branches else self.fresh()
      if isinstance(e, Comb):
        te = self.instantiate(self.schemes[e.name]) if e.name in self.schemes else self.fresh()
        for arg in e.args:
          at = yield rec(arg)
          if not isinstance(te, FuncType):
            result = self.fresh()
            self.match(te, FuncType(at, result))
            te = self.resolve(result)
          else:
            self.match(te.domain, at)
            te = self.resolve(te.range)
        return self.resolve(te)
      raise TypeError('not an expression: %r' % (e,))
    return trampoline(rec(expr))

def typed_format(prog, imports=()):
  '''Typed locals or the delimited instance names identify the new format.'''
  return has_typed_locals(prog) or any(
      fd.name[1].startswith('_inst#') and fd.name[1].endswith('#')
        for p in [prog] + list(imports) for fd in p.functions)

def quantify_type(te, kinds=None):
  '''Quantify a synthesized scheme without renumbering local annotations.'''
  variables = {}
  indices = set()
  stack = [te]
  while stack:
    t = stack.pop()
    if isinstance(t, TVar) and t.index >= 0:
      indices.add(t.index)
    elif isinstance(t, Term):
      stack.extend(t._args_)
    elif isinstance(t, (list, tuple)):
      stack.extend(t)
  nextvar = max(indices, default=-1) + 1
  def rec(t):
    nonlocal nextvar
    if isinstance(t, TVar):
      if t.index not in variables:
        variables[t.index] = t.index if t.index >= 0 else nextvar
        if t.index < 0:
          nextvar += 1
      return TVar(variables[t.index])
    if isinstance(t, FuncType):
      return FuncType(rec(t.domain), rec(t.range))
    if isinstance(t, TCons):
      return TCons(t.name, [rec(a) for a in t.args])
    return t
  te = rec(te)
  kinds = kinds or {}
  return ForallType([(i, kinds.get(v, KStar)) for v, i in variables.items()], te) if variables else te
