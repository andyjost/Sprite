'''Functional tests for the equational constraint.'''
import cytest # from ./lib; must be first

class TestEqConstr(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/eqconstr/'
  PRINT_SKIPPED_GOALS = True
  # RUN_ONLY = ['a0_.[02468][048]', 'a0b0c0_.[037][048]', 'prog0.'] # A subset for quick checks.
  # SKIP = []

