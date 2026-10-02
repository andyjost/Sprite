'''Tests for code evaluation in the Curry interpreter.'''
import cytest # from ./lib; must be first
import curry
import unittest

class TestPyEvaluation(cytest.TestCase):
  def check(self, name, expected):
    '''
    Run the main function the the named module and ensure it produces the
    expected results.
    '''
    module = curry.import_(name)
    main = curry.raw_expr(module.main)
    values = list(curry.eval(main))
    self.assertEqual(values, expected)

  def checkAsString(self, args, expected):
    '''
    Form an expression from the given args, evaluate it, convert it to a
    string, and then compare that string against the expected results.  This
    can be used to check partial applications.
    '''
    expr = curry.raw_expr(*args)
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

  def test_naive_reverse(self):
    '''
    Covers a 2023 report by Michael Hanus: ``rev [1..10]`` hit the Python
    recursion limit while converting the result to a string.  The check goes
    through ``str`` so the show path is exercised.
    '''
    Rev = curry.compile(
        '''
        rev :: [Int] -> [Int]
        rev []     = []
        rev (x:xs) = rev xs ++ [x]

        main :: [Int]
        main = rev [1..10]
        '''
      , modulename='Rev'
      )
    self.checkAsString([Rev.main], '[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]')

  @cytest.with_flags(defaultconverter='topython')
  def test_addSomeNum2(self):
    '''
    Covers a 2023 report by Michael Hanus: ``isZero (addSomeNum2 2000)`` never
    yielded a value on the Python backend.  The evaluation is quadratic in the
    argument: ``addSomeNum2 2000`` takes about 200 seconds on the Python
    backend, so this test uses 50 on both backends.  func_complete checks the
    reported size on the C++ backend.  The program is in
    data/curry/SomeNum.curry.
    '''
    SomeNum = curry.import_('SomeNum')
    self.assertEqual(list(curry.eval(SomeNum.check, 50)), [True])

  @cytest.with_flags(defaultconverter='topython')
  def test_partial(self):
    '''Checks the string representation of partial applications.'''
    m = curry.import_('myand')
    self.checkAsString([m.and_]             , 'and_')
    self.checkAsString([m.and_, True]       , '(and_ True)')
    self.checkAsString([m.and_, False]      , '(and_ False)')
    self.checkAsString([m.and_, True, True] , 'True')
    self.checkAsString([m.and_, True, False], 'False')

