'''Weak rewriting shares the caller boundary of allValues, in both routes.'''
import cytest # from ./lib; must be first
import json
import unittest


PROBE = r'''
import curry, json
curry.reset(interpret=MODE, jit='off')
M = curry.compile("""
import Control.Search.Unsafe
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
""")
for name in ('choice','choiceAll','choiceSome','empty','insideFailure','freeAll','freeSome',
             'nested','infinite','exceptionTail'):
 print(json.dumps([name, sorted(curry.show(v) for v in curry.eval(M[name]))]),
       flush=True)
'''


class TestWeakRewriting(cytest.TestCase):
  def check_route(self, mode):
    # Isolate module generations and bound divergence if the tail is demanded.
    proc = cytest.run_in_subprocess('MODE = %r\n' % mode + PROBE,
                                   timeout=90, address_space=2 << 30)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    actual = dict(json.loads(line) for line in proc.stdout.splitlines())
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
