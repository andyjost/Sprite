'''Tests running the Kiel code examples.'''
import cytest # from ./lib; must be first
import curry

class TestSmap(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/smap/'
  SKIP = ['flight_itinerary']

  if curry.flags['backend'] == 'cxx':
    SKIP += ['queens']

