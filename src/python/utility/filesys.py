from .. import config
import os
import shutil
import sys
import tempfile

try:
  from tempfile import TemporaryDirectory # Py3
except ImportError:
  from ._tempfile import TemporaryDirectory # Py2

__all__ = ['findfiles', 'getDebugSourceDir', 'getdir', 'makeNewfile', 'newer', 'CurryModuleDir']

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
  Indicates whether file a is newer than file b.  Also returns true if a exists
  and b does not.
  '''
  try:
    t_b = os.path.getctime(b)
  except OSError:
    return os.path.exists(a) and not os.path.exists(b)
  return os.path.getctime(a) > t_b

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

class CurryModuleDir(TemporaryDirectory):
  '''
  Manages a temporary directory for compiling a Curry module.

  The Curry source file will be created with the specified name and contents.

  Unlike TmpDir, the __exit__ method does not delete the directory.  That is
  handled by the __del__ method, which ensures the directory is deleted before
  program exit.  When used as a context manager, if debuggin is enabled, this
  object handles exceptions by copying the directory to a more convenient
  location for postmortem analysis.

  Set 'keep' to keep the directory after the program exits.  If set to a
  nonempty string, that string will be used as the directory name.
  '''
  def __init__(self, modulename, currysrc, keep=False):
    self.keep = keep
    if keep and isinstance(keep, str):
      dir = filesys.getdir(keep)
    else:
      dir = tempfile.gettempdir()
    TemporaryDirectory.__init__(self, prefix='sprite-', dir=dir)
    self.curryfile = os.path.join(self.name, modulename + '.curry')
    with open(self.curryfile, 'w') as out:
      out.write(currysrc)

  def __exit__(self, exc, value, tb):
    if exc and config.debugging():
      dst = os.path.basename(self.name)
      try:
        shutil.copytree(self.name, dst)
      except Exception as e:
        sys.stderr.write('Failed to copy %s to %s: %s\n' % (self.name, dst, e))
      else:
        sys.stderr.write('****** Copied %s to %s for postmortem\n' % (self.name, dst))

  def __del__(self):
    if not self.keep:
      self.cleanup()

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

