'''D53: a failed direct successor fails a constructor before N descends.'''
import cytest # from ./lib; must be first
from func_community import sprite_results
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parent / 'data' / 'curry' / 'encapsulation'
TIMEOUT = 60


class CursorFailureCase(cytest.TestCase):
  def check(self, module, expected):
    proc, actual = sprite_results(SOURCE / (module + '.curry'), 'main',
                                  timeout=TIMEOUT, interpret=self.MODE)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(actual.splitlines(), expected)

  def test_failed_later_field(self):
    self.check('CursorFail', [])

  def test_shared_constraint_failure(self):
    self.check('CursorBeta', ['Pair True True'])


class TestCompiled(CursorFailureCase):
  MODE = 'off'


class TestInterpreted(CursorFailureCase):
  MODE = 'all'


del CursorFailureCase # Only run the two concrete routes.


if __name__ == '__main__':
  unittest.main()
