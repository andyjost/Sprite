import cytest # from ./lib; must be first
import curry
from cytest.tty import CLOSE

class TestExamples(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/readshow/'
  RUN_ONLY = 'readchar'
