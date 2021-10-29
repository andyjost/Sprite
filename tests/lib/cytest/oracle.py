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

Selecting the Oracle
--------------------
The oracle flavor can be specified by putting a line such as the following in
the Curry source file:

    {-# ORACLE KICS2 #-}

The provided string is lowered and appended to the oracle name with a dot.
So, the above line would use oracle.kics2 to provide golden results.


Bypassing the Oracle
--------------------
The oracle can be bypassed by specifying result(s) directly in the Curry
source using an ORACLE_RESULT directive.  The format is as follows:

    {-# ORACLE_RESULT pattern: result #-}

``pattern`` is matched against the goal name.  It is a glob pattern unless
enclosed with slashes, as in /.*/, in which case it is a regular expression.
``result`` is a Curry result expression indicating the expected result as the
REPL prints it.  It must be understood by the ``readcurry`` module.

Each matching occurrence of an ORACLE_RESULT directive indicates a result for
the matching goal(s).  The program is expected to output each and only the
specified results.
'''

from curry.utility import binding, filesys
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

def get_flavor(currymodule):
  filename = currymodule.__file__
  pat = re.compile(r'{-#\s*ORACLE\s+(\w+)\s*#-}')
  if filename:
    with open(filename) as stream:
      m = re.search(pat, stream.read())
      if m:
        return m.group(1).lower()

def get_embedded_results(currymodule, goal):
  filename = currymodule.__file__
  linepat = re.compile(r'{-#\s*ORACLE_RESULT\s+(\S+)\s+(.*)#-}')
  if filename:
    results = []
    with open(filename) as stream:
      for line in stream:
        m = re.search(linepat, line)
        if m:
          goalpat, text = m.groups()
          if goalpat.endswith(':'):
            goalpat = goalpat[:-1]
          if goalpat.startswith('/') and goalpat.endswith('/'):
            if re.match(goalpat[1:-1], str(goal)):
              results.append(text.strip())
          elif glob.fnmatch.fnmatch(str(goal), goalpat):
            results.append(text.strip())
    return '\n'.join(results) if results else None

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

  # Check whether the file specifies the expected result.
  output = get_embedded_results(module, goal)
  if output is None:
    # Call the oracle.
    oracle_ = oracle(flavor=get_flavor(module))
    assert oracle_
    with binding.binding(os.environ, 'CURRYPATH', ':'.join(currypath)):
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

