'''
Python wrappers for Curry objects.
'''

from . import exceptions
from .common import T_FAIL, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
import types
import weakref
import icurry

__all__ = ['CurryModule', 'CurryPackage', 'CurryDataType', 'CurryNodeInfo']

# Note: artibrary symbols imported from Curry are added to Curry modules,
# risking name clashes.  Therefore, only hidden attributes are allowed here,
# and all must begin with a dot.  The exceptions are Python special names,
# which are unavoidable.
class CurryModule(types.ModuleType):
  '''A Python module for interfacing with Curry code.'''
  def __new__(cls, imodule):
    assert isinstance(imodule, (icurry.IPackage, icurry.IModule))
    self = types.ModuleType.__new__(cls, imodule.name)
    self.__file__ = getattr(imodule, 'filename', None)
    setattr(self, '.icurry', imodule)
    setattr(self, '.symbols', {})
    setattr(self, '.types', {})
    return self

  def __init__(self, imodule):
    super(CurryModule, self).__init__(imodule.name)

  def __repr__(self):
    return "<curry module '%s'>" % self.__name__

  __str__ = __repr__

class CurryPackage(CurryModule):
  pass

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


class CurryNodeInfo(object):
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
          'no implementation code available for %r' % self.fullname
        )

  def __str__(self):
    return self.name

  def __repr__(self):
    if self.info.tag >= T_CTOR:
      return "<curry constructor '%s'>" % self.fullname
    if self.info.tag == T_FUNC:
      return "<curry function '%s'>" % self.fullname
    if self.info.tag == T_CHOICE:
      return "<curry choice>"
    if self.info.tag == T_FWD:
      return "<curry forward node>"
    if self.info.tag == T_FAIL:
      return "<curry failure>"
    if self.info.tag == T_FREE:
      return "<curry free variable>"
    if self.info.tag == T_CONSTR:
      return "<curry constraint>"
    return "<invalid curry node>"


class _Handle(object):
  '''
  Provides an internal interface to proxy objects such as CurryModule and
  CurryPackage.  Since those objects contain arbitrary user-defined names, it
  is not safe to add any methods.  Instead, when such objects themselves
  (rather than their contents) are of interest, this class can be used.
  '''
  def __init__(self, obj):
    assert isinstance(obj, (CurryModule, CurryPackage))
    self.obj = obj

  def __repr__(self):
    return '<object interface to Curry %s %r>' % (
        'package' if self.is_package else 'module'
      , self.name
      )

  @property
  def name(self):
    return self.obj.__name__

  @property
  def fullname(self):
    return self.icurry.fullname

  @property
  def is_package(self):
    return isinstance(self.obj, CurryPackage)

  def packagename(self):
    return self.icurry.packagename

  def package(self, interp):
    pkg = interp.modules.get(self.packagename, None)
    if pkg is not None:
      return _Handle(pkg)

  def __nonzero__(self):
    return not self.empty()

  def empty(self):
    try:
      next(self.iterkeys())
    except StopIteration:
      return True
    else:
      return False

  def iterkeys(self):
    return (name for name in dir(self.obj) if name[0].isalpha())

  def keys(self):
    return list(self.iterkeys())

  def itervalues(self):
    return (self[key] for key in self.iterkeys())

  def values(self):
    return list(itervalues())

  def iteritems(self):
    return ((key, self[key]) for key in self.iterkeys())

  def items(self):
    return list(iteritems())

  def __getitem__(self, name):
    return getattr(self.obj, name)

  def __setitem__(self, name, value):
    setattr(self, name, value)

  def __delitem__(self, name):
    delattr(self.obj, name)

  @property
  def icurry(self):
    return getattr(self.obj, '.icurry')

  @property
  def symbols(self):
    return getattr(self.obj, '.symbols')

  @property
  def types(self):
    return getattr(self.obj, '.types')

  def submodule(self, name):
    if self.is_package:
      try:
        submodule = getattr(self.obj, name)
      except KeyError:
        raise exceptions.SymbolLookupError(
            'package %r has no submodule %r' % (self.name, name)
          )
      else:
        return _Handle(submodule)

  def itermodules(self):
    if self.is_package:
      for subpkg in self.itervalues():
        for module in _Handle(subpkg).itermodules():
          yield module
    else:
      yield self.obj

  def findmodule(self, fullname):
    for module in self.itermodules():
      if _Handle(module).fullname == fullname:
        return module
    else:
      raise exceptions.SymbolLookupError(
          'no module %r exists in package %r' % (fullname, self.fullname)
        )

  def getsymbol(self, name):
    '''Method of CurryModule to look up a symbol by name.'''
    if self.is_package:
      head, tail = icurry.splitname(name)
      return self.submodule(head).getsymbol(tail)
    else:
      try:
        return self.symbols[name]
      except KeyError:
        raise exceptions.SymbolLookupError(
            'module %r has no symbol %r' % (self.obj.__name__, name)
          )

  def gettype(self, name):
    '''Method of CurryModule to look up a type by name.'''
    if self.is_package:
      head, tail = icurry.splitname(name)
      return self.submodule(head).getsymbol(tail)
    else:
      try:
        return self.types[name]
      except KeyError:
        raise exceptions.TypeLookupError(
            'module %r has no type %r' % (self.obj.__name__, name)
          )

  def unlink(self, interp):
    del interp.modules[self.fullname]
    pkg = self.package(interp)
    if pkg is not None:
      del pkg.icurry[self.name]
      self.icurry.setparent(None)
      del pkg[self.name]
      if not pkg:
        pkg.unlink(interp)
