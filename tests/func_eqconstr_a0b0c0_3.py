'''
Functional tests for the equational constraint: the generated programs over
the type with three nullary constructors, data T = A | B | C, numbers 300
to 443 (a0b0c0_*).  See func_eqconstr_a0b0c0_1.py.
'''
import cytest # from ./lib; must be first
import curry

class TestEqConstrA0B0C0Part3(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/eqconstr/'
  FILE_PATTERN = ['a0b0c0_3*.curry', 'a0b0c0_4*.curry']
  PRINT_SKIPPED_GOALS = True
