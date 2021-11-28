from .. import config
import contextlib, logging, os, shutil, sys, tempfile
from ._tempfile import TemporaryDirectory

logger = logging.getLogger(__name__)

__all__ = [
    'findfiles', 'getDebugSourceDir', 'getdir', 'makeNewfile', 'newer'
  , 'remove_file_on_error'
  ]

def getdir(name, mkdirs=False, access=os.O_RDWR):
  '''
  Creates or gets a directory and ensures it has the specified access rights.
  '''
  path = os.path.abspath(name)
  if not os.path.exists(path):
    if mkdirs:
      os.makedirs(path)
    else:
      os.mkdir(path)
  elif not os.path.isdir(path):
    raise RuntimeError("%s exists but is not a directory" % path)
  if not os.access(path, access):
    aname = [k for k,v in os.__dict__.items() if k.startswith('O_') and v == access]
    aname = aname[0] if len(aname) else '(invalid)'
    raise RuntimeError("%s does not have %s access" % (path, aname))
  return path

def newer(a, b):
  '''
  Indicates whether file a is newer than file b.  Also returns true if b does
  not exist.
  '''
  try:
    t_b = os.path.getctime(b)
  except OSError:
    return True
  else:
    try:
      t_a = os.path.getctime(a)
    except OSError:
      return False
    else:
      return t_a > t_b

def newest(files):
  '''Find the newest file from a collection of filenames.'''
  assert files
  newest = files[0]
  for x in files[1:]:
    if not newer(newest, x):
      newest = x
  return newest

def findfiles(searchpaths, names):
  '''
  Searches the specified paths for a file with the given name.

  Parameters:
  -----------
  ``searchpaths``
      A sequence of paths to search.
  ``names``
      A sequence of file names to search for.

  Returns:
  --------
  A sequence containing the files found.
  '''
  if isinstance(searchpaths, str):
    searchpaths = [searchpaths]
  if isinstance(names, str):
    names = [names]
  for path in searchpaths:
    for name in names:
      filename = os.path.join(path, name)
      if os.path.exists(filename):
        yield filename

def makeNewfile(*args):
  filename = os.path.join(*args)
  if os.path.exists(filename):
    i = 0
    while os.path.exists(filename + '.' + str(i)):
      i += 1
    return filename + '.' + str(i)
  return filename

debug_source_dir_init = True

def getDebugSourceDir():
  '''
  Returns a directory in which the source code of dynamically-compiled
  functions can be placed.  This is used to make the source code available to
  PDB when debugging.
  '''
  srcdir = os.path.abspath('.src')
  global debug_source_dir_init
  if debug_source_dir_init:
    try:
      shutil.rmtree(srcdir)
    except OSError: # pragma: no cover
      pass
    os.mkdir(srcdir)
    debug_source_dir_init = False
  return srcdir

@contextlib.contextmanager
def remove_file_on_error(filename):
  try:
    yield
  except:
    if os.path.exists(filename):
      try:
        os.unlink(filename)
      except BaseException as err:
        logger.warn(
            'an error occurred while writing the output file %r; while removing '
            'that file, the following additional error was ignored: %s'
                % (filename, str(err))
          )
    raise
