import cytest # from ./lib; must be first
from curry.interpreter import runtime
from curry.runtime import UNDETERMINED, LEFT, RIGHT
import curry
import itertools

class TestConstraintStore(cytest.TestCase):
  def testShared(self):
    o = runtime.Shared(dict)
    self.assertTrue(o.unique)
    p = o
    self.assertTrue(o.unique and p.unique)
    self.assertTrue(o.refcnt == p.refcnt == 1)
    o.read
    self.assertTrue(o.unique and p.unique)
    self.assertTrue(o.refcnt == p.refcnt == 1)
    self.assertEqual(len(o), 0)
    o.write['a'] = 1
    self.assertEqual(len(o), 1)
    self.assertTrue(o.unique and p.unique)
    self.assertTrue(o.refcnt == p.refcnt == 1)
    self.assertTrue(o.read['a'] == p.read['a'] == 1)
    p = o.__copy__()
    self.assertTrue(not o.unique and not p.unique)
    self.assertTrue(o.refcnt == p.refcnt == 2)
    self.assertTrue(o.read['a'] == p.read['a'] == 1)
    p.write
    self.assertTrue(o.unique and p.unique)
    self.assertTrue(o.refcnt == p.refcnt == 1)
    self.assertTrue(o.read['a'] == p.read['a'] == 1)
    p.write['a'] = 2
    self.assertTrue(o.unique and p.unique)
    self.assertTrue(o.refcnt == p.refcnt == 1)
    self.assertTrue('a' in o)
    self.assertTrue('a' in p)
    self.assertEqual(o.read['a'], 1)
    self.assertEqual(p.read['a'], 2)

  def equivalenceChecker(self, store):
    def eq(*args):
      prod = itertools.product(*[list(args)]*2)
      for a,b in (pair for pair in prod if pair[0] != pair[1]):
        self.assertIn(a, store)
        self.assertTrue(store.find(a, b))
    def ne(a, b):
      self.assertFalse(store.find(a, b))
    return eq, ne

  def testUnionFindBasic(self):
    cs = runtime.UnionFind()
    eq,ne = self.equivalenceChecker(cs)
    self.assertEqual(cs.root(0), 0)
    eq(0,0)
    self.assertTrue(cs.find(0,0))
    #
    self.assertEqual(cs.root(5), 5)
    eq(0,0)
    ne(0,5)
    #
    cs.unite(0,5)
    eq(0,5)
    #
    cs.unite(0,1)
    eq(0,1,5)
    ne(0,2)
    #
    cs.unite(2,5)
    eq(0,1,2,5)
    ne(0,3)

  def testUnionFindSharing(self):
    a = runtime.UnionFind()
    b = a.__copy__()
    eqa,nea = self.equivalenceChecker(a)
    eqb,neb = self.equivalenceChecker(b)
    self.assertEqual(id(a.choices.obj), id(b.choices.obj))
    a.unite(0,1)
    self.assertNotEqual(id(a.choices.obj), id(b.choices.obj))
    eqa(0,1)
    neb(0,1)

  def checkFingerprint(self, f, values={}):
    # Check that every element in the fingerprint is ``UNDETERMINED``, except
    # those mentioned in ``values``.
    f = getattr(f, 'fingerprint', f)
    self.assertTrue(all(
        f.get(i) == values.get(i, UNDETERMINED) for i in xrange(f.capacity)
      ))

  def testFrameFork(self):
    Unit = curry.symbol('Prelude.()')
    e = curry.expr(curry.symbol('Prelude.?'), -10, 10)
    curry.getInterpreter().step(e)
    cid,l,r = e
    assert cid == 0 # cytest.TestCase should have reset curry.
    #
    frame = runtime.Frame(e)
    self.checkFingerprint(frame)
    #
    buf = list(frame.fork())
    self.assertTrue(all(x.expr is y for x,y in zip(buf, [l,r])))
    self.checkFingerprint(buf[0], {cid:LEFT})
    self.checkFingerprint(buf[1], {cid:RIGHT})
    #
    lhs,rhs = buf
    frame = runtime.Frame(e, lhs)
    buf = list(frame.fork())
    self.assertIs(buf.pop().expr, l)
    self.assertFalse(buf)
    #
    frame = runtime.Frame(e, rhs)
    buf = list(frame.fork())
    self.assertIs(buf.pop().expr, r)
    self.assertFalse(buf)
    #
    e = curry.expr(curry.symbol('Prelude.?'), -10, 10)
    curry.getInterpreter().step(e)
    cid2,_,_ = e
    self.assertNotEqual(cid, cid2)
    frame = runtime.Frame(e, frame)
    buf = list(frame.fork())
    self.assertEqual(len(buf), 2)
    self.checkFingerprint(buf[0], {cid:RIGHT, cid2:LEFT})
    self.checkFingerprint(buf[1], {cid:RIGHT, cid2:RIGHT})

