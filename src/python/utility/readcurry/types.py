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
  def __init__(self, token, is_operator=False):
    self.name = str(token)
  def __str__(self):
    return self.name
  def __repr__(self):
    return '<%s %r>' % (type(self).__name__, self.name)
  def __hash__(self):
    return hash(self.name)
  def __eq__(self, rhs):
    return self.name == rhs.name
  def __ne__(self, rhs):
    return not (self == rhs)
  def __lt__(self, rhs):
    return self.name < rhs.name
  def __gt__(self, rhs):
    return rhs.name < self.name
  def __le__(self, rhs):
    return self.name <= rhs.name
  def __ge__(self, rhs):
    return rhs.name <= self.name

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

def make_identifier(token):
  ty = _TYPE_MAP_.get(type(token), Identifier)
  return ty(token)

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
    from .show_ import show
    return show(self)
  def __repr__(self):
    return '<Applic %s>' % ' '.join(map(repr, self._seq_))
  def __hash__(self):
    return hash(tuple(self._seq_))
  def __eq__(self, rhs):
    return tuple(self._seq_) == tuple(rhs._seq_)
  def __ne__(self, rhs):
    return not (self == rhs)
  def __lt__(self, rhs):
    return tuple(self._seq_) < tuple(rhs._seq_)
  def __gt__(self, rhs):
    return rhs < self
  def __le__(self, rhs):
    return tuple(self._seq_) <= tuple(rhs._seq_)
  def __ge__(self, rhs):
    return tuple(rhs._seq_) <= tuple(self._seq_)
