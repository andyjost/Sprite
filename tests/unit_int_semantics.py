'''Unbounded Int arithmetic and retained errors for invalid conversions and division.'''
import cytest # from ./lib; must be first
import curry, math, textwrap, unittest

INT_MIN = -(1 << 63)
INT_MAX = (1 << 63) - 1

def values(*goal):
  '''The values of a goal as Python objects.'''
  return list(curry.eval(goal[0](*goal[1:]) if len(goal) > 1 else goal[0]))

class TestIntSemantics(cytest.TestCase):
  def setUp(self):
    self.P = curry.import_('Prelude')

  def sym(self, name):
    return curry.import_('Prelude')[name]

  def assertError(self, message, *goal):
    '''The goal raises EvaluationError with exactly ``message``.'''
    error = curry.DivisionByZeroError if message.startswith('division by zero:') else curry.IntOverflowError
    with self.assertRaises(error) as cm:
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
    for value in [INT_MAX + 1, INT_MIN - 1, 10**30, -(10**30), 2**64]:
      self.assertEqual(values(curry.term(value)), [value])
      self.assertEqual(cytest.raw.interp().topython(cytest.raw.expr(value)), value)
      self.assertEqual(values(value), [value])
      self.assertEqual(values(self.P.Just(value))[0].args, (value,))
      self.assertEqual(values(curry.term([1, value])), [[1, value]])
      node = cytest.raw.interp().backend.make_node(self.P.Int, value)
      self.assertEqual(cytest.raw.interp().topython(node), value)

  def test_addition(self):
    plus = self.sym('+')
    self.assertEqual(values(plus, INT_MAX, 1), [(INT_MAX) + (1)])
    self.assertEqual(values(plus, 1, INT_MAX), [(1) + (INT_MAX)])
    self.assertEqual(values(plus, 2**62, 2**62), [(2**62) + (2**62)])
    self.assertEqual(values(plus, INT_MIN, -1), [(INT_MIN) + (-1)])

  def test_subtraction(self):
    minus = self.sym('-')
    self.assertEqual(values(minus, INT_MIN, -1), [INT_MIN + 1])
    self.assertEqual(values(minus, INT_MAX, INT_MAX), [0])
    self.assertEqual(values(minus, INT_MIN, 1), [(INT_MIN) - (1)])
    self.assertEqual(values(minus, INT_MAX, -1), [(INT_MAX) - (-1)])
    self.assertEqual(values(minus, -1, INT_MAX), [INT_MIN])
    self.assertEqual(values(minus, -2, INT_MAX), [(-2) - (INT_MAX)])

  def test_multiplication(self):
    times = self.sym('*')
    self.assertEqual(values(times, 2**31, 2**31), [2**62])
    self.assertEqual(values(times, 2**32, 2**31 - 1), [2**63 - 2**32])
    self.assertEqual(values(times, INT_MIN, 1), [INT_MIN])
    self.assertEqual(values(times, 3037000499, 3037000499), [3037000499**2])
    self.assertEqual(values(times, INT_MAX, 0), [0])
    self.assertEqual(values(times, 2**32, 2**31), [(2**32) * (2**31)])
    self.assertEqual(values(times, 3037000500, 3037000500), [(3037000500) * (3037000500)])
    self.assertEqual(values(times, INT_MIN, -1), [(INT_MIN) * (-1)])
    self.assertEqual(values(times, 2, INT_MIN), [(2) * (INT_MIN)])

  def test_negate(self):
    # Negation and abs promote the inline negative endpoint.
    self.assertEqual(values(self.P.negate, INT_MIN), [abs(INT_MIN)])
    self.assertEqual(values(self.P.abs, INT_MIN), [abs(INT_MIN)])
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
    self.assertEqual(values(self.P.div, INT_MIN, -1), [(INT_MIN) // (-1)])
    self.assertEqual(values(self.P.quot, INT_MIN, -1), [(INT_MIN) // (-1)])

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
      self.assertEqual(values(convert, 1e30), [int(1e30)])
      self.assertEqual(values(convert, -1e30), [int(-1e30)])
      self.assertEqual(values(convert, 2.0**63), [int(2.0**63)])
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
    module = curry.compile(textwrap.dedent('\n        big :: Int\n        big = 99999999999999999999\n        isBig :: Int -> Bool\n        isBig 99999999999999999999 = True\n        isBig _ = False\n        bottom :: Int\n        bottom = -9223372036854775808\n        '), name='BigLiterals')
    self.assertEqual(values(module.big), [99999999999999999999])
    self.assertEqual(values(module.isBig, 1), [False])
    # Curry keeps both overlapping rules for the matching literal.
    self.assertCountEqual(values(module.isBig, 99999999999999999999), [True, False])
    self.assertEqual(values(module.bottom), [INT_MIN])
    self.assertEqual(values(curry.parse('99999999999999999999 :: Int')), [99999999999999999999])

  def test_read_outside_the_range(self):
    # Reading crosses the inline boundary without losing digits.
    module = curry.compile(textwrap.dedent('''
        readsOk, readsBig :: [(Int, String)]
        readsOk = reads "9223372036854775807"
        readsBig = reads "9223372036854775808"

        readOk, readBig :: Int
        readOk = read "9223372036854775807"
        readBig = read "9223372036854775808"
        '''), name='ReadBig')
    self.assertEqual(values(module.readsOk), [[(INT_MAX, '')]])
    self.assertEqual(values(module.readOk), [INT_MAX])
    self.assertEqual(values(module.readsBig), [[(INT_MAX + 1, '')]])
    self.assertEqual(values(module.readBig), [INT_MAX + 1])

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
        '''), name='IntSemantics')
    self.assertEqual(values(module.ok), [INT_MAX])
    self.assertEqual(values(module.fac, 20), [math.factorial(20)])
    self.assertEqual(values(module.big), [INT_MAX + 1])
    self.assertError('division by zero: div 1 0', module.zero)
    self.assertEqual(values(module.fac, 21), [math.factorial(21)])

if __name__ == '__main__':
  unittest.main()
