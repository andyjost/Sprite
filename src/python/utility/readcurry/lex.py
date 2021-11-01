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
  print showtok(tok)

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
  }
OCTAL = re.compile(r'\\([0-7]{1,3})')
UNICODE = re.compile(r'\\u[0-9a-fA-f]{4}')

def qescape(text, chars, j):
  # Must be one of:
  #   - One of the named escape sequences listed in NAMED_ESC.
  #   - An octal escape sequence; '\' followed by one two or three octal digits,
  #     not all zero.
  #   - A Unicode escape sequence; 'u' followed by four hex digits.
  if text[j:j+2] in NAMED_ESC:
    chars.append(NAMED_ESC[text[j:j+2]])
    return 2

  match = re.match(OCTAL, text[j:])
  if match:
    digits = match.group(1)[1:]
    if digits == '000':
      raise ValueError('Invalid escape sequence: %s' % r'\000')
    chars.append(unichr(int(digits, base=8)).encode('utf-8'))
    return match.end()
  match = re.match(UNICODE, text[j:])
  if match:
    digits = match.group(1)[1:]
    chars.append(unichr(int(digits, base=16)).encode('utf-8'))
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

NUMBER = re.compile('(\d+(\.\d*)?)')
def tokenize_number(text, i, iend):
  match = re.match(NUMBER, text[i:])
  return i+match.end(), NumberToken(match.group(1))

def tokenize(text):
  i = 0
  iend = len(text)
  while i < iend:
    c = text[i]
    if c.isspace():
      i += 1
    elif c in DELIMITERS:
      yield DELIMITERS[c]
      i += 1
    elif c == "'":
      i, tok = tokenize_quoted(text, i, iend, CharToken, "'")
      yield tok
    elif c == '"':
      i, tok = tokenize_quoted(text, i, iend, StringToken, '"')
      yield tok
    elif c.isdigit():
      i, tok = tokenize_number(text, i, iend)
      yield tok
    else:
      for pattern, TokenType in [
          (CONSTRUCTOR, ConstructorToken)
        , (FUNCTION   , FunctionToken)
        , (FREEVAR    , FreevarToken)
        , (OPERATOR   , OperatorToken)
        ]:
        m = re.match(pattern, text[i:])
        if m:
          yield TokenType(m.group(1))
          i += m.end()
          break
      else:
        assert False
