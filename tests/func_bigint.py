'''Exact integer parity with the pinned PAKCS oracle.'''
import cytest # from ./lib; must be first
import re

def compare_values(self, observed, expected):
  # The node printer parenthesizes negative list elements. Compare their
  # values, as func_readshow does, keeping the committed oracle text intact.
  observed = re.sub(r'\((-\d+)\)', r'\1', observed)
  expected = re.sub(r'\((-\d+)\)', r'\1', expected)
  self.assertEqual(observed, expected)


class TestBigIntegers(cytest.FunctionalTestCase):
  COMPARISON_METHOD = compare_values
  SOURCE_DIR = 'data/curry/'
  FILE_PATTERN = 'BigIntegers.curry'
  GOAL_PATTERN = r'(promotion|demotion|divisions|powers|fibonacci|conversions|roundtrips|unification|patternValues|ordering|unary|pairedDivisions|numericReads)$'
