import cytest # from ./lib; must be first
import curry

class TestSetFunctions(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/setfunctions/'
  DO_CLEAN = False
  COMPARISON_METHOD = cytest.FunctionalTestCase.assertSameResultSet
  # RUN_ONLY = ['basic00']

  SKIP = [
      'basic00', 'basic01'
    , 'constr07', 'constr09', 'constr18', 'constr19', 'constr21', 'constr25'
    , 'constr26', 'constr30', 'constr35'
    , 'notground03', 'notground07'
    ]

  if curry.flags['setfunction_strategy'] != 'lazy':
    SKIP += [
        'abc04', 'abc05', 'abc06'
      , 'apply15', 'apply16', 'apply17'
      , 'basic07'
      , 'basic08', 'basic15', 'basic16', 'basic17', 'basic18', 'basic19'
      , 'basic26', 'basic27', 'basic28', 'basic29', 'basic30', 'constr03'
      , 'constr04', 'constr05', 'constr10', 'constr11', 'constr20', 'constr22'
      , 'constr23', 'constr24', 'constr27', 'constr28', 'constr29', 'notground00'
      , 'notground01', 'notground02', 'notground04', 'notground05', 'notground06'
      ]

  SKIP += ['constr', 'notground']
