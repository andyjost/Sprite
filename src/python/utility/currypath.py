import os

def clean_currypath(currypath):
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
