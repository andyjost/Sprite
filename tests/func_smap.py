'''Tests running the Kiel code examples.'''
import cytest # from ./lib; must be first

class TestKiel(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/smap/'
  # RUN_ONLY = ['']
  SKIP = [
      'arith'   # need SetFunctions.selectValue
    , 'flight'  # incorret answer
    ]

