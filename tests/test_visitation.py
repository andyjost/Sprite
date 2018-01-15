import cytest
import re
import unittest
from curry.compiler.visitation import dispatch

class TestVisitation(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    global F
    @dispatch.on('x')
    def F(x, y):
      return 'default', x, y
    @F.when(str)
    def F(x, y):
      return 'str', x, y
    @F.when(int)
    def F(x, y):
      return 'int', x, y

    global MyErr
    class MyErr(Exception): pass

    global G
    @dispatch.on('a')
    def G(a):
      raise MyErr("foo")

  @classmethod
  def tearDownClass(cls):
    global F, G, MyErr
    del F, G, MyErr

  def testBasicVisitation(self):
    o = object()
    # 2 named args.
    self.assertEqual(F(x=o,y=1.), ('default', o, 1.))
    self.assertEqual(F(x='a',y=2), ('str', 'a', 2))
    self.assertEqual(F(x=1,y='foo'), ('int', 1, 'foo'))
    # 1 named arg.
    self.assertEqual(F(o,y=1.), ('default', o, 1.))
    self.assertEqual(F('a',y=2), ('str', 'a', 2))
    self.assertEqual(F(1,y='foo'), ('int', 1, 'foo'))
    # 0 named args.
    self.assertEqual(F(o,1.), ('default', o, 1.))
    self.assertEqual(F('a',2), ('str', 'a', 2))
    self.assertEqual(F(1,'foo'), ('int', 1, 'foo'))

  def testDefaultOnly(self):
    @dispatch.on('a')
    def h(a=None):
      return 42
    self.assertEqual(h(), 42)

  def testErrorPropagation(self):
    self.assertRaisesRegexp(
        TypeError
      , re.escape(r"F() got an unexpected keyword argument 'z'")
      , lambda: F(1,z=1)
      )
    self.assertRaisesRegexp(
        TypeError, re.escape(r"G() takes exactly 1 argument (0 given)"), G
      )
    self.assertRaisesRegexp(MyErr, re.escape(r"foo"), lambda: G(1))
    self.assertRaisesRegexp(
        TypeError, re.escape(r"F() takes exactly 2 arguments (0 given)"), F
      )

  def testBadSelector(self):
    # The selector must name an actual parameter...
    def go():
      @dispatch.on('a')
      def h(x,y,z): pass
    self.assertRaisesRegexp(TypeError, "'h' has no parameter 'a'", go)

    # unless there are keywords.
    def go():
      @dispatch.on('a')
      def h(x,y,z,**kwds): pass
    go()

    # Varargs make no difference.
    def go():
      @dispatch.on('a')
      def h(x,y,z,*args): pass
    self.assertRaisesRegexp(TypeError, "'h' has no parameter 'a'", go)

    # Check the no-args corner.
    def go():
      @dispatch.on('a')
      def h(): pass
    self.assertRaisesRegexp(TypeError, "'h' has no parameter 'a'", go)


