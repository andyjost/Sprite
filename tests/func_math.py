'''Math test programs.'''
import cytest # from ./lib; must be first
import curry

class TestMath(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/math/'
  CLEAN_KWDS = {
      'floatmath': {'standardize_floats': True}
    }
  if curry.flags['backend'] == 'cxx':
    SKIP = ['sort']
