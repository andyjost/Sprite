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
  , 'read', 'show', 'write'
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
      for v, b in e.bindings:
        items.append([v])
        items.append(b)
      stack.extend(reversed(items))
    elif isinstance(e, Free):
      stack.append(e.body)
      stack.append(list(e.vars))
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
