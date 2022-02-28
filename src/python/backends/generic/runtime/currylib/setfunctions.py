'''
Implements the external parts of Control.SetFunctions.
'''

from .....common import T_SETGRD, F_PARTIAL_TYPE
from . import ModuleSpecification
from ..... import icurry

def _T(name, constructors):
  return icurry.IDataType('Control.SetFunctions.' + name, constructors)
def _C(name, *args, **kwds):
  return icurry.IConstructor('Control.SetFunctions.' + name, *args, **kwds)
def _F(name, *args, **kwds):
  return icurry.IFunction('Control.SetFunctions.' + name, *args, **kwds)

TYPES = [
    _T('PartialS' , [_C('PartialS', 2, metadata={'all.flags': F_PARTIAL_TYPE})])
  , _T('SetEval'  , [_C('SetEval', 2)])
  , _T('_SetGuard', [_C('_SetGuard', 2, metadata={'all.tag':T_SETGRD})])
  ]

FUNCTIONS = [
    _F('allValues', 1)
  , _F('applyS'   , 2)
  , _F('captureS' , 2)
  , _F('evalS'    , 1)
  , _F('exprS'    , 1)
  , _F('set'      , 1)
  , _F('set0'     , 1)
  , _F('set1'     , 2)
  , _F('set2'     , 3)
  , _F('set3'     , 4)
  , _F('set4'     , 5)
  , _F('set5'     , 6)
  , _F('set6'     , 7)
  , _F('set7'     , 8)
  ]

MODULE = icurry.IModule(
    fullname='Control.SetFunctions', imports=[], types=TYPES, functions=FUNCTIONS
  )

class SetFunctionsSpecification(ModuleSpecification):
  @staticmethod
  def aliases():
    return []

  @staticmethod
  def exports():
    yield 'PartialS'
    yield 'SetEval'
    yield '_SetGuard'

  @staticmethod
  def extern():
    return MODULE
