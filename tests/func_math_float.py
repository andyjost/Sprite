'''Math test programs: floating-point arithmetic (floatmath*).  See func_math.py.'''
import cytest # from ./lib; must be first
import curry

class TestFloatMath(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/math/'
  FILE_PATTERN = 'floatmath*.curry'
  CLEAN_KWDS = {
      'floatmath': {'standardize_floats': True}
    }
