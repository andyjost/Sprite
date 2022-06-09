import cytest # from ./lib; must be first
from curry.interpreter import Interpreter
from cytest import bootstrap
import curry
import itertools
import unittest

try:
  import numpy as np
except ImportError:
  np = None

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
    one = interp.raw_expr(1)
    self.assertEqual(repr(one), '<Int 1>')
    self.assertEqual(str(one), '1')

    # Float.
    pi = interp.raw_expr(3.14)
    self.assertEqual(repr(pi), '<Float 3.14>')
    self.assertEqual(str(pi), '3.14')

    # Node.
    example = interp.import_(self.EXAMPLE)
    A = interp.raw_expr(example.A)
    self.assertEqual(repr(A), '<A>')
    self.assertEqual(str(A), 'A')

    # Nodes with nonzero arity.
    mylist = interp.import_(self.MYLIST)
    nil = interp.raw_expr(mylist.Nil)
    self.assertEqual(repr(nil), '<Nil>')
    self.assertEqual(str(nil), 'Nil')
    #
    cons = interp.raw_expr(mylist.Cons, 1, mylist.Nil)
    self.assertEqual(repr(cons), '<Cons <Int 1> <Nil>>')
    self.assertEqual(str(cons), 'Cons 1 Nil')
    #
    cons = interp.raw_expr(mylist.Cons, 0, cons)
    self.assertEqual(str(cons), 'Cons 0 (Cons 1 Nil)')

    # Nested data specifications.
    list2 = interp.raw_expr(mylist.Cons, 0, [mylist.Cons, 1, mylist.Nil])
    self.assertEqual(cons, list2)
    list3 = interp.raw_expr(mylist.Cons, 1, [mylist.Cons, 2, mylist.Nil])
    self.assertNotEqual(list2, list3)

    # Negative tests.
    self.assertRaisesRegex(
        TypeError
      , r"cannot build a Curry expression from type 'dict'"
      , lambda: interp.raw_expr({})
      )

  def testToPython(self):
    '''Test the conversions from Curry to Python.'''
    interp = Interpreter(flags={'defaultconverter':'topython'})
    # Bool
    x = interp.raw_expr(True)
    self.assertNotEqual(x, True)
    self.assertEqual(interp.topython(x), True)
    self.assertEqual(repr(x), '<True>')
    x = interp.raw_expr(False)
    self.assertNotEqual(x, False)
    self.assertEqual(interp.topython(x), False)
    self.assertEqual(repr(x), '<False>')
    # Int
    x = interp.raw_expr(1)
    self.assertNotEqual(x, 1)
    self.assertEqual(interp.topython(x), 1)
    self.assertEqual(repr(x), '<Int 1>')
    # Float
    x = interp.raw_expr(1.2)
    self.assertNotEqual(x, 1.2)
    self.assertEqual(interp.topython(x), 1.2)
    self.assertEqual(repr(x), '<Float 1.2>')
    # Char
    x = interp.raw_expr('a')
    self.assertNotEqual(x, 'a')
    self.assertEqual(interp.topython(x), 'a')
    self.assertEqual(repr(x), "<Char 'a'>")
    # String
    x = interp.raw_expr('abc')
    self.assertEqual(interp.topython(x), 'abc')
    self.assertEqual(repr(x), "<: <Char 'a'> <: <Char 'b'> <: <Char 'c'> <[]>>>>")
    # (empty string tested in testConvertEmptyString)
    # List
    x = interp.raw_expr([1,2,3])
    self.assertEqual(interp.topython(x), [1,2,3])
    self.assertEqual(repr(x), "<: <Int 1> <: <Int 2> <: <Int 3> <[]>>>>")
    # (empty list)
    x = interp.raw_expr([])
    self.assertEqual(interp.topython(x), [])
    self.assertEqual(repr(x), "<[]>")
    # Tuple
    x = interp.raw_expr((1,2,3))
    self.assertEqual(interp.topython(x), (1,2,3))
    self.assertEqual(repr(x), "<(,,) <Int 1> <Int 2> <Int 3>>")
    # (empty tuple)
    x = interp.raw_expr(())
    self.assertEqual(interp.topython(x), ())
    self.assertEqual(repr(x), "<()>")
    # (one-tuple)
    self.assertRaisesRegex(
        TypeError, 'Curry has no 1-tuple', lambda: interp.raw_expr((1,))
      )
    # Complex/nested.
    v = [[('a', 1.2, [1,2]), ('b', 3.1, [3,4])]]
    x = interp.raw_expr(v)
    self.assertEqual(interp.topython(x), v)
    self.assertEqual(repr(x)
      , "<: <: <(,,) <Char 'a'> <Float 1.2> <: <Int 1> <: <Int 2> <[]>>>> <: <(,,) <Char 'b'> <Float 3.1> <: <Int 3> <: <Int 4> <[]>>>> <[]>>> <[]>>"
      )

  @unittest.expectedFailure
  def testConvertEmptyString(self):
    # An empty [Char] should convert to an empty Python string.  But the
    # to-string conversion inspects the data (list) to determine type.  It
    # really ought to ask Curry about the return type, but I'm not sure how to
    # do that yet.  See conversions.py:192 (6/6/2018).
    x = curry.raw_expr('')
    y = curry.topython(x)
    self.assertIsInstance(y, str)

  @cytest.with_flags(defaultconverter='topython')
  def testIteratorToPython(self):
    # Iterator.
    take = curry.symbol('Prelude.take')
    seq = itertools.count() # infinite sequence.
    x = curry.raw_expr(seq)
    self.assertTrue(repr(x).startswith('<_biGenerator'))
    goal = curry.raw_expr([take, 5, x])
    self.assertEqual(list(curry.eval(goal)), [[0,1,2,3,4]])
    # Generator.
    seq = (2*i for i in range(10))
    goal = curry.raw_expr([take, 3, seq])
    self.assertEqual(list(curry.eval(goal)), [[0,2,4]])

  def testTypesToPython(self):
    interp = Interpreter()
    self.assertEqual(interp.currytype(int), interp.type('Prelude.Int'))
    self.assertEqual(interp.currytype(float), interp.type('Prelude.Float'))
    self.assertEqual(interp.currytype(str), interp.type('Prelude.Char'))
    self.assertEqual(interp.currytype(bool), interp.type('Prelude.Bool'))
    self.assertEqual(interp.currytype(list), interp.type('Prelude.[]'))
    #
    if np is not None:
      self.assertEqual(interp.currytype(np.float16), interp.type('Prelude.Float'))
      self.assertEqual(interp.currytype(np.float32), interp.type('Prelude.Float'))
      self.assertEqual(interp.currytype(np.int8), interp.type('Prelude.Int'))
      self.assertEqual(interp.currytype(np.byte), interp.type('Prelude.Int'))
      self.assertIsNone(interp.currytype(np.complex64))
      #
    # Note: the Python tuple type has no analog in Curry, where each arity is a
    # distinct type.
    self.assertIsNone(interp.currytype(tuple))

  def testUnboxedExpr(self):
    self.assertIs(curry.raw_expr(curry.unboxed(0)), 0)

  @unittest.skipIf(curry.flags['backend'] == 'cxx', 'TODO for C++')
  def testNestedUnboxed(self):
    t1 = curry.raw_expr((0, 1))
    t2 = curry.raw_expr((0, curry.unboxed(1)))
    self.assertNotEqual(t1, t2)
    self.assertEqual(t1[1].info.name, 'Int')
    self.assertIs(t2[1], 1)

  def testUnboxedRewriteTarget(self):
    e = curry.raw_expr('dummy')
    self.assertRaisesRegex(
        ValueError
      , 'cannot rewrite a node to an unboxed value'
      , lambda: curry.raw_expr(curry.unboxed(0), target=e)
      )

  @cytest.with_flags(defaultconverter='topython')
  def testForwardExpr(self):
    a = curry.raw_expr(curry.getInterpreter().prelude.id, 0)
    b = curry.raw_expr(curry.getInterpreter().prelude.id, 1)
    curry.raw_expr(b, target=a)
    self.assertEqual(list(curry.eval(a)), [1])


