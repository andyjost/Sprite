'''Functional tests for the equational constraint.'''
import cytest # from ./lib; must be first

class TestEqConstr(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/eqconstr/'
  PRINT_SKIPPED_GOALS = True
  SKIP = ['a2b1c0_000', 'a2b1c0_001', 'a2b1c0_003', 'a2b1c0_004', 'a2b1c0_005', 'a2b1c0_006', 'a2b1c0_007', 'a2b1c0_008', 'a2b1c0_009', 'a2b1c0_010', 'a2b1c0_011', 'a2b1c0_012', 'a2b1c0_013']
  RUNONLY = ['split_01']

