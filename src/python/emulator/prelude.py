from ..compiler.icurry import *
from .node import TypeInfo, T_FAIL, T_CHOICE, T_FWD

Failure = IType('Failure', [IConstructor('Failure', 0, format='failure', metadata=T_FAIL)])
Choice = IType('Choice', [IConstructor('Choice', 2, format='{1} ? {2}', metadata=T_CHOICE)])
Fwd = IType('Fwd', [IConstructor('Fwd', 1, format='{1} ? {2}', metadata=T_FWD)])
Float = IType('Float', [IConstructor('Float', 1, format='{1}')])
Int = IType('Int', [IConstructor('Int', 1, format='{1}')])

negate = IFunction('negate', 1, []) # FIXME

Prelude = IModule(
    name='Prelude'
  , imports=[]
  , types=[Failure, Choice, Fwd, Float, Int]
  , functions=[negate]
  )
