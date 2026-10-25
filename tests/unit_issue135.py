'''Issue #135: normalizing a shared argument must not overwrite it with failure.'''
import cytest # from ./lib; must be first
import curry, unittest

PROGRAM = '''
nfShared :: Int
nfShared = let p = (failed :: Int, 1) in fst (id $!! p) ? snd p

nfUnshared :: Int
nfUnshared = fst (id $!! (failed :: Int, 1)) ? snd (failed :: Int, 1)
'''

class TestIssue135(cytest.TestCase):
  def check_normalization(self):
    M = curry.compile(PROGRAM)
    self.assertEqual(list(curry.eval(M.nfShared)), [1])
    self.assertEqual(list(curry.eval(M.nfUnshared)), [1])

  def test_shared_failure(self):
    self.check_normalization()

  @cytest.with_flags(checker=True)
  def test_shared_failure_with_checker(self):
    self.check_normalization()

  @cytest.with_flags(checker=True)
  def test_checker_refuses_write_to_argument(self):
    from curry.backends.cxx import curryrtbindings as cb
    P = cytest.raw.interp().prelude
    pair = cytest.raw.expr((cytest.raw.fail, 1))
    redex = cytest.raw.expr(getattr(P, '$!!'), cytest.raw.expr(P.id), pair)
    rts = cb.RuntimeState(cytest.raw.interp(), redex)
    cb.checker_debug_normalization_failure(rts, redex)
    with self.assertRaisesRegex(AssertionError, 'step writes redex'):
      cb.checker_debug_normalization_failure(rts, pair)

if __name__ == '__main__':
  unittest.main()
