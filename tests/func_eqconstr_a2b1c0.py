'''
Functional tests for the equational constraint: the generated programs over
the type whose constructors take arguments, data T = A T T | B T | C
(a2b1c0_*).  See func_eqconstr.py for the split of the corpus.
'''
import cytest # from ./lib; must be first
import curry

class TestEqConstrA2B1C0(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/eqconstr/'
  FILE_PATTERN = 'a2b1c0_*.curry'
  PRINT_SKIPPED_GOALS = True
