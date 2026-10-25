'''Tests running the Kiel code examples.'''
import cytest # from ./lib; must be first
from curry import config
import curry, unittest

class TestSmap(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/smap/'
  SKIP = ['flight_itinerary']

if config.frontend_version() >= '3.0.0':
  TestSmap.test_poker_four_of_a_kind = unittest.skip(
      'poker requires currypp; only the pinned 2.0.0 overlay supplies its product'
    )(TestSmap.test_poker_four_of_a_kind)

