from ..compiler.icurry import *
from .node import TypeInfo
from .evaluator import choice_step

Choice = IType('Choice', [IConstructor('Choice', 2, format='{1} ? {2}', step=choice_step)])
Int = IType('Int', [IConstructor('Int', 1, format='{1}')])
Float = IType('Float', [IConstructor('Float', 1, format='{1}')])

Prelude = IModule(
    name='Prelude'
  , imports=[]
  , types=[Choice, Int, Float]
  , functions=[]
  )
