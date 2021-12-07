from .. import config
from ..utility import filesys, formatDocstring
from . import makecurry, loadjson
import logging, os, shutil, tempfile, weakref

__all__ = ['str2icurry']
logger = logging.getLogger(__name__)

@formatDocstring(__package__[:__package__.find('.')])
def str2icurry(
    moduletext
  , currypath=None
  , modulename=config.interactive_modname()
  , keep_temp_files=False
  , postmortem=False
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
      Whether to keep intermediate files.
  ``postmoretem``
      Whether to copy intermediate files to the current working directory upon
      failure.

  Returns:
  --------
  The ICurry object.  The attributes __file__ and _tmpd_ will be set.
  '''
  if keep_temp_files and isinstance(keep_temp_files, str):
    parentdir = filesys.getdir(keep_temp_files)
  else:
    parentdir = tempfile.gettempdir()
  moduledir = tempfile.mkdtemp(prefix='sprite-', dir=parentdir)
  logger.debug('Created directory %r for a dynamic Curry module', moduledir)
  try:
    curryfile = os.path.join(moduledir, modulename + '.curry')
    with open(curryfile, 'w') as ostream:
      ostream.write(moduletext)
    jsonfile = makecurry(curryfile, currypath, is_sourcefile=True)
    icur = loadjson(jsonfile)
    icur.__file__ = curryfile
    icur._tmpd_ = moduledir
    if not keep_temp_files:
      if hasattr(weakref, 'finalize'):
        icur._finalizer_ = weakref.finalize(icur, _rmdir, moduledir)
      else:
        icur.__del__ = lambda self: _rmdir(moduledir)
    return icur
  except:
    if postmortem:
      dst = os.path.basename(moduledir)
      try:
        shutil.copytree(moduledir, dst)
      except Exception as e:
        logger.error('Failed to copy %r to %r: %r', moduledir, dst, e)
      else:
        logger.info('****** Copied %r to %r for postmortem', moduledir, dst)
    _rmdir(moduledir)
    raise

def _rmdir(moduledir):
  logger.debug('Removing Curry module directory: %r', moduledir)
  shutil.rmtree(moduledir)
