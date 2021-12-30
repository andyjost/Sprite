'''Tests running the Kiel code examples.'''
import cytest # from ./lib; must be first

class TestResiduation(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/residuation/'
  # RUN_ONLY = []
  # EXPECTED_FAILURE = []
  SKIP = ['reslist02']

