from . import lex, types

__all__ = ['Parser', 'parse']

def parse(curry_text, **kwds):
  '''
  Parse the output of a Curry system.

  This is a parser for Curry values, not source code.  It reads tuples, lists,
  numbers, strings, character constants, free variables, constructor symbols,
  and function symbols.  As such, is is suitable for reading certain Curry-like
  data formats, such as FlatCurry and ICurry.  It is also useful in testing, as
  it provides a way to load the results (i.e., values) of Curry programs.  This
  way, one can compare the output of different Curry systems.

  It is assumed that functions begin with lowercase letters, data constructors
  begin with uppercase letters, and free variables are represented as an
  underscore followed by one or more lowercase letters, followed by zero or
  more digits.
  '''
  parser = Parser(curry_text, **kwds)
  return parser.parse()

class Parser(object):
  def __init__(self, text):
    self.text = text
    self.tokens = list(lex.tokenize(self.text))
    self.index = self.study()

  def study(self):
    '''Builds an index of matching positions for parentheses and brackets.'''
    stack = []
    index = {}
    lparen,rparen,lbracket,rbracket = [lex.DELIMITERS[c] for c in '()[]']
    for ipos, tok in enumerate(self.tokens):
      if tok is lparen or tok is lbracket:
        stack.append(ipos)
      elif tok is rparen or tok is rbracket:
        index[stack.pop()] = ipos
    return index

  def parse(self):
    expr, i = self.parse_expr(0, len(self.tokens))
    assert i == len(self.tokens)
    return expr

  def parse_expr(self, begin, end):
    # Example:
    #     'F (A 5), (B 6)'
    # Parses 'F (A 5)', eats the comma, returns the cursor at '(' before B.
    terms = []
    while begin < end:
      tok = self.tokens[begin]
      if isinstance(tok, lex.DelimiterToken):
        if tok == '(':
          close =  self.index[begin]
          terms.append(self.parse_parens(begin+1, close))
          begin = close + 1
        elif tok == '[':
          close =  self.index[begin]
          terms.append(self.parse_sequence(begin+1, close))
          begin = close + 1
        elif tok == ',':
          begin += 1
          break
        else:
          assert False
      elif isinstance(tok, lex.NumberToken):
        try:
          value = types.Int(tok)
        except ValueError:
          value = types.Float(tok)
        terms.append(value)
        begin += 1
      elif isinstance(tok, lex.StringToken):
        terms.append(types.String(tok))
        begin += 1
      elif isinstance(tok, lex.CharToken):
        terms.append(types.Char(tok))
        begin += 1
      elif isinstance(tok, lex.IdentifierToken):
        if terms:
          term, begin = self.parse_expr(begin, begin+1)
          terms.append(term)
        else:
          terms.append(types.make_identifier(tok))
          begin += 1
      else:
        assert False

    expr = make_expression(terms, otherwise=types.Applic)
    return expr, begin

  def parse_parens(self, begin, end):
    terms = self.parse_sequence(begin, end)
    return make_expression(terms, otherwise=lambda *args: tuple(args))

  def parse_sequence(self, begin, end):
    expressions = []
    while begin < end:
      expr, begin = self.parse_expr(begin, end)
      expressions.append(expr)
    return expressions

  def is_integer(self, tok):
    return tok.isdigit()

  def is_string(self, tok):
    return tok.startswith('"') and tok.endswith('"')

  def is_float(self, tok):
    try:
      float(tok)
    except ValueError:
      return False
    else:
      return True


def make_expression(terms, otherwise):
  if len(terms) == 1 and not isinstance(terms[0], types.Applicative):
    return terms[0]
  elif len(terms) == 3 and isinstance(terms[1], types.Operator):
    return types.Applic(terms[1], terms[0], terms[2])
  else:
    return otherwise(*terms)

