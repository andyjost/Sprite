'''
Tests for the binding optimization of the build route
(curry.toolchain.flat2icurry.bindingopt) and for the programs of issue #37.

PAKCS runs the tool transbooleq over every FlatCurry file it compiles (the
property bindingoptimization, fast by default): a Boolean equality whose
value is required to be True becomes an equational constraint.  The
sendMoreMoney program of the test data binds its digits through (==) in a
guard, and PAKCS solves it for that reason alone; with
-Dbindingoptimization=no PAKCS suspends, as Sprite did.  The build route
applies the same pass now.  The expected values of the programs below were
taken from PAKCS 3.4.1 with its default settings.

TestPass checks the pass on FlatCurry terms.  TestRoute compiles Curry text
through the build route and evaluates it on the backend of the run.  The two
defects of the Python backend found with the program, in the order of the
suspension of a primitive and in ($##) over a bound variable, are tested in
unit_py_residuation.py.
'''
import cytest # from ./lib; must be first
from curry.exceptions import EvaluationSuspended
from curry.toolchain import flat2icurry as f2i
from curry.toolchain.flat2icurry import __main__ as cli
from curry.toolchain.flat2icurry import (
    bindingopt as bo, flatcurry as fc, icurrytypes as ic, terms
  )
from curry import config
import curry, glob, os, shutil, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, 'data', 'curry')
SEND_MORE_MONEY = os.path.join(DATA, 'sendMoreMoney.curry')
# Where the FlatCurry interfaces of the library modules may be found: the
# Curry library of the installation, and the source tree when the front end
# wrote them there (make -C curry interfaces).
LIBRARY_DIRS = [config.system_curry_path(), os.path.join(ROOT, 'curry', 'lib')]

# FlatCurry terms
# ===============
def P(name):
  return fc.prelude(name)

def M(name):
  return ('M', name)

def fcall(name, *args):
  return fc.Comb(fc.FuncCall, name, list(args))

def ccall(name, *args):
  return fc.Comb(fc.ConsCall, name, list(args))

def pcall(name, missing, *args):
  return fc.Comb(fc.FuncPartCall(missing), name, list(args))

def lit(n):
  return fc.Lit(fc.Intc(n))

X, Y, D = fc.Var(1), fc.Var(2), fc.Var(3)
EQ_INT = P('_impl#==#Prelude.Eq#Prelude.Int')
NE_INT = P('_impl#/=#Prelude.Eq#Prelude.Int')
TRUE_PAT = fc.Pattern(P('True'), [])
FALSE_PAT = fc.Pattern(P('False'), [])
TRUE = ccall(P('True'))

def eq(a, b):
  return fcall(EQ_INT, a, b)

def ne(a, b):
  return fcall(NE_INT, a, b)

def constr(a, b):
  return fcall(P('constrEq'), a, b)

def guard(cond, e):
  '''The case the front end writes for a guard without a fallback.'''
  return fc.Case(
      fc.Rigid, cond, [fc.Branch(TRUE_PAT, e), fc.Branch(FALSE_PAT, bo.FAILED)]
    )

def func(name, args, body):
  return fc.Func(M(name), len(args), fc.Public, fc.TVar(0), fc.Rule(args, body))

def prog(*functions):
  return fc.Prog('M', ['Prelude'], [], list(functions), [])

# A stand-in for the Prelude interface with the entities the tests use.
BOOL = fc.Type(P('Bool'), fc.Public, [], [
    fc.Cons(P('False'), 0, fc.Public, []), fc.Cons(P('True'), 0, fc.Public, [])
  ])
def pfunc(name, arity):
  return fc.Func(P(name), arity, fc.Public, fc.TVar(0), fc.Rule([], fc.Var(0)))
PRELUDE = fc.Prog(
    'Prelude', [], [BOOL]
  , [pfunc('failed', 0), pfunc('constrEq', 2), pfunc(EQ_INT[1], 2)], []
  )

class TestPass(cytest.TestCase):
  '''The pass on FlatCurry terms.'''

  def transformed(self, e, reqval=bo.ANY, **kwds):
    return bo.transform_exp(e, reqval, **kwds)

  def test_guard(self):
    '''The condition of a rule is required True.'''
    self.assertEqual(
        self.transformed(guard(eq(X, lit(3)), X))
      , (guard(constr(X, lit(3)), X), 1)
      )

  def test_guard_with_the_failing_branch_first(self):
    e = fc.Case(
        fc.Rigid, eq(X, lit(3))
      , [fc.Branch(FALSE_PAT, bo.FAILED), fc.Branch(TRUE_PAT, X)]
      )
    out, n = self.transformed(e)
    self.assertEqual(n, 1)
    self.assertEqual(out.scrutinee, constr(X, lit(3)))

  def test_if_then_else_is_kept(self):
    '''Both branches live: nothing is required of the scrutinee.'''
    e = fc.Case(
        fc.Rigid, eq(X, lit(3))
      , [fc.Branch(TRUE_PAT, X), fc.Branch(FALSE_PAT, lit(0))]
      )
    self.assertEqual(self.transformed(e), (e, 0))

  def test_conjunctions_in_a_guard(self):
    for conj in '&&', '&':
      with self.subTest(conj=conj):
        e = guard(fcall(P(conj), eq(X, lit(1)), eq(Y, lit(2))), ccall(P('(,)'), X, Y))
        self.assertEqual(
            self.transformed(e)
          , ( guard(
                  fcall(P(conj), constr(X, lit(1)), constr(Y, lit(2)))
                , ccall(P('(,)'), X, Y)
                )
            , 2
            )
          )

  def test_concurrent_conjunction_as_a_value(self):
    '''(&) requires both arguments True whatever its result is required.'''
    e = fcall(P('&'), eq(X, lit(1)), eq(Y, lit(2)))
    self.assertEqual(
        self.transformed(e), (fcall(P('&'), constr(X, lit(1)), constr(Y, lit(2))), 2)
      )

  def test_boolean_conjunction_as_a_value_is_kept(self):
    e = fcall(P('&&'), eq(X, lit(1)), TRUE)
    self.assertEqual(self.transformed(e), (e, 0))

  def test_disjunction_is_kept(self):
    e = guard(fcall(P('||'), eq(X, lit(3)), eq(X, lit(4))), X)
    self.assertEqual(self.transformed(e), (e, 0))

  def test_negated_disequality(self):
    '''not requires its argument False, and a disequality required False is
    the negated constraint.'''
    e = guard(fcall(P('not'), ne(X, lit(3))), X)
    self.assertEqual(
        self.transformed(e)
      , (guard(fcall(P('not'), fcall(P('not'), constr(X, lit(3)))), X), 1)
      )

  def test_disequality_in_a_guard_is_kept(self):
    e = guard(ne(X, lit(3)), X)
    self.assertEqual(self.transformed(e), (e, 0))

  def test_solve(self):
    e = guard(fcall(P('solve'), eq(X, lit(3))), X)
    self.assertEqual(self.transformed(e), (guard(fcall(P('solve'), constr(X, lit(3))), X), 1))

  def test_not_as_a_value(self):
    '''
    not as a value requires True or False of its argument, the join of the
    two entries of the table, which requires nothing of the arguments of
    the call below it: (&) and solve under not keep their equalities, as
    under PAKCS (lubAType joins two constructors to a set, not to AnyC).
    '''
    e = fcall(P('not'), fcall(P('&'), eq(X, lit(1)), eq(Y, lit(2))))
    self.assertEqual(self.transformed(e), (e, 0))
    e = fcall(P('not'), fcall(P('solve'), eq(X, lit(3))))
    self.assertEqual(self.transformed(e), (e, 0))
    # not (not e) requires nothing of e, and (&) under no requirement
    # requires True of both arguments.
    e = fcall(P('not'), fcall(P('not'), fcall(P('&'), eq(X, lit(1)), eq(Y, lit(2)))))
    self.assertEqual(
        self.transformed(e)
      , ( fcall(P('not'), fcall(P('not'), fcall(P('&'), constr(X, lit(1)), constr(Y, lit(2)))))
        , 2
        )
      )

  def test_lub(self):
    T, F, A, C = P('True'), P('False'), bo.ANY, bo.ANYC
    both = frozenset([T, F])
    self.assertEqual(bo.lub(T, T), T)
    self.assertEqual(bo.lub(T, F), both)
    self.assertEqual(bo.lub(both, T), both)
    self.assertEqual(bo.lub(both, both), both)
    self.assertEqual(bo.lub(T, C), C)
    self.assertEqual(bo.lub(both, C), C)
    self.assertEqual(bo.lub(C, A), A)
    self.assertEqual(bo.lub(both, A), A)
    self.assertEqual(bo.constructors(T), frozenset([T]))
    self.assertEqual(bo.constructors(both), both)

  def test_dollar(self):
    '''f $ x with a partial application f is reduced to the call first.'''
    e = guard(fcall(P('$'), pcall(P('solve'), 1), eq(X, lit(3))), X)
    self.assertEqual(
        self.transformed(e), (guard(fcall(P('solve'), constr(X, lit(3))), X), 1)
      )
    # id requires nothing of its argument: the equality stays.
    e = guard(fcall(P('$'), pcall(P('id'), 1), eq(X, lit(3))), X)
    self.assertEqual(self.transformed(e), (guard(fcall(P('id'), eq(X, lit(3))), X), 0))

  def test_class_method_through_apply(self):
    '''A method applied to a dictionary and then to the operands.'''
    e = guard(fcall(P('apply'), fcall(P('apply'), fcall(P('=='), D), X), Y), TRUE)
    self.assertEqual(self.transformed(e), (guard(constr(X, Y), TRUE), 1))
    # A default instance method without a dictionary.
    e = guard(fcall(P('apply'), fcall(P('apply'), fcall(EQ_INT), X), Y), TRUE)
    self.assertEqual(self.transformed(e), (guard(constr(X, Y), TRUE), 1))
    # A partial application under apply is not the shape.
    e = guard(fcall(P('apply'), pcall(EQ_INT, 1, X), lit(3)), X)
    self.assertEqual(self.transformed(e), (e, 0))

  def test_instance_with_dictionary_arguments(self):
    '''The operands are the last two arguments of an instance method.'''
    e = guard(fcall(P('_impl#==#Prelude.Eq#[]'), D, X, Y), X)
    self.assertEqual(self.transformed(e), (guard(constr(X, Y), X), 1))

  def test_data_equality(self):
    for name in P('==='), ('M', '_impl#===#Prelude.Data#M.T'):
      with self.subTest(name=name):
        e = guard(fcall(name, X, Y), X)
        self.assertEqual(self.transformed(e), (guard(constr(X, Y), X), 1))
    e = guard(fcall(P('not'), fcall(P('/=='), X, Y)), X)
    self.assertEqual(
        self.transformed(e)
      , (guard(fcall(P('not'), fcall(P('not'), constr(X, Y))), X), 1)
      )

  def test_equivalence_off(self):
    '''Without equivalence, == stays and === goes, as under -s.'''
    e = guard(eq(X, lit(3)), X)
    self.assertEqual(self.transformed(e, equivalence=False), (e, 0))
    e = guard(fcall(P('==='), X, lit(3)), X)
    self.assertEqual(
        self.transformed(e, equivalence=False), (guard(constr(X, lit(3)), X), 1)
      )

  def test_let_binding_is_not_required(self):
    '''The pass does not look through a let: the binding gets no
    requirement, and the scrutinee is a variable.'''
    e = fc.Let([(4, eq(X, lit(3)))], guard(fc.Var(4), X))
    self.assertEqual(self.transformed(e), (e, 0))

  def test_free_or_typed_pass_the_requirement_through(self):
    inner = guard(eq(X, lit(3)), X)
    expected = guard(constr(X, lit(3)), X)
    self.assertEqual(self.transformed(fc.Free([1], inner)), (fc.Free([1], expected), 1))
    self.assertEqual(
        self.transformed(fc.Or(inner, inner)), (fc.Or(expected, expected), 2)
      )
    texp = fc.TCons(P('Int'), [])
    self.assertEqual(self.transformed(fc.Typed(inner, texp)), (fc.Typed(expected, texp), 1))

  def test_case_arg_type(self):
    self.assertEqual(bo.case_arg_type(guard(X, X).branches), P('True'))
    just = fc.Branch(fc.Pattern(P('Just'), [5]), fc.Var(5))
    nothing = fc.Branch(fc.Pattern(P('Nothing'), []), bo.FAILED)
    self.assertEqual(bo.case_arg_type([just, nothing]), P('Just'))
    self.assertEqual(bo.case_arg_type([nothing, just]), P('Just'))
    self.assertEqual(bo.case_arg_type([just, fc.Branch(fc.Pattern(P('Nothing'), []), X)]), bo.ANY)
    self.assertEqual(bo.case_arg_type([fc.Branch(fc.LPattern(fc.Intc(1)), X)]), bo.ANY)

  def test_required_argument_values(self):
    T, F, A = P('True'), P('False'), bo.ANY
    rav = bo.required_argument_values
    self.assertEqual(rav(P('&&'), T, 2), [T, T])
    self.assertEqual(rav(P('&&'), F, 2), [A, A])
    self.assertEqual(rav(P('&&'), A, 2), [A, A])
    self.assertEqual(rav(P('&'), A, 2), [T, T])
    self.assertEqual(rav(P('&'), T, 2), [T, T])
    self.assertEqual(rav(P('not'), T, 1), [F])
    # The join of the two entries of not is the set of True and False, and
    # a set requires nothing below it.
    both = frozenset([T, F])
    self.assertEqual(rav(P('not'), A, 1), [both])
    self.assertEqual(rav(P('not'), both, 1), [A])
    self.assertEqual(rav(P('&'), both, 2), [A, A])
    self.assertEqual(rav(P('solve'), both, 1), [A])
    self.assertEqual(rav(P('&&>'), both, 2), [T, A])
    self.assertEqual(rav(P('||'), T, 2), [A, A])
    self.assertEqual(rav(P('||'), F, 2), [F, F])
    self.assertEqual(rav(P('&&>'), A, 2), [T, A])
    self.assertEqual(rav(P('&&>'), bo.ANYC, 2), [T, A])
    self.assertEqual(rav(M('f'), T, 3), [A, A, A])
    # More arguments than the table lists are not required.
    self.assertEqual(rav(P('not'), T, 3), [F, A, A])

  def test_prog(self):
    f = func('f', [1], guard(eq(X, lit(3)), X))
    g = func('g', [1], X)
    h = func('h', [1], guard(fcall(P('$'), pcall(P('id'), 1), eq(X, lit(3))), X))
    ext = fc.Func(M('e'), 0, fc.Public, fc.TVar(0), fc.External('M.e'))
    out, n = bo.transform_prog(prog(f, g, h, ext))
    self.assertEqual(n, 1)
    tf, tg, th, text = out.functions
    self.assertEqual(tf.rule.body, guard(constr(X, lit(3)), X))
    self.assertIs(tg, g)
    self.assertIs(text, ext)
    # A rule with an equality is rebuilt, so its $ is reduced, as in the
    # tool of PAKCS.
    self.assertEqual(th.rule.body, guard(fcall(P('id'), eq(X, lit(3))), X))
    # A program without an equality is returned as it is.
    p = prog(g, ext)
    self.assertEqual(bo.transform_prog(p), (p, 0))
    self.assertIs(bo.optimize_bindings(p), p)

  def test_translate_flag(self):
    '''translate applies the pass on request only.'''
    p = prog(func('f', [1], guard(eq(X, lit(3)), X)))
    # The name of a call in the ICurry of the port carries the index of the
    # symbol in its module after the module and the name.
    names = lambda iprog: {
        tuple(node.name[:2])
            for fd in iprog.functions
            for node in flat_icurry_calls(fd)
      }
    self.assertIn(P('constrEq'), names(f2i.translate(p, [PRELUDE], bindingopt=True)))
    self.assertNotIn(P('constrEq'), names(f2i.translate(p, [PRELUDE])))

  def test_cli(self):
    '''--bindingopt on the FlatCurry of the sendMoreMoney program.'''
    pattern = os.path.join(DATA, '.curry', '*', 'sendMoreMoney.fcy')
    found = sorted(glob.glob(pattern))
    if not found:
      self.skipTest('sendMoreMoney.fcy is not in the test corpus')
    fcyfile = found[0]
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    try:
      texts = {}
      for flag in (), ('--bindingopt',):
        out = os.path.join(tmpdir, 'sendMoreMoney.icy')
        argv = list(flag) + ['-o', out, fcyfile]
        for directory in LIBRARY_DIRS:
          argv[:0] = ['-i', directory]
        try:
          self.assertEqual(cli.main(argv), 0)
        except f2i.Flat2ICurryError as e:
          if 'no FlatCurry interface' in str(e):
            self.skipTest(str(e).splitlines()[0])
          raise
        with open(out, 'r', encoding='utf-8', newline='') as istream:
          texts[flag] = istream.read()
    finally:
      shutil.rmtree(tmpdir)
    self.assertNotIn('constrEq', texts[()])
    self.assertIn('constrEq', texts[('--bindingopt',)])
    # Every (==) of the program sits in the guard: none is left.
    self.assertNotIn('_impl#==#', texts[('--bindingopt',)])

def flat_icurry_calls(iobj):
  '''The IFCall nodes of an ICurry term of the port.'''
  found = []
  def walk(x):
    if isinstance(x, ic.IFCall):
      found.append(x)
    if isinstance(x, terms.Term):
      for arg in x._args_:
        walk(arg)
    elif isinstance(x, (list, tuple)):
      for arg in x:
        walk(arg)
  walk(iobj)
  return found

# Curry programs
# ==============
def values(goal):
  '''The values of a goal as Python objects, in order.'''
  return list(curry.eval(goal, converter='topython'))

SUSPENDS = object()

SMALL = '''
-- One rigid constraint over one generator.
oneGenerator :: Int
oneGenerator | (x + 1 == 4) & (x == (2 ? 3 ? 4)) = x where x free

-- Two generators and a constraint that needs both.
twoGenerators :: (Int, Int)
twoGenerators | (x + y == 5) & (x == (1 ? 2 ? 3)) & (y == (2 ? 3 ? 4)) = (x, y)
  where x, y free
'''

# The shapes probed under PAKCS 3.4.1, with its answers.
PARITY = '''
-- (&) as a value, not in a condition.
concurrentAsValue :: Bool
concurrentAsValue = (x == 1) & (y == 2) where x, y free

-- (&) as a value with a false conjunct: no value, not False.
concurrentFalse :: Bool
concurrentFalse = (1 == 2) & True

-- (&&) as a value with a free variable.
booleanAndAsValue :: Bool
booleanAndAsValue = (x == 1) && True where x free

-- not (/=) in a condition.
notDisequality :: Int
notDisequality | not (x /= 3) = x where x free

-- if-then-else over a free variable: not a condition.
ifThenElse :: Int
ifThenElse = if x == 3 then x else 0 where x free

-- A guard with an otherwise branch.
otherwiseGuard :: Int
otherwiseGuard | x == 3 = x
               | otherwise = 0
  where x free

-- (===) in a condition.
dataEquality :: Int
dataEquality | x === 3 = x where x free

-- A condition built with (&&).
booleanAndGuard :: (Int, Int)
booleanAndGuard | x == 1 && y == 2 = (x, y) where x, y free

-- A condition under ($) of a function the pass does not know.
dollarId :: Int
dollarId | id $ x == 3 = x where x free

-- (||) in a condition: the arguments are not required True.
disjunction :: Int
disjunction | x == 3 || x == 4 = x where x free

-- solve in a condition.
solveGuard :: Int
solveGuard | solve (x == 3) = x where x free

-- A condition over a polymorphic Eq dictionary.
eqDict :: Eq a => a -> a -> Bool
eqDict u v | u == v = True

dictionary :: Bool
dictionary = eqDict x (3 :: Int) where x free

-- Equality of a free list in a condition.
listEquality :: [Int]
listEquality | xs == [1, 2] = xs where xs free

-- (/=) in a condition: required True, not transformed.
disequalityGuard :: Int
disequalityGuard | x /= 3 = x where x free

-- not over (&) as a value: the arguments of (&) are not required True.
notConcurrent :: Bool
notConcurrent = not ((x == 3) & (y == 4)) where x, y free

-- not over solve as a value.
notSolve :: Bool
notSolve = not (solve (x == 3)) where x free

-- not (not e) requires nothing of e, and (&) then requires True of both.
notNotConcurrent :: Bool
notNotConcurrent = not (not ((x == 3) & (y == 4))) where x, y free
'''

PARITY_RESULTS = [
    ('concurrentAsValue', [True])
  , ('concurrentFalse', [])
  , ('booleanAndAsValue', SUSPENDS)
  , ('notDisequality', [3])
  , ('ifThenElse', SUSPENDS)
  , ('otherwiseGuard', SUSPENDS)
  , ('dataEquality', [3])
  , ('booleanAndGuard', [(1, 2)])
  , ('dollarId', SUSPENDS)
  , ('disjunction', SUSPENDS)
  , ('solveGuard', [3])
  , ('dictionary', [True])
  , ('listEquality', [[1, 2]])
  , ('disequalityGuard', SUSPENDS)
  , ('notConcurrent', SUSPENDS)
  , ('notSolve', SUSPENDS)
  , ('notNotConcurrent', [True])
  ]

class TestRoute(cytest.TestCase):
  '''Programs compiled through the build route, on the backend of the run.'''

  def assertSuspends(self, goal):
    with self.assertRaises(EvaluationSuspended):
      values(goal)

  def test_one_generator(self):
    M = curry.compile(SMALL)
    self.assertEqual(values(M.oneGenerator), [3])

  def test_two_generators(self):
    M = curry.compile(SMALL)
    self.assertEqual(sorted(values(M.twoGenerators)), [(1, 4), (2, 3), (3, 2)])

  def test_parity_with_pakcs(self):
    M = curry.compile(PARITY)
    for name, expected in PARITY_RESULTS:
      with self.subTest(goal=name):
        goal = getattr(M, name)
        if expected is SUSPENDS:
          self.assertSuspends(goal)
        else:
          self.assertEqual(values(goal), expected)

  @cytest.timeout(300)
  def test_send_more_money(self):
    '''
    The program of the test data, as written, with (==) in the guard.  The
    pass turns the guard into constraints, the digit generators bind the
    letters, and the arithmetic conjuncts suspend and resume as the letters
    are bound.  The C++ backend takes 0.1 s, the Python backend about 7 s.
    Before the fix of ($##) over a bound variable (unit_py_residuation.py)
    the Python backend finished the search and then spun in show.
    '''
    with open(SEND_MORE_MONEY, 'r', encoding='utf-8') as istream:
      M = curry.compile(istream.read())
    self.assertEqual(values(M.main), ['\n 9567\n 1085\n10652\n'])

if __name__ == '__main__':
  unittest.main()
