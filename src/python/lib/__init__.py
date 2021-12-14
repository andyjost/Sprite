'''
A virtual package that overloads the import mechanism to import Curry modules
into Python.

Any name imported relative to this package is considered to be a Curry module.
It will be located using CURRYPATH and imported into the global interpreter via
``import_``.

Example:
--------

  To import the Prelude:

      >>> from curry.lib import Prelude
'''

class CurryImportHook(object):
  '''An import hook that loads Curry modules into Python.'''
  import sys
  from .. import config
  LIBPATH = config.python_package_name() + '.lib.'

  def __init__(self):
    self.curry = __import__(__name__.split('.')[0])

  def find_module(self, fullname, path=None):
    if fullname.startswith(self.LIBPATH):
      return self

  def load_module(self, fullname):
    if fullname not in self.sys.modules:
      cyname = fullname[len(self.LIBPATH):]
      moduleobj = self.curry.import_(cyname)
      assert moduleobj.__name__
      assert moduleobj.__file__
      moduleobj.__loader__ = self
      # The module should notmally be placed into sys.modules before processing
      # the import.  In this case, however, this is not critical because the
      # import is anyways cached in curry.modules.  There could be a
      # multiple-import, but it will not be expensive and updating
      # curry.import_ to handle this is not straightforward.
      self.sys.modules[fullname] = moduleobj
    return self.sys.modules[fullname]


import sys
sys.meta_path.insert(0, CurryImportHook())
del CurryImportHook, sys # Leave it empty so that imported Curry moduels cannot clash.

