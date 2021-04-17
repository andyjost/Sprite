'''Tests running the Kiel code examples.'''
import cytest # from ./lib; must be first

class TestKiel(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/kiel/'
  PRINT_SKIPPED_GOALS = False
  CURRYPATH = 'data/curry/kiel/lib'
  # To determine the curent set of failures, clear this list and run.
  SKIP = [
    # InstantiationError: =:= cannot bind to an unboxed value
      'account'
    , 'assembler'
    , 'infresiduate'
    , 'last'
    , 'member'
    , 'nondetfunc'
    , 'mergesort'
    , 'relational'

    # assert inspect.isa_freevar(interp, freevar)
    , 'digit'
    , 'rigidadd'

    # Problem comparing quoted strings.
    , 'diamond'
    ]
