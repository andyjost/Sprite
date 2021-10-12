'''Tests for code evaluation in the Curry interpreter.'''
import cytest # from ./lib; must be first
import curry
import unittest
from curry.backends.py import runtime

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

  @cytest.with_flags(defaultconverter='topython')
  def test_atableFlex(self):
    self.check('atableFlex', [True])

  @cytest.with_flags(defaultconverter='topython')
  def test_atableNoflex(self):
    self.check('atableNoflex', [False])

  @cytest.with_flags(defaultconverter='topython')
  def test_btable(self):
    self.check('btable', [0])

  @cytest.with_flags(defaultconverter='topython')
  def test_partial(self):
    '''Checks the string representation of partial applications.'''
    m = curry.import_('myand')
    self.checkAsString([m.and_]             , 'and_')
    self.checkAsString([m.and_, True]       , '(and_ True)')
    self.checkAsString([m.and_, False]      , '(and_ False)')
    self.checkAsString([m.and_, True, True] , 'True')
    self.checkAsString([m.and_, True, False], 'False')

