import os, re
from ..exceptions import ModuleLookupError

__all__ = [
    'getModuleName', 'isLegalModulename', 'makeCurryPath', 'prefixes'
  , 'removeSuffix', 'split', 'validateModulename'
  ]

def getModuleName(name, is_sourcefile):
  '''
  Interpret ``name`` as a modulename, removing the suffix from source files.

  Raises:
  -------
    - ValueError if the name is a source file with the wrong suffix.
    - ModuleLookupError if an invalid module name was provided.
  '''
  if is_sourcefile:
    name = removeSuffix(name, '.curry')
  validateModulename(name)
  return name

g_ident = re.compile(r'[_a-zA-Z][_a-zA-Z0-9]*$')
def isLegalModulename(name):
  return all(re.match(g_ident, part) for part in name.split('.'))

def makeCurryPath(currypath):
  '''
  Validate the given Curry path and return it as a list.  Each part of the
  supplied path will be interpreted as a string and converted to an absolute
  path.

  Parameters:
  -----------
    ``currypath``
      A colon-delimited string or list of strings.
  '''
  if isinstance(currypath, str):
    currypath = currypath.split(':')
  try:
    currypath = map(str, currypath)
  except:
    raise TypeError(
        "'currypath' must be a string or sequence of strings, got %r."
            % currypath
      )
  currypath = map(os.path.abspath, filter(lambda x:x, currypath))
  return currypath

def prefixes(name, sep='.'):
  '''
  Yields the prefixes of ``name``, separated on ``sep``.

  Examples:
  ---------
  'Prelude' yields 'Prelude'.  'Data.Maybe', yields 'Data' followed by
  'Data.Maybe'.
  '''
  parts = name.split(sep)
  for end in range(len(parts)):
    yield sep.join(parts[:end+1])

def removeSuffix(name, suffix):
  if not name.endswith(suffix):
    raise ValueError('expected suffix %r' % suffix)
  return name[:-len(suffix)]

def validateModulename(name):
  if not isLegalModulename(name):
    raise ModuleLookupError('%r is not a legal module name.' % name)

