'''
Trait checking by narrowing over an algebraic model of C++ types.

Passes a depth and the names of the properties to Curry.  For each property,
Curry searches every type of the model up to that depth for a counterexample
and returns a report as text, which this driver prints.

Usage: python go.py [DEPTH] [PROPERTY ...]      (default: 2, every property)
'''
import os
import sys
import curry

# Find the shared modules under ../cxx, whatever the working directory is.
HERE = os.path.dirname(os.path.abspath(__file__))
curry.path.insert(0, os.path.join(HERE, '..', 'cxx'))
from curry.lib import CxxCheck

# The properties of CxxCheck, in the order of the report.  The last one
# checks a trait that is wrong on purpose.
PROPERTIES = [
    'scalar', 'fundamental', 'object', 'category', 'decay_twice', 'cvref'
  , 'wrong_scalar'
  ]

def text(goal, *args):
  '''The one value of a goal that returns a String, as a str.'''
  return next(curry.eval(goal, *args, converter='topython'))

def main(depth, names):
  print(text(CxxCheck.header, depth))
  for name in names:
    # A name is passed as a list of characters: a str of length one would
    # become a Char.
    print(text(CxxCheck.check, depth, list(name)))

if __name__ == '__main__':
  args = sys.argv[1:]
  depth = int(args.pop(0)) if args and args[0].isdigit() else 2
  main(depth, args or PROPERTIES)
