'''Functional tests for the equational constraint.'''
import cytest # from ./lib; must be first
from cytest.functional import FunctionalTestCase

class TestKiel(FunctionalTestCase):
  SOURCE_DIR = 'data/curry/eqconstr/'
  PRINT_SKIPPED_GOALS = True

