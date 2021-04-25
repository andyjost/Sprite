'''
Utilities for comparing Curry output.
'''
from curry import importer
from curry.utility import visitation, filesys
import collections
import os
import subprocess
import unittest

@visitation.dispatch.on('arg')
def cyclean(arg, **kwds):
  '''
  Clean up Curry output for string-based comparisons.

  Each line is treated as a value of the program.  Insignificant whitespace is
  removed, and the lines are sorted.
  '''
  raise RuntimeError('unhandled type: %s' % type(arg))

@cyclean.when(collections.Sequence, no=(str,))
def cyclean(lines, **kwds):
  if not kwds.get('keep_empty_lines', False):
    lines = (line for line in lines if line)
  if not kwds.get('keep_spacing', False):
    lines = (line.replace(' ','').replace('\t','') for line in lines)
  if kwds.get('sort_lines', True):
    lines = sorted(lines)
  return '\n'.join(lines)

@cyclean.when(str)
def cyclean(string, **kwds):
  return cyclean(string.split('\n'), **kwds)

def oracle():
  '''Gets the path to the oracle.  Returns None if there is no oracle.'''
  # Note: the CWD is assumed to be $root/tests.
  oracle = os.path.abspath('oracle')
  if os.path.isfile(oracle) and os.access(oracle, os.X_OK):
    return oracle
  else:
    return None

def require(f):
  '''Decorator that skips a test if the oracle is not present.'''
  return unittest.skipIf(oracle() is None, 'no oracle found')(f)

def divine(module, goal, currypath, timeout=None, goldenfile=None, clean_kwds={}):
  '''
  Invokes the oracle with a Curry goal to generate a golden result.

  Parameters:
  -----------
  ``module``
      A ``CurryModule`` or module name.
  ``goal``
      A goal object or name.
  ``currypath``
      The path to use for loading the module.
  ``timeout``
      The time limit for running the oracle.  This can be anything the timeout
      program accepts.
  ``goldenfile``
      Specifies a file that contains this result.  If supplied, the file
      will be updated with the command output, if necessary.

  Returns:
  --------
  If ``goldenfile`` is None, a string containing the values of ``goal``.
  Otherwise, a Boolean indicating whether the golden file was updated.
  '''
  # Check for a previous result.
  if isinstance(module, str):
    module = curry.import_(module)
  if goldenfile is not None:
    if not filesys.newer(module.__file__, goldenfile):
      return False

  # Call the oracle.
  oracle_ = oracle()
  assert oracle_
  try:
    goal = goal.ident.basename
  except AttributeError:
    pass
  with importer.binding(os.environ, 'CURRYPATH', ':'.join(currypath)):
    cmd = '%s %s %s' % (oracle_, module.__name__, goal)
    if timeout:
      cmd = 'timeout %s %s' % (timeout, cmd)
    output = cyclean(subprocess.check_output(cmd.split()), **clean_kwds)

  # Update the golden file or return the output.
  if goldenfile is not None:
    with open(goldenfile, 'wb') as au:
      au.write(output)
    return True
  else:
    return output

