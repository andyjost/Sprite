'''Math test programs.'''
import cytest # from ./lib; must be first
import curry

class TestMath(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/math/'
  CLEAN_KWDS = {
      'floatmath|sort03': {'standardize_floats': True}
    }
