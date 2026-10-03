'''
Runs a Curry program from Python.

Imports the module rev from the directory of this script and prints every
value of its goal main.
'''
import os
import curry

# Find rev.curry next to this file, whatever the working directory is.
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import rev

# A Curry evaluation can produce several values, so curry.eval returns an
# iterator.  Print each value.
for value in curry.eval(rev.main):
  print(value)
