'''
Regular expressions by non-determinism.

Python parses a small pattern syntax into Curry data of type Regex.RE and
calls two Curry functions on it.  match tests whether a whole subject is a
word of the pattern.  grep finds every substring of the subject that is a
word of the pattern.

Pattern syntax: a character stands for itself, . is any character, | is
alternation, * + ? repeat the item before them, and parentheses group.  A
backslash makes the next character literal.

Usage: python go.py                  (runs the built-in cases)
       python go.py PATTERN SUBJECT  (runs match and grep on one pair)
'''
import os
import sys
import curry

# Find Regex.curry next to this file, whatever the working directory is.
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Regex

CASES = [
    ('match', 'ab*c', 'abbbc'),
    ('match', 'a.c', 'axc'),
    ('match', 'a.c', 'abbc'),
    ('grep', 'ab*c', 'xxxxxxxxxxxxxxxabbbcyyyyyyyyyyyyyyyyyyyyy'),
    ('grep', 'a+b?', 'zzaaabzz'),
    ('grep', '(cat|dog)s?', 'cats and dogs and a dog'),
  ]

class PatternError(Exception):
  pass

def parse(pattern):
  '''Parses a pattern into nested tuples.  The first item of each tuple is
  the name of a constructor of Regex.RE.

  alt  := seq ('|' seq)*
  seq  := rep rep*
  rep  := atom ('*' | '+' | '?')*
  atom := '(' alt ')' | '.' | '\\' char | char
  '''
  pos = 0

  def peek():
    return pattern[pos] if pos < len(pattern) else None

  def alt():
    nonlocal pos
    node = seq()
    while peek() == '|':
      pos += 1
      node = ('Alt', node, seq())
    return node

  def seq():
    node = None
    while peek() not in (None, '|', ')'):
      item = rep()
      node = item if node is None else ('Seq', node, item)
    if node is None:
      raise PatternError('empty branch at position %d of %r' % (pos, pattern))
    return node

  def rep():
    nonlocal pos
    node = atom()
    while peek() in ('*', '+', '?'):
      node = ({'*': 'Star', '+': 'Plus', '?': 'Opt'}[peek()], node)
      pos += 1
    return node

  def atom():
    nonlocal pos
    ch = peek()
    if ch in ('*', '+', '?'):
      raise PatternError('nothing to repeat at position %d of %r' % (pos, pattern))
    pos += 1
    if ch == '(':
      node = alt()
      if peek() != ')':
        raise PatternError('missing ) in %r' % pattern)
      pos += 1
      return node
    if ch == '.':
      return ('Any',)
    if ch == '\\':
      if peek() is None:
        raise PatternError('nothing after \\ in %r' % pattern)
      ch = peek()
      pos += 1
    return ('Lit', ch)

  node = alt()
  if pos != len(pattern):
    raise PatternError('unexpected ) at position %d of %r' % (pos, pattern))
  return node

def build(ast):
  '''Builds the Curry value of type Regex.RE for a parsed pattern.

  Each tuple becomes an application of the constructor of the same name.
  The argument of Lit is a str of length one, which curry.expr turns into a
  Char.
  '''
  tag, args = ast[0], ast[1:]
  args = [build(arg) if isinstance(arg, tuple) else arg for arg in args]
  return curry.expr(getattr(Regex, tag), *args)

def match(pattern, subject):
  '''True when the whole subject is a word of the pattern.'''
  values = curry.eval(Regex.match, build(parse(pattern)), subject,
                      converter='topython')
  # A failed guard is not an error: the goal has no value.  One True is
  # enough, so take the first value and stop the search.
  return next(values, False)

def grep(pattern, subject):
  '''Every hit of the pattern in the subject as (before, hit, after).'''
  values = curry.eval(Regex.grep, build(parse(pattern)), subject,
                      converter='topython')
  # Each value is a tuple of three Curry Strings, which the converter turns
  # into Python strings, the empty String into ''.  A pattern such as a*a*
  # derives one hit in several ways, and each derivation is one value, so a
  # set keeps one copy of each hit.
  hits = set(tuple(value) for value in values)
  # The order of the values is not promised.  Sort by position, then length.
  return sorted(hits, key=lambda hit: (len(hit[0]), len(hit[1])))

def show_match(pattern, subject):
  print('match %s %s: %s' % (pattern, subject, match(pattern, subject)))

def show_grep(pattern, subject):
  hits = grep(pattern, subject)
  print('grep %s in %s: %d hit%s' % (pattern, subject, len(hits),
                                     '' if len(hits) == 1 else 's'))
  for before, hit, after in hits:
    print('  %s[%s]%s' % (before, hit, after))

def main(argv):
  if len(argv) == 3:
    cases = [('match',) + tuple(argv[1:]), ('grep',) + tuple(argv[1:])]
  elif len(argv) == 1:
    cases = CASES
  else:
    sys.stderr.write(__doc__)
    return 2
  try:
    for kind, pattern, subject in cases:
      (show_match if kind == 'match' else show_grep)(pattern, subject)
  except PatternError as error:
    sys.stderr.write('go.py: %s\n' % error)
    return 1
  return 0

if __name__ == '__main__':
  sys.exit(main(sys.argv))
