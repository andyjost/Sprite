'''
Python wrappers for Curry objects.

These objects constitute the primary user interface to Curry from Python, and,
as such, merge the Python and Curry worlds.  A CurryModule, for example,
contains not only attributes for all of the Curry objects in that module, but
also special Python attributes such as __name__, __file__, and __path__, which
are needed to convince Python to treat the object as a Python module.

When the interest is to interact with Curry -- e.g., get symbols, form Curry
expressions, and evaluate Curry goals -- the objects in this module should be
used directly.  Alternatively, when the focus is on system-level activities, such
as finding submodules, getting the ICurry, and so on, these objects should be
wrapped in handle.Handle.
'''

from ..common import T_FAIL, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from .. import icurry
import os, types, weakref

__all__ = ['CurryModule', 'CurryPackage', 'CurryDataType', 'CurryNodeInfo']

# Note: artibrary symbols imported from Curry are added to Curry modules,
# risking name clashes.  Therefore, only hidden attributes are allowed here,
# and all must begin with a dot.  The exceptions are Python special names,
# which are unavoidable.
class CurryModule(types.ModuleType):
  '''
  A Python module for interfacing with Curry modules.

  This object is produced when a Curry module is imported into Python.  The
  public module contents are exposed as attributes.

  Special attributes beginning with '.' (so as not to conflict with Curry
  names) contain information used by the Curry system.  These should generally
  be accessed by other means, such as curry.symbol, curry.type, or
  curry.inspect.icurry.
  '''
  def __new__(cls, imodule):
    assert not isinstance(imodule, icurry.IPackage) or cls is CurryPackage
    assert not isinstance(imodule, icurry.IModule) or cls is CurryModule
    self = types.ModuleType.__new__(cls, imodule.name)
    setattr(self, '.icurry', getattr(imodule, 'icurry', imodule))
    setattr(self, '.symbols', {})
    setattr(self, '.types', {})
    return self

  def __init__(self, imodule):
    types.ModuleType.__init__(self, imodule.name)
    self.__file__ = imodule.filename
    self.__package__ = self.__name__.rpartition('.')[0]

  def __repr__(self):
    return "<curry module '%s'>" % self.__name__

  __str__ = __repr__

  @property
  def is_package(self):
    return False


class CurryPackage(CurryModule):
  '''
  A Python package for interfacing with Curry packages.
  '''
  def __init__(self, imodule):
    CurryModule.__init__(self, imodule)
    self.__file__ = os.path.join(self.__file__, '<virtual>')
    self.__path__ = [os.path.dirname(self.__file__)]
    self.__package__ = self.__name__

  def __repr__(self):
    return "<curry package '%s'>" % self.__name__

  __str__ = __repr__

  @property
  def is_package(self):
    return True


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

def create_module_or_pacakge(icur):
  if isinstance(icur, icurry.IPackage):
    return CurryPackage(icur)
  else:
    return CurryModule(icur)

