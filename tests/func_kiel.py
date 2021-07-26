'''Tests running the Kiel code examples.'''
import cytest # from ./lib; must be first

class TestKiel(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/kiel/'
  PRINT_SKIPPED_GOALS = False
  CURRYPATH = 'data/curry/kiel/lib'
  CONVERTER = 'topython'
  CLEAN_KWDS = {
      'diamond': {'keep_empty_lines': True, 'keep_spacing': True, 'sort_lines': False}
    }
  # RUN_ONLY = 'digit'
  SKIP = [
      'account'    # Does not terminate after 1 minute
    , 'digit'      # EvaluationSuspended
    ]
