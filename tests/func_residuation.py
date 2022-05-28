'''Tests running the Kiel code examples.'''
import cytest # from ./lib; must be first
import curry

class TestResiduation(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/residuation/'
  SKIP = ['reslist02']

