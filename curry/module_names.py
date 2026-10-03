#!/usr/bin/env python3
'''
Prints the names of the Curry system libraries, one per line.

The sources live under lib/ beside this script.  The Prelude comes first.
The other names are sorted.
'''
import os, sys

def get_modules(root=None):
  if root is None:
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
  names = set()
  for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if not d.startswith('.')]
    for filename in filenames:
      if filename.endswith('.curry'):
        relpath = os.path.relpath(os.path.join(dirpath, filename[:-6]), root)
        names.add('.'.join(relpath.split(os.sep)))
  if 'Prelude' in names:
    yield 'Prelude'
    names.remove('Prelude')
  for name in sorted(names):
    yield name

if __name__ == '__main__':
  for module in get_modules(*sys.argv[1:2]):
    print(module)
