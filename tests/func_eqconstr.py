'''Functional tests for the equational constraint.'''
import cytest # from ./lib; must be first
import curry

class TestEqConstr(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/eqconstr/'
  PRINT_SKIPPED_GOALS = True
  # RUN_ONLY = ['a0_.[02468][048]', 'a0b0c0_.[037][048]', 'prog0.'] # A subset for quick checks.
  CLEAN_KWDS = {
      'fprog': {'standardize_floats': True}
    }
  if curry.flags['backend'] == 'cxx':
    RUN_ONLY = ['iprog06|prog01|prog03|prog09|prog10$|prog11$']

