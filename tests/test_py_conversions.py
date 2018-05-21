import cytest # from ./lib; must be first
from curry.interpreter import Interpreter
from cytest import bootstrap
import numpy as np

class TestPyConversions(cytest.TestCase):
  '''Tests conversions between Python and Curry.'''
  @classmethod
  def setUpClass(cls):
    cls.EXAMPLE = bootstrap.getexample()
    cls.MYLIST = bootstrap.getlist()

  @classmethod
  def tearDownClass(cls):
    del cls.EXAMPLE
    del cls.MYLIST

  def testExpressionBuilding(self):
    '''Use Interpreter.expr to build expressions.'''
    interp = Interpreter()

    # Int.
    one = interp.expr(1)
    self.assertEqual(repr(one), '<Int [1]>')
    self.assertEqual(str(one), '1')

    # Float.
    pi = interp.expr(3.14)
    self.assertEqual(repr(pi), '<Float [3.14]>')
    self.assertEqual(str(pi), '3.14')

    # Node.
    example = interp.import_(self.EXAMPLE)[0]
    A = interp.expr(example.A)
    self.assertEqual(repr(A), '<A []>')
    self.assertEqual(str(A), 'A')

    # Nodes with nonzero arity.
    mylist = interp.import_(self.MYLIST)
    nil = interp.expr(mylist.Nil)
    self.assertEqual(repr(nil), '<Nil []>')
    self.assertEqual(str(nil), '[]')
    #
    cons = interp.expr(mylist.Cons, 1, mylist.Nil)
    self.assertEqual(repr(cons), '<Cons [<Int [1]>, <Nil []>]>')
    self.assertEqual(str(cons), '[1]')
    #
    cons = interp.expr(mylist.Cons, 0, cons)
    self.assertEqual(str(cons), '[0, 1]')

    # Nested data specifications.
    list2 = interp.expr(mylist.Cons, 0, [mylist.Cons, 1, mylist.Nil])
    self.assertEqual(cons, list2)
    list3 = interp.expr(mylist.Cons, 1, [mylist.Cons, 2, mylist.Nil])
    self.assertNotEqual(list2, list3)

    # Negative tests.
    self.assertRaisesRegexp(
        TypeError
      , r'cannot build a Curry expression from type "dict"'
      , lambda: interp.expr({})
      )

  def testToPython(self):
    '''Test the conversions from Curry to Python.'''
    interp = Interpreter(flags={'debug':True})
    # Bool
    x = interp.expr(True)
    self.assertNotEqual(x, True)
    self.assertEqual(interp.topython(x), True)
    x = interp.expr(False)
    self.assertNotEqual(x, False)
    self.assertEqual(interp.topython(x), False)
    # Int
    x = interp.expr(1)
    self.assertNotEqual(x, 1)
    self.assertEqual(interp.topython(x), 1)
    # Float
    x = interp.expr(1.2)
    self.assertNotEqual(x, 1.2)
    self.assertEqual(interp.topython(x), 1.2)
    # Char
    x = interp.expr('a')
    self.assertNotEqual(x, 'a')
    self.assertEqual(interp.topython(x), 'a')
    # List
    x = interp.tocurry([1,2,3])
    self.assertNotEqual(x, [1,2,3])
    self.assertEqual(interp.topython(x), [1,2,3])
    # Tuple
    x = interp.tocurry((1,2,3))
    self.assertNotEqual(x, (1,2,3))
    self.assertEqual(interp.topython(x), (1,2,3))
    # TODO: it needs to make an I/O type.
    # # Iterator.
    # interp.path.insert(0, 'data/curry')
    # interp.import_('head')
    # seq = itertools.count() # infinite sequence.
    # x = interp.tocurry(seq)

    # Complex/nested.
    v = [[('a', 1.2, [1,2]), ('b', 3.1, [3,4])]]
    x = interp.tocurry(v)
    self.assertNotEqual(x, v)
    self.assertEqual(interp.topython(x), v)

    # Test the list type check.
    self.assertRaisesRegexp(
        TypeError, r"malformed Curry list containing types \('Float', 'Int'\)"
      , lambda: interp.tocurry([1,2.,3])
      )

  def testTypesToPython(self):
    interp = Interpreter()
    self.assertEqual(interp.tocurry(int), interp.type('Prelude.Int'))
    self.assertEqual(interp.tocurry(float), interp.type('Prelude.Float'))
    self.assertEqual(interp.tocurry(str), interp.type('Prelude.Char'))
    self.assertEqual(interp.tocurry(bool), interp.type('Prelude.Bool'))
    self.assertEqual(interp.tocurry(list), interp.type('Prelude.List'))
    #
    self.assertEqual(interp.tocurry(np.float16), interp.type('Prelude.Float'))
    self.assertEqual(interp.tocurry(np.float32), interp.type('Prelude.Float'))
    self.assertEqual(interp.tocurry(np.int8), interp.type('Prelude.Int'))
    self.assertEqual(interp.tocurry(np.byte), interp.type('Prelude.Int'))
    #
    # Note: the Python tuple type has no analog in Curry, where each arity is a
    # distinct type.
    self.assertRaises(TypeError, lambda: interp.tocurry(tuple))
    self.assertRaises(TypeError, lambda: interp.tocurry(np.complex64))
