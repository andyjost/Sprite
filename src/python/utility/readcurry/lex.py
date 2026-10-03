import re

__all__ = [
    'tokenize'
  , 'CharToken', 'DelimiterToken', 'IdentifierToken', 'NumberToken'
  , 'OperatorToken', 'StringToken'
  ]

# Identifiers
class IdentifierToken(str): pass
class ApplicativeToken(IdentifierToken): pass
#
class ConstructorToken(ApplicativeToken): pass
class FreevarToken(IdentifierToken): pass
class FunctionToken(ApplicativeToken): pass
class OperatorToken(ApplicativeToken): pass

# Other tokens.
class CharToken(str): pass
class DelimiterToken(str): pass
class NumberToken(str): pass
class StringToken(str): pass

CONSTRUCTOR = re.compile(r'([A-Z]\w*)')   # E.g., F or Apple
FREEVAR     = re.compile(r'(_[a-z]+\d*)') # E.g., _a or _x5
FUNCTION    = re.compile(r'([a-z]\w*)')   # E.g., f or zip
OPERATOR    = re.compile(r'([^\w\s]+)')   # E.g., : or =:= or <<

DELIMITERS = {s: DelimiterToken(s) for s in '()[],'}

def printtok(tok):
  print(showtok(tok))

def showtok(tok):
  return '%-18s %s' % (type(tok).__name__, tok)

NAMED_ESC = {
    r"\'" : "'"
  , r"\"" : '"'
  , r"\\" : '\\'
  , r"\a" : '\a'
  , r"\b" : '\b'
  , r"\f" : '\f'
  , r"\n" : '\n'
  , r"\r" : '\r'
  , r"\t" : '\t'
  , r"\v" : '\v'
  , r"\&" : ''     # the empty escape, which ends a decimal escape before a digit
  }
# The ASCII control names, as the Haskell show writes them.  The Curry front
# end writes FlatCurry with show, so a NUL character is '\NUL' and DEL is
# '\DEL'.  The longest name must match first: '\SOH' is one character.
ASCII_NAMES = [
    'NUL', 'SOH', 'STX', 'ETX', 'EOT', 'ENQ', 'ACK', 'BEL', 'BS', 'HT', 'LF'
  , 'VT', 'FF', 'CR', 'SO', 'SI', 'DLE', 'DC1', 'DC2', 'DC3', 'DC4', 'NAK'
  , 'SYN', 'ETB', 'CAN', 'EM', 'SUB', 'ESC', 'FS', 'GS', 'RS', 'US', 'SP'
  ]
ASCII_CODES = {name: code for code, name in enumerate(ASCII_NAMES)}
ASCII_CODES['DEL'] = 127
ASCII = re.compile(
    r'\\(' + '|'.join(sorted(ASCII_CODES, key=len, reverse=True)) + ')'
  )
DEC = re.compile(r'\\([1-9][0-9]{0,6})') # up to 1114111, the last code point
OCTAL = re.compile(r'\\([0-7]{1,3})')
UNICODE = re.compile(r'\\u[0-9a-fA-f]{4}')

def qescape(text, chars, j):
  # Must be one of:
  #   - One of the named escape sequences listed in NAMED_ESC.
  #   - An ASCII control name, such as '\NUL' or '\DEL'.
  #   - A decimal escape sequence; '\' followed by up to seven decimal digits,
  #     not all zero.  A code point above 999 has more than three digits.  The
  #     read is greedy, as in Curry: "\2281" is one character.
  #   - An octal escape sequence; '\0' followed by one, two or three octal digits,
  #     not all zero.
  #   - A Unicode escape sequence; 'u' followed by four hex digits.
  if text[j:j+2] in NAMED_ESC:
    chars.append(NAMED_ESC[text[j:j+2]])
    return 2

  match = re.match(ASCII, text[j:])
  if match:
    chars.append(chr(ASCII_CODES[match.group(1)]))
    return match.end()

  for pattern, base in [(DEC, 10), (OCTAL, 8), (UNICODE, 16)]:
    match = re.match(pattern, text[j:])
    if match:
      digits = match.group(1)
      if digits == '000':
        raise ValueError('Invalid escape sequence: %s' % r'\000')
      chars.append(chr(int(digits, base=base)))
      return match.end()
  raise ValueError('Invalid escape sequence: %s ...' % text[j:j+8])

def tokenize_quoted(text, j, iend, token_type, endquote):
  j += 1
  chars = []
  while j < iend:
    if text[j] == '\\':
      j += qescape(text, chars, j)
    elif text[j] == endquote:
      j += 1
      break
    else:
      chars.append(text[j])
      j += 1
  return j, token_type(''.join(chars))

# A number has an optional sign, digits, an optional fraction, and an optional
# exponent, e.g., 5, -5, 1.5, 1.0e-5.
NUMBER = re.compile(r'(-?\d+(\.\d*)?([eE][-+]?\d+)?)')
def tokenize_number(text, i, iend):
  match = re.match(NUMBER, text[i:])
  return i+match.end(), NumberToken(match.group(1))

def is_sign(text, i, iend, prev):
  '''
  Tells whether the '-' at position ``i`` is the sign of a number.  Curry
  writes a negative number only at the start of the text or after an opening
  delimiter or a comma, as in "(-1)" or "[1,-2]".  Elsewhere, '-' is an
  operator.
  '''
  if i+1 >= iend or not text[i+1].isdigit():
    return False
  return prev is None or (isinstance(prev, DelimiterToken) and prev in '([,')

def tokenize(text):
  i = 0
  iend = len(text)
  prev = None
  while i < iend:
    c = text[i]
    if c.isspace():
      i += 1
      continue
    elif c in DELIMITERS:
      tok = DELIMITERS[c]
      i += 1
    elif c == "'":
      i, tok = tokenize_quoted(text, i, iend, CharToken, "'")
    elif c == '"':
      i, tok = tokenize_quoted(text, i, iend, StringToken, '"')
    elif c.isdigit() or (c == '-' and is_sign(text, i, iend, prev)):
      i, tok = tokenize_number(text, i, iend)
    else:
      for pattern, TokenType in [
          (CONSTRUCTOR, ConstructorToken)
        , (FUNCTION   , FunctionToken)
        , (FREEVAR    , FreevarToken)
        , (OPERATOR   , OperatorToken)
        ]:
        m = re.match(pattern, text[i:])
        if m:
          tok = TokenType(m.group(1))
          i += m.end()
          break
      else:
        assert False
    yield tok
    prev = tok
