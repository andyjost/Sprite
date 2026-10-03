'''
Solves Sudoku puzzles with Curry's built-in search.

Python reads each puzzle file, hands the grid to the Curry function
Sudoku.solve as a nested list of Ints, and takes every value of the goal.
Each value is one completed board.  The number of values is the number of
solutions.

Usage: python go.py [FILE ...]
With no arguments, it solves puzzle.txt and ambiguous.txt.
'''
import os
import sys
import curry

# Add this directory to the Curry search path so that Sudoku.curry is found
# from any working directory.
HERE = os.path.dirname(os.path.abspath(__file__))
curry.path.insert(0, HERE)

from curry.lib import Sudoku

DEFAULT_FILES = ['puzzle.txt', 'ambiguous.txt']

def read_puzzle(filename):
  '''Reads nine lines of nine characters.  A dot is a blank cell, stored as 0.'''
  board = []
  with open(filename) as stream:
    for line in stream:
      line = line.strip()
      if line:
        board.append([0 if ch == '.' else int(ch) for ch in line])
  if len(board) != 9 or any(len(row) != 9 for row in board):
    raise SystemExit('%s must hold nine rows of nine cells' % filename)
  return board

def show(board):
  '''Formats a board as nine lines.  A zero prints as a dot.'''
  return '\n'.join(''.join('.' if v == 0 else str(v) for v in row) for row in board)

def solve_file(filename):
  board = read_puzzle(filename)
  print('puzzle %s:' % os.path.basename(filename))
  print(show(board))

  # The nested Python list becomes the Curry value of type [[Int]].  The goal
  # is the expression `solve board`.  Each value of the goal is one solution,
  # converted back to a nested Python list by converter='topython'.  The
  # values are sorted because Curry promises no order among them.
  solutions = sorted(curry.eval(Sudoku.solve, board, converter='topython'))

  for i, solution in enumerate(solutions, 1):
    print('solution %d:' % i)
    print(show(solution))
  print('solutions:', len(solutions))
  print()

def main():
  files = sys.argv[1:] or [os.path.join(HERE, name) for name in DEFAULT_FILES]
  for filename in files:
    solve_file(filename)

if __name__ == '__main__':
  main()
