from curry.compiler import icurry
import cytest

GENERATE_GOLDENS = False

class ParseJSON(cytest.TestCase):
  '''Tests parsing the ICurry JSON format.'''
  def test_parseJSON(self):
    json = open('data/json/1.json', 'rb').read()
    icur = icurry.parse(json)[0]

    # Test equality.
    self.assertTrue(icur, icur)

    # Test repr.
    local={}
    exec 'from curry.compiler.icurry import *' in local
    icur2 = eval(repr(icur), local)
    with trap():
      self.assertEqual(icur, icur2)

    # Check against the golden.
    self.compareGolden(icur, 'data/json/1.au', GENERATE_GOLDENS)
