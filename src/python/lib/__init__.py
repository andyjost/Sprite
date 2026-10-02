from .. import config

__doc__ = '''
A virtual package that overloads the import mechanism to import Curry modules
into Python.

Any name imported relative to this package is considered to be a Curry module.
It will be located using :data:`{0}.path` (which is initialized from CURRYPATH)
and imported into the global interpreter via :func:`{0}.import_`.

Example:

  To import the Prelude:

      >>> from curry.lib import Prelude
'''.format(config.python_package_name())

class CurryImportHook(object):
  '''An import hook that loads Curry modules into Python.'''
  import sys
  from importlib.machinery import ModuleSpec
  from .. import config
  LIBPATH = config.python_package_name() + '.lib.'

  def __init__(self):
    self.curry = __import__(__name__.split('.')[0])

  def find_spec(self, fullname, path=None, target=None):
    if fullname.startswith(self.LIBPATH):
      return self.ModuleSpec(fullname, self)

  def create_module(self, spec):
    fullname = spec.name
    if fullname not in self.sys.modules:
      cyname = fullname[len(self.LIBPATH):]
      moduleobj = self.curry.import_(cyname)
      assert moduleobj.__name__
      assert moduleobj.__file__
      moduleobj.__loader__ = self
      # The module should normally be placed into sys.modules before processing
      # the import.  In this case, however, this is not critical because the
      # import is anyways cached in curry.modules.  There could be a
      # multiple-import, but it will not be expensive and updating
      # curry.import_ to handle this is not straightforward.
      self.sys.modules[fullname] = moduleobj
    return self.sys.modules[fullname]

  def exec_module(self, module):
    # The Curry module is fully built by create_module.  The import system
    # fills only the module attributes that are still None, so the attributes
    # set by the interpreter survive.
    pass


import sys
sys.meta_path.insert(0, CurryImportHook())
del config, CurryImportHook, sys # Empty this module to avoid name clashes.

