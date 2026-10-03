'''
An expression parser from functional patterns.

Parses arithmetic expressions with the Curry function ``expr``.  For each
input it prints every parse tree, the value of the tree, and the number of
parses.  An input with no parse prints "no parse".

Usage: python go.py [EXPRESSION ...]
'''
import os
import sys
import curry

# Find Parser.curry next to this file, whatever the working directory is.
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Parser

DEFAULT_INPUTS = [
    '1+2*3',
    '2*(3+4)-5',
    '10-2-3',
    '(1+2)*(3+4)+5*6',
    '1+2*3-4*5+6*7-8*9+10',
    '2*(3+4',
  ]

def text(s):
  '''A Python str of length one converts to a Curry Char.  Pass every String
  argument as a list of characters instead.'''
  return list(s)

def parses(s):
  '''Returns every parse tree of s.  Each tree is a Curry value.'''
  # The scheduler does not promise an order of the values, so sort them.
  return sorted(curry.eval(Parser.expr, text(s)), key=str)

def value(tree):
  '''Passes a parse tree back to Curry and returns its value as an int.'''
  return next(curry.eval(Parser.eval, tree, converter='topython'))

def main(inputs):
  for raw in inputs:
    s = ''.join(raw.split())   # the grammar has no whitespace
    trees = parses(s)
    if not trees:
      print('%s  ->  no parse' % s)
      continue
    count = '%d parse%s' % (len(trees), '' if len(trees) == 1 else 's')
    for tree in trees:
      # str of a Curry value prints its constructors, e.g. Add (Num 1) (Num 2).
      print('%s  ->  %s  =  %d  (%s)' % (s, tree, value(tree), count))

if __name__ == '__main__':
  main(sys.argv[1:] or DEFAULT_INPUTS)
