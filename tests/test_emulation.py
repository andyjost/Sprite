from curry.compiler.emulation import Emulator
from curry.compiler import icurry
import cytest

SRCS = ['data/json/1.json']

class TestEmulation(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.ICURRY = map(lambda src: icurry.parse(open(src, 'rb').read()), SRCS)

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

  def testBuilding(self):
    em = Emulator()
    one = em.build(1)
    self.assertEqual(repr(one), '<Int [1]>')
    self.assertEqual(str(one), '1')

    example = em.import_(self.ICURRY[0])[0]
    A = em.build(example.A)
    self.assertEqual(repr(A), '<A ()>')
    self.assertEqual(str(A), 'A')

