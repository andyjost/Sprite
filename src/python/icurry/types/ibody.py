from __future__ import absolute_import
from .iobject import IObject
from abc import ABCMeta
from ...utility import translateKwds
import types

__all__ = [
    'IBody'       # Normal definition (i.e., IBlock).
  , 'IBuiltin'    # No body specified.
  , 'IExternal'   # External definition.  The body will be resolved later.
  , 'IFuncBody'   # Alias for IBody.
  , 'ILink'       # Linker name.
  , 'IMaterial'   # Back-end code implementing the function.
  ]

class IBuiltin(IObject):
  '''The function implementation should be provided in the metadata.'''
  def __init__(self, metadata):
    for kind in ['py.boxedfunc', 'py.rawfunc', 'py.unboxedfunc']:
      if kind in metadata:
        kindname = kind.partition('.')[-1]
        impl = metadata[kind]
        self.text = '(%s %r from %r)' % (kindname, impl.__name__, impl.__module__)
        break
    else:
      self.text = '(built-in)'
  def __str__(self):
    return self.text
  def __repr__(self):
    return '%s()' % type(self).__name__


class IExternal(IObject):
  '''A link to external Curry function.'''
  @translateKwds({'name': 'symbolname'})
  def __init__(self, symbolname, **kwds):
    self.symbolname = str(symbolname)
    IObject.__init__(self, **kwds)
  def __str__(self):
    return 'extern(%s)' % self.symbolname
  def __repr__(self):
    return '%s(symbolname=%r)' % (type(self).__name__, self.symbolname)


class ILink(IExternal):
  '''A link to an external backend function.'''
  @property
  def linkname(self):
    return self.symbolname


class IMaterial(IObject):
  '''A materialized backend function.'''
  def __init__(self, function, **kwds):
    if not isinstance(function, types.FunctionType):
      raise TypeError(
          'expected a materialized function, not type %r'
              % type(function).__name__
        )
    self.function = function
    IObject.__init__(self, **kwds)
  @property
  def function_name(self):
    return self.function.__name__
  def __str__(self):
    return 'material(%s)' % self.function_name
  def __repr__(self):
    return '<IMaterial for %r>' % self.function_name


class IFuncBody(IObject):
  __metaclass__ = ABCMeta
  def __init__(self, block, **kwds):
    self.block = block
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.block,
  def __str__(self):
    return str(self.block)
  def __repr__(self):
    return 'IFuncBody(block=%r)' % self.block

IFuncBody.register(IBuiltin)
IFuncBody.register(IExternal)
IFuncBody.register(ILink)
IFuncBody.register(IMaterial)

IBody = IFuncBody
