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
  # RUNONLY = 'account'
  SKIP = [
      'account'    # no JSON object could be decoded
    , 'nondetfunc' # never terminates
    , 'member'     # '' != 2\n3
    , 'mergesort'  # never terminates

    # EvaluationSuspended
    , 'assembler'
    , 'digit'
    , 'relational'
    ]
