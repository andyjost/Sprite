'''Tests for code evaluation in the Curry interpreter.'''
import cytest # from ./lib; must be first
import curry
import unittest
from curry.interpreter import runtime
from curry.interpreter.eval import makegoal

class TestPyEvaluation(cytest.TestCase):
  def check(self, name, expected):
    module = curry.import_(name)
    main = curry.expr(module.main)
    values = list(curry.eval(main))
    self.assertEqual(values, expected)

  def test_atableFlex(self):
    self.check('atableFlex', [True])

  def test_atableNoflex(self):
    self.check('atableNoflex', [False])

  def test_btable(self):
    self.check('btable', [0])

  def test_blockedFrames(self):
    '''Test blocking, unblocking, and suspension of evaluation.'''
    interp = curry.interpreter.Interpreter()
    goal = makegoal(interp, interp.expr(91))
    evaluator = runtime.Evaluator(interp, goal)
    Q = evaluator.queue
    Q[0] = Q[0].block([17])
    self.assertTrue(Q[0].blocked)
    self.assertFalse(Q[0].unblock())
    self.assertRaises(curry.EvaluationSuspended, lambda: list(evaluator.D()))
    Q[0].fingerprint[17] = runtime.LEFT
    self.assertEqual(list(evaluator.D()), [interp.expr(91)])

