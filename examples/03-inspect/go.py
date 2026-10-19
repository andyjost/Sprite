import os
import sys
import curry

curry.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
Peano = curry.import_('Peano')
info = curry.info(Peano)
print('Module:', info.name)
print('Module file:', os.path.basename(info.file))
for name, datatype in sorted(info.types.items()):
  print('Type:', name, [c.name for c in datatype.constructors])
print('Symbols:', ', '.join(sorted(info.symbols)))
print('Qualified symbol:', curry.symbol('Data.List.nub').fullname)
print('Qualified type:', curry.type('Peano.Nat').fullname)
M = curry.import_('Prelude')  # operators belong to their defining module
print('Operator:', M['=:='].symbol.fullname, M['=:='].symbol.signature)

print('\nInternal: compiler products')
from curry import inspect
print('ICurry:', os.path.basename(inspect.geticurryfile(Peano)))
print('JSON:', os.path.basename(inspect.getjsonfile(Peano)))
code = inspect.getimpl(Peano.add)
print('Generated code:', code.splitlines()[0].strip())
print(code, file=sys.stderr)
