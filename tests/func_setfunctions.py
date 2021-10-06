import cytest # from ./lib; must be first
from cytest.logging import capture_log
import curry.config
import curry, logging

class TestSetFunctions(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/setfunctions/'
  DO_CLEAN = False
  COMPARISON_METHOD = cytest.FunctionalTestCase.assertSameResultSet
  # RUN_ONLY = ['']

  if curry.flags['setfunction_strategy'] == 'pakcs':
    SKIP = ['free'] # Evaluation suspends.

  # Override the evaluation routine.
  #
  # If set0 appears in the goal and warnings are enabled, check for the proper
  # warning.
  def evaluate(self, testname, module, goal):
    results = super(TestSetFunctions, self).evaluate(testname, module, goal)
    #
    uses_set0 = 'Control.SetFunctions.set0' in repr(goal.icurry)
    warnings_enabled = curry.config.logging_enabled_for(logging.WARNING)
    if uses_set0 and warnings_enabled:
      with capture_log('curry.backends.py.runtime.currylib.setfunctions') as log:
        for result in results:
          yield result
      log.checkMessages("set0 is ambiguous with strategy 'sprite'")
    else:
      for result in results:
        yield result
