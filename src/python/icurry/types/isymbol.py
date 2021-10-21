from .iobject import IObject
from . import inspect

__all__ = ['ISymbol']

class ISymbol(IObject):
  '''
  An IObject that appears in a symbol table.  Has ``fullname``, ``modulename``,
  ``name``, and ``parent`` attributes.  Derived types include modules, types,
  constructors, and functions.
  '''
  # The name is the unqualified name.  If the object belongs to a module or
  # package, then the prefix is stripped.
  @property
  def name(self):
    if not hasattr(self, '_name'):
      packagename = self.packagename
      if packagename is not None:
        assert self.fullname.startswith(packagename + '.')
        self._name = self.fullname[len(packagename)+1:]
      else:
        self._name = self.fullname
    return self._name

  @name.setter
  def name(self, name):
    self._name = name

  @property
  def modulename(self):
    '''
    Returns the fully-qualified name of the module containing a sybmol such as
    a function or constructor.

    Examples:
    ---------
        Prelude.: -> 'Prelude'
        Control.SetFunctions.Values -> 'Control.SetFunctions'
        Control.SetFunctions -> 'Control.SetFunctions'
        Control -> None
    '''
    if inspect.isa_module(self):
      return self.fullname
    else:
      try:
        parent = self.parent
      except AttributeError:
        return None
      else:
        return parent().modulename

  @property
  def packagename(self):
    '''
    Returns the qualifier of a name, which is the name of the containing module
    or package, if there is one.  For modules and packages, this returns the
    name of the contining package, if there is one, or None.  For other
    objects, such as functions and constructors, this is equivalent to
    ``modulename``.

    Examples:
    ---------
        Prelude.: -> 'Prelude'
        Control.SetFunctions.Values -> 'Control.SetFunctions'
        Control.SetFunctions -> 'Control'
        Control -> None
    '''
    from . import imodule, ipackage
    if inspect.isa_module_or_package(self):
      try:
        parent = self.parent
      except AttributeError:
        return None
      else:
        return parent().fullname
    else:
      return self.modulename
