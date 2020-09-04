from __future__ import absolute_import

from .exceptions import CompileError, ModuleLookupError
from . import cache
from . import icurry
from .utility.binding import binding, del_
from .utility.visitation import dispatch
import inspect
import logging
import os
import shutil
import subprocess
import sys
import types

logger = logging.getLogger(__name__)

try:
  from tempfile import TemporaryDirectory # Py3
except ImportError:
  from .utility._tempfile import TemporaryDirectory # Py2

def newer(a, b):
  '''
  Indicates whether file a is newer than file b.  Also returns true if a exists
  and b does not.
  '''
  try:
    t_b = os.path.getmtime(b)
  except OSError:
    return os.path.exists(a) and not os.path.exists(b)
  return os.path.getmtime(a) > t_b

def findfiles(searchpaths, names):
  '''
  Searches the specified paths for a file with the given name and suffix.

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
  assert not isinstance(searchpaths, str)
  for path in searchpaths:
    for name in names:
      filename = os.path.join(path, name)
      if os.path.exists(filename):
        yield filename

def findCurryModule(modulename, currypath):
  '''
  Searches for a Curry module.

  Parameters:
  -----------
  ``modulename``
      The module modulename.
  ``currypath``
      A sequence of paths to search (i.e., CURRYPATH split on ':').

  Raises:
  -------
  ``ModuleLookupError`` if the module is not found.

  Returns:
  --------
  The name of either an ICurry-JSON file (suffix: .json) or Curry source file
  (suffix: .curry)
  '''
  # Search for the ICurry-JSON file first, then the .curry file.
  if '/' in modulename or modulename in ['.', '..']:
    raise ModuleLookupError('"%s" is not a legal module name.' % modulename)
  names = [os.path.join('.curry', modulename + '.json'), modulename + '.curry']
  files = findfiles(currypath, names)
  try:
    tgtfile = next(files)
    assert tgtfile.endswith('.curry') or tgtfile.endswith('.json')
  except StopIteration:
    raise ModuleLookupError('Curry module "%s" not found' % modulename)

  # If a .json file was found, then check whether the corresponding .curry file
  # is newer.
  if tgtfile.endswith('.json'):
    try:
      srcfile = next(files)
    except StopIteration:
      pass
    else:
      # Check whether the source file is newer than the JSON file.
      if newer(srcfile, tgtfile):
        if srcfile.endswith('.curry') and jsonFilename(srcfile) == tgtfile:
          tgtfile = srcfile
  return os.path.abspath(tgtfile)

g_curry2jsontool = None
def curry2jsontool():
  global g_curry2jsontool
  if not g_curry2jsontool:
    thispath = inspect.getsourcefile(sys.modules[__name__])
    g_curry2jsontool = os.path.abspath(
        os.path.join(thispath, '../../../../.bin/curry2json')
      )
    assert os.path.exists(g_curry2jsontool)
  return g_curry2jsontool

def curry2json(curryfile, currypath):
  '''
  Calls curry2json to produce an ICurry-JSON file.

  Parameters:
  -----------
  ``curryfile``
      The name of the Curry file to convert.
  ``currypath``
      The list of Curry code search paths.

  Returns:
  -------
  The JSON file name.
  '''
  jsonfile = jsonFilename(curryfile)
  assert not os.path.exists(jsonfile) or newer(curryfile, jsonfile)
  sink = open('/dev/null', 'w')
  with binding(os.environ, 'TARGET_CURRYPATH', ':'.join(currypath)) \
     , binding(os.environ, 'CURRYPATH', del_):
    cached = cache.Curry2JsonCache(curryfile, jsonfile)
    if not cached:
      child = subprocess.Popen(
        [curry2jsontool(), '-q', curryfile]
        , stdout=sink, stderr=subprocess.PIPE
        )
  if not cached:
    _,errs = child.communicate()
    retcode = child.wait()
    if retcode or not os.path.exists(jsonfile):
      raise CompileError(errs)
    with open(jsonfile, 'r+') as json:
      text = icurry.despace(json.read())
      json.seek(0)
      json.truncate()
      json.write(text)
    cached.update()
  return jsonfile

def jsonFilename(curryfile):
  assert curryfile.endswith('.curry')
  path,name = os.path.split(curryfile)
  return os.path.join(path, '.curry', name[:-6]+'.json')

def findOrBuildICurryForModule(modulename, currypath):
  '''
  See getICurryForModule.  This function returns the name of the ICurry-JSON
  file and builds the file, if necessary.
  '''
  filename = findCurryModule(modulename, currypath)
  if filename.endswith('.json'):
    return filename
  elif filename.endswith('.curry'):
    return curry2json(filename, currypath)
  assert False

def getICurryFromJson(jsonfile):
  '''
  Reads an ICurry-JSON file and returns the ICurry.  The file
  must contain one Curry module.
  '''
  logger.debug('Reading ICurry-JSON from %s' % jsonfile)
  assert os.path.exists(jsonfile)
  cached = cache.ParsedJson(jsonfile)
  if cached:
    return cached.icur
  icur, = icurry.parse(open(jsonfile, 'r').read())
  icur.filename = jsonfile
  cached.update(icur)
  return icur

def getICurryForModule(modulename, currypath):
  '''
  Gets the ICurry source for a module.  May invoke curry2json.

  Parameters:
  -----------
  ``modulename``
      The module name.
  ``currypath``
      A sequence of paths to search (i.e., CURRYPATH split on ':').

  Raises:
  -------
  ``ValueError`` if the module is not found.

  Returns:
  The name of the ICurry-JSON file.
  '''
  filename = findOrBuildICurryForModule(modulename, currypath)
  logger.debug('Found module %s at %s' % (modulename, filename))
  return getICurryFromJson(filename)

class TmpDir(TemporaryDirectory):
  '''
  Like TemporaryDirectory, but does not issue warnings when __del__ is used to
  clean up.
  '''
  def __del__(self):
    self.cleanup()

def str2icurry(string, currypath, modulename='_interactive_'):
  '''
  Compile a string into ICurry.  The string is interpreted as a module
  definition.

  Returns:
  --------
  The ICurry object.  The attributes __file__ and _tmpd_ will be set.
  '''
  tmpd = TmpDir()
  curryfile = os.path.join(tmpd.name, modulename + '.curry')
  with open(curryfile, 'w') as out:
    out.write(string)
  jsonfile = curry2json(curryfile, currypath)
  icur = getICurryFromJson(jsonfile)
  icur.__file__ = curryfile
  icur._tmpd_ = tmpd
  return icur

class CurryImporter(object):
  '''An importer that loads Curry modules as Python.'''
  def __init__(self):
    self.curry = __import__(__name__.split('.')[0])
  def find_module(self, fullname, path=None):
    if fullname.startswith('curry.lib.'):
      return self
    return None
  def load_module(self, fullname):
    if fullname not in sys.modules:
      name = fullname[len('curry.lib.'):]
      moduleobj = self.curry.import_(name)
      this = sys.modules[__name__]
      head = name.split('.')[0]
      assert head
      setattr(this, head, moduleobj)
      sys.modules[fullname] = moduleobj
    return sys.modules[fullname]

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

def makeNewfile(*args):
  filename = os.path.join(*args)
  if os.path.exists(filename):
    i = 0
    while os.path.exists(filename + '.' + str(i)):
      i += 1
    return filename + '.' + str(i)
  return filename

def getImportSpecForExpr(interpreter, modules):
  '''
  Generates the import statements and the CURRYPATH to use when compiling a
  standalone Curry expression.

  Parameters:
  -----------
  ``interpreter``
      The interpreter.
  ``modules``
      The list of modules to import.  Each one may be a string or a Curry
      module object.

  Returns:
  --------
  A pair consisting of a list of Curry import statements and the updated search
  path.
  '''
  stmts = []
  currypath = list(interpreter.path)
  for module in modules:
    _updateImports(interpreter, module, stmts, currypath)
  return stmts, currypath

@dispatch.on('module')
def _updateImports(interpreter, module, stmts, currypath):
  assert False

@_updateImports.when(str)
def _updateImports(interpreter, modulename, stmts, currypath):
  module = interpreter.modules[modulename]
  return _updateImports(interpreter, module, stmts, currypath)

@_updateImports.when(types.ModuleType)
def _updateImports(interpreter, module, stmts, currypath):
  if module.__name__ != '_System':
    stmts.append('import ' + module.__name__)
    # If this is a dynamic module, add its directory to the search path.
    try:
      currypath.insert(0, module._tmpd_.name)
    except AttributeError:
      pass
