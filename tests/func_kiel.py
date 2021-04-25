'''Tests running the Kiel code examples.'''
import cytest # from ./lib; must be first

class TestKiel(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/kiel/'
  PRINT_SKIPPED_GOALS = False
  CURRYPATH = 'data/curry/kiel/lib'
  # FILE_PATTERN = 'colormap'
  CLEAN_KWDS = {
      'diamond': {'keep_empty_lines': True, 'keep_spacing': True, 'sort_lines': False}
    }
  # To determine the curent set of failures, clear this list and run.
  SKIP = [
      # These never terminate.
      'account'
    , 'digit'
    , 'infresiduate'
    , 'nondetfunc'
    , 'relational'

    # TypeError: unexpected tag -1
    , 'assembler'
    , 'mergesort'
    ]
