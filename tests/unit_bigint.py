'''Canonical unbounded Int values in arithmetic, literals, and the boundary.'''
import cytest # from ./lib; must be first
import copy, curry, gc, io, math, unittest
from curry.backends.cxx import curryrtbindings as rt
from curry.icurry import IInt, json, readcurry

LO, HI = -(1 << 63), (1 << 63) - 1
BIG = 10 ** 30

class TestBigInt(cytest.TestCase):
  def test_python_boundary(self):
    for n in [LO-1, LO, HI, HI+1, BIG, -BIG, 2**200, -2**200]:
      with self.subTest(n=n):
        term = curry.term(n, type='Int')
        self.assertEqual(curry.eval(term).one(), n)
        self.assertEqual(curry.typeof(term), 'Int')
        self.assertEqual(curry.show(term), '(' + str(n) + ')' if n < 0 else str(n))

  def test_python_digit_limit_is_not_an_int_limit(self):
    for n in [10**5000, -(10**5000)]:
      digits = ('-' if n < 0 else '') + '1' + '0'*5000
      term = curry.term(n, type='Int')
      self.assertEqual(curry.eval(term).one(), n)
      self.assertEqual(curry.show(term), '(' + digits + ')' if n < 0 else digits)
      self.assertEqual(json.loads(json.dumps(IInt(n))).value, n)
      decoded = readcurry.load(io.StringIO('IInt (' + digits + ')'))
      self.assertEqual(decoded.value, n)

  def test_float_rounding(self):
    P = curry.import_('Prelude')
    for tail in [-1, 0, 1]:
      for sign in [-1, 1]:
        n = sign * ((1 << 120) + (1 << 67) + tail)
        self.assertEqual(curry.eval(P.toFloat(n)).one(), float(n))
        goal = curry.term(P.fromInt(n), type='Float')
        self.assertEqual(curry.eval(goal).one(), float(n))

  def test_char_range(self):
    P = curry.import_('Prelude')
    # The public Prelude wrapper retains its existing clamp. The primitive
    # rejects a big operand before the machine-word cast.
    self.assertEqual(curry.eval(P.chr(BIG)).one(), chr(0x10ffff))
    self.assertEqual(curry.eval(P.chr(-BIG)).one(), chr(0))
    self.assertEqual(curry.eval(P.ord(curry.Char('A'))).one(), 65)
    with self.assertRaises(curry.IntOverflowError):
      cytest.raw.values(cytest.raw.expr(P['prim_chr'], BIG, typed=True)).one()

  def test_every_binary_operation(self):
    P = curry.import_('Prelude')
    for x in [LO-1, LO, LO+1, -1, 0, 1, HI-1, HI, HI+1, BIG, -BIG]:
      for y in [-BIG, LO, -3, -1, 0, 1, 3, HI, BIG]:
        for name, expected in [('plusInt', x+y), ('minusInt', x-y), ('timesInt', x*y)]:
          with self.subTest(name=name, x=x, y=y):
            self.assertEqual(curry.eval(P[name](x,y)).one(), expected)
        if y:
          q = (abs(x) // abs(y)) * (-1 if (x < 0) != (y < 0) else 1)
          for name, expected in [('divInt',x//y), ('modInt',x%y),
                                 ('quotInt',q), ('remInt',x-q*y)]:
            with self.subTest(name=name, x=x, y=y):
              self.assertEqual(curry.eval(P[name](x,y)).one(), expected)

  def test_canonical_nodes(self):
    P = curry.import_('Prelude')
    small = cytest.raw.values(P.minusInt(HI+1, 1)).one()
    large = cytest.raw.values(P.plusInt(HI, 1)).one()
    a = small
    b = large
    self.assertEqual(a.info.format, 'i')
    self.assertEqual(b.info.format, 'x')
    first = rt.make_integer(str(BIG))
    second = rt.make_integer(str(BIG))
    self.assertEqual(first, second)
    self.assertEqual(hash(first), hash(second))
    arithmetic = cytest.raw.values(P.plusInt(BIG-1, 1)).one()
    parsed = cytest.raw.values(curry.parse(str(BIG) + ' :: Int')).one()
    for other in [arithmetic, parsed]:
      self.assertEqual(first, other)
      self.assertEqual(hash(first), hash(other))
    self.assertEqual(first.copy(), first)
    self.assertEqual(copy.deepcopy(first), first)

  def test_json(self):
    for n in [LO-1, HI+1, BIG, -(2**200)]:
      encoded = json.dumps(IInt(n))
      self.assertIn('"%s"' % n, encoded)
      self.assertEqual(json.loads(encoded).value, n)

  def test_bindings(self):
    goal = curry.parse('x =:= 10^30 &> x where x free')
    answer = curry.solve(goal).one()
    self.assertEqual(answer.value, BIG)
    self.assertEqual(answer.bindings['x'], BIG)

  def test_module_modes_and_checker(self):
    source = '''
import Data.List (product)
answer :: [Int]
answer = [2^200, product [1..30], f (10^30), f 7]
f :: Int -> Int
f 1000000000000000000000000000000 = 11
f 7 = 12
'''
    for mode in ['new', 'tiered', 'off']:
      with self.subTest(mode=mode):
        curry.reset(backend='cxx', interpret=mode, checker=True)
        M = curry.compile(source, name='BigMode' + mode)
        self.assertEqual(curry.eval(M.answer).one(), [2**200, math.factorial(30), 11, 12])
        if mode == 'off':
          self.assertFalse(rt.icurry_is_interpreted(M.answer.info))

  def test_unary_and_conversions(self):
    P = curry.import_('Prelude')
    for n in [LO-1, LO, HI, HI+1, BIG, -BIG]:
      self.assertEqual(curry.eval(P.negate(n)).one(), -n)
      self.assertEqual(curry.eval(P.abs(n)).one(), abs(n))
      self.assertEqual(curry.eval(P.signum(n)).one(), (n > 0) - (n < 0))
      self.assertEqual(curry.eval(P.succ(n)).one(), n+1)
      self.assertEqual(curry.eval(P.pred(n)).one(), n-1)
      self.assertEqual(curry.eval(P.toFloat(n)).one(), float(n))
      text = str(n)
      self.assertEqual(curry.eval(curry.term(P.read(text), type='Int')).one(), n)
    for name, operation in [('truncate', math.trunc), ('round', round),
                            ('floor', math.floor), ('ceiling', math.ceil)]:
      for value in [1e30, -1e30, float(2**63), -float(2**63)]:
        self.assertEqual(curry.eval(curry.term(P[name](value), type='Int')).one(), operation(value))
    for name in ['divInt', 'modInt', 'quotInt', 'remInt']:
      with self.assertRaises(curry.DivisionByZeroError):
        curry.eval(P[name](BIG, 0)).one()

  def test_payload_reclamation(self):
    # Values made from Python are heap values, not module constants.  Keep a
    # batch alive, then release it, proving that foreign payloads are freed.
    gc.collect()
    for _ in range(3): rt.gc_collect()
    baseline = rt.bigint_live_count()
    values = [rt.make_integer(str(BIG+i)) for i in range(5000)]
    self.assertGreaterEqual(rt.bigint_live_count(), baseline+5000)
    del values
    gc.collect()
    for _ in range(4): rt.gc_collect()
    self.assertLess(rt.bigint_live_count(), baseline+100)

if __name__ == '__main__':
  unittest.main()
