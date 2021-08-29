'''
Python wrappers for Curry objects.
'''

from . import exceptions
from .common import T_FAIL, T_CONSTR, T_VAR, T_FWD, T_CHOICE, T_FUNC, T_CTOR
import types
import weakref
import icurry

__all__ = ['CurryModule', 'CurryDataType', 'CurryNodeLabel']

# Note: artibrary symbols imported from Curry are added to Curry modules,
# risking name clashes.  Therefore, only hidden attributes are allowed here,
# and all must begin with a dot.  The exceptions are Python special names,
# which are unavoidable.
class CurryModule(types.ModuleType):
  '''A Python module for interfacing with Curry code.'''
  def __new__(cls, imodule):
    assert isinstance(imodule, (icurry.IPackage, icurry.IModule))
    self = types.ModuleType.__new__(cls, imodule.name)
    self.__file__ = imodule.filename
    setattr(self, '.icurry', imodule)
    setattr(self, '.symbols', {})
    setattr(self, '.types', {})
    return self

  def __init__(self, imodule):
    super(CurryModule, self).__init__(imodule.name)

  def __repr__(self):
    return "<curry module '%s'>" % self.__name__

  __str__ = __repr__


def _modgetsymbol(moduleobj, name):
  '''Method of CurryModule to look up a symbol by name.'''
  symbols = getattr(moduleobj, '.symbols')
  try:
    return symbols[name]
  except KeyError:
    raise exceptions.SymbolLookupError(
        'module %r has no symbol %r' % (moduleobj.__name__, name)
      )

setattr(CurryModule, '.getsymbol', _modgetsymbol)


def _modgettype(moduleobj, name):
  '''Method of CurryModule to look up a type by name.'''
  types = getattr(moduleobj, '.types')
  try:
    return types[name]
  except KeyError:
    raise exceptions.TypeLookupError(
        'module %r has no type %r' % (moduleobj.__name__, name)
      )

setattr(CurryModule, '.gettype', _modgettype)

class CurryPackage(CurryModule):
  pass

def _pkgget(attr, pkgobj, name):
  '''Method of CurryPackage to look up a symbol or type by name.'''
  prefix, remname = icurry.splitname(name)
  try:
    submodule = getattr(pkgobj, prefix)
  except KeyError:
    raise exceptions.SymbolLookupError(
        'package %r has no submodule %r' % (pkgobj.__name__, prefix)
      )
  else:
    getter = getattr(submodule, attr)
    return getter(remname)

setattr(CurryPackage, '.getsymbol'
  , lambda *args, **kwds: _pkgget('.getsymbol', *args, **kwds))
setattr(CurryPackage, '.gettype'
  , lambda *args, **kwds: _pkgget('.gettype', *args, **kwds))


class CurryDataType(object):
  def __init__(self, name, constructors, module):
    self.name = name
    self.constructors = constructors
    for ctor in self.constructors:
      ctor.typedef = weakref.ref(self)
    self.module = weakref.ref(module)

  @property
  def fullname(self):
    return '%s.%s' % (self.module().__name__, self.name)

  def __repr__(self):
    return "<curry type %s>" % self.fullname


class CurryNodeLabel(object):
  '''
  Compile-time node info.

  Each kind of node has its own compiler-generated info.  Each Curry function,
  each constructor of a Curry type, and each of the special nodes such as FAIL,
  FWD, and CHOICE is associated with an instance of this object.

  Attributes:
  -----------
  ``icurry``
      The ICurry source of this Node.
  ``name``
      The fully-qualified Curry identifier for this kind of node.
  ``info``
      An instance of ``InfoTable``.
  '''
  def __init__(self, icurry, info):
    self.icurry = icurry
    self.info = info

  @property
  def name(self):
    return self.icurry.name

  # TODO: add getsource to get the Curry source.  It will require an
  # enhancement to CMC and maybe FlatCurry to generate source range
  # annotations.

  @property
  def fullname(self):
    return '%s.%s' % (self.icurry.modulename, self.name)

  def getimpl(self):
    '''Returns the implementation code of the step function, if available.'''
    step = self.info.step
    try:
      return getattr(step, 'source')
    except AttributeError:
      raise ValueError(
          'no implementation code available for "%s"' % self.fullname
        )

  def __str__(self):
    return self.name

  def __repr__(self):
    if self.info.tag >= T_CTOR:
      return "<curry constructor '%s'>" % self.name
    if self.info.tag == T_FUNC:
      return "<curry function '%s'>" % self.name
    if self.info.tag == T_CHOICE:
      return "<curry choice>"
    if self.info.tag == T_FWD:
      return "<curry forward node>"
    if self.info.tag == T_FAIL:
      return "<curry failure>"
    if self.info.tag == T_VAR:
      return "<curry variable>"
    if self.info.tag == T_CONSTR:
      return "<curry constraint>"
    return "<invalid curry node>"

