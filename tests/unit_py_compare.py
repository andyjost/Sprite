import cytest # from ./lib; must be first
import curry

eq = getattr(curry.prelude, '==')
ne = getattr(curry.prelude, '/=')
lt = getattr(curry.prelude, '<')
le = getattr(curry.prelude, '<=')
gt = getattr(curry.prelude, '>')
ge = getattr(curry.prelude, '>=')

t = curry.compile('data T = A | B | C Int | D Int Int | E Int Int Int | F T T')
A, B, C, D, E, F = t.A, t.B, t.C, t.D, t.E, t.F

class TestComparisons(cytest.TestCase):

  def check(self, lhs, op, rhs, ans):
    x = next(curry.eval(op, lhs, rhs))
    self.assertEqual(x, ans)

  def suite(self, a, b): # where a < b
    '''A test suite for checking all comparisons between two values.'''
    self.check(b, eq, b, True) # eq
    self.check(b, eq, a, False)
    self.check(b, ne, b, False) # ne
    self.check(b, ne, a, True)
    self.check(b, lt, b, False) # lt
    self.check(b, lt, a, False)
    self.check(a, lt, b, True)
    self.check(b, le, b, True) # le
    self.check(b, le, a, False)
    self.check(a, le, b, True)
    self.check(b, gt, b, False) # gt
    self.check(b, gt, a, True)
    self.check(a, gt, b, False)
    self.check(b, ge, b, True) # ge
    self.check(b, ge, a, True)
    self.check(a, ge, b, False)

  def testPrim(self):
    self.suite(0, 1)
    self.suite(curry.unboxed(0), curry.unboxed(1))

  def testNullary(self):
    self.suite(A, B)

  def testUnary(self):
    self.suite([C, 0], [C, 1])
    self.suite([C, curry.unboxed(0)], [C, curry.unboxed(1)])

  def testBinary(self):
    self.suite([D, 0, 0], [D, 0, 1])
    self.suite([D, 0, 1], [D, 1, 0])
    self.suite([D, 1, 0], [D, 1, 1])

    u = curry.unboxed
    self.suite([D, u(0), 0], [D, u(0), 1])
    self.suite([D, u(0), 1], [D, u(1), 0])
    self.suite([D, u(1), 0], [D, u(1), 1])
    #
    self.suite([D, 0, u(0)], [D, 0, u(1)])
    self.suite([D, 0, u(1)], [D, 1, u(0)])
    self.suite([D, 1, u(0)], [D, 1, u(1)])
    #
    self.suite([D, u(0), u(0)], [D, u(0), u(1)])
    self.suite([D, u(0), u(1)], [D, u(1), u(0)])
    self.suite([D, u(1), u(0)], [D, u(1), u(1)])

  def testTrinary(self):
    self.suite([E, 0, 0, 0], [E, 0, 0, 1])
    self.suite([E, 0, 0, 0], [E, 0, 1, 0])
    self.suite([E, 0, 0, 0], [E, 1, 0, 0])
    self.suite([E, 0, 0, 1], [E, 0, 1, 0])
    self.suite([E, 0, 0, 1], [E, 1, 0, 0])
    self.suite([E, 0, 1, 0], [E, 0, 1, 1])
    self.suite([E, 0, 1, 0], [E, 1, 0, 0])
    self.suite([E, 1, 0, 1], [E, 1, 1, 0])
    self.suite([E, 1, 1, 0], [E, 1, 1, 1])

  def testRecursive(self):
    a = A
    b = B
    c = [C, 0]
    d = [D, 0, 0]
    e = [E, 0, 0, 0]
    #
    self.suite([F, a, a], [F, a, b])
    self.suite([F, a, a], [F, a, c])
    self.suite([F, a, a], [F, a, d])
    self.suite([F, a, a], [F, a, e])
    self.suite([F, a, a], [F, a, [F, a, a]])
    self.suite([F, a, a], [F, b, a])
    self.suite([F, a, a], [F, c, a])
    self.suite([F, a, a], [F, d, a])
    self.suite([F, a, a], [F, e, a])
    self.suite([F, a, a], [F, [F, a, a], a])
    self.suite([F, [F, a, a], a], [F, [F, a, b], a])
    self.suite([F, [F, a, e], a], [F, [F, b, a], a])
