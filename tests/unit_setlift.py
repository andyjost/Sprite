'''
Tests for the set0 lift of the toolchain
(curry.toolchain.flat2icurry.setlift; decision D28 of 2026-10-12).

The captured variables of the expression of set0 are arguments of the
capsule, boxed at the entry, as the arguments of setk are: set0 e with the
captured variables x1 .. xk is the set function of the lifted operation
L x1 .. xk = e applied to x1 .. xk.  The authority is the paper of
Christiansen, Hanus, Reck and Seidel (PPDP 2013, section 3.3): let x = coin
in allValues x yields {0} and {1}, one set per outside alternative, and
let x = failedBool in allValues x fails instead of yielding a set.  The
compiler makes it so, with a FlatCurry pass that both routes apply to the
FlatCurry file beside the binding optimization; the runtime is unchanged,
since set1 (L x1 .. x(k-1)) xk and setk L x1 .. xk reach one entry state.

TestPass checks the pass on FlatCurry terms.  TestGoals and
TestPinnedValues run the programs of data/curry/SetLift.curry on the
backend of the run, in a child under prlimit and timeout, plain and under
the checker: each program point set0 e with captured variables stands
beside its hand-written lifting setk L xs, and the two give the same
values; the pinned values are those of the probes of the decision.
TestChecker reads the counts of the checker: a closed set0 keeps its
capsule without a box, a lifted one has a box.  TestFiles checks the pass
over the FlatCurry file of the module as the routes apply it: the file,
the interface left alone, the command lines, the staleness of a pair made
before the lift, the hit of the ICurry cache, and the version of the
route.
'''
import cytest # from ./lib; must be first
from curry import cache, config, toolchain
from curry.toolchain import _curry2icurry, _frontend, _system, flat2icurry as f2i
from curry.toolchain.flat2icurry import __main__ as cli
from curry.toolchain.flat2icurry import (
    bindingopt as bo, flatcurry as fc, rewrite, setlift as sl
  )
from curry.utility import filesys
import contextlib, curry, io, os, shutil, tempfile, unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data', 'curry')
MODULE = 'SetLift'
ADDRESS_SPACE = 2 << 30
TIMEOUT = 300

# FlatCurry terms
# ===============
def P(name):
  return fc.prelude(name)

def M(name):
  return ('M', name)

def fcall(name, *args):
  return fc.Comb(fc.FuncCall, name, list(args))

def pcall(name, missing, *args):
  return fc.Comb(fc.FuncPartCall(missing), name, list(args))

def lit(n):
  return fc.Lit(fc.Intc(n))

def var(i):
  return fc.Var(i)

def func(name, args, body, visibility=fc.Public):
  return fc.Func(M(name), len(args), visibility, fc.TVar(0), fc.Rule(args, body))

def prog(*functions):
  return fc.Prog('M', ['Prelude', 'Control.SetFunctions'], [], list(functions), [])

INT = fc.TCons(P('Int'), [])
PLUS = P('_impl#+#Prelude.Num#Prelude.Int')
SET0 = sl.SET0

def set0(e):
  return fcall(SET0, e)

def setk(k, name, *vs):
  return fcall(sl.setk(k), pcall(name, k), *[var(v) for v in vs])

def lifted(name, vs, body):
  return fc.Func(
      M(name), len(vs), fc.Private, sl.lift_type(len(vs)), fc.Rule(list(vs), body)
    )

# The functions of SetLift.curry whose rules hold a set0 over captured
# variables, with the number of program points each holds: nested holds
# two (one inside the other), caseS two (one per branch), and the lambda of
# lam is a function of its own after the front end's lambda lifting.
LIFTED_POINTS = {
    'one': 1, 'two': 1, 'showD': 1, 'freeS': 1, 'sevenP': 1, 'nineP': 1
  , 'nested': 2, 'lam._#lambda1': 1, 'dollar': 1, 'dollar2': 1, 'typed': 1
  , 'caseS': 2, 'letS': 1, 'wrap': 1, 'heap1': 1, 'heap2': 1, 'f0cap': 1
  }

def lifted_names():
  '''The local names of the lifted functions of SetLift, as a set.'''
  return set(
      '%s%s%d' % (name, sl.SUFFIX, i)
          for name, count in LIFTED_POINTS.items() for i in range(count)
    )


class TestPass(cytest.TestCase):
  '''The pass on FlatCurry terms.'''

  def test_captured_vars(self):
    '''
    The variables an expression does not bind, each once, in the order of
    their first occurrence; a variable bound by a let, a free declaration
    or a pattern inside the expression is left out under its binder.
    '''
    self.assertEqual(sl.captured_vars(fcall(PLUS, var(2), var(1))), [2, 1])
    self.assertEqual(sl.captured_vars(fcall(PLUS, var(1), fcall(PLUS, var(2), var(1)))), [1, 2])
    self.assertEqual(sl.captured_vars(lit(1)), [])
    e = fc.Let([(3, fcall(PLUS, var(1), lit(1)))], fcall(PLUS, var(3), var(2)))
    self.assertEqual(sl.captured_vars(e), [1, 2])
    e = fc.Free([4], fcall(P('&>'), fcall(P('=:='), var(4), var(1)), var(4)))
    self.assertEqual(sl.captured_vars(e), [1])
    e = fc.Case(
        fc.Rigid, var(1)
      , [ fc.Branch(fc.Pattern(P('Just'), [5]), fcall(PLUS, var(5), var(2)))
        , fc.Branch(fc.Pattern(P('Nothing'), []), var(3))
        ]
      )
    self.assertEqual(sl.captured_vars(e), [1, 2, 3])
    self.assertEqual(sl.captured_vars(fc.Typed(var(7), INT)), [7])
    self.assertEqual(sl.captured_vars(fc.Or(var(2), var(1))), [2, 1])

  def test_lift_type(self):
    '''A fresh polymorphic scheme over k + 1 variables, as the front end
    writes one.'''
    self.assertEqual(
        sl.lift_type(1)
      , fc.ForallType([(0, fc.KStar), (1, fc.KStar)], fc.FuncType(fc.TVar(0), fc.TVar(1)))
      )
    t = sl.lift_type(3)
    self.assertEqual(t.typevars, [(0, fc.KStar), (1, fc.KStar), (2, fc.KStar), (3, fc.KStar)])
    self.assertEqual(
        t.typeexpr
      , fc.FuncType(fc.TVar(0), fc.FuncType(fc.TVar(1), fc.FuncType(fc.TVar(2), fc.TVar(3))))
      )
    self.assertEqual(fc.show(sl.lift_type(1)), 'ForallType [(0,KStar),(1,KStar)] (FuncType (TVar 0) (TVar 1))')

  def test_set0_call(self):
    '''The saturated call, directly or through $; a partial application
    alone is no call.'''
    call = set0(var(1))
    self.assertIs(sl.set0_call(call), call)
    self.assertEqual(sl.set0_call(fcall(P('$'), pcall(SET0, 1), var(1))), call)
    self.assertIsNone(sl.set0_call(pcall(SET0, 1)))
    self.assertIsNone(sl.set0_call(fcall(P('map'), pcall(SET0, 1), var(1))))
    self.assertIsNone(sl.set0_call(fcall(P('$'), pcall(P('id'), 1), var(1))))
    self.assertIsNone(sl.set0_call(var(1)))

  def test_names(self):
    self.assertTrue(sl.is_lifted_name('f_SET00'))
    self.assertTrue(sl.is_lifted_name('f._#lambda1_SET012'))
    self.assertFalse(sl.is_lifted_name('f_SET0'))
    self.assertFalse(sl.is_lifted_name('f_CASE0'))
    self.assertFalse(sl.is_lifted_name('_SET00'))
    self.assertEqual(sl.setk(3), ('Control.SetFunctions', 'set3'))

  def test_one_variable(self):
    '''f x = set0 (x + 1) becomes f x = set1 f_SET00 x with f_SET00 x = x + 1,
    a private function of a polymorphic type, after f.'''
    body = fcall(P('sortValues'), set0(fcall(PLUS, var(1), lit(1))))
    p = prog(func('f', [1], body))
    q, n = sl.transform_prog(p)
    self.assertEqual(n, 1)
    self.assertEqual(
        q.functions
      , [ func('f', [1], fcall(P('sortValues'), setk(1, M('f_SET00'), 1)))
        , lifted('f_SET00', [1], fcall(PLUS, var(1), lit(1)))
        ]
      )
    self.assertEqual(q.functions[1].visibility, fc.Private)
    self.assertEqual(q.functions[1].arity, 1)
    self.assertEqual(q.functions[1].typeexpr, sl.lift_type(1))
    self.assertEqual((q.imports, q.types, q.operators), (p.imports, p.types, p.operators))
    # Idempotent: the lifted program is given back, with the count zero.
    r, m = sl.transform_prog(q)
    self.assertEqual(m, 0)
    self.assertIs(r, q)
    self.assertIs(sl.optimize_set0(q), q)
    self.assertIsNot(sl.optimize_set0(p), p)
    self.assertEqual(sl.lifted_functions(q), [M('f_SET00')])
    self.assertEqual(sl.lifted_functions(p), [])

  def test_two_variables_in_order(self):
    '''The arguments of the lifted function are the captured variables in
    the order of their first occurrence.'''
    p = prog(func('g', [1, 2], set0(fcall(PLUS, var(2), var(1)))))
    q, n = sl.transform_prog(p)
    self.assertEqual(n, 1)
    self.assertEqual(q.functions[0].rule.body, setk(2, M('g_SET00'), 2, 1))
    self.assertEqual(q.functions[1].rule.args, [2, 1])

  def test_closed_is_unchanged(self):
    '''A set0 without captured variables, and a set0 that is not a
    saturated call, leave the program as it is.'''
    for body in [
        set0(fcall(P('?'), lit(0), lit(1)))
      , set0(fc.Let([(1, lit(0))], var(1)))
      , set0(fc.Free([1], var(1)))
      , fcall(P('map'), pcall(SET0, 1), var(1))
      , fcall(P('$'), pcall(SET0, 1), lit(1))
      , fcall(P('apply'), pcall(SET0, 1), var(1))
      ]:
      p = prog(func('f', [1], body))
      q, n = sl.transform_prog(p)
      self.assertEqual(n, 0, body)
      self.assertIs(q, p, body)

  def test_dollar(self):
    '''set0 $ e is the call set0 e.'''
    p = prog(func('f', [1], fcall(P('$'), pcall(SET0, 1), fcall(PLUS, var(1), lit(1)))))
    q, n = sl.transform_prog(p)
    self.assertEqual(n, 1)
    self.assertEqual(q.functions[0].rule.body, setk(1, M('f_SET00'), 1))

  def test_root_typed_is_stripped(self):
    '''A type annotation at the root of the expression is not in the body
    of the lifted function; one below the root stays.'''
    inner = fc.Typed(fcall(PLUS, var(1), lit(1)), INT)
    p = prog(func('f', [1], set0(fc.Typed(inner, INT))))
    q, n = sl.transform_prog(p)
    self.assertEqual(n, 1)
    self.assertEqual(q.functions[1].rule.body, fcall(PLUS, var(1), lit(1)))
    p = prog(func('f', [1], set0(fcall(P('id'), inner))))
    q, n = sl.transform_prog(p)
    self.assertEqual(q.functions[1].rule.body, fcall(P('id'), inner))

  def test_nested_inner_first(self):
    '''A set0 inside the expression of a set0 is lifted first, so the outer
    lifted function calls the set function of the inner one.'''
    inner = set0(fcall(P('?'), var(1), lit(5)))
    outer = set0(fcall(P('length'), fcall(P('sortValues'), inner)))
    p = prog(func('f', [1], outer))
    q, n = sl.transform_prog(p)
    self.assertEqual(n, 2)
    self.assertEqual([fd.name[1] for fd in q.functions], ['f', 'f_SET00', 'f_SET01'])
    self.assertEqual(q.functions[0].rule.body, setk(1, M('f_SET01'), 1))
    self.assertEqual(q.functions[1].rule.body, fcall(P('?'), var(1), lit(5)))
    self.assertEqual(
        q.functions[2].rule.body
      , fcall(P('length'), fcall(P('sortValues'), setk(1, M('f_SET00'), 1)))
      )
    self.assertEqual(sl.transform_prog(q), (q, 0))

  def test_every_rule(self):
    '''The pass reaches the lambdas of the front end, the bodies of a let
    and of a case, the alternatives of a choice and a free declaration;
    the counter is per enclosing function.'''
    lam = fc.Func(
        M('f._#lambda1'), 2, fc.Private, fc.TVar(0)
      , fc.Rule([1, 2], set0(fcall(PLUS, var(2), var(1))))
      )
    body = fc.Free([3], fc.Let(
        [(4, set0(var(3)))]
      , fc.Case(
          fc.Flex, var(1)
        , [ fc.Branch(fc.Pattern(P('True'), []), fc.Or(set0(var(4)), set0(var(1))))
          , fc.Branch(fc.Pattern(P('False'), []), fcall(P('id'), set0(lit(1))))
          ]
        )
      ))
    p = prog(func('f', [1], body), lam)
    q, n = sl.transform_prog(p)
    self.assertEqual(n, 4)
    self.assertEqual(
        [fd.name[1] for fd in q.functions]
      , ['f', 'f_SET00', 'f_SET01', 'f_SET02', 'f._#lambda1', 'f._#lambda1_SET00']
      )
    expected = fc.Free([3], fc.Let(
        [(4, setk(1, M('f_SET00'), 3))]
      , fc.Case(
          fc.Flex, var(1)
        , [ fc.Branch(
                fc.Pattern(P('True'), [])
              , fc.Or(setk(1, M('f_SET01'), 4), setk(1, M('f_SET02'), 1))
              )
          , fc.Branch(fc.Pattern(P('False'), []), fcall(P('id'), set0(lit(1))))
          ]
        )
      ))
    self.assertEqual(q.functions[0].rule.body, expected)
    self.assertEqual(q.functions[4].rule.body, setk(2, M('f._#lambda1_SET00'), 2, 1))
    self.assertEqual(q.functions[5].rule.args, [2, 1])

  def test_beyond_seven(self):
    '''Eight or more captured variables give set1 over a partial application
    of the lifted function that holds all but the last.'''
    vs = list(range(1, 9))
    e = var(1)
    for v in vs[1:]:
      e = fcall(PLUS, e, var(v))
    p = prog(func('f', vs, set0(e)))
    q, n = sl.transform_prog(p)
    self.assertEqual(n, 1)
    self.assertEqual(
        q.functions[0].rule.body
      , fcall(sl.setk(1), pcall(M('f_SET00'), 1, *[var(v) for v in vs[:-1]]), var(8))
      )
    self.assertEqual(q.functions[1].arity, 8)
    self.assertEqual(q.functions[1].typeexpr, sl.lift_type(8))
    # Seven is the largest arity the library has a set function for.
    p = prog(func('g', vs[:7], set0(e.args[0])))
    q, n = sl.transform_prog(p)
    self.assertEqual(q.functions[0].rule.body, setk(7, M('g_SET00'), *vs[:7]))

  def test_name_collision_is_skipped(self):
    '''A generated name that an original function has is skipped, and the
    counter still advances.'''
    taken = func('f_SET00', [], lit(0))
    p = prog(func('f', [1], set0(var(1))), taken)
    q, n = sl.transform_prog(p)
    self.assertEqual(n, 1)
    self.assertEqual([fd.name[1] for fd in q.functions], ['f', 'f_SET01', 'f_SET00'])
    self.assertEqual(q.functions[0].rule.body, setk(1, M('f_SET01'), 1))

  def test_external_rule(self):
    p = prog(fc.Func(M('ext'), 1, fc.Public, fc.TVar(0), fc.External('ext')))
    self.assertEqual(sl.transform_prog(p), (p, 0))

  def test_rewrite_prog(self):
    '''The rewrite step of the routes: the binding optimization, then the
    lift, with the pair of counts; a program neither pass changes is given
    back.'''
    guard = fc.Case(
        fc.Rigid, fcall(P('_impl#==#Prelude.Eq#Prelude.Int'), var(1), lit(3))
      , [ fc.Branch(fc.Pattern(P('True'), []), set0(var(1)))
        , fc.Branch(fc.Pattern(P('False'), []), bo.FAILED)
        ]
      )
    p = prog(func('f', [1], guard))
    q, counts = f2i.rewrite_prog(p)
    self.assertEqual(counts, (1, 1))
    self.assertEqual(
        q.functions[0].rule.body.scrutinee, fcall(P('constrEq'), var(1), lit(3))
      )
    self.assertEqual(q.functions[0].rule.body.branches[0].body, setk(1, M('f_SET00'), 1))
    self.assertEqual(f2i.rewrite_prog(q), (q, (0, 0)))
    closed = prog(func('f', [1], set0(lit(1))))
    self.assertEqual(f2i.rewrite_prog(closed), (closed, (0, 0)))
    self.assertEqual(rewrite.describe((0, 0)), 'unchanged')
    self.assertEqual(rewrite.describe((1, 1)), '1 equality replaced, 1 set0 call lifted')
    self.assertEqual(rewrite.describe((0, 2)), '2 set0 calls lifted')


# Curry programs
# ==============
# Evaluates goals of the test module and prints one line per goal: its name
# and the sorted values as Curry text, or the name of the error.
CHILD = '''
import cytest, curry
curry.reset(**%(flags)r)
M = curry.import_(%(module)r)
for name in %(goals)r:
  try:
    values = cytest.raw.values(getattr(M, name))
    print(name, sorted(str(value) for value in values))
  except Exception as exc:
    print(name, 'error', type(exc).__name__, str(exc))
'''

# Evaluates goals under the checker and prints, per goal, the sorted values
# and the counts of the capsules and of the capsules without a box.  The
# checker of the Python backend keeps no count of the capsules without a
# box; the line then says None for it.
COUNTS_CHILD = '''
import cytest, curry
curry.reset(**%(flags)r)
M = curry.import_(%(module)r)
if curry.flags['backend'] == 'cxx':
  from curry.backends.cxx import curryrtbindings as cb
  def run(goal):
    rts = cb.RuntimeState(cytest.raw.interp(), cytest.raw.expr(goal))
    values = sorted(str(v) for v in rts.generate_values())
    counts = dict(cb.checker_counts(rts))
    return values, counts.get('capsules', 0), counts.get('capsules_without_box', 0)
else:
  from curry.backends.py.eval.rts import RuntimeState
  def run(goal):
    rts = RuntimeState(cytest.raw.interp(), cytest.raw.expr(goal))
    values = sorted(str(v) for v in rts.generate_values())
    return values, rts.checker.counts.get('capsules', 0), None
for name in %(goals)r:
  print(name, repr(run(getattr(M, name))))
'''

def run_child(goals, code=CHILD, **flags):
  '''
  Evaluates ``goals`` in a child on the backend of this test process and
  returns a dict from the name to the sorted list of values (as text), to
  the error line, or to the tuple the counts child prints.  A child that
  does not end fails the test.
  '''
  flags.setdefault('backend', curry.flags['backend'])
  text = code % {'flags': flags, 'goals': list(goals), 'module': MODULE}
  proc = cytest.run_in_subprocess(text, TIMEOUT, address_space=ADDRESS_SPACE)
  if proc.returncode != 0:
    raise AssertionError(
        'the child ended with status %s; stdout:\n%s\nstderr:\n%s'
            % (proc.returncode, proc.stdout, proc.stderr)
      )
  results = {}
  for line in proc.stdout.splitlines():
    name, _, rest = line.partition(' ')
    results[name] = eval(rest) if rest[:1] in '[(' else rest
  return results


class GoalsCase(cytest.TestCase):
  '''Two children per class, plain and under the checker; a test reads the
  values of one goal from both.'''
  EXPECTED = {}

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    # Compile the module here; the children load it from the cache.
    curry.import_(MODULE)
    cls.results = run_child(cls.EXPECTED)
    cls.checked = run_child(cls.EXPECTED, checker=True)

  def check(self, goal):
    # The children sort the values as text; the expectations are written in
    # the order of the values and sorted here.
    expected = sorted(self.EXPECTED[goal])
    self.assertEqual(self.results[goal], expected, goal)
    self.assertEqual(self.checked[goal], expected, goal + ' under the checker')

  def parity(self, lifted, hand):
    '''The program point set0 e and its hand-written lifting agree.'''
    self.check(lifted)
    self.check(hand)
    self.assertEqual(self.results[lifted], self.results[hand], (lifted, hand))


class TestGoals(GoalsCase):
  '''
  The parity corpus: one captured variable (one), two (two), a class
  dictionary (dictS: show over a Show-constrained parameter), a free
  variable of the enclosing where (freeS; one set per binding, as s6PG of
  SetFunctionsSemantics.curry), seven captured variables (set7) and nine
  (beyond the arities of the library: set1 over a partial application),
  a nested set0 (nested), a set0 inside a lambda (lam), set0 $ e (dollar,
  dollar2), a root type annotation (typed), set0 in the branches of a case
  and under a let (caseS, letS), the wrapper of the paper applied to a
  choice (wrapc: one set per alternative, by call-time choice), a free
  variable declared inside the expression (innerFree: closed), a closed
  set0 (closed) and the limit of the lift, set0 as a partial application
  (partial: the element reaches set0 as a closed expression).
  '''
  EXPECTED = {
      'one': ['[1]', '[2]']
    , 'oneL': ['[1]', '[2]']
    , 'two': ['[10]', '[11]', '[20]', '[21]']
    , 'twoL': ['[10]', '[11]', '[20]', '[21]']
    , 'dictS': ['["0"]', '["1"]']
    , 'dictSL': ['["0"]', '["1"]']
    , 'freeS': ['[False]', '[True]']
    , 'freeSL': ['[False]', '[True]']
    , 'innerFree': ['[0, 1]']
    , 'seven': ['[21]', '[22]']
    , 'sevenL': ['[21]', '[22]']
    , 'nine': ['[36]', '[37]']
    , 'nineL': ['[36]', '[37]']
    , 'nested': ['[2]', '[2]']
    , 'nestedL': ['[2]', '[2]']
    , 'lam': ['[[1], [2]]', '[[11], [12]]']
    , 'lamL': ['[[1], [2]]', '[[11], [12]]']
    , 'dollar': ['[1]', '[2]']
    , 'dollar2': ['[1]', '[2]']
    , 'typed': ['[1]', '[2]']
    , 'caseS0': ['[1]']
    , 'caseS3': ['[3]', '[4]']
    , 'letS': ['[1]', '[2]']
    , 'wrapc': ['[0]', '[1]']
    , 'wrapcL': ['[0]', '[1]']
    , 'closed': ['[0, 1]']
    , 'partial': ['[[0, 1]]']
    }

  def test_one(self): self.parity('one', 'oneL')
  def test_two(self): self.parity('two', 'twoL')
  def test_dictionary(self): self.parity('dictS', 'dictSL')
  def test_free_variable(self): self.parity('freeS', 'freeSL')
  def test_inner_free_variable(self): self.check('innerFree')
  def test_seven(self): self.parity('seven', 'sevenL')
  def test_nine(self): self.parity('nine', 'nineL')
  def test_nested(self): self.parity('nested', 'nestedL')
  def test_lambda(self): self.parity('lam', 'lamL')
  def test_dollar(self):
    self.parity('dollar', 'oneL')
    self.parity('dollar2', 'oneL')
  def test_typed(self): self.parity('typed', 'oneL')
  def test_case_and_let(self):
    self.check('caseS0')
    self.check('caseS3')
    self.parity('letS', 'oneL')
  def test_wrapper(self): self.parity('wrapc', 'wrapcL')
  def test_closed(self): self.check('closed')
  def test_partial_application_is_a_limit(self): self.check('partial')


class TestPinnedValues(GoalsCase):
  '''
  The probes of decision D28, with the values the decision fixes: a
  captured variable that fails fails the set function (heap1, f0cap: no
  value; before the lift the set was empty), a captured choice gives one
  set per alternative (heap2; before, one set), a closed expression that
  fails gives the empty set (s0idf, s0f), the failing function value of
  set1 fails (s1f1), a closed choice gives one set (s0c), the choice as the
  argument of set1 gives one set per alternative (s1idc), and the wrapper
  of the paper applied to a choice gives one set per alternative (wrapc).
  '''
  EXPECTED = {
      'heap1': []
    , 'heap2': ['[0]', '[1]']
    , 'f0cap': []
    , 's0idf': ['[]']
    , 's0f': ['[]']
    , 's1f1': []
    , 's0c': ['[0, 1]']
    , 's1idc': ['[0]', '[1]']
    , 'wrapc': ['[0]', '[1]']
    }

  def test_heap1(self): self.check('heap1')
  def test_heap2(self): self.check('heap2')
  def test_f0cap(self): self.check('f0cap')
  def test_s0idf(self): self.check('s0idf')
  def test_s0f(self): self.check('s0f')
  def test_s1f1(self): self.check('s1f1')
  def test_s0c(self): self.check('s0c')
  def test_s1idc(self): self.check('s1idc')
  def test_wrapc(self): self.check('wrapc')

  def test_capture_against_closed(self):
    '''The captured variable and the closed expression differ as the
    paper says: the one fails the set function, the other gives a set.'''
    self.assertEqual(self.results['heap1'], [])
    self.assertEqual(self.results['s0idf'], ['[]'])
    self.assertEqual(self.results['heap2'], self.results['s1idc'])
    self.assertNotEqual(self.results['heap2'], self.results['s0c'])


class TestChecker(cytest.TestCase):
  '''The entry walk of the checker: a closed set0 is a capsule without a
  box (the count capsules_without_box of the C++ checker), and a lifted
  set0 has its box, as setk has.'''

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    curry.import_(MODULE)
    cls.counts = run_child(['closed', 'one', 'heap2'], code=COUNTS_CHILD, checker=True)

  def test_closed_capsule_has_no_box(self):
    values, capsules, without_box = self.counts['closed']
    self.assertEqual(values, ['[0, 1]'])
    self.assertEqual(capsules, 1)
    if curry.flags['backend'] == 'cxx':
      self.assertEqual(without_box, 1)

  def test_lifted_capsule_has_a_box(self):
    for goal, expected in [('one', ['[1]', '[2]']), ('heap2', ['[0]', '[1]'])]:
      values, capsules, without_box = self.counts[goal]
      self.assertEqual(values, expected, goal)
      self.assertGreaterEqual(capsules, 1, goal)
      if curry.flags['backend'] == 'cxx':
        self.assertEqual(without_box, 0, goal)


# FlatCurry files
# ===============
def readbytes(filename):
  with open(filename, 'rb') as istream:
    return istream.read()

def snapshot(filename):
  '''The bytes and the modification time of a file.'''
  return readbytes(filename), os.stat(filename).st_mtime_ns

def quoted(name):
  return ('"%s"' % name).encode('utf-8')


class TestFiles(cytest.TestCase):
  '''
  The pass over the FlatCurry file of SetLift as the routes apply it.  The
  files come from the front end, in a scratch directory, without the
  ICurry cache unless a test names one.
  '''

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    if config.curry_frontend() is None:
      raise unittest.SkipTest('the Curry front end is not configured')

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, self.tmpdir, True)
    self.set_cache_file('')
    _curry2icurry.reset_counts()
    self.addCleanup(_curry2icurry.reset_counts)
    self.curryfile = os.path.join(self.tmpdir, MODULE + '.curry')
    shutil.copy(os.path.join(DATA, MODULE + '.curry'), self.curryfile)

  def set_cache_file(self, filename):
    patcher = mock.patch.dict(os.environ, {'SPRITE_CACHE_FILE': filename})
    patcher.start()
    self.addCleanup(patcher.stop)
    cache.reset()
    self.addCleanup(cache.reset)

  def fresh_flatcurry(self):
    '''
    The FlatCurry of the module as the front end writes it, without the
    rewrite step a run of the routes applies to every file it wrote.
    '''
    old = _frontend.flatcurryfile(self.curryfile)
    if os.path.exists(old):
      os.unlink(old)
    return _frontend.curry2flat(self.curryfile, [self.tmpdir], quiet=True, rewrite=False)

  def pre_rewrite_pair(self):
    '''
    The products of the module as a route made them before the lift
    existed: the FlatCurry file of the front end, its plain translation,
    and the copies of the interfaces beside the ICurry file.  Both files
    are newer than the source, so the pair is current by the times.
    '''
    fcy = self.fresh_flatcurry()
    icy = toolchain.icurryfilename(self.curryfile)
    os.makedirs(os.path.dirname(icy), exist_ok=True)
    _frontend.flat2icy(fcy, icy, _frontend.searchdirs(self.curryfile, [self.tmpdir]))
    converter = _curry2icurry.Curry2ICurryConverter(curry2icurry='frontend')
    converter.place_interfaces(self.curryfile, icy)
    cache.write_file(icy + '.source', _curry2icurry.source_digest(self.curryfile))
    self.assertNotIn(sl.SUFFIX.encode('utf-8'), readbytes(fcy))
    self.assertNotIn(sl.SUFFIX.encode('utf-8'), readbytes(icy))
    self.assertTrue(filesys.newer(icy, self.curryfile))
    self.assertTrue(filesys.newer(fcy, self.curryfile))
    return fcy, icy

  def convert(self, **kwds):
    kwds.setdefault('curry2icurry', 'frontend')
    kwds.setdefault('quiet', True)
    return toolchain.curry2icurry(self.curryfile, [self.tmpdir], **kwds)

  def no_front_end(self):
    '''Fails the test when the front end runs from here on.'''
    frontend = config.curry_frontend()
    real = _system.pexec
    def pexec(cmd, *args, **kwds):
      if cmd[0] == frontend:
        raise AssertionError('the front end ran: %s' % ' '.join(cmd))
      return real(cmd, *args, **kwds)
    patcher = mock.patch.object(_system, 'pexec', pexec)
    patcher.start()
    self.addCleanup(patcher.stop)

  def test_transform_prog(self):
    '''
    The pass over the program of the front end: one lifted function per
    program point, private, of the polymorphic type, with the captured
    variables as its parameters; the root annotation of typed stripped;
    the closed points unchanged; idempotent; and the lifted program
    survives the writer and the reader.
    '''
    prog = fc.load(self.fresh_flatcurry())
    lifted, n = sl.transform_prog(prog)
    self.assertEqual(n, sum(LIFTED_POINTS.values()))
    names = {fd.name[1]: fd for fd in lifted.functions}
    new = set(names) - set(fd.name[1] for fd in prog.functions)
    self.assertEqual(new, lifted_names())
    self.assertEqual(set(n for _, n in sl.lifted_functions(lifted)), new)
    for name in new:
      fd = names[name]
      self.assertEqual(fd.visibility, fc.Private, name)
      self.assertEqual(fd.typeexpr, sl.lift_type(fd.arity), name)
      self.assertEqual(len(fd.rule.args), fd.arity, name)
      self.assertNotIsInstance(fd.rule.body, fc.Typed, name)
      self.assertEqual(sl.captured_vars(fd.rule.body), fd.rule.args, name)
    # The dictionary of showD is its first parameter, the free variable of
    # freeS its one parameter, and the lambda of lam captures y before z.
    self.assertEqual(names['showD_SET00'].arity, 2)
    self.assertEqual(names['freeS_SET00'].arity, 1)
    self.assertEqual(names['lam._#lambda1_SET00'].arity, 2)
    self.assertEqual(names['nineP_SET00'].arity, 9)
    self.assertEqual(names['sevenP_SET00'].arity, 7)
    nine = names['nineP'].rule.body
    self.assertTrue(sl.contains_set0(prog.functions[[fd.name[1] for fd in prog.functions].index('nineP')].rule.body))
    self.assertFalse(sl.contains_set0(nine))
    # The call of nineP: set1 over a partial application of eight.
    text = fc.show(lifted)
    self.assertIn(
        'Comb FuncCall ("Control.SetFunctions","set1") [Comb (FuncPartCall 1) '
        '("SetLift","nineP_SET00") [Var 1,Var 2,Var 3,Var 4,Var 5,Var 6,Var 7,Var 8],Var 9]'
      , text
      )
    self.assertIn('Comb FuncCall ("Control.SetFunctions","set7") [Comb (FuncPartCall 7) ("SetLift","sevenP_SET00") []', text)
    self.assertIn('Comb FuncCall ("Control.SetFunctions","set2") [Comb (FuncPartCall 2) ("SetLift","showD_SET00") []', text)
    for name in ['closed', 'innerFree', 'partial', 's0idf', 's0f', 's0c']:
      self.assertNotIn(name + sl.SUFFIX, names, name)
    self.assertEqual(sl.transform_prog(lifted), (lifted, 0))
    self.assertTrue(fc.read(text) == lifted)

  def test_optimize_file(self):
    '''
    The file is written again when a call was lifted: the lifted program,
    in the format of the front end.  The interface files beside it keep
    their bytes and their times.  A second run lifts nothing and leaves
    the file alone, time included.
    '''
    fcy = self.fresh_flatcurry()
    fint = _frontend.interfacefile(self.curryfile, '.fint')
    icurry = _frontend.interfacefile(self.curryfile, '.icurry')
    before = snapshot(fcy)
    interfaces = snapshot(fint), snapshot(icurry)
    self.assertNotIn(sl.SUFFIX.encode('utf-8'), before[0])
    self.assertEqual(sl.optimize_file(fcy), sum(LIFTED_POINTS.values()))
    after, mtime = snapshot(fcy)
    self.assertNotEqual(after, before[0])
    for name in lifted_names():
      self.assertIn(quoted(name), after, name)
    self.assertTrue(after.startswith(b'Prog "SetLift" ["Prelude","Control.SetFunctions"] '))
    self.assertFalse(after.endswith(b'\n'))
    prog = fc.load(fcy)
    self.assertEqual(fc.show(prog).encode('utf-8'), after)
    self.assertEqual(prog, sl.optimize_set0(fc.read(before[0].decode('utf-8'))))
    self.assertEqual(sl.optimize_file(fcy), 0)
    self.assertEqual(snapshot(fcy), (after, mtime))
    self.assertEqual((snapshot(fint), snapshot(icurry)), interfaces)
    self.assertNotIn(sl.SUFFIX.encode('utf-8'), readbytes(fint))
    # The step of the routes over the same file: both passes, one write.
    fcy = self.fresh_flatcurry()
    self.assertEqual(f2i.rewrite_file(fcy), (0, sum(LIFTED_POINTS.values())))
    self.assertEqual(readbytes(fcy), after)
    self.assertEqual(f2i.rewrite_file(fcy), (0, 0))

  def test_command_lines(self):
    '''
    The rewrite command lifts the file in place and reports the count;
    --rewrite of the translation applies the step in memory and leaves the
    file alone, and the rewritten file translates to the text of the
    option.
    '''
    fcy = self.fresh_flatcurry()
    before = snapshot(fcy)
    importdirs = [self.tmpdir, config.system_curry_path()]
    texts = {}
    for flag in (), ('--rewrite',):
      out = os.path.join(self.tmpdir, MODULE + '.icy')
      argv = list(flag) + ['-o', out, fcy]
      for directory in importdirs:
        argv[:0] = ['-i', directory]
      self.assertEqual(cli.main(argv), 0)
      texts[flag] = readbytes(out)
    self.assertNotIn(sl.SUFFIX.encode('utf-8'), texts[()])
    self.assertIn(quoted('one_SET00'), texts[('--rewrite',)])
    self.assertEqual(snapshot(fcy), before)
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
      self.assertEqual(rewrite.main([fcy]), 0)
    self.assertEqual(
        stdout.getvalue(), '%s: %d set0 calls lifted\n' % (fcy, sum(LIFTED_POINTS.values()))
      )
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
      self.assertEqual(rewrite.main([fcy]), 0)
    self.assertEqual(stdout.getvalue(), '%s: unchanged\n' % fcy)
    argv = ['-o', out, fcy]
    for directory in importdirs:
      argv[:0] = ['-i', directory]
    self.assertEqual(cli.main(argv), 0)
    self.assertEqual(readbytes(out), texts[('--rewrite',)])

  def test_pre_lift_pair_is_stale(self):
    '''
    A pair translated before the lift is stale: the route runs the step
    again at the next conversion, the file and the ICurry hold the lifted
    functions, and the pair is current then.  A FlatCurry file of the
    front end written again beside the lifted ICurry (the PAKCS oracle
    does so) is current: the product is right.
    '''
    fcy, icy = self.pre_rewrite_pair()
    self.assertTrue(_curry2icurry.translated_before_rewrite(self.curryfile, icy))
    self.assertTrue(_curry2icurry.icurry_is_stale(icy))
    self.assertIn(os.path.abspath(icy), _curry2icurry.stale_pairs)
    self.assertEqual(self.convert(), icy)
    for name in lifted_names():
      self.assertIn(quoted(name), readbytes(fcy), name)
      self.assertIn(quoted(name), readbytes(icy), name)
    self.assertFalse(_curry2icurry.translated_before_rewrite(self.curryfile, icy))
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))
    self.assertEqual(_curry2icurry.pairs_refreshed(), 1)
    # The oracle's case: the front end alone writes the file again.
    os.unlink(fcy)
    _system.pexec(
        _frontend.command(self.curryfile, [self.tmpdir], quiet=True), cwd=self.tmpdir
      )
    self.assertNotIn(sl.SUFFIX.encode('utf-8'), readbytes(fcy))
    self.assertTrue(filesys.newer(fcy, icy))
    self.assertFalse(_curry2icurry.translated_before_rewrite(self.curryfile, icy))
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))
    # A pair the lift cannot judge by its spelling: without set0 in the
    # text there is nothing to lift.
    plain = os.path.join(self.tmpdir, 'Plain.curry')
    with open(plain, 'w', encoding='utf-8') as ostream:
      ostream.write('module Plain where\nmain :: Int\nmain = 3\n')
    plainicy = toolchain.curry2icurry(plain, [self.tmpdir], curry2icurry='frontend', quiet=True)
    self.assertNotIn(_curry2icurry.SET0_NAME, readbytes(_frontend.flatcurryfile(plain)))
    self.assertFalse(_curry2icurry.translated_before_rewrite(plain, plainicy))

  def test_cache_hit_lifts_the_file(self):
    '''
    A hit of the ICurry cache on a module whose FlatCurry file holds an
    unlifted set0 leaves the file lifted, byte for byte the text a
    translation writes, and the ICurry of the cache holds the lifted
    functions.
    '''
    self.set_cache_file(os.path.join(self.tmpdir, 'cache', 'icurry.db'))
    icy = self.convert(use_cache=True)
    fcy = _frontend.flatcurryfile(self.curryfile)
    lifted = readbytes(fcy)
    self.assertIn(quoted('one_SET00'), lifted)
    self.pre_rewrite_pair()
    _curry2icurry.reset_counts()
    self.assertTrue(_curry2icurry.icurry_is_stale(icy))
    self.no_front_end()
    stats = dict(cache.Curry2ICurryCache.stats)
    self.assertEqual(self.convert(use_cache=True), icy)
    self.assertEqual(cache.Curry2ICurryCache.stats['hit'], stats['hit'] + 1)
    self.assertEqual(readbytes(fcy), lifted)
    self.assertIn(quoted('one_SET00'), readbytes(icy))
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))
    self.assertEqual(_curry2icurry.pairs_served(), 1)
    self.assertEqual(_curry2icurry.pairs_refreshed(), 0)
    # The function alone: a second run lifts nothing.
    self.assertEqual(_curry2icurry.rewrite_on_hit(self.curryfile), 0)
    self.assertEqual(readbytes(fcy), lifted)

  def test_route_version(self):
    '''The lift joined the step with version 2 of the route, in the key of
    the ICurry cache.'''
    self.assertEqual(_frontend.ROUTE_VERSION, 2)
    self.assertEqual(cache.route_version(), 2)
    self.assertIn('setlift.py', cache.REWRITE_SOURCES)
    key = lambda: cache.icurry_cache_key(self.curryfile, [self.tmpdir], (), 'frontend')
    now = key()
    with mock.patch.object(_frontend, 'ROUTE_VERSION', 1):
      self.assertNotEqual(key(), now)
    self.assertEqual(key(), now)


if __name__ == '__main__':
  unittest.main()
