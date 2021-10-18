'''
Functions for parsing literals.
'''
# FIXME: the functions in this module may not handle set guards properly.

from ...... import inspect

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
  --------
    Components of a Curry pair consisting of the parsed character and the
    string tail following the closing quote.  If no character can be parsed,
    returns char '\0' and the original string.
  '''
  s_in = s
  try:
    # First, yield the Curry symbol for a pair.
    yield getattr(rts.prelude, '(,)')

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

    # Second, yield the character as a Curry Char.
    yield rts.expr(c_out)

    # Third, yield the string tail.
    yield s
  except ParseError:
    yield rts.expr('\0')
    yield s_in


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
      break
  yield getattr(rts.prelude, '(,)')
  yield rts.expr(float(''.join(num) if num else 'nan'))
  yield s


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
      break
  yield getattr(rts.prelude, '(,)')
  yield rts.expr(int(''.join(num)) if num else 0)
  yield s

def readStringLiteral(rts, s):
  '''
  Parse a string literal from a Curry string.

  The literal begins and ends with a double quote.  The body contains a string of ASCII
  characters and uses the same escape codes as for character literals.

  Yields:
  --------
    Components of a Curry pair consisting of the parsed string literal and the
    Curry string tail following the closing quote.  If no string can be parsed,
    returns and empty string and the original string.
  '''
  s_in = s
  try:
    yield getattr(rts.prelude, '(,)')
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
          yield rts.expr(''.join(s_out))
          yield s
          return
        else:
          s_out.append(c)
      else:
        raise ParseError()
  except ParseError:
    yield rts.expr("")
    yield s_in


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
      return unichr(int(''.join(digits), 10)).encode('utf-8'), s_prev
    s_prev = s

ESCAPE_CODES = {
    '\\':'\\'  # \\ -> \
  , '"':'"'    # \" -> "
  , "'":"'"    # \' -> '
  , 'b':'\b', 'f':'\f', 'n':'\n', 'r':'\r', 't':'\t', 'v':'\v'
  }

def _parseEscapeCode(rts, s):
  c, s = _getchar(rts, s)
  if c in ESCAPE_CODES:
    return ESCAPE_CODES[c], s
  elif c == 'x': # hex escape code
    return _parseHexChar(rts, s)
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
      return unichr(int(''.join(digits), 16)).encode('utf-8'), s_prev
    s_prev = s

