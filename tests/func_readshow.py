import cytest # from ./lib; must be first
import curry
from cytest.tty import CLOSE

class TestExamples(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/readshow/'
  CLEAN_KWDS = {
      'readfloat|show': {'standardize_floats': True}
    }
