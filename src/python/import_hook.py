import logging, sys
from . import config

__all__ = ['CurryImportHook']
logger = logging.getLogger(__name__)

class CurryImportHook(object):
  '''An import hook that loads Curry modules into Python.'''
  def __init__(self):
    self.curry = __import__(__name__.split('.')[0])

  @property
  def libpath(self):
    return config.python_package_name() + '.lib.'

  def find_module(self, fullname, path=None):
    if fullname.startswith(self.libpath):
      return self

  def load_module(self, fullname):
    if fullname not in sys.modules:
      name = fullname[len(self.libpath):]
      moduleobj = self.curry.import_(name)
      this = sys.modules[__name__]
      head = name.split('.')[0]
      assert head
      setattr(this, head, moduleobj)
      sys.modules[fullname] = moduleobj
    return sys.modules[fullname]

