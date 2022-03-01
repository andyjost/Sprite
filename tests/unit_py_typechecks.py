import cytest # from ./lib; must be first
from curry.common import LEFT, RIGHT, UNDETERMINED
from curry.backends.py.eval import typecheckers as tc
from curry.backends.py.eval.rts import RuntimeState
from curry.backends.py.graph import Node
from curry import inspect
import curry, sys, unittest

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
        , lambda: Node(I.prelude.Int.info, 'a')
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct an Int node from an argument of type float\.'
        , lambda: Node(I.prelude.Int.info, 1.0)
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct a Float node from an argument of type int\.'
        , lambda: Node(I.prelude.Float.info, 1)
        )
      if debug and sys.version_info.major == 2:
        # There is an assertion for this even in non-debug mode.
        self.assertRaisesRegex(
            TypeError
          , r'Cannot construct a Char node from an argument of type unicode\.'
          , lambda: Node(I.prelude.Char.info, unicode('a'))
          )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct a Char node from a str of length 0\.'
        , lambda: Node(I.prelude.Char.info, '')
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct a Char node from a str of length 2\.'
        , lambda: Node(I.prelude.Char.info, 'ab')
        )

  def testConstraints(self):
    for debug in [True, False]:
      I = curry.interpreter.Interpreter(flags={'debug':debug})
      rts = RuntimeState(I)
      q = I.symbol('Prelude.?')
      xy = list(I.eval(q, rts.freshvar(), rts.freshvar()))
      x, y = map(inspect.fwd_chain_target, xy)
      for constraint_type in [I.prelude._StrictConstraint, I.prelude._NonStrictConstraint]:
        self.assertMayRaise(
            None
          , lambda: I.expr(constraint_type, True, (x, y))
          )
        self.assertMayRaiseRegexp(
            TypeError if debug else None
          , r'Cannot construct a _Constraint node relating variable . to itself\.'
          , lambda: I.expr(constraint_type, True, (x, x))
          )
        self.assertMayRaiseRegexp(
            TypeError if debug else None
          , r'Cannot construct a _Constraint node from an argument '
             '\(in position 2.1\) of type int\.'
          , lambda: I.expr(constraint_type, True, (u(1), y))
          )

  def testCoverage(self):
    self.assertEqual(tc._typecategory(list), ())
    self.assertEqual(tc._articlefor(''), 'a')

