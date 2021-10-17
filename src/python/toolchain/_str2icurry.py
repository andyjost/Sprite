from .. import config
from ..utility import filesys
from . import makecurry, loadjson
import logging

__all__ = ['str2icurry']
logger = logging.getLogger(__name__)

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
    jsonfile = makecurry(moduledir.curryfile, currypath, is_sourcefile=True)
    icur = loadjson(jsonfile)
    icur.__file__ = moduledir.curryfile
    icur._tmpd_ = moduledir
  return icur


