from curry import icurry
import inspect
import os
import subprocess
import sys

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

def findCurryModule(modulename, searchpaths):
  '''
  Searches for a Curry module.

  Parameters:
  -----------
  ``modulename``
      The module modulename.
  ``searchpaths``
      A sequence of paths to search (i.e., CURRYPATH split on ':').

  Raises:
  -------
  ``ValueError`` if the module is not found.

  Returns:
  --------
  The name of either an ICurry-JSON file (suffix: .json) or Curry source file
  (suffix: .curry)
  '''
  # Search for the ICurry-JSON file first, then the .curry file.
  names = [os.path.join('.curry', modulename + '.json'), modulename + '.curry']
  files = findfiles(searchpaths, names)
  try:
    file_ = next(files)
  except StopIteration:
    raise ValueError('module "%s" not found' % name)
  return os.path.abspath(file_)

def curry2json():
  thispath = inspect.getsourcefile(sys.modules[__name__])
  curry2json = os.path.abspath(
      os.path.join(thispath, '../../../../bin/curry2json')
    )
  assert os.path.exists(curry2json)
  return curry2json

def jsonFilename(curryfile):
  assert curryfile.endswith('.curry')
  path,name = os.path.split(curryfile)
  return os.path.join(path, '.curry', name[:-6]+'.json')

def findOrBuildICurryForModule(modulename, searchpaths):
  '''
  See getICurryForModule.  This function returns the name of the ICurry-JSON
  file and builds the file, if necessary.
  '''
  curryfile = findCurryModule(modulename, searchpaths)
  if curryfile.endswith('.json'):
    return curryfile
  # curryfile is a .curry file.  Call curry2json to produce the ICurry-JSON file.
  json = jsonFilename(curryfile)
  assert not os.path.exists(json)
  sink = open('/dev/null', 'w')
  retcode = subprocess.call([curry2json(), curryfile], stdout=sink, stderr=sink)
  if retcode or not os.path.exists(json): #pragma: no cover
    raise RuntimeError('curry2json "%s" failed' % curryfile)
  return json

def getICurryForModule(modulename, searchpaths):
  '''
  Gets the ICurry source for a module.  May invoke curry2json.

  Parameters:
  -----------
  ``modulename``
      The module name.
  ``searchpaths``
      A sequence of paths to search (i.e., CURRYPATH split on ':').

  Raises:
  -------
  ``ValueError`` if the module is not found.

  Returns:
  The name of the ICurry-JSON file.
  '''
  filename = findOrBuildICurryForModule(modulename, searchpaths)
  assert os.path.exists(filename)
  return icurry.parse(open(filename, 'r').read())

