'''
Tests for the residuation of the Python backend: the steps that suspend on a
free variable, and the information that releases them.  The programs run on
both backends; the C++ backend had neither defect.

Two defects of the Python backend were found with the sendMoreMoney program
of issue #37.  A primitive on unboxed values (_unbox in
backends/py/currylib/prelude/math.py) evaluated every argument to a head
normal form before it suspended, so a generator in a later argument forked
the configuration once per alternative while the step could not complete,
and a conjunction of such steps forked their product.  And ($##) (apply_gnf
in backends/py/currylib/prelude/apply.py) counted a free variable with a
binding, and no generator, as a residual.  ready() releases a configuration
whose residual has a binding at once, so the step suspended on the same
variable again without end: show x after x =:= (3 ? 4) spun at full load,
and so did the puzzle after its search.  The step now suspends on the
variables without any information (rts.is_void), as ensureNotFree does.
'''
import cytest # from ./lib; must be first
from curry.exceptions import EvaluationSuspended
import curry, unittest

def values(goal):
  '''The values of a goal as Python objects, in order.'''
  return list(curry.eval(goal, converter='topython'))

ORDER = '''
loopInt :: Int -> Int
loopInt n = loopInt (n + 1)

-- A rigid equality as a value: the binding optimization leaves it.  The
-- left operand is free; the right one does not end.  The step must suspend
-- at once.
leftFree :: Bool
leftFree = v == loopInt 0 where v free

-- The same for (+) under a comparison.
plusLeftFree :: Bool
plusLeftFree = v + loopInt 0 == 1 where v free

-- Four digit generators under rigid equalities, joined by (&) through let
-- bindings, which the binding optimization does not look through.  The
-- value suspends.  A backend that evaluates a generator before it suspends
-- on the free operand forks ten configurations per letter first.
fourValue :: (Int, Int, Int, Int)
fourValue | b1 & b2 & b3 & b4 = (vm, vs, vo, ve)
  where
    vm, vs, vo, ve free
    store = [_,_,_,_,_,_,_,_,_,_]
    digit token | store !! x == token = x
      where x = 0 ? 1 ? 2 ? 3 ? 4 ? 5 ? 6 ? 7 ? 8 ? 9
    b1 = vm == digit 'M'
    b2 = vs == digit 'S'
    b3 = vo == digit 'O'
    b4 = ve == digit 'E'
'''

BOUND = '''
-- A variable bound by a constraint to a choice.  show applies its
-- primitive with ($##); the bound variable is not a residual.
showBound :: String
showBound | x =:= (3 ? 4) = show x where x free

showConcat :: String
showConcat | x =:= (3 ? 4) = show x ++ "!" where x free

-- A variable bound to another one, which is bound to a value.
showChain :: String
showChain | x =:= y & y =:= (5 :: Int) = show x where x, y free

-- ($##) alone.
groundBound :: Int
groundBound | x =:= (3 ? 4) = id $## x where x free

-- Two variables bound to each other and nothing else: no information.
showVarBound :: String
showVarBound | x =:= (y :: Int) = show x where x, y free
'''

NARROWED = '''
import Control.SetFunctions

-- A constructor with a String argument: the generator of a String has a
-- nested generator for the tail of every cons cell, and the fresh
-- variables of a branch that an alternative does not take get no value.
data U = UA | UB U | UName String
  deriving (Eq, Ord, Show)

anyU :: Int -> U
anyU n = UA ? (if n > 0 then UB (anyU (n - 1)) ? UName "x" else failed)

-- A name is any string.
anyNamed :: Int -> U
anyNamed n = UA ? (if n > 0 then UB (anyNamed (n - 1)) ? UName s else failed)
  where s free

isUB :: U -> Bool
isUB u = case u of
  UB _ -> True
  _    -> False

-- The variable is narrowed by =:= and then evaluated to ground normal form.
pick :: Int -> U
pick n | t =:= anyU n && (isUB $## t) = t
  where t free

picks :: [U]
picks = sortValues (set1 pick 1)

-- The alternative with the free name has no ground normal form: the step
-- suspends there, after the other alternatives gave their values.
pickNamed :: Int -> U
pickNamed n | t =:= anyNamed n && (isUB $## t) = t
  where t free

-- ($##) first.  The step suspends on the free variable, the narrowing of
-- the second conjunct wakes it (& works on the other conjunct when one
-- suspends), and the step then meets the bare variable with its generator,
-- whose untaken branches hold fresh variables without a value.
pickFirst :: Int -> U
pickFirst n | (isUB $## t) & (t =:= anyU n) = t
  where t free
'''

BEHIND = '''
-- Two alternatives, both blocked.  The first binds v and suspends on u; the
-- second suspends on v and has no binding for it.  The release test of
-- ready() must read the configuration that waits, not the head of the
-- queue: with the head's binding of v the second was released, its step
-- suspended again at once, and the two took turns without end.
blockedBehindHead :: Int
blockedBehindHead = ((v =:= 1) &> (u + 1)) ? (v + 1)
  where u, v free

-- The same alternatives in the other order: the waiting configuration is
-- the head, and its own state is read either way.
blockedAtHead :: Int
blockedAtHead = (v + 1) ? ((v =:= 1) &> (u + 1))
  where u, v free
'''

def texts(*args):
  '''The values of a goal as Curry text, in order.'''
  return [str(value) for value in curry.eval(*args, converter=None)]

class TestSuspensionOrder(cytest.TestCase):
  '''
  A primitive on unboxed values suspends at the first free argument, before
  it touches the arguments after it, on both backends.
  '''
  @cytest.timeout(60)
  def test_rigid_primitive_suspends_before_the_later_arguments(self):
    M = curry.compile(ORDER)
    for name in 'leftFree', 'plusLeftFree', 'fourValue':
      with self.subTest(goal=name):
        with self.assertRaises(EvaluationSuspended):
          values(getattr(M, name))

class TestGroundNormalForm(cytest.TestCase):
  '''
  ($##) over a variable with a binding ends; over a variable without any
  information it suspends.  Before the fix the first case did not end on
  the Python backend.
  '''
  @cytest.timeout(60)
  def test_bound_variable_is_not_a_residual(self):
    M = curry.compile(BOUND)
    self.assertEqual(sorted(values(M.showBound)), ['3', '4'])
    self.assertEqual(sorted(values(M.showConcat)), ['3!', '4!'])
    self.assertEqual(values(M.showChain), ['5'])
    self.assertEqual(sorted(values(M.groundBound)), [3, 4])

  @cytest.timeout(60)
  def test_variable_without_information_suspends(self):
    M = curry.compile(BOUND)
    with self.assertRaises(EvaluationSuspended):
      values(M.showVarBound)

class TestNormalFormOfNarrowedVariable(cytest.TestCase):
  '''
  ($##) over a variable that =:= narrowed to a structured value.  The check
  for residuals runs over the normal form, after the normalization, and
  enters no generator (apply_gnf, as applygnf_step of the C++ runtime).  A
  check over the argument before its normalization walked the generators of
  the narrowed variables as well, where the fresh variables of the branches
  the alternative did not take never get a value, and the step suspended
  for good: scenario (d) of example 21 on the Python backend, which
  unit_examples.py runs on both backends now.  With the former step
  installed in place of apply_gnf, pick 1, pickFirst 1 and picksFirst did
  not end within 20 s on the Python backend; pickFirst reaches the step
  with the bare narrowed variable, the condition of the defect.
  '''
  @cytest.timeout(60)
  def test_narrowed_structure_is_ground(self):
    M = curry.compile(NARROWED)
    self.assertEqual(texts(M.pick, 1), ['UB UA'])
    self.assertEqual(texts(M.picks), ['[UB UA]'])
    self.assertEqual(texts(M.pickFirst, 1), ['UB UA'])

  @cytest.timeout(60)
  def test_free_name_suspends_after_the_values(self):
    M = curry.compile(NARROWED)
    got = []
    with self.assertRaises(EvaluationSuspended):
      for value in curry.eval(M.pickNamed, 1, converter=None):
        got.append(str(value))
    self.assertEqual(got, ['UB UA'])

class TestReleaseReadsTheWaitingConfiguration(cytest.TestCase):
  '''
  ready() releases a blocked configuration on the information of that
  configuration (_make_ready passes it to rts.is_void).  It read the head of
  the queue instead: a configuration behind a head that held a binding of
  its residual was released, suspended again at once, and the evaluation
  spun; the C++ runtime passes the configuration (rts_control.cpp).  Both
  goals suspend on both backends.
  '''
  @cytest.timeout(60)
  def test_binding_of_the_head_does_not_release_another(self):
    M = curry.compile(BEHIND)
    for name in 'blockedBehindHead', 'blockedAtHead':
      with self.subTest(goal=name):
        with self.assertRaises(EvaluationSuspended):
          values(getattr(M, name))

if __name__ == '__main__':
  unittest.main()
