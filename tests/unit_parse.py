import cytest # from ./lib; must be first
import curry
from curry import icurry
from glob import glob
import gzip
import unittest

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
        self.compareGolden(icur, goldenfile, GENERATE_GOLDENS)
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
    for jsonfile in glob('data/json/kiel-*.json*'):
      icur = icurry.parse(gzip.open(jsonfile, 'rb').read())
      curry.import_(icur)

