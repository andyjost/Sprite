from __future__ import print_function
import curry
from curry import inspect

curry.path.insert(0, '.')
Nat = curry.import_('Nat')

print('Symbols defined in Nat:', inspect.symbols(Nat))
print('Types defined in Nat:', inspect.types(Nat))
print()
print('ICurry for Nat is located at:', inspect.geticurryfile(Nat))
print('ICurry-JSON for Nat is located at:', inspect.getjsonfile(Nat))
print('ICurry for Nat.natToInt:')
print('------------------------')
print(inspect.geticurry(Nat.natToInt))
print()
print('The Python implementation of Nat.natToInt:')
print('------------------------------------------')
print(inspect.getimpl(Nat.natToInt))

