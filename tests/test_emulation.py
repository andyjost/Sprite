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

  def testWIP(self):
    icur = self.ICURRY[0]
    em = Emulator()
    example = em.import_(icur)
    self.assertEqual(em.modules.keys(), ['example'])
    # self.assertIs(em.modules['example'], example)
    breakpoint()


    # self.assertEqual(em.modules.keys(), ['example'])
    # example = em.modules['example']
    # self.assertEqual([ty.basename for ty in example.types.keys()], ['AB'])
    # self.assertEqual([f.basename for f in example.functions.keys()], ['f', 'f_case_#1', 'g', 'main'])

