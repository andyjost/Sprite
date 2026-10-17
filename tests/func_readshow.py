import cytest # from ./lib; must be first
import curry, re
from cytest.tty import CLOSE

def compare_values(self, observed, expected):
  # The converted empty String prints as "". Parentheses around negative
  # list elements were a property of the node printer.
  expected = expected.replace(',[])', ',"")')
  expected = re.sub(r'\((-\d+)\)', r'\1', expected)
  observed = re.sub(r'\((-\d+)\)', r'\1', observed)
  self.assertEqual(observed, expected)


class TestExamples(cytest.FunctionalTestCase):
  COMPARISON_METHOD = compare_values
  SOURCE_DIR = 'data/curry/readshow/'
  CLEAN_KWDS = {
      'readfloat|show': {'standardize_floats': True}
    }
