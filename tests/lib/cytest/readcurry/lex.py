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

def tokenize(text):
  i = 0
  iend = len(text)
  while i < iend:
    c = text[i]
    if c.isspace():   # whitespace
      i += 1
    elif c in '([]),': # special symbols
      yield DelimiterToken(c)
      i += 1
    elif c == "'":    # chars
      j = i + 1
      chars = []
      while j < iend:
        if text[j:j+2] == r"\'":
          chars.append("'")
          j += 2
        elif text[j] == "'":
          j += 1
          break
        else:
          chars.append(text[j])
          j += 1
      yield CharToken(''.join(chars))
      i = j
    elif c == '"':    # strings
      j = i + 1
      chars = []
      while j < iend:
        if text[j:j+2] == r'\"':
          chars.append('"')
          j += 2
        elif text[j] == '"':
          j += 1
          break
        else:
          chars.append(text[j])
          j += 1
      yield StringToken(''.join(chars))
      i = j
    elif c.isdigit():  # numbers
      j = i + 1
      while j < iend and text[j].isdigit():
        j += 1
      if text[j] == '.':
        j += 1
        while j < iend and text[j].isdigit():
          j += 1
      yield NumberToken(text[i:j])
      i = j
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
