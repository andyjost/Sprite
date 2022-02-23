from .iobject import IObject
from .isymbol import ISymbol
from ...common import Fingerprint
import abc, collections, six

__all__ = ['IChar', 'IFloat', 'IInt', 'ILiteral', 'IString', 'IUnboxedLiteral']

class IInt(ISymbol):
  def __init__(self, value, **kwds):
    ISymbol.__init__(self, 'Prelude.Int', **kwds)
    self.value = int(value)
  @property
  def _fields_(self):
    return 'value',
  @property
  def modulename(self):
    return 'Prelude'
  def __str__(self):
    return '(%r)' % self.value # parens to suggest boxing
  def __repr__(self):
    return 'IInt(value=%r)' % self.value

class IChar(ISymbol):
  def __init__(self, value, **kwds):
    ISymbol.__init__(self, 'Prelude.Char', **kwds)
    self.value = str(value)
    assert len(self.value) in (1,2) # Unicode can have length 2 in utf-8
  @property
  def _fields_(self):
    return 'value',
  @property
  def modulename(self):
    return 'Prelude'
  def __str__(self):
    return '(%r)' % self.value # parens to suggest boxing
  def __repr__(self):
    return 'IChar(value=%r)' % self.value

class IFloat(ISymbol):
  def __init__(self, value, **kwds):
    ISymbol.__init__(self, 'Prelude.Float', **kwds)
    self.value = float(value)
  @property
  def _fields_(self):
    return 'value',
  @property
  def modulename(self):
    return 'Prelude'
  def __str__(self):
    return '(%r)' % self.value # parens to suggest boxing
  def __repr__(self):
    return 'IFloat(value=%r)' % self.value

class IString(ISymbol):
  def __init__(self, value, **kwds):
    ISymbol.__init__(self, 'Prelude._PyString', **kwds)
    self.value = str(value)
  @property
  def modulename(self):
    return 'Prelude'
  def __str__(self):
    return '_PyString(%r)' % self.value
  def __repr__(self):
    return 'IString(value=%r)' % self.value

class IUnboxedLiteral(six.with_metaclass(abc.ABCMeta, IObject)):
  pass
IUnboxedLiteral.register(int)
IUnboxedLiteral.register(str)
IUnboxedLiteral.register(float)
# An iterator is considered a fundamental data type so that Sprite does not try
# to reduce it.  This should always be the argument to an instance of
# Prelude._PyGenerator.
IUnboxedLiteral.register(collections.Iterator)
# A view of raw memory (used by _PyString).
IUnboxedLiteral.register(memoryview)
# Extend the builtins to include fingerprints.
IUnboxedLiteral.register(Fingerprint)

class ILiteral(six.with_metaclass(abc.ABCMeta, IObject)):
  pass
ILiteral.register(IInt)
ILiteral.register(IChar)
ILiteral.register(IFloat)
ILiteral.register(IUnboxedLiteral)
ILiteral.register(IString)

