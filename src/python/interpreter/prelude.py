from ..icurry import *
from .runtime import T_FAIL, T_CHOICE, T_FWD
import operator as op

Failure = IType('Failure', [IConstructor('Failure', 0, metadata={'py.format':'failure', 'py.tag':T_FAIL})])
Choice = IType('Choice', [IConstructor('Choice', 2, metadata={'py.format':'{1} ? {2}', 'py.tag':T_CHOICE})])
Fwd = IType('Fwd', [IConstructor('Fwd', 1, metadata={'py.tag':T_FWD})])
Float = IType('Float', [IConstructor('Float', 1, metadata={'py.format':'{1}'})])
Int = IType('Int', [IConstructor('Int', 1, metadata={'py.format':'{1}'})])

negate = IFunction('negate', 1, metadata={'py.func':op.neg})

Prelude = IModule(
    name='Prelude'
  , imports=[]
  , types=[Failure, Choice, Fwd, Float, Int]
  , functions=[negate]
  )
