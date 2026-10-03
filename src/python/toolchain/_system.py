from ..exceptions import CompileError
from .. import config
from ..tools.utility import make_exception
from ..utility import binding, curryname, filesys, formatting, strings
import errno, functools, logging, os, subprocess as sp, sys, time

__all__ = [
    'bindCurryPath', 'makeOutputDir', 'pexec', 'pexec_message'
  , 'targetNotUpdatedHint', 'updateCheck'
  ]
logger = logging.getLogger(__name__)
SUBDIR = config.intermediate_subdir()

def bindCurryPath(currypath):
  '''
  Returns a context manager that temporarily binds ``currypath`` to the
  environment variable CURRYPATH.
  '''
  value = ':'.join(curryname.makeCurryPath(currypath))
  return binding.binding(os.environ, 'CURRYPATH', value)

def makeOutputDir(file_out):
  dirname, _ = os.path.split(file_out)
  try:
    os.makedirs(dirname)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise

def pexec(cmd, cwd=None):
  '''
  Invokes the given command and returns its stdout as a string.  ``cwd`` is
  the working directory of the command.  A command that fails raises
  CompileError; the exception carries the command, the exit status, and the
  standard error text as ``command``, ``returncode``, and ``stderr``.
  '''
  child = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE, cwd=cwd)

  try:
    stdout,stderr = child.communicate()
    stdout = strings.ensure_text(stdout)
    stderr = strings.ensure_text(stderr)
  except:
    child.kill()
    raise

  try:
    retcode = child.wait()
  except:
    child.kill()
    sys.stderr.write(stderr)
    raise

  if retcode:
    err = CompileError(pexec_message(cmd, stderr))
    err.command = list(cmd)
    err.returncode = retcode
    err.stderr = stderr
    raise err
  return stdout

def pexec_message(cmd, stderr):
  '''The message of the CompileError raised for a failed command.'''
  return 'while running %s:\n%s' % (' '.join(cmd), formatting.indent(stderr, 8))

def targetNotUpdatedHint(prereq, target, start_time, **kwds):
  # Perhaps there is some file under a subdirectory of .curry with the correct
  # name and which is new enough.
  dirname, targetname = os.path.split(target)
  while not dirname.endswith('.curry'):
    dirname, _ = os.path.split(dirname)
  for root, dirs, files in os.walk(dirname):
    candidate = os.path.join(root, targetname)
    if os.path.exists(candidate):
      if start_time <= os.stat(candidate).st_mtime:
        assert not filesys.newer(prereq, candidate)
        return 'It appears %s was updated instead.  Sprite was configured ' \
               'with %s.' % (candidate, SUBDIR)

def updateCheck(f):
  @functools.wraps(f)
  def replacement(self, file_in, currypath, *args, **kwds):
    start_time = time.time()
    file_out = f(self, file_in, currypath, *args, **kwds)
    if filesys.newer(file_in, file_out):
      raise make_exception(
          CompileError
        , '%s was not updated as expected.' % file_out
        , hint=lambda:targetNotUpdatedHint(file_in, file_out, start_time)
        )
    elif os.stat(file_out).st_mtime >= start_time:
      logger.debug('Updated %r', file_out)
    return file_out
  return replacement

