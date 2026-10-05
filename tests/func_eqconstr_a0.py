'''
Functional tests for the equational constraint: the generated programs over
the type with one nullary constructor, data T = A (a0_*).  See
func_eqconstr.py for the split of the corpus.
'''
import cytest # from ./lib; must be first
import curry

class TestEqConstrA0(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/eqconstr/'
  FILE_PATTERN = 'a0_*.curry'
  PRINT_SKIPPED_GOALS = True
