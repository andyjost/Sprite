import os

def _checksuffixes(path, name, suffixes):
  '''Implements the inner loop of ``findfile``.'''
  for suffix in suffixes:
    filename = os.path.join(path, name + ('.' + suffix if suffix else ''))
    if os.path.exists(filename):
      yield filename

def findfile(paths, name, suffixes=['curry']):
  '''
  Searches the specified paths for a file with the given name and suffix.

  Parameters:
  -----------
  ``paths``
      A sequence of paths to search.
  ``name``
      The file name to search for.  May contain path components.
  ``suffixes``
      A sequence of suffixes.  Any file(s) found with any of these suffixes
      will be returned.  At least one suffix must be provided, but the empty
      string will match files with no suffix.

  Returns:
  --------
  A sequence containing the files matched.
  '''
  assert not isinstance(paths, str)
  assert suffixes
  assert not isinstance(suffixes, str)
  if not suffixes: suffixes = ['']
  if name == os.path.abspath(name):
    for result in _checksuffixes('', name, suffixes):
      yield result
  for path in paths:
    for result in _checksuffixes(path, name, suffixes):
      yield result

