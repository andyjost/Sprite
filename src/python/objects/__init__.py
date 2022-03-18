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
import abc, inspect, os, six, types, weakref

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
  def __new__(cls, interp, imodule):
    assert not isinstance(imodule, icurry.IPackage) or cls is CurryPackage
    assert not isinstance(imodule, icurry.IModule) or cls is CurryModule
    self = types.ModuleType.__new__(cls, imodule.name)
    setattr(self, '.icurry', getattr(imodule, 'icurry', imodule))
    setattr(self, '.symbols', {})
    setattr(self, '.types', {})
    setattr(self, '.backend_handle', None)
    return self

  def __init__(self, interp, imodule):
    types.ModuleType.__init__(self, imodule.fullname)
    self.__file__ = imodule.filename
    self.__package__ = self.__name__.rpartition('.')[0]
    setattr(self, '.backend_handle', interp.backend.find_or_create_module(self))

  def __repr__(self):
    return '<curry module %r>' % self.__name__

  __str__ = __repr__

  @property
  def is_package(self):
    return False


class CurryPackage(CurryModule):
  '''
  A Python package for interfacing with Curry packages.
  '''
  def __init__(self, interp, imodule):
    CurryModule.__init__(self, interp, imodule)
    self.__file__ = os.path.join(self.__file__, '<virtual>')
    self.__path__ = [os.path.dirname(self.__file__)]
    self.__package__ = self.__name__

  def __repr__(self):
    return '<curry package %r>' % self.__name__

  __str__ = __repr__

  @property
  def is_package(self):
    return True


class CurryExpression(object):
  def __init__(self, raw_expr):
    self.raw_expr = raw_expr

  def __getitem__(self, key):
    return CurryExpression(self.raw_expr[key])

  @property
  def info(self):
    from .. import inspect
    return inspect.info_of(self.raw_expr)

  @property
  def is_boxed(self):
    from .. import inspect
    return inspect.is_boxed(self.raw_expr)

  def __str__(self):
    return str(self.raw_expr)

  def __repr__(self):
    from .. import inspect
    info = inspect.info_of(self.raw_expr)
    if info is None:
      return '<curry constructor expression: type=unboxed %r, value=%r>' % (
          type(self.raw_info).__name__, self.raw_expr
        )
    if info.tag >= T_CTOR:
      return '<curry constructor expression: type=%r, head=%r>' % (
          info.typedef().name, info.name
        )
    if info.tag == T_FUNC:
      return '<curry function expression: head=%r>' % info.name
    if info.tag == T_CHOICE:
      return '<curry choice expression>: id=%r>' % \
          inspect.get_choice_id(self.raw_expr)
    if info.tag == T_FWD:
      return '<curry forward expression>'
    if info.tag == T_FAIL:
      return '<curry failure expression>'
    if info.tag == T_FREE:
      return '<curry free variable expression: id=%r>' % \
          inspect.get_freevar_id(self.raw_expr)
    if info.tag == T_CONSTR:
      return '<curry constraint expression>'
    return '<invalid curry expression>'


class CurryDataType(object):
  def __init__(self, datatype, icurry=None):
    self.datatype = datatype
    self.icurry = icurry

  @property
  def name(self):
    return self.datatype.name

  def __repr__(self):
    return '<curry type %r>' % self.name


class CurryNodeInfo(object):
  '''
  Static information for a Curry function or constructor symbol.
  '''
  def __init__(self, info, icurry=None, typename=None):
    self.info = info
    self.icurry = icurry
    self.typename = typename

  @property
  def name(self):
    return self.info.name

  # TODO: add getsource to get the Curry source.  It will require an
  # enhancement to CMC and maybe FlatCurry to generate source range
  # annotations.

  def getimpl(self):
    '''Returns the implementation code of the step function, if available.'''
    step = self.info.step
    try:
      return getattr(step, 'source')
    except AttributeError:
      pass

    try:
      return inspect.getsource(step)
    except OSError:
      pass

    raise ValueError(
        'no implementation code available for %r' % self.fullname
      )

  def __str__(self):
    return self.name

  def __repr__(self):
    if self.info.tag >= T_CTOR:
      return '<curry constructor %r>' % self.name
    if self.info.tag == T_FUNC:
      return '<curry function %r>' % self.name
    if self.info.tag == T_CHOICE:
      return '<curry choice>'
    if self.info.tag == T_FWD:
      return '<curry forward node>'
    if self.info.tag == T_FAIL:
      return '<curry failure>'
    if self.info.tag == T_FREE:
      return '<curry free variable>'
    if self.info.tag == T_CONSTR:
      return '<curry constraint>'
    return '<invalid curry node>'


def create_module_or_package(interp, icur):
  if isinstance(icur, icurry.IPackage):
    return CurryPackage(interp, icur)
  else:
    return CurryModule(interp, icur)

