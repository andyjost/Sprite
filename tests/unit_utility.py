import cytest # from ./lib; must be first
from curry import icurry
from curry.utility.binding import binding, del_
from curry.utility import encoding
from curry.utility.visitation import dispatch, instance_checker
import collections
import re
import unittest


class TestUtility(unittest.TestCase):
  def testEncode(self):
    names = [
        # 'ni__eq__eq_'
        'ni_Prelude_dot__eq__eq_'
      , 'ni_Prelude_dot__eq__eq__0'
      , 'ni_Prelude_dot__eq__eq__1'
      , 'ni_Prelude_dot__eq__eq__2'
      , 'ni_Prelude_dot__eq__eq__3'
      ]
    for n in range(len(names)):
      self.assertEqual(
          encoding.encode('Prelude.==', disallow=names[:n])
        , names[n]
        )


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

  def testVisitICurry(self):
    '''Visit elements of an ICurry module.'''
    tally = collections.defaultdict(int)

    @dispatch.on('node')
    def count(node):
      if isinstance(node, collections.Sequence):
        map(count, node)
      elif isinstance(node, collections.Mapping):
        map(count, node.values())
      # else:
      #   raise TypeError("'%s' not handled" % str(type(node)))

    @count.when(icurry.IModule)
    def count(node):
      tally['modules'] += 1
      count(node.types)
      count(node.functions)

    @count.when(icurry.IConstructor)
    def count(node):
      tally['constructors'] += 1

    @count.when(icurry.IFunction)
    def count(node):
      # Ignore generated functions.
      if '#' not in node.name:
        tally['functions'] += 1

    @count.when(icurry.IDataType)
    def count(node):
      tally['datatypes'] += 1
      count(node.constructors)

    json = open('data/json/example.json', 'rb').read()
    icur = icurry.json.parse(json)
    count(icur)
    self.assertEqual(tally, {'modules':1, 'datatypes':1, 'constructors':2, 'functions':4})

  def testCoverage(self):
    seq = instance_checker(yes=collections.Sequence, no=str)
    self.assertIsInstance([], seq)
    self.assertNotIsInstance('', seq)
    self.assertIsInstance('', (seq,str))
    self.assertTrue(issubclass(list, seq))
    self.assertFalse(issubclass(str, seq))
    self.assertTrue(issubclass(str, (seq,str)))


class TestBinding(unittest.TestCase):
  def setUp(self):
    self.mapping = {'a':1, 'b':2}

  def testReplace(self):
    with binding(self.mapping, 'a', 10):
      self.assertEqual(self.mapping['a'], 10)
    self.assertEqual(self.mapping['a'], 1)

  def testCreate(self):
    with binding(self.mapping, 'x', None):
      self.assertIs(self.mapping['x'], None)
    self.assertFalse('x' in self.mapping)

  def testDelete(self):
    with binding(self.mapping, 'a', del_):
      self.assertFalse('a' in self.mapping)
    self.assertTrue('a' in self.mapping)
    self.assertEqual(self.mapping['a'], 1)

  def testDeleteNonexistent(self):
    with binding(self.mapping, 'x', del_):
      self.assertFalse('x' in self.mapping)
    self.assertFalse('x' in self.mapping)
