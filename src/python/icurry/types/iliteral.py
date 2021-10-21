from .iobject import IObject
from .isymbol import ISymbol
from abc import ABCMeta
from ...backends.py.sprite import Fingerprint
import collections

__all__ = ['IChar', 'IFloat', 'IInt', 'IUnboxedLiteral', 'ILiteral']

class IInt(ISymbol):
  def __init__(self, value, **kwds):
    self.fullname = 'Prelude.Int'
    self.value = int(value)
    ISymbol.__init__(self, **kwds)
  @property
  def modulename(self):
    return 'Prelude'
  def __str__(self):
    return '(%r)' % self.value # parens to suggest boxing
  def __repr__(self):
    return 'IInt(value=%r)' % self.value

class IChar(ISymbol):
  def __init__(self, value, **kwds):
    self.fullname = 'Prelude.Char'
    self.value = str(value)
    assert len(self.value) in (1,2) # Unicode can have length 2 in utf-8
    ISymbol.__init__(self, **kwds)
  @property
  def modulename(self):
    return 'Prelude'
  def __str__(self):
    return '(%r)' % self.value # parens to suggest boxing
  def __repr__(self):
    return 'IChar(value=%r)' % self.value

class IFloat(ISymbol):
  def __init__(self, value, **kwds):
    self.fullname = 'Prelude.Float'
    self.value = float(value)
    ISymbol.__init__(self, **kwds)
  @property
  def modulename(self):
    return 'Prelude'
  def __str__(self):
    return '(%r)' % self.value # parens to suggest boxing
  def __repr__(self):
    return 'IFloat(value=%r)' % self.value

class IUnboxedLiteral(IObject):
  __metaclass__ = ABCMeta
IUnboxedLiteral.register(int)
IUnboxedLiteral.register(str)
IUnboxedLiteral.register(float)
# An iterator is considered a fundamental data type so that Sprite does not try
# to reduce it.  This should always be the argument to an instance of
# Prelude._PyGenerator.
IUnboxedLiteral.register(collections.Iterator)
# Extend the builtins to include fingerprints.
IUnboxedLiteral.register(Fingerprint)

class ILiteral(IObject):
  __metaclass__ = ABCMeta
ILiteral.register(IInt)
ILiteral.register(IChar)
ILiteral.register(IFloat)
ILiteral.register(IUnboxedLiteral)

