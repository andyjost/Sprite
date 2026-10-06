'''
The cost of a name that a functional pattern produced (issue #86).

The pattern variables of a functional pattern are narrowed and bound while
the pattern matches: ``source (stem ++ ".o") = stem ++ ".c"`` leaves
``stem`` a list of bound variables.  A binding is private to the
configuration that made it, so a later read of the name resolves every
variable again: the runtime copies the spine from the root of the
configuration to the variable, puts the binding or the decided generator
into the copy, and restarts the evaluation from the root (replace_freevar
of the C++ runtime and of the Python backend).  The copy and the restart
are repeated at every comparison of the name, and nothing of them goes
back into the shared graph.  Evaluating the name to normal form with $##
changes nothing: the normal form lives in the private copy, and the next
reader of the shared node starts over.  A set function is the idiom: the
capsule resolves the variables once, inside its own queue, and its value
leaves it as plain data, written in place.  This file pins the shape on
both backends: the same values by every route, the forks of the direct
route growing with the comparisons, and the forks of the set-function
route staying at the match.  A runtime change that removes the cost
flips the assertions on the direct route, which is the point.
'''
import cytest # from ./lib; must be first
import curry, unittest

CXX = curry.flags['backend'] == 'cxx'

SOURCE = '''
import Control.SetFunctions
import Data.List (nub)

-- The pattern rule %.o: %.c as a functional pattern.
source :: String -> String
source (stem ++ ".o") = stem ++ ".c"

-- The rule read through a set function: the value is plain data.
sourceS :: String -> String
sourceS t = case sortValues (set1 source t) of [s] -> s

-- The rule with its result evaluated to normal form first.
sourceN :: String -> String
sourceN t = id $## source t

-- One comparison.
one :: (String -> String) -> Bool
one f = f "ab.o" == "ab.c"

-- One name compared many times.  The name is shared, the comparisons
-- are not.
many :: (String -> String) -> Int
many f = length [() | _ <- [1 .. 200], s == "ab.c"]
  where s = f "ab.o"

-- Every pair of names compared, as nub does.
distinct :: (String -> String) -> Int
distinct f = length (nub (map f [[x, y] ++ ".o" | x <- "abc", y <- "abc"]))
'''

COMPARISONS = 200

def totals():
  t = curry.getInterpreter()._evaluation_totals
  return t.steps, t.forks

def measure(goal):
  '''The value of a goal with the steps and forks of its evaluation.'''
  steps0, forks0 = totals()
  value = next(curry.eval(goal, converter='topython'))
  steps1, forks1 = totals()
  return value, steps1 - steps0, forks1 - forks0

class TestNarrowedName(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.M = curry.compile(SOURCE, modulename='FuncPatNarrowed')

  def test_values(self):
    '''The three routes give the same values.'''
    M = self.M
    for f in [M.source, M.sourceS, M.sourceN]:
      self.assertEqual(next(curry.eval(M.one, f, converter='topython')), True)
      self.assertEqual(next(curry.eval(M.many, f, converter='topython')), COMPARISONS)
      self.assertEqual(next(curry.eval(M.distinct, f, converter='topython')), 9)

  def test_forks(self):
    '''
    The match of a two-letter stem forks eight times.  Through the set
    function the forks stay there.  Through the pattern rule every
    comparison meets the decided generators of the stem again, and each is
    counted as a fork; $## does not change that.
    '''
    M = self.M
    _, _, forks_once = measure([M.one, M.source])
    self.assertEqual(forks_once, 8)
    _, steps_set, forks_set = measure([M.many, M.sourceS])
    self.assertEqual(forks_set, forks_once)
    _, steps_direct, forks_direct = measure([M.many, M.source])
    _, steps_nf, forks_nf = measure([M.many, M.sourceN])
    per_comparison = (forks_direct - forks_once) / COMPARISONS
    self.assertGreaterEqual(per_comparison, 1)
    self.assertEqual(forks_nf, forks_direct)
    if CXX:
      # The restart repeats the steps of the spine, and the C++ runtime
      # counts them (procS); the Python backend counts a rewrite alone.
      self.assertGreater(steps_direct, 5 * steps_set)
      self.assertGreater(steps_nf, 5 * steps_set)
