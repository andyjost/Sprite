from curry.emulator import Emulator, Prelude
from curry.compiler import icurry
from curry.visitation import dispatch
import cytest
from cStringIO import StringIO

SRCS = ['data/json/1.json']

def listformat(node):
  def gen():
    p = node
    while p.info.name == 'Cons':
      value = p.successors[0]
      yield value.info.show(value)
      p = p.successors[1]
  return '[' + ', '.join(gen()) + ']'


class TestEmulation(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.ICURRY = map(lambda src: icurry.parse(open(src, 'rb').read()), SRCS)
    cls.MYLIST = icurry.IModule(
        name='mylist', imports=[], functions=[]
      , types=[
            icurry.IType(
                ident='List'
              , constructors=[
                  icurry.IConstructor('Cons', 2, format=listformat)
                , icurry.IConstructor('Nil', 0, format=listformat)
                ]
              )
          ]
      )
    cls.X = icurry.IModule(
        name='X', imports=[], functions=[]
      , types=[
            icurry.IType(
                ident='X'
              , constructors=[icurry.IConstructor('X', 1)]
              )
          ]
      )

  @classmethod
  def tearDownClass(cls):
    del cls.ICURRY
    del cls.MYLIST
    del cls.X

  def testImport(self):
    icur = self.ICURRY[0]
    em = Emulator()
    imported = em.import_(icur)
    self.assertEqual(sorted(em.modules.keys()), ['example'])
    self.assertEqual(len(imported), 1)
    example = imported[0]
    self.assertFalse(set('A B f f_case_#1 g main'.split()) - set(dir(example)))
    self.assertIs(em.modules['example'], example)

  def testExpr(self):
    '''Use Emulator.expr to build expressions.'''
    em = Emulator()

    # Int.
    one = em.expr(1)
    self.assertEqual(repr(one), '<Int [1]>')
    self.assertEqual(str(one), '1')

    # Float.
    pi = em.expr(3.14)
    self.assertEqual(repr(pi), '<Float [3.14]>')
    self.assertEqual(str(pi), '3.14')

    # Node.
    example = em.import_(self.ICURRY[0])[0]
    A = em.expr(example.A)
    self.assertEqual(repr(A), '<A []>')
    self.assertEqual(str(A), 'A')

    # Nodes with nonzero arity.
    mylist = em.import_(self.MYLIST)
    nil = em.expr(mylist.Nil)
    self.assertEqual(repr(nil), '<Nil []>')
    self.assertEqual(str(nil), '[]')
    #
    cons = em.expr(mylist.Cons, 1, mylist.Nil)
    self.assertEqual(repr(cons), '<Cons [<Int [1]>, <Nil []>]>')
    self.assertEqual(str(cons), '[1]')
    #
    cons = em.expr(mylist.Cons, 0, cons)
    self.assertEqual(str(cons), '[0, 1]')

    # Nested data specifications.
    list2 = em.expr(mylist.Cons, 0, [mylist.Cons, 1, mylist.Nil])
    self.assertEqual(cons, list2)
    list3 = em.expr(mylist.Cons, 1, [mylist.Cons, 2, mylist.Nil])
    self.assertNotEqual(list2, list3)


  def testEvalValues(self):
    '''Evaluate simple goals that are already values.'''
    em = Emulator()
    L = em.import_(self.MYLIST)
    TESTS = [
        [1, '1\n']
      , [2.0, '2.0\n']
      , [[L.Cons, 0, [L.Cons, 1, L.Nil]], '[0, 1]\n']
      ]
    for value, result in TESTS:
      stream = StringIO()
      goal = em.expr(value)
      em.eval(goal, stream.write)
      self.assertEqual(stream.getvalue(), result)

  def testBuildChoice(self):
    '''Build and evaluate simple expressions involving the choice operator.'''
    em = Emulator()
    X = em.import_(self.X).X
    P = em.import_(Prelude)

    # 1 ? 2
    one_or_two = em.expr(P.Choice, 1, 2)
    self.assertEqual(str(one_or_two), '1 ? 2')
    stream = StringIO()
    em.eval(one_or_two, stream.write)
    self.assertEqual(sorted(stream.getvalue().split()), ['1','2'])

    # X (1 ? 2)
    goal = em.expr(X, [P.Choice, 1, 2])
    stream = StringIO()
    em.eval(goal, stream.write)
    results = sorted(x for x in stream.getvalue().split('\n') if x)
    self.assertEqual(results, ['X 1', 'X 2'])

