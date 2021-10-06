'''Tests running the Kiel code examples.'''
import cytest # from ./lib; must be first

class TestSmap(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/smap/'
  # RUN_ONLY = ['']
  EXPECTED_FAILURE = ['flight']

