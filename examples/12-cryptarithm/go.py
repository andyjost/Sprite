'''
Solves cryptarithms with a Curry solver driven from Python.

Usage: python go.py [WORD ... WORD RESULT]

The last word is the result and the words before it are the addends.  Without
arguments, the script solves SEND + MORE = MONEY and TWO + TWO = FOUR.
'''

import os
import sys
import curry

# Find Crypt.curry next to this script, from any working directory.
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Crypt

DEFAULT_PUZZLES = [
    ['SEND', 'MORE', 'MONEY'],
    ['TWO', 'TWO', 'FOUR'],
  ]

def text(s):
  # A Python str of length one converts to a Curry Char, so pass every
  # String argument as a list of characters.
  return list(s)

def check(words):
  '''Returns an error message if the solver cannot handle the puzzle.'''
  if len(words) < 2:
    return 'a puzzle needs at least one addend and a result'
  for word in words:
    if not (word.isascii() and word.isalpha() and word.isupper()):
      return 'word %r is not made of upper-case letters' % word
  letters = set(''.join(words))
  if len(letters) > 10:
    return 'a puzzle has at most ten distinct letters; this one has %d' \
        % len(letters)
  return None

def number(digits, word):
  '''The number a word stands for under an assignment.'''
  return int(''.join(str(digits[c]) for c in word))

def solve(addends, result):
  '''Returns the solutions as lists of numbers, one per word, sorted.'''
  # Each value of solveCrypt is one assignment, converted to a list of
  # (letter, digit) pairs.  The order of the values is not fixed, so sort.
  values = curry.eval(
      Crypt.solveCrypt, [text(w) for w in addends], text(result)
    , converter='topython'
    )
  solutions = []
  for env in values:
    digits = dict(env)
    solutions.append([number(digits, w) for w in addends + [result]])
  return sorted(solutions)

def main(argv):
  puzzles = [argv[1:]] if len(argv) > 1 else DEFAULT_PUZZLES
  for words in puzzles:
    error = check(words)
    if error is not None:
      sys.stderr.write('go.py: %s\n' % error)
      return 1
  for i, words in enumerate(puzzles):
    addends, result = words[:-1], words[-1]
    if i:
      print()
    print('%s = %s' % (' + '.join(addends), result))
    solutions = solve(addends, result)
    for numbers in solutions:
      print('  %s = %d' % (' + '.join(map(str, numbers[:-1])), numbers[-1]))
    print('solutions: %d' % len(solutions))
  return 0

if __name__ == '__main__':
  sys.exit(main(sys.argv))
