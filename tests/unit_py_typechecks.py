import cytest # from ./lib; must be first
from curry.interpreter import runtime
import curry
from curry.runtime import LEFT, RIGHT, UNDETERMINED
from curry.interpreter import typecheckers as tc

u = curry.unboxed
hint = r'  \(An unboxed value was expected but a boxed value of the ' \
        'correct type was supplied\.  Did you forget to wrap an '     \
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

  def testEqChoices(self):
    for debug in [True, False]:
      I = curry.interpreter.Interpreter(flags={'debug':debug})
      self.assertMayRaise(
          None
        , lambda: I.expr(I.prelude._EqChoices, True, (u(101), u(102)))
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct an _EqChoices node from an argument '
           '\(in position 2\) of type list\.'
        , lambda: runtime.Node(I.prelude._EqChoices.info, True, [])
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct an _EqChoices node from an argument '
           '\(in position 2.1\) of type str\.'
        , lambda: I.expr(I.prelude._EqChoices, True, (u('a'), u(102)))
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct an _EqChoices node from an argument '
           '\(in position 2.2\) of type Int\.'
        , lambda: I.expr(I.prelude._EqChoices, True, (u(101), 102))
        )

  def testChoiceConstr(self):
    for debug in [True, False]:
      I = curry.interpreter.Interpreter(flags={'debug':debug})
      self.assertMayRaise(
          None
        , lambda: I.expr(I.prelude._ChoiceConstr, True, (u(101), u(LEFT)))
        )
      self.assertMayRaise(
          None
        , lambda: I.expr(I.prelude._ChoiceConstr, True, (u(101), u(RIGHT)))
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct a _ChoiceConstr node from the UNDETERMINED choice '
           'state \(in position 2.2\)\.'
        , lambda: I.expr(I.prelude._ChoiceConstr, True, (u(101), u(UNDETERMINED)))
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct a _ChoiceConstr node from an argument '
           '\(in position 2.2\) of type Int\.' + hint
        , lambda: I.expr(I.prelude._ChoiceConstr, True, (u(101), LEFT))
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct a _ChoiceConstr node from an argument '
           '\(in position 2.2\) of type Char\.'
        , lambda: I.expr(I.prelude._ChoiceConstr, True, (u(101), 'a'))
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct a _ChoiceConstr node from an argument '
           '\(in position 2.2\) of type str\.'
        , lambda: I.expr(I.prelude._ChoiceConstr, True, (u(101), u('a')))
        )

  def testEqVars(self):
    for debug in [True, False]:
      I = curry.interpreter.Interpreter(flags={'debug':debug})
      unknown = I.symbol('Prelude.unknown')
      q = I.symbol('Prelude.?')
      x,y = list(I.eval(q, unknown, unknown))
      self.assertMayRaise(
          None
        , lambda: I.expr(I.prelude._EqVars, True, (x, y))
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct an _EqVars node binding variable 0 to itself\.'
        , lambda: I.expr(I.prelude._EqVars, True, (x, x))
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct an _EqVars node from an argument '
           '\(in position 2.1\) of type int\.'
        , lambda: I.expr(I.prelude._EqVars, True, (u(1), y))
        )
      self.assertMayRaiseRegexp(
          TypeError if debug else None
        , r'Cannot construct an _EqVars node from an argument '
           '\(in position 2.2\) of type str\.'
        , lambda: I.expr(I.prelude._EqVars, True, (x, u('a')))
        )

  def testCoverage(self):
    self.assertEqual(tc._typecategory(list), ())
    self.assertEqual(tc._articlefor(''), 'a')

