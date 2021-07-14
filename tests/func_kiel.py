'''Tests running the Kiel code examples.'''
import cytest # from ./lib; must be first

class TestKiel(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/kiel/'
  PRINT_SKIPPED_GOALS = False
  CURRYPATH = 'data/curry/kiel/lib'
  CONVERTER = 'topython'
  # FILE_PATTERN = 'UseConc'
  CLEAN_KWDS = {
      'diamond': {'keep_empty_lines': True, 'keep_spacing': True, 'sort_lines': False}
    }
  # RUNONLY = 'diamond' # diamond, member
  SKIP = [
      # These never terminate.
      'account'
    , 'digit'
    # , 'last' # introduced when $!! was removed from the goal
    # , 'member' # introduced when $!! was removed from the goal
    , 'infresiduate'
    , 'nondetfunc'
    , 'relational'

    # Maximum recursion depth exceeded
    , 'assembler'
    , 'member'

    # E_RESIDUAL
    , 'rigidadd'
    , 'mergesort'
    ]
