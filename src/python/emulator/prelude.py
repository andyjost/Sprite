from ..compiler.icurry import *
from .node import TypeInfo

Choice = IType('Choice', [IConstructor('Choice', 2, format='{1} ? {2}')])
Int = IType('Int', [IConstructor('Int', 1, format='{1}')])
Float = IType('Float', [IConstructor('Float', 1, format='{1}')])

Prelude = IModule(
    name='Prelude'
  , imports=[]
  , types=[Choice, Int, Float]
  , functions=[]
  )
