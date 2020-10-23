'''Tests for code evaluation in the Curry interpreter.'''
import cytest # from ./lib; must be first
import curry
import unittest
from curry.interpreter import runtime
from curry.interpreter.eval import makegoal
from curry import types

class TestPyEvaluation(cytest.TestCase):
  def check(self, name, expected):
    '''
    Run the main function the the named module and ensure it produces the
    expected results.
    '''
    module = curry.import_(name)
    main = curry.expr(module.main)
    values = list(curry.eval(main))
    self.assertEqual(values, expected)

  def checkAsString(self, args, expected):
    '''
    Form an expression from the given args, evaluate it, convert it to a
    string, and then compare that string against the expected results.  This
    can be used to check partial applications.
    '''
    expr = curry.expr(*args)
    values = list(curry.eval(expr))
    self.assertEqual(len(values), 1)
    self.assertEqual(str(values[0]), expected)

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

  def test_narrowing(self):
    _a = types.FreeType('_a')
    self.check('narrowing', [(_a, _a), (True, False), (False, True)])

  def test_partial(self):
    '''Checks the string representation of partial applications.'''
    m = curry.import_('myand')
    self.checkAsString([m.and_]             , 'and_')
    self.checkAsString([m.and_, True]       , '(and_ True)')
    self.checkAsString([m.and_, False]      , '(and_ False)')
    self.checkAsString([m.and_, True, True] , 'True')
    self.checkAsString([m.and_, True, False], 'False')

