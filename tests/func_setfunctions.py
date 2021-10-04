import cytest # from ./lib; must be first

class TestSetFunctions(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/setfunctions/'
  DO_CLEAN = False
  COMPARISON_METHOD = cytest.FunctionalTestCase.assertSameResultSet
  # RUN_ONLY = ['']
  SKIP = [
      'basic03', 'basic04', 'basic05', 'basic06', 'basic08', 'basic20'
    , 'basic21', 'basic22', 'basic23', 'basic24', 'basic25', 'basic26'
    , 'basic27', 'basic28', 'basic29', 'basic30', 'basic31', 'basic32'
    , 'constr04', 'constr05', 'constr07', 'constr10', 'constr11'
    ]
