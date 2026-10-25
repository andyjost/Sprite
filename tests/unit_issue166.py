'''Issue #166: the checker's invariant B1 (group) fires on two strict
equalities over a bound free variable in a set function.

The values are right without the checker. With it, the union of a decided
singleton generator with a fresh variable leaves the root of the group
undetermined while its member is decided, and the checker stops.
'''
import cytest # from ./lib; must be first
from unit_setfunctions_bugs import run_child, goals
import unittest


class TestIssue166(cytest.TestCase):
  def test_values_without_the_checker(self):
    self.assertEqual(run_child(self, goals('plain2', 'inside2'), module='LiftGuardB1'),
        {'plain2': ['[True]'], 'inside2': ['[]']})

  @unittest.expectedFailure
  def test_values_with_the_checker(self):
    self.assertEqual(
        run_child(self, goals('plain2', 'inside2'), module='LiftGuardB1', checker=True),
        {'plain2': ['[True]'], 'inside2': ['[]']})


if __name__ == '__main__':
  unittest.main()
