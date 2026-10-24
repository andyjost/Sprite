'''
The set0 lift, a FlatCurry-to-FlatCurry pass over the FlatCurry file of a
module (decision D28 of 2026-10-12).

``set0 e`` is the set function of the expression ``e``.  When ``e`` holds
variables of the enclosing context (the captured variables), those
variables are arguments of the capsule, boxed at the entry as the arguments
of ``setk`` are: the set function of ``e`` is the set function of the
operation ``\\v_1 .. v_p -> e`` applied to ``v_1 .. v_p``, and the
non-determinism and the failure of a captured variable stay outside the
set, one set per outside alternative.  That is the semantics of weakly
encapsulated search (Christiansen, Hanus, Reck and Seidel, PPDP 2013,
section 3.3): ``let x = coin in allValues x`` yields {0} and {1}, and
``let x = failed in allValues x`` fails instead of yielding a set.  The
implementations that scope by the time of the first evaluation (KiCS2,
PAKCS) are not the authority; the paper is.

The compiler, not the runtime, makes it so.  The runtime boxes the
arguments a function value holds (``set_step`` of
``curryrt/currylib/setfunctions.cpp``, ``set_`` of the former runtime; issue
#117), so ``set1 (f x_1 .. x_(k-1)) x_k`` and ``setk f x_1 .. x_k`` reach
one entry state for any ``k``, and this pass turns every saturated call
``set0 e`` whose argument has captured variables ``x_1 .. x_k`` into that
call:

  - A new function ``L x_1 .. x_k = e``, ``Private``, with the arity ``k``
    and a fresh polymorphic type ``forall a_0 .. a_k. a_0 -> .. -> a_k``
    (the file is written to disk, and a reader of the file may read the
    type; the ICurry compiler ignores it).  A type annotation at the root
    of ``e`` is removed first: a root annotation over a let, a free
    declaration or a case meets a defect of ``icurry`` 3.1.0 (see
    ``compiler.to_iblock``).
  - The call becomes ``setk L x_1 .. x_k`` for ``k`` up to seven, the
    arities the library has, and ``set1 (L x_1 .. x_(k-1)) x_k`` beyond,
    which reaches the same entry state.

The captured variables are the variables ``e`` does not bind (the Curry
``unboundVars``), in the order of their first occurrence in ``e``.  A class
dictionary and a variable of a ``where .. free`` declaration outside ``e``
are captured variables like any other, as they are arguments of a
lambda-lifted function.  The pass runs bottom-up, so a ``set0`` inside
``e`` is lifted first, and it reaches every rule of the module, the lifted
lambdas of the front end (``f._#lambdaN``) and the bodies of lets and
cases included.  ``set0 $ e`` is the call ``set0 e`` (the ``$`` on a
partial application is reduced as the binding optimization reduces it).

The name of a lifted function is ``f_SET0n``, where ``f`` is the local
name of the enclosing function and ``n`` counts from zero per enclosing
function; a name an original function of the module has is skipped, and
the counter still advances.  The front end writes no such name
(``f._#lambdaN``, ``f.g.N``, ``_impl#``, ``_inst#``, ``_super#``,
``_def#``), and the case lifting of the translation
(:mod:`caselifting`, names ``f_CASEn``, ``f_LETn``, ``f_FREEn``,
``f_COMPLEXCASEn``) runs after this pass over a program that holds the
lifted functions, whose names it skips.  A lifted function has no entry
in the interface ``M.fint``, which the pass never writes: it is private,
and the importers number the public functions of the module from that
file.

A closed ``set0 e`` (no captured variable) is unchanged: an encapsulated
expression, with no argument to box.  A ``set0`` that is not a saturated
call, a partial application such as ``map set0 xs`` or a ``set0`` reached
through a variable, is left alone: the pass sees no argument there.

:func:`optimize_file` applies the pass to a FlatCurry file in place, as
:func:`bindingopt.optimize_file` applies the binding optimization; the
routes apply the two passes together (:func:`rewrite.rewrite_file`),
after the front end and before the translation, so the ``.fcy`` on disk
is the lifted program and both routes translate the same text.  The pass
is idempotent: over a lifted program it lifts nothing and writes nothing.
'''

from . import flatcurry as fc
from ...utility.trampoline import trampoline

__all__ = [
    'MAX_ARITY', 'SET0', 'SETFUNCTIONS', 'SUFFIX', 'captured_vars'
  , 'contains_set0', 'is_lifted_name', 'lift_type', 'lifted_functions'
  , 'optimize_file', 'optimize_set0', 'set0_call', 'strip_typed'
  , 'transform_exp', 'transform_func', 'transform_prog'
  ]

SETFUNCTIONS = 'Control.SetFunctions'
SET0 = (SETFUNCTIONS, 'set0')
DOLLAR = fc.prelude('$')

# The largest arity the library has a set function for (set1 .. set7).
MAX_ARITY = 7

# The suffix of the name of a lifted function: f_SET0n.
SUFFIX = '_SET0'

def setk(k):
  '''The qualified name of the set function of arity ``k``.'''
  return (SETFUNCTIONS, 'set%d' % k)

def is_lifted_name(name):
  '''Whether the local name ``name`` is the name of a lifted function.'''
  stem, sep, count = name.rpartition(SUFFIX)
  return bool(sep) and bool(stem) and count.isdigit()

def strip_typed(e):
  '''The expression under any type annotations at the root.'''
  while isinstance(e, fc.Typed):
    e = e.expr
  return e

def lift_type(k):
  '''
  The type of a lifted function of arity ``k``: a fresh polymorphic scheme
  over ``k + 1`` type variables, ``forall a_0 .. a_k. a_0 -> .. -> a_k``,
  written as the front end writes a scheme.
  '''
  typeexpr = fc.TVar(k)
  for i in reversed(range(k)):
    typeexpr = fc.FuncType(fc.TVar(i), typeexpr)
  return fc.ForallType([(i, fc.KStar) for i in range(k + 1)], typeexpr)

def set0_call(e):
  '''
  The saturated call ``set0 e'`` that ``e`` is, or None.  Two shapes count:
  the call itself, and ``set0 $ e'`` (a call of ``$`` on the partial
  application ``set0``, which is reduced to the call).  A partial
  application of ``set0`` alone is no call.
  '''
  if not isinstance(e, fc.Comb) or e.combtype != fc.FuncCall:
    return None
  if e.name == SET0:
    return e if len(e.args) == 1 else None
  if e.name == DOLLAR and len(e.args) == 2:
    head, arg = e.args
    if isinstance(head, fc.Comb) and head.name == SET0 \
        and head.combtype == fc.FuncPartCall(1) and not head.args:
      return fc.Comb(fc.FuncCall, SET0, [arg])
  return None

def captured_vars(e):
  '''
  The variables ``e`` does not bind (the Curry ``unboundVars``), each once,
  in the order of their first occurrence in a left-to-right walk of ``e``:
  the arguments of a call in order, the bindings of a let before its body,
  the scrutinee of a case before its branches.  A variable a let, a free
  declaration or a pattern of ``e`` binds is left out under its binder.
  The walk keeps its own stack, so an expression of any depth needs no
  recursion.
  '''
  out = []
  seen = set()
  stack = [(e, frozenset())]
  while stack:
    x, bound = stack.pop()
    if isinstance(x, fc.Var):
      if x.index not in bound and x.index not in seen:
        seen.add(x.index)
        out.append(x.index)
    elif isinstance(x, fc.Lit):
      pass
    elif isinstance(x, fc.Comb):
      stack.extend((arg, bound) for arg in reversed(x.args))
    elif isinstance(x, fc.Let):
      inner = bound | frozenset(v for v, _ in x.bindings)
      items = [b for _, b in x.bindings] + [x.body]
      stack.extend((item, inner) for item in reversed(items))
    elif isinstance(x, fc.Free):
      stack.append((x.body, bound | frozenset(x.vars)))
    elif isinstance(x, fc.Or):
      stack.append((x.rhs, bound))
      stack.append((x.lhs, bound))
    elif isinstance(x, fc.Case):
      for br in reversed(x.branches):
        inner = bound
        if isinstance(br.pattern, fc.Pattern):
          inner = bound | frozenset(br.pattern.vars)
        stack.append((br.body, inner))
      stack.append((x.scrutinee, bound))
    elif isinstance(x, fc.Typed):
      stack.append((x.expr, bound))
    else:
      raise TypeError('not an expression: %r' % (x,))
  return out

def contains_set0(e):
  '''
  Whether an expression holds a call or a partial application of ``set0``.
  The walk keeps its own stack.
  '''
  stack = [e]
  while stack:
    e = stack.pop()
    if isinstance(e, (fc.Var, fc.Lit)):
      continue
    elif isinstance(e, fc.Comb):
      if e.name == SET0:
        return True
      stack.extend(reversed(e.args))
    elif isinstance(e, fc.Free):
      stack.append(e.body)
    elif isinstance(e, fc.Typed):
      stack.append(e.expr)
    elif isinstance(e, fc.Or):
      stack.append(e.rhs)
      stack.append(e.lhs)
    elif isinstance(e, fc.Case):
      stack.extend(reversed([br.body for br in e.branches]))
      stack.append(e.scrutinee)
    elif isinstance(e, fc.Let):
      stack.extend(reversed([b for _, b in e.bindings]))
      stack.append(e.body)
    else:
      raise TypeError('not an expression: %r' % (e,))
  return False

class LiftState:
  '''
  The names of the functions of the module (the originals and the lifted
  ones so far, shared by the whole program), the enclosing function, its
  counter, and the functions lifted out of it, in the order of their
  creation (an inner ``set0`` before the ``set0`` around it).
  '''

  def __init__(self, qname, names):
    self.modname, self.funcname = qname
    self.names = names
    self.index = 0
    self.lifted = []

  def gen_name(self):
    while True:
      name = (self.modname, '%s%s%d' % (self.funcname, SUFFIX, self.index))
      self.index += 1
      if name not in self.names:
        self.names.add(name)
        return name

  def lift(self, arg):
    '''
    Lifts the argument ``arg`` of a saturated call of ``set0`` with the
    captured variables ``vs`` and returns the call that takes its place.
    '''
    vs = captured_vars(arg)
    assert vs
    name = self.gen_name()
    k = len(vs)
    self.lifted.append(
        fc.Func(name, k, fc.Private, lift_type(k), fc.Rule(list(vs), strip_typed(arg)))
      )
    if k <= MAX_ARITY:
      head = fc.Comb(fc.FuncPartCall(k), name, [])
      return fc.Comb(fc.FuncCall, setk(k), [head] + [fc.Var(v) for v in vs])
    head = fc.Comb(fc.FuncPartCall(1), name, [fc.Var(v) for v in vs[:-1]])
    return fc.Comb(fc.FuncCall, setk(1), [head, fc.Var(vs[-1])])

def transform_exp(state, e):
  '''
  Transforms an expression bottom-up: the subexpressions first, then the
  expression itself when it is a saturated call of ``set0`` whose argument
  has captured variables.  The walk runs on a stack of its own
  (:func:`utility.trampoline.trampoline`), so a nested application of any
  depth needs no recursion (issue #125).
  '''
  def rec(e):
    if isinstance(e, (fc.Var, fc.Lit)):
      return e
    elif isinstance(e, fc.Comb):
      args = []
      for arg in e.args:
        arg = yield rec(arg)
        args.append(arg)
      e = fc.Comb(e.combtype, e.name, args)
      call = set0_call(e)
      if call is not None and captured_vars(call.args[0]):
        return state.lift(call.args[0])
      return e
    elif isinstance(e, fc.Free):
      body = yield rec(e.body)
      return fc.Free(e.vars, body)
    elif isinstance(e, fc.Or):
      lhs = yield rec(e.lhs)
      rhs = yield rec(e.rhs)
      return fc.Or(lhs, rhs)
    elif isinstance(e, fc.Typed):
      expr = yield rec(e.expr)
      return fc.Typed(expr, e.typeexpr)
    elif isinstance(e, fc.Case):
      scrutinee = yield rec(e.scrutinee)
      branches = []
      for br in e.branches:
        body = yield rec(br.body)
        branches.append(fc.Branch(br.pattern, body))
      return fc.Case(e.casetype, scrutinee, branches)
    elif isinstance(e, fc.Let):
      bindings = []
      for v, b in e.bindings:
        b = yield rec(b)
        bindings.append((v, b))
      body = yield rec(e.body)
      return fc.Let(bindings, body)
    raise TypeError('not an expression: %r' % (e,))

  return trampoline(rec(e))

def transform_func(fd, names):
  '''
  Transforms a function declaration.  Returns the declaration and the list
  of the functions lifted out of it.  ``names`` is the set of the qualified
  names of the functions of the module, which the new names join.  A rule
  without a ``set0``, and one whose every ``set0`` is closed or not a
  saturated call, is returned as it is.
  '''
  if isinstance(fd.rule, fc.External) or not contains_set0(fd.rule.body):
    return fd, []
  state = LiftState(fd.name, names)
  body = transform_exp(state, fd.rule.body)
  if not state.lifted:
    return fd, []
  newfd = fc.Func(
      fd.name, fd.arity, fd.visibility, fd.typeexpr, fc.Rule(fd.rule.args, body)
    )
  return newfd, state.lifted

def transform_prog(prog):
  '''
  Transforms a FlatCurry program.  Returns the new program and the number
  of ``set0`` calls lifted, or the program itself and zero.  A lifted
  function follows the function it was lifted out of.
  '''
  names = set(fd.name for fd in prog.functions)
  functions = []
  total = 0
  for fd in prog.functions:
    fd, lifted = transform_func(fd, names)
    functions.append(fd)
    functions.extend(lifted)
    total += len(lifted)
  if total == 0:
    return prog, 0
  return fc.Prog(
      prog.name, prog.imports, prog.types, functions, prog.operators
    ), total

def lifted_functions(prog):
  '''The qualified names of the lifted functions of a program.'''
  return [fd.name for fd in prog.functions if is_lifted_name(fd.name[1])]

def optimize_set0(prog):
  '''
  Applies the set0 lift to a FlatCurry program.  Returns the transformed
  program when a call was lifted, else ``prog`` itself.
  '''
  newprog, n = transform_prog(prog)
  return newprog if n else prog

def optimize_file(fcyfile):
  '''
  Applies the set0 lift to the FlatCurry file ``fcyfile`` in place.  The
  file is written again, in the format of the front end, when the pass
  lifted a call; else it is left as it is, with its time.  Returns the
  number of calls lifted.
  '''
  prog = fc.load(fcyfile)
  newprog, n = transform_prog(prog)
  if n:
    fc.write(newprog, fcyfile)
  return n
