'''Weak rewriting shares the caller boundary of allValues, in both routes.'''
import cytest # from ./lib; must be first
import json
import unittest


PROBE = r'''
import curry, json, os, tempfile
curry.reset(interpret=MODE, jit='off')
helper_dir = tempfile.TemporaryDirectory()
curry.path.insert(0, helper_dir.name)
with open(os.path.join(helper_dir.name, 'RewriteHelpers.curry'), 'w') as stream:
 stream.write("""
module RewriteHelpers where
import Control.Search.Unsafe
helperAll :: Int -> [Int]
helperAll x = rewriteAll (x+10)
helperSome :: Int -> Maybe Int
helperSome x = rewriteSome (x+10)
referenceAll :: Int -> [Int]
referenceAll x = allValues (x+10)
referenceSome :: Int -> Maybe Int
referenceSome x = oneValue (x+10)
""")
with open(os.path.join(helper_dir.name, 'RewriteProbe.curry'), 'w') as stream:
 stream.write("""
module RewriteProbe where
import RewriteHelpers
import Control.Search.Unsafe
import Control.SetFunctions (set0, sortValues)
choice :: (Int,[Int],Maybe Int)
choice = let x = 0 ? 1 in (x,rewriteAll (x+10),rewriteSome (x+10))
choiceAll :: [Int]
choiceAll = let x = 0 ? 1 in rewriteAll (x+10)
choiceSome :: Maybe Int
choiceSome = let x = 0 ? 1 in rewriteSome (x+10)
empty :: ([Int],Maybe Int)
empty = (rewriteAll failed,rewriteSome failed)
insideFailure :: ([Int],Maybe Int)
insideFailure = (rewriteAll (failed ? 7),rewriteSome (failed ? 7))
freeAll :: (Bool,[Bool])
freeAll = (x,rewriteAll (not x)) where x free
freeSome :: (Bool,Maybe Bool)
freeSome = (x,rewriteSome (not x)) where x free
nested :: ([[Int]],Maybe (Maybe Int),[[Int]])
nested = (rewriteAll (rewriteAll (7 ? 8)),
          rewriteSome (rewriteSome (failed :: Int)),
          rewriteAll (rewriteAll (failed :: Int)))
from n = n ? from (n+1)
infinite :: Maybe Int
infinite = rewriteSome (from 0)
exceptionTail :: Maybe Int
exceptionTail = rewriteSome (7 ? error "tail demanded")
partialAll :: [[Int]]
partialAll = let x = 0 ? 1 in map rewriteAll [x+10]
partialAllRef :: [[Int]]
partialAllRef = let x = 0 ? 1 in map allValues [x+10]
partialSome :: [Maybe Int]
partialSome = let x = 0 ? 1 in map rewriteSome [x+10]
partialSomeRef :: [Maybe Int]
partialSomeRef = let x = 0 ? 1 in map oneValue [x+10]
helperAllGoal :: [Int]
helperAllGoal = let x = 0 ? 1 in helperAll x
helperAllRef :: [Int]
helperAllRef = let x = 0 ? 1 in referenceAll x
helperSomeGoal :: Maybe Int
helperSomeGoal = let x = 0 ? 1 in helperSome x
helperSomeRef :: Maybe Int
helperSomeRef = let x = 0 ? 1 in referenceSome x
surroundAll :: [[Int]]
surroundAll = let x = 0 ? 1 in sortValues (set0 (rewriteAll (x+10)))
surroundAllRef :: [[Int]]
surroundAllRef = let x = 0 ? 1 in sortValues (set0 (allValues (x+10)))
surroundSome :: [Maybe Int]
surroundSome = let x = 0 ? 1 in sortValues (set0 (rewriteSome (x+10)))
surroundSomeRef :: [Maybe Int]
surroundSomeRef = let x = 0 ? 1 in sortValues (set0 (oneValue (x+10)))
""")
M = curry.import_("RewriteProbe")
for name in ('choice','choiceAll','choiceSome','empty','insideFailure','freeAll','freeSome',
             'nested','infinite','exceptionTail',
             'partialAll','partialAllRef','partialSome','partialSomeRef',
             'helperAllGoal','helperAllRef','helperSomeGoal','helperSomeRef',
             'surroundAll','surroundAllRef','surroundSome','surroundSomeRef'):
 print(json.dumps([name, sorted(curry.show(v) for v in curry.eval(M[name]))]),
       flush=True)
helper_dir.cleanup()
'''


class TestWeakRewriting(cytest.TestCase):
  def check_route(self, mode):
    # Isolate module generations and bound divergence if the tail is demanded.
    proc = cytest.run_in_subprocess('MODE = %r\n' % mode + PROBE,
                                   timeout=90, address_space=2 << 30)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    actual = dict(json.loads(line) for line in proc.stdout.splitlines())
    # Partial applications expose no argument to the lift, just as allValues
    # and oneValue do: the expression's choice stays inside the observer.
    for probe, expected in (
        ('partialAll', ['[[10,11]]']), ('partialSome', ['[Just 10]']),
        ('helperAll', ['[10]', '[11]']),
        ('helperSome', ['Just 10', 'Just 11']),
        ('surroundAll', ['[[10]]', '[[11]]']),
        ('surroundSome', ['[Just 10]', '[Just 11]'])):
      with self.subTest(mode=mode, probe=probe):
        name = probe + 'Goal' if probe.startswith('helper') else probe
        values = actual.pop(name)
        self.assertEqual(values, actual.pop(probe + 'Ref'))
        self.assertEqual(values, expected)
    self.assertEqual(actual, {
        'choice': ['(0,[10],Just 10)', '(1,[11],Just 11)'],
        'choiceAll': ['[10]', '[11]'],
        'choiceSome': ['Just 10', 'Just 11'],
        'empty': ['([],Nothing)'],
        'insideFailure': ['([7],Just 7)'],
        'freeAll': ['(False,[True])', '(True,[False])'],
        'freeSome': ['(False,Just True)', '(True,Just False)'],
        'nested': ['([[7,8]],Just Nothing,[[]])'],
        'infinite': ['Just 0'],
        'exceptionTail': ['Just 7'],
      })

  def test_interpreted(self):
    self.check_route('all')

  def test_compiled(self):
    self.check_route('off')


if __name__ == '__main__':
  unittest.main()
