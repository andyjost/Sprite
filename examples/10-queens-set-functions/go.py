'''
N queens with set functions.

Calls the Curry function ``queens`` with an Int from Python, collects every
value it produces, counts the solutions, and draws the smallest board.

Usage: python go.py [N ...]      (default: 4 5 6)
'''
import os
import sys
import curry

# Find Queens.curry next to this file, whatever the working directory is.
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Queens

def board(solution):
  '''Draws a placement as rows of dots with one Q in each row.'''
  n = len(solution)
  rows = []
  for q in solution:
    rows.append(' '.join('Q' if col == q else '.' for col in range(1, n + 1)))
  return '\n'.join(rows)

def main(sizes):
  first = True
  for n in sizes:
    if not first:
      print()
    first = False
    # One Curry call is a generator of solutions.  converter='topython' turns
    # each Curry list of Ints into a Python list of ints.  The order of the
    # values is not promised, so sort them before taking the smallest.
    solutions = sorted(curry.eval(Queens.queens, n, converter='topython'))
    if not solutions:
      print('n=%d: 0 solutions' % n)
      continue
    print('n=%d: %d solutions, smallest %s' % (n, len(solutions), solutions[0]))
    print(board(solutions[0]))

if __name__ == '__main__':
  main([int(arg) for arg in sys.argv[1:]] or [4, 5, 6])
