'''Math test programs: integer arithmetic (intmath*).  See func_math.py.'''
import cytest # from ./lib; must be first
import curry

class TestIntMath(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/math/'
  FILE_PATTERN = 'intmath*.curry'
