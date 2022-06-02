from .. import config
from . import makecurry, loadjson
from ..objects import handle
from ..toolchain import plans
from ..utility import filesys
from ..utility import filesys, formatDocstring
import logging, os, shutil, tempfile, weakref

__all__ = ['str2module']
logger = logging.getLogger(__name__)

@formatDocstring(config.python_package_name())
def str2module(
    interp
  , moduletext
  , currypath=None
  , modulename=config.interactive_modname()
  , keep_temp_files=False
  , postmortem=False
  ):
  '''
  Load a Curry module from a string.

  This generates new Curry code in a temporary directory.  The ICurry object
  stores the name of that directory in the 'all.tmpd' metadata.  A hook is
  created to delete the temporary directory when the ICurry object is
  destroyed.

  Args:
    interp:
        The interpreter in charge of this compilation.
    moduletext:
        A string containing a Curry module definition to compile.
    currypath:
        A sequence of paths to search (i.e., CURRYPATH split on ':').  By default,
        ``{0}.path`` is used.
    modulename:
        The module name.
    keep_temp_files:
        Whether to keep intermediate files.
    postmoretem:
        Whether to copy intermediate files to the current working directory upon
        failure.

  Returns:
    A pair of the imported module and ICurry object.
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
    moduleobj = interp.import_(modulename, currypath=[moduledir] + currypath)
    moduleobj.__file__ = curryfile
    h = handle.Handle(moduleobj)
    icur = h.icurry
    icur.__file__ = curryfile
    icur.update_metadata({'all.tmpd': moduledir})
    if not keep_temp_files:
      if hasattr(weakref, 'finalize'):
        icur._finalizer_ = weakref.finalize(icur, _rmdir, moduledir)
      else:
        icur.__del__ = lambda self: _rmdir(moduledir)
    return moduleobj, icur
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
