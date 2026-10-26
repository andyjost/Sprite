'''D53: a failed direct successor fails a constructor before N descends.'''
import cytest # from ./lib; must be first
from func_community import sprite_results
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parent / 'data' / 'curry' / 'encapsulation'
TIMEOUT = 60


class CursorFailureCase(cytest.TestCase):
  def check(self, module, expected, timeout=TIMEOUT):
    proc, actual = sprite_results(SOURCE / (module + '.curry'), 'main',
                                  timeout=timeout, interpret=self.MODE)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(actual.splitlines(), expected)

  def test_failed_later_field(self):
    self.check('CursorFail', [])

  # awaits the constraint half of the whole-cell read of N (decision D59,
  # pending): the second field is a live constraint behind a forward chain,
  # which only the cursor lifts; the test asserts the rule's answer, exactly
  # `Pair True True` and termination.
  @unittest.expectedFailure
  def test_shared_constraint_failure(self):
    self.check('CursorBeta', ['Pair True True'], timeout=20)


class TestCompiled(CursorFailureCase):
  MODE = 'off'


class TestInterpreted(CursorFailureCase):
  MODE = 'all'


del CursorFailureCase # Only run the two concrete routes.


if __name__ == '__main__':
  unittest.main()
