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
    em.compile_(icur)

