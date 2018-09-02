'''API parameter validation code.'''

import collections

# TODO: scan the API functions in Interpreter and add the rest.

def currypath(interp, currypath):
  '''Process the currypath API parameter.'''
  currypath = interp.path if currypath is None else currypath
  if isinstance(currypath, str):
    currypath = currypath.split(':')
  if not isinstance(currypath, collections.Sequence):
    raise TypeError(
        "'currypath' must be a string or list, got %s."
            % repr(type(currypath).__name__)
      )
  return currypath
