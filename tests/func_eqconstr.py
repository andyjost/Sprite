'''Functional tests for the equational constraint.'''
import cytest # from ./lib; must be first

class TestEqConstr(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/eqconstr/'
  PRINT_SKIPPED_GOALS = True
  # RUN_ONLY = ['iprog07']
  # SKIP = []

