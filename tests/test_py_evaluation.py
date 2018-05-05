'''Tests for code evaluation in the Curry interpreter.'''
import curry
import cytest # from ./lib
import unittest

class TestPyEvaluation(cytest.TestCase):
  def check(self, name, expected):
    module = curry.import_(name)
    main = curry.expr(module.main)
    values = list(curry.eval(main))
    self.assertEqual(values, expected)

  def test_atableFlex(self):
    self.check('atableFlex', [True])

  @unittest.expectedFailure # TODO: Needs Prelude.failed.
  def test_atableNoflex(self):
    self.check('atableNoflex', [False])

  def test_btable(self):
    self.check('btable', [0])
