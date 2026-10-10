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

class Frame(object):
  '''
  An open parenthesis or bracket of the parser, or the whole text
  (``opening`` None): the expressions closed so far, and the terms of the
  expression under way.
  '''
  __slots__ = ('opening', 'expressions', 'terms')

  def __init__(self, opening):
    self.opening = opening
    self.expressions = []
    self.terms = []

  def end_expression(self):
    '''Closes the expression under way, as a comma does.'''
    self.expressions.append(make_expression(self.terms, otherwise=types.Applic))
    self.terms = []

  def value(self):
    '''
    The value of the closed frame: a list for a bracket, and for a
    parenthesis the one expression, an infix application, or a tuple.
    '''
    if self.terms:
      self.end_expression()
    if self.opening == '(':
      return make_expression(self.expressions, otherwise=lambda *args: tuple(args))
    return self.expressions

class Parser(object):
  '''
  Parses the tokens on a stack of frames of its own, so a nesting of any
  depth needs no recursion (issue #125: a literal list of 1200 elements
  failed at import).  A comma ends an expression, and the closing delimiter
  ends the frame, whose value becomes a term of the frame below.
  '''
  def __init__(self, text):
    self.text = text
    self.tokens = list(lex.tokenize(self.text))

  def parse(self):
    frames = [Frame(None)]
    for tok in self.tokens:
      frame = frames[-1]
      if isinstance(tok, lex.DelimiterToken):
        if tok == '(' or tok == '[':
          frames.append(Frame(tok))
        elif tok == ',':
          frame.end_expression()
        else:
          assert frame.opening == ('(' if tok == ')' else '['), tok
          frames.pop()
          frames[-1].terms.append(frame.value())
      elif isinstance(tok, lex.NumberToken):
        try:
          value = types.Int(tok)
        except ValueError:
          value = types.Float(tok)
        frame.terms.append(value)
      elif isinstance(tok, lex.StringToken):
        frame.terms.append(types.String(tok))
      elif isinstance(tok, lex.CharToken):
        frame.terms.append(types.Char(tok))
      elif isinstance(tok, lex.IdentifierToken):
        # An identifier after the first term is an expression of its own:
        # an applicative symbol is applied to no arguments.
        term = types.make_identifier(tok)
        if frame.terms:
          term = make_expression([term], otherwise=types.Applic)
        frame.terms.append(term)
      else:
        assert False
    frame, = frames
    assert not frame.expressions
    return make_expression(frame.terms, otherwise=types.Applic)


def make_expression(terms, otherwise):
  if len(terms) == 1 and not isinstance(terms[0], types.Applicative):
    return terms[0]
  elif len(terms) == 3 and isinstance(terms[1], types.Operator):
    return types.Applic(terms[1], terms[0], terms[2])
  else:
    return otherwise(*terms)
