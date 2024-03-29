from .. import exceptions, icurry
from . import CurryModule, CurryPackage
import six

__all__ = ['Handle', 'getHandle']

def getHandle(obj):
  return Handle(obj)

class Handle(object):
  '''
  Provides an internal interface to proxy objects such as CurryModule and
  CurryPackage.  Since those objects contain arbitrary user-defined names, it
  is not safe to add any methods.  When such objects themselves (rather than
  their contents) are of interest, this interface can instead be used.
  '''
  def __init__(self, obj):
    assert isinstance(obj, (CurryModule, CurryPackage))
    self.obj = obj

  def __repr__(self):
    return '<system interface to Curry %s %r>' % (
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
  def sofilename(self):
    shlib = self.icurry.metadata.get('cxx.shlib')
    if shlib is not None:
      return shlib.sofilename()

  @property
  def is_package(self):
    return isinstance(self.obj, CurryPackage)

  def packagename(self):
    return self.icurry.packagename

  def package(self, interp):
    pkg = interp.modules.get(self.packagename, None)
    if pkg:
      return Handle(pkg)

  def __bool__(self):
    return not self.empty()

  __nonzero__ = __bool__

  def empty(self):
    try:
      next(six.iterkeys(self))
    except StopIteration:
      return True
    else:
      return False

  def iterkeys(self):
    return (name for name in dir(self.obj) if name[0].isalpha())

  def keys(self):
    return list(six.iterkeys(self))

  def itervalues(self):
    return (self[key] for key in six.iterkeys(self))

  def values(self):
    return list(itervalues())

  def iteritems(self):
    return ((key, self[key]) for key in six.iterkeys(self))

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
  def public_symbols(self):
    return {k:v for k,v in self.symbols.items() if k[:1].isalnum()}

  @property
  def symbolnames(self):
    return self.symbols.keys()

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
        return Handle(submodule)

  def itermodules(self):
    if self.is_package:
      for subpkg in six.itervalues(self):
        for module in Handle(subpkg).itermodules():
          yield module
    else:
      yield self.obj

  def findmodule(self, fullname):
    for module in self.itermodules():
      if Handle(module).fullname == fullname:
        return module
    else:
      raise exceptions.SymbolLookupError(
          'no module %r exists in package %r' % (fullname, self.fullname)
        )

  def getsymbol(self, name):
    '''Method of CurryModule to look up a symbol by name.'''
    if self.is_package:
      head, _, tail = name.partition('.')
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
      head, _, tail = name.partition('.')
      return self.submodule(head).gettype(tail)
    else:
      try:
        return self.types[name]
      except KeyError:
        raise exceptions.TypeLookupError(
            'module %r has no type %r' % (self.obj.__name__, name)
          )

  @property
  def backend_handle(self):
    return getattr(self.obj, '.backend_handle', None)

  @property
  def get_builtin_symbolname(self):
    h = self.backend_handle
    if h is None:
      return lambda _: None
    else:
      return h.get_builtin_symbolname

  @property
  def get_builtin_typename(self):
    h = self.backend_handle
    if h is None:
      return lambda _: None
    else:
      return h.get_builtin_typename

  def unlink(self, interp):
    del interp.modules[self.fullname]
    pkg = self.package(interp)
    if pkg is not None:
      del pkg.icurry[self.name]
      self.icurry.setparent(None)
      del pkg[self.name]
      if not pkg:
        pkg.unlink(interp)
