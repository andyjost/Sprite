from . import lex

__all__ = [
    'Applic', 'Char', 'Float', 'Identifier', 'Int', 'Literal', 'String'
  , 'is_operator'
  ]

class Char(str): pass
class Float(float): pass
class Int(int): pass
class String(str): pass
Literal = String, Char, Int, Float

class Identifier(object):
  def __new__(cls, token):
    if cls is Identifier:
      cls = _TYPE_MAP_.get(type(token), Identifier)
    return object.__new__(cls, token)
  def __init__(self, token, is_operator=False):
    self.name = str(token)
  def __str__(self):
    return self.name
  def __repr__(self):
    return '<%s %r>' % (type(self).__name__, self.name)
  def __eq__(self, rhs):
    return isinstance(rhs, Identifier) and self.name == rhs.name
  def __ne__(self, rhs):
    return not (self == rhs)

class Applicative(Identifier) : pass # Identifiers that can be applied.
class Constructor(Applicative): pass
class Freevar    (Identifier) : pass # Cannot be applied.
class Function   (Applicative): pass
class Operator   (Applicative): pass

_TYPE_MAP_ = {
    lex.ConstructorToken : Constructor
  , lex.FreevarToken     : Freevar
  , lex.FunctionToken    : Function
  , lex.OperatorToken    : Operator
  }
  
class Applic(object):
  '''Application of an ``Applicative`` symbol to arguments.'''
  def __init__(self, f, *args):
    assert isinstance(f, Applicative)
    self.f = f
    self.args = args
  @property
  def _seq_(self):
    yield self.f
    for arg in self.args:
      yield arg
  def __str__(self):
    from .show import show
    return show(self)
  def __repr__(self):
    return '<Applic %s>' % ' '.join(map(repr, self._seq_))
  def __eq__(self, rhs):
    return isinstance(rhs, Applic) and \
        all(a==b for a,b in zip(self._seq_, rhs._seq_))
  def __ne__(self, rhs):
    return not (self == rhs)
