'''
Functional tests for the equational constraint: the hand-written programs.

The corpus under data/curry/eqconstr runs in several test files, so the
parallel runner spreads its compile time (tests/README, section 10).  This
file runs the programs that generate_test_programs.py lists by hand:
prog (the general cases), iprog, cprog, and fprog (Int, Char, and Float).
The generated programs over data types run in the func_eqconstr_* files.
unit_func_parts.py checks that the parts cover the corpus once.
'''
import cytest # from ./lib; must be first
import curry

class TestEqConstr(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/eqconstr/'
  FILE_PATTERN = ['prog*.curry', 'iprog*.curry', 'cprog*.curry', 'fprog*.curry']
  PRINT_SKIPPED_GOALS = True
  CLEAN_KWDS = {
      'fprog': {'standardize_floats': True}
    }
