import cytest # from ./lib; must be first
from curry import icurry
from glob import glob
import curry
import gzip

GENERATE_GOLDENS = False

class ParseJSON(cytest.TestCase):
  '''Tests parsing the ICurry JSON format.'''
  def test_parseJSON(self):
    for jsonfile in glob('data/json/*.json*'):
      open_ = gzip.open if jsonfile.endswith('.gz') else open
      json = open_(jsonfile, 'rb').read()
      icur = icurry.json.parse(json)

      # Test equality.
      self.assertTrue(icur, icur)

      # Test repr.
      local={}
      exec 'from curry.icurry import *' in local
      icur2 = eval(repr(icur), local)
      try:
        self.assertEqual(icur, icur2)
      except:
        # To debug:
        # from cytest.dissect import dissect
        # dissect(icur, icur2)
        # breakpoint()
        raise

      # Check against the golden.
      goldenfile = jsonfile.replace('.json', '.au')
      self.assertEqualToFile(icur, goldenfile, GENERATE_GOLDENS)

  def test_exempt(self):
    curry.import_('head')

  def test_atableFlex(self):
    curry.import_('atableFlex')

  def test_atableNoflex(self):
    curry.import_('atableNoflex')

  def test_btable(self):
    curry.import_('btable')

  def testKielExamples(self):
    '''Parse example programs from Kiel.'''
    for jsonfile in glob('data/json/kiel-*.json'):
      icur = icurry.json.parse(open(jsonfile, 'rb').read())
      curry.import_(icur)

