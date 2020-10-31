import sys

class ImportBlocker(object):
  def __init__(self, *args):
    self.module_names = args

  def find_module(self, fullname, path=None):
    if fullname in self.module_names:
      return self
    return None

  def load_module(self, name):
    raise ImportError("%s is blocked and cannot be imported" % name)

def with_import_blocked(*module_names):
  import_blocker = ImportBlocker(*module_names)
  def decorator(f):
    def replacement(*args, **kwds):
      removed_from_sysmodules = {}
      for module_name in module_names:
        if module_name in sys.modules:
          removed_from_sysmodules[module_name] = sys.modules[module_name]
          del sys.modules[module_name]
      sys.meta_path.insert(0, import_blocker)
      try:
        return f(*args, **kwds)
      finally:
        sys.meta_path[:] = [x for x in sys.meta_path if x is not import_blocker]
        sys.modules.update(removed_from_sysmodules)
    return replacement
  return decorator
