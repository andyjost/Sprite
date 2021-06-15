'''Functional tests for functional patterns.'''
import cytest # from ./lib; must be first

class TestFunpat(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/funpat/'
  PRINT_SKIPPED_GOALS = True
  # RUNONLY = ['funpat_last01']

