from .. import config
from ..utility import filesys, formatDocstring
from . import makecurry, loadjson
import logging

__all__ = ['str2icurry']
logger = logging.getLogger(__name__)

@formatDocstring(__package__[:__package__.find('.')])
def str2icurry(
    moduletext
  , currypath=None
  , modulename=config.interactive_modname()
  , keep_temp_files=False
  ):
  '''
  Compile a string into ICurry.

  Parameters:
  -----------
  ``moduletext``
      A string containing a Curry module definition to compile.
  ``currypath``
      A sequence of paths to search (i.e., CURRYPATH split on ':').  By default,
      ``{0}.path`` is used.
  ``modulename``
      The module name.
  ``keep_temp_files``
      Whether to keep temporary intermediate files.

  Returns:
  --------
  The ICurry object.  The attributes __file__ and _tmpd_ will be set.
  '''
  moduledir = filesys.CurryModuleDir(
      modulename, moduletext, keep=keep_temp_files
    )
  with moduledir:
    jsonfile = makecurry(moduledir.curryfile, currypath, is_sourcefile=True)
    icur = loadjson(jsonfile)
    icur.__file__ = moduledir.curryfile
    icur._tmpd_ = moduledir
  return icur


