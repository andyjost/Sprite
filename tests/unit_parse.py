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
      try:
        open_ = gzip.open if jsonfile.endswith('.gz') else open
        json = open_(jsonfile, 'rb').read()
        icur = icurry.parse(json)[0]

        # Test equality.
        self.assertTrue(icur, icur)

        # Test repr.
        local={}
        exec 'from curry.icurry import *' in local
        icur2 = eval(repr(icur), local)
        self.assertEqual(icur, icur2)

        # Check against the golden.
        goldenfile = jsonfile.replace('.json', '.au')
        self.compareCurryOutputToGoldenFile(icur, goldenfile, GENERATE_GOLDENS)

        # Test despace.
        jsonsmall = icurry.despace(json)
        self.assertLess(len(jsonsmall), len(json))
        icur2 = icurry.parse(jsonsmall)[0]
        self.assertEqual(icur, icur2)
      except:
        print 'Error while processing', jsonfile
        raise

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
      icur = icurry.parse(open(jsonfile, 'rb').read())
      curry.import_(icur)

