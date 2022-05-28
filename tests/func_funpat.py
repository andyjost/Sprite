'''Functional tests for functional patterns.'''
import cytest # from ./lib; must be first
import curry

class TestFunpat(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/funpat/'
  PRINT_SKIPPED_GOALS = True
  if curry.flags['backend'] == 'cxx':
    SKIP = 'funpat_isin0[345]'

