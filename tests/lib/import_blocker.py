class ImportBlocker(object):
  def __init__(self, *args):
    self.module_names = args

  def find_module(self, fullname, path=None):
    if fullname in self.module_names:
      return self
    return None

  def load_module(self, name):
    raise ImportError("%s is blocked and cannot be imported" % name)
