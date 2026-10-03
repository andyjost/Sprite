'''
Inspects a Curry module with curry.inspect.

Imports the module Nat and prints its symbols, its types, the constructors
of its type, the names of the files that hold its ICurry, and the first line
of the Python code that Sprite generated for one of its functions.  The
whole generated code goes to the standard error stream.  It changes with the
compiler, and expected.out holds the standard output only.
'''
import os
import sys
import curry
from curry import inspect

# Find Nat.curry next to this file, whatever the working directory is.
HERE = os.path.dirname(os.path.abspath(__file__))
curry.path.insert(0, HERE)
from curry.lib import Nat

# The public symbols and the types of the module, by name.
print('Symbols defined in Nat:', ', '.join(sorted(inspect.symbols(Nat))))
print('Types defined in Nat:', ', '.join(sorted(inspect.types(Nat))))

# A type object lists its constructors.  Types are not attributes of the
# module, so look the type up by its full name.
nat = curry.type('Nat.Nat')
print('Constructors of Nat.Nat:',
      ', '.join('%s (arity %d)' % (c.name, c.info.arity) for c in nat.constructors))
print()

# The front end writes ICurry under .curry/ next to the source, in a
# subdirectory named after the front end version.  Only the file names are
# printed, so that the output does not change with that version.
print('ICurry file:', os.path.basename(inspect.geticurryfile(Nat)))
print('ICurry-JSON file:', os.path.basename(inspect.getjsonfile(Nat)))
print('Both live under .curry/ next to Nat.curry.')
print()

# The code that the Python backend generated for a function.  The first
# line, without its trailing comment, is the signature.
code = inspect.getimpl(Nat.natToInt)
print('The Python implementation of Nat.natToInt starts with:')
print('   ', code.splitlines()[0].partition('#')[0].strip())
print('The whole code is on the standard error stream.')
print('The Python implementation of Nat.natToInt:', file=sys.stderr)
print('------------------------------------------', file=sys.stderr)
print(code, file=sys.stderr)
