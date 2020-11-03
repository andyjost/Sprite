import cytest # from ./lib; must be first
from curry.interpreter import runtime
import curry
from curry.runtime import LEFT, RIGHT, UNDETERMINED
from curry.interpreter import typecheckers as tc
import unittest

u = curry.unboxed
hint = r'  \(An unboxed value was expected but a boxed value of the ' \
        'correct type was supplied\.  Perhaps you need to wrap an '   \
        'argument with curry\.unboxed\?\)'

class TestPyTypeChecks(cytest.TestCase):
  '''These checks are enabled in debug mode.'''
  def testBuiltins(self):
    for debug in [True, False]:
      I = curry.interpreter.Interpreter(flags={'debug':debug})
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct an Int node from an argument of type str\.'
        , lambda: runtime.Node(I.prelude.Int.info, 'a')
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct an Int node from an argument of type float\.'
        , lambda: runtime.Node(I.prelude.Int.info, 1.0)
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct a Float node from an argument of type int\.'
        , lambda: runtime.Node(I.prelude.Float.info, 1)
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct a Char node from an argument of type unicode\.'
        , lambda: runtime.Node(I.prelude.Char.info, unicode('a'))
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct a Char node from a str of length 0\.'
        , lambda: runtime.Node(I.prelude.Char.info, '')
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct a Char node from a str of length 2\.'
        , lambda: runtime.Node(I.prelude.Char.info, 'ab')
        )

  def testBinding(self):
    for debug in [True, False]:
      I = curry.interpreter.Interpreter(flags={'debug':debug})
      unknown = I.symbol('Prelude.unknown')
      q = I.symbol('Prelude.?')
      x,y = list(I.eval(q, unknown, unknown))
      self.assertMayRaise(
          None
        , lambda: I.expr(I.prelude._Binding, True, (x, y))
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct a _Binding node binding variable . to itself\.'
        , lambda: I.expr(I.prelude._Binding, True, (x, x))
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct a _Binding node from an argument '
           '\(in position 2.1\) of type int\.'
        , lambda: I.expr(I.prelude._Binding, True, (u(1), y))
        )

  def testCoverage(self):
    self.assertEqual(tc._typecategory(list), ())
    self.assertEqual(tc._articlefor(''), 'a')

