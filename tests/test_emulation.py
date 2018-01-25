from curry.compiler.emulation import Emulator
from curry.compiler import icurry
import cytest

SRCS = ['data/json/1.json']

class TestEmulation(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.ICURRY = map(lambda src: icurry.parse(open(src, 'rb').read()), SRCS)
    cls.MYLIST =icurry.IModule(
        name='mylist', imports=[], functions=[]
      , types={'List': [
            icurry.IConstructor('Cons', 2, format='{1}:{2}')
          , icurry.IConstructor('Nil', 0, format='[]')
          ]}
      )

  @classmethod
  def tearDownClass(cls):
    del cls.ICURRY

  def testImport(self):
    icur = self.ICURRY[0]
    em = Emulator()
    imported = em.import_(icur)
    self.assertEqual(em.modules.keys(), ['example'])
    self.assertEqual(len(imported), 1)
    example = imported[0]
    self.assertFalse(set('A B f f_case_#1 g main'.split()) - set(dir(example)))
    self.assertIs(em.modules['example'], example)

  def testBuildExpr(self):
    em = Emulator()
    one = em.build(1)
    self.assertEqual(repr(one), '<Int [1]>')
    self.assertEqual(str(one), '1')

    pi = em.build(3.14)
    self.assertEqual(repr(pi), '<Float [3.14]>')
    self.assertEqual(str(pi), '3.14')

    example = em.import_(self.ICURRY[0])[0]
    A = em.build(example.A)
    self.assertEqual(repr(A), '<A ()>')
    self.assertEqual(str(A), 'A')

    mylist = em.import_(self.MYLIST)
    nil = em.build(mylist.Nil)
    self.assertEqual(repr(nil), '<Nil ()>')
    self.assertEqual(str(nil), '[]')
    cons = em.build(mylist.Cons, 1, mylist.Nil)
    self.assertEqual(repr(cons), '<Cons (<Int [1]>, <Nil ()>)>')
    self.assertEqual(str(cons), '1:[]')


