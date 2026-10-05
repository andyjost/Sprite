'''
Functional tests for the equational constraint: the generated programs over
the type with three nullary constructors, data T = A | B | C, numbers 000
to 149 (a0b0c0_*).  The 444 programs of this type run in three files of
equal size.  See func_eqconstr.py for the split of the corpus.
'''
import cytest # from ./lib; must be first
import curry

class TestEqConstrA0B0C0Part1(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/eqconstr/'
  FILE_PATTERN = ['a0b0c0_0*.curry', 'a0b0c0_1[0-4]*.curry']
  PRINT_SKIPPED_GOALS = True
