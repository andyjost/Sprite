import cytest # from ./lib; must be first

class TestSetFunctions(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/setfunctions/'
  DO_CLEAN = False
  COMPARISON_METHOD = cytest.FunctionalTestCase.assertSameResultSet
  # RUN_ONLY = []
  SKIP = [
      'basic00', 'basic01', 'constr07', 'constr09', 'constr18', 'constr19'
    , 'constr21', 'constr25', 'constr26', 'constr30', 'constr35'
    , 'notground03', 'notground07'
    ]
