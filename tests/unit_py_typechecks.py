import cytest # from ./lib; must be first
from curry.backends.py import runtime
from curry.backends.py.runtime import LEFT, RIGHT, UNDETERMINED, RuntimeState, typecheckers as tc
from curry.backends.py.runtime.fairscheme.freevars import freshvar
import curry
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
      rts = RuntimeState(I)
      q = I.symbol('Prelude.?')
      x,y = list(I.eval(q, freshvar(rts), freshvar(rts)))
      for binding_type in (
          [I.prelude._Binding] if runtime.api.FAIR_SCHEME_VERSION == 1 else
          [I.prelude._StrictBinding, I.prelude._NonStrictBinding]
          ):
        self.assertMayRaise(
            None
          , lambda: I.expr(binding_type, True, (x, y))
          )
        self.assertMayRaiseRegexp(
            TypeError if debug else None
          , r'Cannot construct a _Binding node binding variable . to itself\.'
          , lambda: I.expr(binding_type, True, (x, x))
          )
        self.assertMayRaiseRegexp(
            TypeError if debug else None
          , r'Cannot construct a _Binding node from an argument '
             '\(in position 2.1\) of type int\.'
          , lambda: I.expr(binding_type, True, (u(1), y))
          )

  def testCoverage(self):
    self.assertEqual(tc._typecategory(list), ())
    self.assertEqual(tc._articlefor(''), 'a')

