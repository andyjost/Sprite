'''
Implements import hacking to load Curry modules into Python.

Any name imported relative to this package is considered to be a Curry module.
It will be located using CURRYPATH and imported into ``curry._i`` via the
``import_`` method.
'''
import sys

class CurryImporter(object):
  def find_module(self, fullname, path=None):
    if fullname.startswith('curry.extern.'):
      return self
    return None
  def load_module(self, fullname):
    import curry
    import sys
    if fullname not in sys.modules:
      name = fullname[len('curry.extern.'):]
      try:
        moduleobj = curry.import_(name)
      except ImportError:
        raise
      except Exception as e:
        raise ImportError(str(e))
      this = sys.modules[__name__]
      head = name.split('.')[0]
      assert head
      setattr(this, head, moduleobj)
      sys.modules[fullname] = moduleobj
    return sys.modules[fullname]

sys.meta_path.insert(0, CurryImporter())

# Remove everything so that imported modules cannot clash.
del sys, CurryImporter

