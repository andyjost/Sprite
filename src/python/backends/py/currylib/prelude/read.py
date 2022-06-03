'''
Functions for parsing literals.
'''
# FIXME: the functions in this module may not handle set guards properly.

from ... import graph
from ..... import inspect
from . import string
import six

__all__ = [
    'readCharLiteral', 'readFloatLiteral', 'readNatLiteral'
  , 'readStringLiteral'
  ]

def readCharLiteral(rts, s):
  '''
  Parse a character literal from a Curry string.

  The literal begins and ends with a single quote.  The body contains an ASCII
  character other than a backslash or single quote, or a backslash followed by
  one of the following:

    - Any character in "bfnrtv".
    - A single quote.
    - A backslash.
    - A natural number less than 1114112.
    - A hexadecimal integer less than 0x110000.

  Yields:
    A list whose head is a pair of the parsed character and remaining string
    and whose tail is this function applied to the tail.
  '''
  s_in = s
  try:
    # Get the character.
    c, s = _getchar(rts, s)
    if c != "'":
      raise ParseError()
    c, s = _getchar(rts, s)
    if c == '\\':
      c_out, s = _parseEscapeCode(rts, s)
    elif ord(c) < 256 and c != "'":
      c_out = c
    else:
      raise ParseError()

    # Eat the closing quote.
    c, s = _getchar(rts, s)
    if c != "'":
      raise ParseError()

    yield rts.prelude.Cons
    yield graph.Node(
        rts.prelude.Pair
      , graph.Node(rts.prelude.Char, c_out)
      , s
      )
    yield graph.Node(rts.prelude.Nil)
  except ParseError:
    yield rts.Failure


def readFloatLiteral(rts, s):
  '''
  Parse a floating-point number from a Curry string.  Returns a pair consisting
  of the value and the remaining string.
  '''
  num = []
  Cons = rts.prelude.Cons
  if inspect.isa(s.target, Cons):
    _1 = rts.variable(s, 0)
    c = _1.unboxed_value
    if c in '+-':
      num.append(c)
      s = rts.variable(s, 1)
  have_dot = False
  while inspect.isa(s.target, Cons):
    _1 = rts.variable(s, 0)
    c = _1.unboxed_value
    if c.isdigit():
      num.append(c)
      s = rts.variable(s, 1)
    elif c == '.' and not have_dot:
      have_dot = True
      num.append(c)
      s = rts.variable(s, 1)
    else:
      yield rts.Failure
      return
  if not num:
    yield rts.Failure
    return
  value = float(''.join(num))
  yield rts.prelude.Cons
  yield graph.Node(
      rts.prelude.Pair
    , graph.Node(rts.prelude.Float, value)
    , s
    )
  yield graph.Node(rts.prelude.Nil)


def readNatLiteral(rts, s):
  '''
  Parse a natural number from a Curry string.  Returns a pair consisting of the
  value and the remaining string.
  '''
  num = []
  Cons = rts.prelude.Cons
  while inspect.isa(s.target, Cons):
    _1 = rts.variable(s, 0)
    c = _1.unboxed_value
    if c.isdigit():
      num.append(c)
      s = rts.variable(s, 1)
    else:
      yield rts.Failure
      return
  if not num:
    yield rts.Failure
    return
  value = int(''.join(num))
  yield rts.prelude.Cons
  yield graph.Node(
      rts.prelude.Pair
    , graph.Node(rts.prelude.Int, value)
    , s
    )
  yield graph.Node(rts.prelude.Nil)

def readStringLiteral(rts, s):
  '''
  Parse a string literal from a Curry string.

  The literal begins and ends with a double quote.  The body contains a string of ASCII
  characters and uses the same escape codes as for character literals.

  Yields:
    A list whose head is a pair of the parsed string and remaining string
    and whose tail is this function applied to the tail.
  '''
  s_in = s
  try:
    s_out = []
    c, s = _getchar(rts, s)
    if c != '"':
      raise ParseError()
    while True:
      c, s = _getchar(rts, s)
      if c == '\\':
        c, s = _parseEscapeCode(rts, s)
        s_out.append(c)
      elif ord(c) < 256:
        if c == '"':
          break
        else:
          s_out.append(c)
      else:
        raise ParseError()
    yield rts.prelude.Cons
    yield graph.Node(
        rts.prelude.Pair
      , string.pystring(rts, ''.join(s_out))
      , s
      )
    yield graph.Node(rts.prelude.Nil)
  except ParseError:
    yield rts.Failure


class ParseError(BaseException):
  '''Used internally.'''

def _getchar(rts, s):
  '''
  Get and unbox the head character of a string.  Return a pair of it and the
  tail.
  '''
  if inspect.isa(s.target, rts.prelude.Cons):
    _1 = rts.variable(s, 0)
    _2 = rts.variable(s, 1)
    return _1.unboxed_value, _2
  raise ParseError()

def _parseDecChar(rts, s, digits=None):
  '''
  Parses a string of decimal digits.  Returns the corresponding character and
  string tail.
  '''
  digits = digits or []
  s_prev = s
  while True:
    c, s = _getchar(rts, s_prev)
    if c.isdigit():
      digits.append(c)
    elif not digits:
      raise ParseError()
    else:
      return six.unichr(int(''.join(digits), 10)), s_prev
    s_prev = s

ESCAPE_CODES = {
    '\\':'\\'  # \\ -> \
  , '"':'"'    # \" -> "
  , "'":"'"    # \' -> '
  , 'a':'\a'
  , 'b':'\b'
  , 'f':'\f'
  , 'n':'\n'
  , 'r':'\r'
  , 't':'\t'
  , 'v':'\v'
  }

def _parseEscapeCode(rts, s):
  c, s = _getchar(rts, s)
  if c in ESCAPE_CODES:
    return ESCAPE_CODES[c], s
  elif c == 'x': # hex escape code
    return _parseHexChar(rts, s)
  elif c == 'o': # octal escape code
    return _parseOctChar(rts, s)
  elif c.isdigit(): # decimal escape code
    return _parseDecChar(rts, s, [c])
  else:
    raise ParseError()

HEXDIGITS = set('0123456789abcdef')

def _parseHexChar(rts, s, digits=None):
  '''
  Parses a string of hexadecimal digits.  Returns the corresponding character
  and string tail.
  '''
  digits = digits or []
  s_prev = s
  while True:
    c, s = _getchar(rts, s_prev)
    if c in HEXDIGITS:
      digits.append(c)
    elif not digits:
      raise ParseError()
    else:
      return six.unichr(int(''.join(digits), 16)), s_prev
    s_prev = s

OCTDIGITS = set('01234567')

def _parseOctChar(rts, s, digits=None):
  '''
  Parses a string of octal digits.  Returns the corresponding character
  and string tail.
  '''
  digits = digits or []
  s_prev = s
  while True:
    c, s = _getchar(rts, s_prev)
    if c in OCTDIGITS:
      digits.append(c)
    elif not digits:
      raise ParseError()
    else:
      return six.unichr(int(''.join(digits), 8)), s_prev
    s_prev = s

