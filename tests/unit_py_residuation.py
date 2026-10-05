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

if __name__ == '__main__':
  unittest.main()
