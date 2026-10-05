'''
Math test programs: comparisons and sorting.

The corpus under data/curry/math runs in three test files, so the parallel
runner spreads its compile time (tests/README, section 10): this file runs
compare* and sort*, func_math_int.py runs intmath*, and func_math_float.py
runs floatmath*.  unit_func_parts.py checks that the three cover the corpus
once.
'''
import cytest # from ./lib; must be first
import curry

class TestMath(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/math/'
  FILE_PATTERN = ['compare*.curry', 'sort*.curry']
  CLEAN_KWDS = {
      'sort03': {'standardize_floats': True}
    }
