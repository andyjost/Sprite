'''
Utilities for comparing output to other Curry systems.

Correct answers are provided by an external Curry system called the oracle.
The test driver calls the oracle, when necessary, to compute correct answers.
Those are stored alongside the Curry source (typically found under
$ROOT/tests/data/curry).  When testing, the Sprite answer is computed and
compared with the saved answer from the oracle.

The $ROOT/tests subdirectory should contain an executable called "oracle" that
provides correct answers.  The expected interface is "oracle <modulename>
<goal>".  This program should use the CURRYPATH environment variable to locate
<modulename>.  The oracle should print the result of the specified goal, one
result per line, and nothing else.
'''

from curry import importer
from curry.utility import filesys
import glob, os, re, subprocess, unittest

def oracle(flavor=None):
  '''Gets the path to the oracle.  Returns None if there is no oracle.'''
  # Note: the CWD is assumed to be $root/tests.
  suffix = '.' + flavor if flavor is not None else ''
  oracle = os.path.abspath('oracle' + suffix)
  if os.path.isfile(oracle) and os.access(oracle, os.X_OK):
    return oracle
  else:
    return None

def get_embedded_result(currymodule, goal):
  # The oracle can be bypassed by specifying the result directly in the Curry
  # source file:
  #
  #     {-# ORACLE_RESULT * True #-}
  #
  # The first argument is a pattern to match against the goal name.  The
  # first such line with a matching pattern (if any) will be used.
  # If the pattern is enclosed with slashes, as in /.*/, it is treated as
  # a regular expression.  Otherwise, it is a glob pattern.
  filename = currymodule.__file__
  linepat = re.compile(r'{-#\s*ORACLE_RESULT\s+(\S+)\s+(.*)#-}')
  if filename:
    with open(filename) as stream:
      for line in stream:
        m = re.search(linepat, line)
        if m:
          goalpat, text = m.groups()
          if goalpat.startswith('/') and goalpat.endswith('/'):
            if re.match(goalpat[1:-1], str(goal)):
              return text.strip()
          elif glob.fnmatch.fnmatch(str(goal), goalpat):
            return text.strip()

def get_flavor(currymodule):
  # The oracle flavor can be specified by putting a line such as the following
  # in the Curry source file:
  #
  #     {-# ORACLE KICS2 #-}
  #
  # The provided string is lowered and appended to the oracle name with a dot.
  # So, the above line would use oracle.kics2 to provide golden results.
  filename = currymodule.__file__
  pat = re.compile(r'{-#\s*ORACLE\s+(\w+)\s*#-}')
  if filename:
    with open(filename) as stream:
      m = re.search(pat, stream.read())
      if m:
        return m.group(1).lower()

def require(f):
  '''Decorator that skips a test if the oracle is not present.'''
  return unittest.skipIf(oracle() is None, 'no oracle found')(f)

def divine(module, goal, currypath, timeout=None, goldenfile=None):
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

  # Check whether the file provides the result directly.
  output = get_embedded_result(module, goal)
  if output is None:
    # Call the oracle.
    oracle_ = oracle(flavor=get_flavor(module))
    assert oracle_
    with importer.binding(os.environ, 'CURRYPATH', ':'.join(currypath)):
      cmd = '%s %s %s' % (oracle_, module.__name__, goal)
      if timeout:
        cmd = 'timeout %s %s' % (timeout, cmd)
      output = subprocess.check_output(cmd.split())

  # Update the golden file or return the output.
  if goldenfile is not None:
    with open(goldenfile, 'wb') as au:
      au.write(output)
    return True
  else:
    return output

