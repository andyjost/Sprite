'''
Implements the external parts of Control.SetFunctions.
'''

from ....common import T_SETGRD, F_PARTIAL_TYPE
from . import ModuleSpecification
from .... import icurry

TYPES = [
    ('PartialS' , [('PartialS' , 2, {'all.flags': F_PARTIAL_TYPE })])
  , ('SetEval'  , [('SetEval'  , 2, {                            })])
  , ('_SetGuard', [('_SetGuard', 2, {'all.tag'  :T_SETGRD        })])
  ]

FUNCTIONS = [
    ('allValues', 1, {})
  , ('applyS'   , 2, {})
  , ('captureS' , 2, {})
  , ('evalS'    , 1, {})
  , ('exprS'    , 1, {})
  , ('set'      , 1, {})
  , ('set0'     , 1, {})
  , ('set1'     , 2, {})
  , ('set2'     , 3, {})
  , ('set3'     , 4, {})
  , ('set4'     , 5, {})
  , ('set5'     , 6, {})
  , ('set6'     , 7, {})
  , ('set7'     , 8, {})
  ]

class SetFunctionsSpecification(ModuleSpecification):
  NAME      = 'Control.SetFunctions'
  TYPES     = TYPES
  FUNCTIONS = FUNCTIONS
  IMPORTS   = []

  def exports(self):
    yield 'PartialS'
    yield 'SetEval'
    yield '_SetGuard'

