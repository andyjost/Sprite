from curry import icurry
from glob import glob
import cytest
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
        self.compareGolden(icur, goldenfile, GENERATE_GOLDENS)
      except:
        print 'Error while processing', jsonfile
        raise

