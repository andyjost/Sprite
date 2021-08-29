#!/usr/bin/python
'''Prints the names of all Curry system libraries.'''
import os

def get_modules():
  yield 'Prelude'
  for dirpath, dirnames, filenames in os.walk('.'):
    dirnames[:] = filter(lambda dirname: not dirname.startswith('pakcs'), dirnames)
    for filename in filenames:
      if filename.endswith('.curry'):
        fullname = os.path.join(dirpath, filename[:-6])
        yield '.'.join(
            part for part in fullname.split(os.sep)
            if part and not part.startswith('.')
          )

if __name__ == '__main__':
  for module in get_modules():
    print module
