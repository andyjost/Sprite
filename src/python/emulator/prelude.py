from ..compiler.icurry import *
from .node import TypeInfo

Choice = IType('Choice', [IConstructor('Choice', 2, format='{1} ? {2}', noexec=True)])
Failure = IType('Failure', [IConstructor('Failure', 0, format='failure', noexec=True)])
Float = IType('Float', [IConstructor('Float', 1, format='{1}')])
Int = IType('Int', [IConstructor('Int', 1, format='{1}')])

Prelude = IModule(
    name='Prelude'
  , imports=[]
  , types=[Choice, Failure, Float, Int]
  , functions=[]
  )
