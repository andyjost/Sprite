'''
Utilities for comparing Curry output.
'''
from curry import importer
from curry import visitation
import collections
import os
import subprocess

@visitation.dispatch.on('arg')
def cyclean(arg):
  '''
  Clean up Curry output for string-based comparisons.

  Each line is treated as a value of the program.  Insignificant whitespace is
  removed, and the lines are sorted.
  '''
  raise RuntimeError('unhandled type: %s' % type(arg))

@cyclean.when(collections.Sequence, no=(str,))
def cyclean(seq):
  return '\n'.join(sorted(
      line.replace(' ','').replace('\t','')
          for line in seq if line
    ))

@cyclean.when(str)
def cyclean(string):
  return cyclean(string.split('\n'))

def ensureGolden(goldenfile, module, *args, **kwds):
  '''
  Ensures the golden result file for a Curry program exists.

  Parameters:
  -----------
  ``module``
      A ``CurryModule`` or module name.
  ``goldenfile``
      The name of the golden file.

  Additional arguments are passed to ``callOracle``.
  '''
  if isinstance(module, str):
    module = curry.import_(module)
  if importer.newer(module.__file__, goldenfile):
    output = cyclean(callOracle(module, *args, **kwds))
    with open(goldenfile, 'wb') as au:
      au.write(output)

def callOracle(module, goal, currypath, timeout=None):
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
  '''
  if isinstance(module, str):
    module = curry.import_(module)
  try:
    goal = goal.ident.basename
  except AttributeError:
    pass
  with importer.binding(os.environ, 'CURRYPATH', ':'.join(currypath)):
    cmd = ('./oracle :l %s :eval %s :q' % (module.__name__, goal))
    if timeout:
      cmd = 'timeout %s %s' % (timeout, cmd)
    return cyclean(subprocess.check_output(cmd.split()))
