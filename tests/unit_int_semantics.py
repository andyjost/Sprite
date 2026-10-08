'''
Tests of the Int of both backends: a signed 64-bit integer with an error at
the boundary (issue #105), and the integer division by zero (issue #106).

A Python int outside the range is a CurryTypeError where it enters a node.
An addition, a subtraction, a multiplication, or a negation whose result is
outside the range raises EvaluationError, as do div and quot of the minimum
by -1 and the conversions of a Float outside the range; a division by zero
raises EvaluationError.  The messages name the operation and its operands,
and they are the same on both backends.
'''
import cytest # from ./lib; must be first
import curry, math, re, textwrap, unittest

INT_MIN = -(1 << 63)
INT_MAX = (1 << 63) - 1
RANGE_TEXT = \
    'is outside the range of Int (-9223372036854775808 to 9223372036854775807)'

def values(*goal):
  '''The values of a goal as Python objects.'''
  return list(curry.eval(*goal, converter='topython'))

class TestIntSemantics(cytest.TestCase):
  def setUp(self):
    self.P = curry.import_('Prelude')

  def sym(self, name):
    return curry.symbol('Prelude.' + name)

  def assertError(self, message, *goal):
    '''The goal raises EvaluationError with exactly ``message``.'''
    with self.assertRaises(curry.EvaluationError) as cm:
      values(*goal)
    self.assertEqual(str(cm.exception), message)

  def test_boundary_values(self):
    self.assertEqual(values(INT_MAX), [INT_MAX])
    self.assertEqual(values(INT_MIN), [INT_MIN])
    self.assertEqual(values(self.sym('+'), INT_MAX - 1, 1), [INT_MAX])
    self.assertEqual(values(self.sym('-'), INT_MIN + 1, 1), [INT_MIN])
    self.assertEqual(values(self.sym('+'), 2**62, 2**62 - 1), [INT_MAX])
    self.assertEqual(values(self.P.negate, INT_MAX), [INT_MIN + 1])
    self.assertEqual(values(self.P.negate, INT_MIN + 1), [INT_MAX])

  def test_int_outside_the_range(self):
    # The typed and the raw routes refuse the value where it enters a node.
    for value in [INT_MAX + 1, INT_MIN - 1, 10**30, -(10**30), 2**64]:
      with self.assertRaises(curry.CurryTypeError):
        curry.expr(value)
      with self.assertRaises(curry.CurryTypeError):
        curry.raw_expr(value)
      with self.assertRaises(curry.CurryTypeError):
        list(curry.eval(value))
      with self.assertRaises(curry.CurryTypeError):
        curry.expr(self.P.Just, value)
      with self.assertRaises(curry.CurryTypeError):
        curry.expr([1, value])
    # The message, at the node.
    make_node = curry.getInterpreter().backend.make_node
    with self.assertRaises(curry.CurryTypeError) as cm:
      make_node(self.P.Int, INT_MAX + 1)
    self.assertEqual(str(cm.exception), '9223372036854775808 ' + RANGE_TEXT)
    with self.assertRaises(curry.CurryTypeError) as cm:
      make_node(self.P.Int, INT_MIN - 1)
    self.assertEqual(str(cm.exception), '-9223372036854775809 ' + RANGE_TEXT)
    with self.assertRaises(curry.CurryTypeError) as cm:
      make_node(self.P.Int, 10**30)
    self.assertEqual(str(cm.exception), '%d %s' % (10**30, RANGE_TEXT))
    # The ends of the range are values.
    self.assertEqual(curry.topython(make_node(self.P.Int, INT_MAX)), INT_MAX)
    self.assertEqual(curry.topython(make_node(self.P.Int, INT_MIN)), INT_MIN)

  def test_addition(self):
    plus = self.sym('+')
    self.assertError('integer overflow: 9223372036854775807 + 1', plus, INT_MAX, 1)
    self.assertError('integer overflow: 1 + 9223372036854775807', plus, 1, INT_MAX)
    self.assertError(
        'integer overflow: 4611686018427387904 + 4611686018427387904'
      , plus, 2**62, 2**62
      )
    self.assertError(
        'integer overflow: (-9223372036854775808) + (-1)', plus, INT_MIN, -1
      )

  def test_subtraction(self):
    minus = self.sym('-')
    self.assertEqual(values(minus, INT_MIN, -1), [INT_MIN + 1])
    self.assertEqual(values(minus, INT_MAX, INT_MAX), [0])
    self.assertError('integer overflow: (-9223372036854775808) - 1', minus, INT_MIN, 1)
    self.assertError('integer overflow: 9223372036854775807 - (-1)', minus, INT_MAX, -1)
    self.assertEqual(values(minus, -1, INT_MAX), [INT_MIN])
    self.assertError(
        'integer overflow: (-2) - 9223372036854775807', minus, -2, INT_MAX
      )

  def test_multiplication(self):
    times = self.sym('*')
    self.assertEqual(values(times, 2**31, 2**31), [2**62])
    self.assertEqual(values(times, 2**32, 2**31 - 1), [2**63 - 2**32])
    self.assertEqual(values(times, INT_MIN, 1), [INT_MIN])
    self.assertEqual(values(times, 3037000499, 3037000499), [3037000499**2])
    self.assertEqual(values(times, INT_MAX, 0), [0])
    self.assertError('integer overflow: 4294967296 * 2147483648', times, 2**32, 2**31)
    self.assertError('integer overflow: 3037000500 * 3037000500', times, 3037000500, 3037000500)
    self.assertError('integer overflow: (-9223372036854775808) * (-1)', times, INT_MIN, -1)
    self.assertError('integer overflow: 2 * (-9223372036854775808)', times, 2, INT_MIN)

  def test_negate(self):
    # negate x is 0 - x in the Prelude, and the message names that
    # subtraction; abs of a negative value is negate.
    self.assertError('integer overflow: 0 - (-9223372036854775808)', self.P.negate, INT_MIN)
    self.assertError('integer overflow: 0 - (-9223372036854775808)', self.P.abs, INT_MIN)
    self.assertEqual(values(self.P.abs, INT_MIN + 1), [INT_MAX])

  def test_division_semantics(self):
    # The signs of div, mod, quot and rem, and the exact quotients of values
    # above 2**53, which a division through a double gets wrong.
    pairs = [
        (7, 2), (-7, 2), (7, -2), (-7, -2), (6, 3), (-6, 3), (0, 5)
      , (2**53 + 1, 1), (2**53 + 1, 3), (2**53 + 1, -3)
      , (INT_MAX, 3), (INT_MAX, -2), (INT_MIN, 7), (INT_MIN, 2**40), (INT_MIN, 1)
      , (INT_MAX, INT_MAX), (INT_MIN, INT_MIN), (1, INT_MIN), (-1, INT_MAX)
      ]
    for x, y in pairs:
      q = abs(x) // abs(y)
      if (x < 0) != (y < 0):
        q = -q
      r = x - y * q
      self.assertEqual(values(self.P.div, x, y), [x // y], (x, y))
      self.assertEqual(values(self.P.mod, x, y), [x % y], (x, y))
      self.assertEqual(values(self.P.quot, x, y), [q], (x, y))
      self.assertEqual(values(self.P.rem, x, y), [r], (x, y))
    self.assertEqual(values(self.P.divMod, 7, -2), [(-4, -1)])
    self.assertEqual(values(self.P.quotRem, 7, -2), [(-3, 1)])
    # The one quotient outside the range; its remainder is zero.
    self.assertEqual(values(self.P.mod, INT_MIN, -1), [0])
    self.assertEqual(values(self.P.rem, INT_MIN, -1), [0])
    self.assertError(
        'integer overflow: div (-9223372036854775808) (-1)', self.P.div, INT_MIN, -1
      )
    self.assertError(
        'integer overflow: quot (-9223372036854775808) (-1)', self.P.quot, INT_MIN, -1
      )

  def test_division_by_zero(self):
    for name in ['div', 'mod', 'quot', 'rem']:
      operation = getattr(self.P, name)
      self.assertError('division by zero: %s 1 0' % name, operation, 1, 0)
      self.assertError('division by zero: %s (-1) 0' % name, operation, -1, 0)
      self.assertError('division by zero: %s 0 0' % name, operation, 0, 0)
      self.assertError(
          'division by zero: %s 9223372036854775807 0' % name, operation, INT_MAX, 0
        )
    with self.assertRaisesRegex(curry.EvaluationError, r'^division by zero: (div|mod) 1 0$'):
      values(self.P.divMod, 1, 0)
    with self.assertRaisesRegex(curry.EvaluationError, r'^division by zero: (quot|rem) 1 0$'):
      values(self.P.quotRem, 1, 0)

  def test_float_division_by_zero(self):
    # Not an error: IEEE 754 on both backends.
    divide = self.sym('/')
    self.assertEqual(values(divide, 1.0, 0.0), [math.inf])
    self.assertEqual(values(divide, -1.0, 0.0), [-math.inf])
    self.assertEqual(values(divide, 1.0, -0.0), [-math.inf])
    self.assertEqual(values(divide, math.inf, 0.0), [math.inf])
    self.assertTrue(math.isnan(values(divide, 0.0, 0.0)[0]))
    self.assertEqual(values(divide, 1.0, 4.0), [0.25])

  def test_conversions(self):
    P = self.P
    largest_below = 2.0**63 - 1024 # the largest double below 2**63
    for name in ['truncate', 'round', 'ceiling', 'floor']:
      convert = getattr(P, name)
      self.assertEqual(values(convert, 1e18), [10**18], name)
      self.assertEqual(values(convert, -1e18), [-10**18], name)
      self.assertEqual(values(convert, -2.0**63), [INT_MIN], name)
      self.assertEqual(values(convert, largest_below), [2**63 - 1024], name)
      self.assertEqual(values(convert, 0.0), [0], name)
      # ceiling and floor convert through truncate, and the message names it.
      named = 'round' if name == 'round' else 'truncate'
      self.assertError('integer overflow: %s 1.0e+30' % named, convert, 1e30)
      self.assertError('integer overflow: %s (-1.0e+30)' % named, convert, -1e30)
      self.assertError(
          'integer overflow: %s 9.223372036854776e+18' % named, convert, 2.0**63
        )
      self.assertError('integer overflow: %s Infinity' % named, convert, math.inf)
      self.assertError('integer overflow: %s (-Infinity)' % named, convert, -math.inf)
      self.assertError('integer overflow: %s NaN' % named, convert, math.nan)
    self.assertEqual(values(P.truncate, 2.7), [2])
    self.assertEqual(values(P.truncate, -2.7), [-2])
    self.assertEqual(values(P.round, 2.4), [2])
    self.assertEqual(values(P.round, 2.6), [3])
    self.assertEqual(values(P.round, -2.6), [-3])
    self.assertEqual(values(P.ceiling, 2.1), [3])
    self.assertEqual(values(P.ceiling, -2.1), [-2])
    self.assertEqual(values(P.floor, 2.9), [2])
    self.assertEqual(values(P.floor, -2.1), [-3])

  def test_literal_outside_the_range(self):
    # An Int literal of a Curry source outside the range is the
    # CurryTypeError of the node, as a Python int is.  The backends raise it
    # at different times: when the module loads, or when the function is
    # first evaluated.
    big_text = re.escape('99999999999999999999 ' + RANGE_TEXT)
    with self.assertRaisesRegex(curry.CurryTypeError, big_text):
      module = curry.compile(textwrap.dedent('''
          big :: Int
          big = 99999999999999999999
          '''), modulename='BigLiteral')
      values(module.big)
    with self.assertRaisesRegex(curry.CurryTypeError, big_text):
      values(curry.compile('99999999999999999999 :: Int', mode='expr'))
    # A literal of a case pattern is checked as well: the C++ generator
    # spells it as a constant of the switch.
    with self.assertRaisesRegex(curry.CurryTypeError, big_text):
      module = curry.compile(textwrap.dedent('''
          isBig :: Int -> Bool
          isBig 99999999999999999999 = True
          isBig _ = False
          '''), modulename='BigPattern')
      values(module.isBig, 1)
    # The maximum is a literal.  The minimum is not: -9223372036854775808
    # is the negation of the literal 9223372036854775808, which is outside
    # the range; -9223372036854775807 - 1 spells it.
    module = curry.compile(textwrap.dedent('''
        top :: Int
        top = 9223372036854775807

        bottom :: Int
        bottom = -9223372036854775807 - 1
        '''), modulename='EdgeLiteral')
    self.assertEqual(values(module.top), [INT_MAX])
    self.assertEqual(values(module.bottom), [INT_MIN])
    with self.assertRaisesRegex(
        curry.CurryTypeError, re.escape('9223372036854775808 ' + RANGE_TEXT)
      ):
      module = curry.compile(textwrap.dedent('''
          bottom :: Int
          bottom = -9223372036854775808
          '''), modulename='MinLiteral')
      values(module.bottom)

  def test_read_outside_the_range(self):
    # read of a numeral outside the range fails the parse, on both backends:
    # the primitive fails, so reads and read of it have no value.
    module = curry.compile(textwrap.dedent('''
        readsOk, readsBig :: [(Int, String)]
        readsOk = reads "9223372036854775807"
        readsBig = reads "9223372036854775808"

        readOk, readBig :: Int
        readOk = read "9223372036854775807"
        readBig = read "9223372036854775808"
        '''), modulename='ReadBig')
    self.assertEqual(values(module.readsOk), [[(INT_MAX, '')]])
    self.assertEqual(values(module.readOk), [INT_MAX])
    self.assertEqual(values(module.readsBig), [])
    self.assertEqual(values(module.readBig), [])

  def test_compiled_program(self):
    # A program reaches the same primitives as a goal built from Python.
    module = curry.compile(textwrap.dedent('''
        big :: Int
        big = 9223372036854775807 + 1

        zero :: Int
        zero = 1 `div` 0

        ok :: Int
        ok = 9223372036854775806 + 1

        fac :: Int -> Int
        fac n = if n <= 1 then 1 else n * fac (n - 1)
        '''), modulename='IntSemantics')
    self.assertEqual(values(module.ok), [INT_MAX])
    self.assertEqual(values(module.fac, 20), [math.factorial(20)])
    self.assertError('integer overflow: 9223372036854775807 + 1', module.big)
    self.assertError('division by zero: div 1 0', module.zero)
    self.assertError('integer overflow: 21 * 2432902008176640000', module.fac, 21)

if __name__ == '__main__':
  unittest.main()
