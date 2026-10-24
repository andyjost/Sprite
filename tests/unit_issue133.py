'''Issue #133: a lifted constraint loses the argument's set guards.

The failing argument must give no set under the deferred failure rule.
Repairing its provenance belongs to the runtime; keep the reproducer.
'''
import cytest # from ./lib; must be first
import curry
from unit_setfunctions_bugs import run_child, goals
import unittest


class TestIssue133(cytest.TestCase):
  def test_plain_failed_argument(self):
    self.assertEqual(run_child(self, goals('goal0'), module='LiftGuard'), {'goal0': []})

  def test_plain_failed_argument_with_checker(self):
    self.assertEqual(run_child(self, goals('goal0'), module='LiftGuard', checker=True),
        {'goal0': []})

  @(unittest.expectedFailure)
  def test_lifted_constraint_failure(self):
    self.assertEqual(run_child(self, goals('goal1'), module='LiftGuard'), {'goal1': []})

  @(unittest.expectedFailure)
  def test_lifted_constraint_failure_with_checker(self):
    self.assertEqual(run_child(self, goals('goal1'), module='LiftGuard', checker=True),
        {'goal1': []})


if __name__ == '__main__':
  unittest.main()
