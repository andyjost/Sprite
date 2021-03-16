from __future__ import absolute_import

from . import cache
from . import config
from . import cymake
from . import icurry
from .utility import filesys
import logging
import os
import sys
import zlib

__all__ = ['CurryImporter', 'loadJsonFile', 'loadModule', 'str2icurry']
logger = logging.getLogger(__name__)

class CurryImporter(object):
  '''An import hook that loads Curry modules into Python.'''
  def __init__(self):
    self.curry = __import__(__name__.split('.')[0])
  def find_module(self, fullname, path=None):
    if fullname.startswith(__package__ + '.lib.'):
      return self
    return None
  def load_module(self, fullname):
    if fullname not in sys.modules:
      name = fullname[len(__package__ + '.lib.'):]
      moduleobj = self.curry.import_(name)
      this = sys.modules[__name__]
      head = name.split('.')[0]
      assert head
      setattr(this, head, moduleobj)
      sys.modules[fullname] = moduleobj
    return sys.modules[fullname]

def loadModule(name, currypath, **kwds):
  '''
  Loads into Python the ICurry for a Curry module or source file, building if
  necessary.

  Parameters:
  -----------
  ``name``
      The module name or source file name.
  ``currypath``
      A sequence of paths to search (i.e., CURRYPATH split on ':').
  ``is_sourcefile``
      If true, the name arguments is interpreted as a source file.  Otherwise,
      it is interpreted as a module name.

  Raises:
  -------
  ``ModuleLookupError`` if the module is not found.

  Returns:
  --------
  A Python object containing the ICurry for the given name.
  '''
  filename = cymake.updateTarget(name, currypath, **kwds)
  logger.debug('Found module %s at %s', name, filename)
  return loadJsonFile(filename)

def loadJsonFile(jsonfile):
  '''
  Reads an ICurry-JSON file and returns the ICurry.  The file
  must contain one Curry module.
  '''
  assert os.path.exists(jsonfile)
  cached = cache.ParsedJsonCache(jsonfile)
  if cached:
    logger.debug('Loading cached ICurry-JSON for %s from %s', jsonfile, cache.filename)
    return cached.icur
  else:
    logger.debug('Reading ICurry-JSON from %s', jsonfile)
  if jsonfile.endswith('.z'):
    json = open(jsonfile, 'rb').read()
    json = zlib.decompress(json)
  else:
    json = open(jsonfile).read()
  icur = icurry.parse(json)
  icur.filename = cymake.curryFilename(jsonfile)
  cached.update(icur)
  return icur

def str2icurry(
    string, currypath
  , modulename=config.interactive_modname()
  , keep_temp_files=False
  ):
  '''
  Compile a string into ICurry.  The string is interpreted as a module
  definition.

  Returns:
  --------
  The ICurry object.  The attributes __file__ and _tmpd_ will be set.
  '''
  moduledir = filesys.CurryModuleDir(modulename, string, keep=keep_temp_files)
  with moduledir:
    jsonfile = cymake.updateTarget(moduledir.curryfile, currypath, is_sourcefile=True)
    icur = loadJsonFile(jsonfile)
    icur.__file__ = moduledir.curryfile
    icur._tmpd_ = moduledir
  return icur

