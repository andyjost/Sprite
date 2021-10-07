import cytest # from ./lib; must be first
from cytest.logging import capture_log
import curry.config
import curry, logging

class TestSetFunctions(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/setfunctions/'
  DO_CLEAN = False
  COMPARISON_METHOD = cytest.FunctionalTestCase.assertSameResultSet
  # RUN_ONLY = ['']

  if curry.flags['setfunction_strategy'] == 'eager':
    SKIP = ['free'] # Evaluation suspends.
