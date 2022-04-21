from ..exceptions import CompileError
from .. import config
from ..tools.utility import make_exception
from ..utility import binding, curryname, filesys, formatting, strings
import errno, functools, logging, os, subprocess as sp, sys, time

__all__ = ['bindCurryPath', 'makeOutputDir', 'popen', 'targetNotUpdatedHint', 'updateCheck']
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

def popen(cmd, input=None, pipecmd=None):
  '''
  Invokes the given command and returns its stdout as a string.  A second
  pipeline stage may be provided.
  '''
  stdin = None if input is None else sp.PIPE
  input = None if input is None else strings.ensure_binary(input)
  child = sp.Popen(cmd, stdin=stdin, stdout=sp.PIPE, stderr=sp.PIPE)
  if pipecmd:
    term = sp.Popen(pipecmd, stdin=child.stdout, stdout=sp.PIPE)
    child.stdout.close()
  else:
    term = child

  try:
    stdout,stderr = term.communicate(input=input)
    stdout = strings.ensure_text(stdout)
    stderr = strings.ensure_text(stderr)
  except:
    term.kill()
    raise

  try:
    retcode = term.wait()
  except:
    term.kill()
    sys.stderr.write(stderr)
    raise

  if retcode:
    raise CompileError(
        'while running %s:\n%s' % (' '.join(cmd), formatting.indent(stderr, 8))
      )
  return stdout

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
        , hint=lambda:_targetNotUpdatedHint(file_in, file_out, start_time)
        )
    elif os.stat(file_out).st_mtime >= start_time:
      logger.debug('Updated %r', file_out)
    return file_out
  return replacement

