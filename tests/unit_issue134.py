'''Issue #134: a generator escape duplicates the set of a cyclic argument.

The deferred failure rule keeps the successful alternative, once. A
one-constructor generator has no program choice to escape.
'''
import cytest # from ./lib; must be first
import curry
from unit_setfunctions_bugs import run_child, goals
import unittest


class TestIssue134(cytest.TestCase):
  def test_free_argument_narrows_outside_with_an_empty_set_for_refusal(self):
    M = curry.compile('onlyTrue :: Bool -> Bool\nonlyTrue True = True\n')
    SF = curry.import_('Control.SetFunctions')
    x = curry.free('x', type='Bool')
    answers = list(curry.solve(SF.set1(M.onlyTrue, x)))
    self.assertEqual(sorted((a.bindings[x], list(a.value)) for a in answers),
        [(False, []), (True, [True])])

  def test_one_set_for_the_successful_alternative(self):
    self.assertEqual(run_child(self, goals('goal2'), module='LiftGuard'),
        {'goal2': ['[True]']})

  def test_one_set_for_the_successful_alternative_with_checker(self):
    self.assertEqual(run_child(self, goals('goal2'), module='LiftGuard', checker=True),
        {'goal2': ['[True]']})

  def test_single_constructor_and_nested_capsule(self):
    for checker in (False, True):
      with self.subTest(checker=checker):
        self.assertEqual(run_child(self,
            goals('one', 'nested2', 'programChoice', 'oneBinding'),
            module='LiftGuard', checker=checker),
            {'one': ['[One, One]'], 'nested2': ['[[True]]'],
             'programChoice': ['[True, True]', '[True]'],
             'oneBinding': ['([True], One)']})


if __name__ == '__main__':
  unittest.main()
