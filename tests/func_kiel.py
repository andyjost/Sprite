'''Tests running the Kiel code examples.'''
import cytest # from ./lib; must be first
import curry

class TestKiel(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/kiel/'
  PRINT_SKIPPED_GOALS = False
  CURRYPATH = 'data/curry/kiel/lib'
  CONVERTER = 'topython'
  CLEAN_KWDS = {
      'diamond': {'keep_empty_lines': True, 'keep_spacing': True, 'sort_lines': False}
    }

  if curry.flags['backend'] == 'cxx':
    SKIP = [
        'account'   # crash
      , 'digit'     # suspends
      ]
