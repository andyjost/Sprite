'''
Regular expressions by non-determinism.

Python parses a small pattern syntax into Curry data of type Regex.RE and
calls three Curry functions on it.  sem generates the words of the pattern,
one per value.  match tests whether a whole subject is a word of the
pattern.  grep finds every substring of the subject that is a word of the
pattern.

Pattern syntax: a character stands for itself, . is any character, | is
alternation, * + ? repeat the item before them, and parentheses group.  A
backslash makes the next character literal.

Usage: python go.py                  (runs the built-in cases)
       python go.py PATTERN SUBJECT  (runs match and grep on one pair)
       python go.py --words PATTERN [N]  (the first N words, 10 by default)
'''
import itertools
import os
import sys
import curry

# Find Regex.curry next to this file, whatever the working directory is.
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Regex

CASES = [
    ('words', '(cat|dog)s?', None),
    ('match', 'ab*c', 'abbbc'),
    ('match', 'a.c', 'axc'),
    ('match', 'a.c', 'abbc'),
    ('grep', 'ab*c', 'xxxxxxxabbbcyyyyyyyy'),
    ('grep', 'a+b?', 'zzaaabzz'),
    ('grep', '(cat|dog)s?', 'cats, dogs and a dog'),
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

def words(pattern):
  '''Every word of a star-free pattern, sorted.'''
  values = curry.eval(Regex.sem, build(parse(pattern)), converter='topython')
  # Each value is one word.  The order of the values is not promised, so
  # sort them.  A pattern with a star has infinitely many words, and a word
  # of a pattern with . holds a free character, which the converter rejects;
  # first_words shows both without the converter.
  return sorted(values)

def first_words(pattern, count):
  '''The first count words of any pattern, in Curry syntax.'''
  values = curry.eval(Regex.sem, build(parse(pattern)))
  return [str(value) for value in itertools.islice(values, count)]

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

def show_words(pattern, subject=None):
  print('words %s: %s' % (pattern, ' '.join(words(pattern))))

def show_match(pattern, subject):
  print('match %s %s: %s' % (pattern, subject, match(pattern, subject)))

def show_grep(pattern, subject):
  hits = grep(pattern, subject)
  print('grep %s in %s: %d hit%s' % (pattern, subject, len(hits),
                                     '' if len(hits) == 1 else 's'))
  for before, hit, after in hits:
    print('  %s[%s]%s' % (before, hit, after))

SHOW = {'words': show_words, 'match': show_match, 'grep': show_grep}

def main(argv):
  if len(argv) in (3, 4) and argv[1] == '--words':
    count = int(argv[3]) if len(argv) == 4 else 10
    try:
      for word in first_words(argv[2], count):
        print(word)
    except PatternError as error:
      sys.stderr.write('go.py: %s\n' % error)
      return 1
    return 0
  if len(argv) == 3:
    cases = [('match',) + tuple(argv[1:]), ('grep',) + tuple(argv[1:])]
  elif len(argv) == 1:
    cases = CASES
  else:
    sys.stderr.write(__doc__)
    return 2
  try:
    for kind, pattern, subject in cases:
      SHOW[kind](pattern, subject)
  except PatternError as error:
    sys.stderr.write('go.py: %s\n' % error)
    return 1
  return 0

if __name__ == '__main__':
  sys.exit(main(sys.argv))
