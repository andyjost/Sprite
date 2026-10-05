'''
Runs one measurement in a child process and reads its numbers.

Every child runs under the ``timeout`` command and, with a cap, under
``prlimit --as``, in a session of its own.  The harness reaps the child with
``os.wait4``, which reports the CPU time of the child together with every
descendant it waited for.  So the compilers and the Curry front end that
sprite-exec runs are counted with it.

The peak resident set needs one more tool.  Linux starts the memory
high-water mark of a new process at the resident set of its parent, so the
peak that ``wait4`` reports for a child of this harness is never below the
size of the harness itself.  GNU time (``/usr/bin/time``) is a small program
that forks the command and reports the peak of the command and its
descendants; the harness runs it inside the wrapper chain when it is
installed.  Without it the peak comes from ``wait4``, with that floor.
'''

import json, os, re, shutil, signal, subprocess, sys, tempfile, time

__all__ = [
    'Run', 'TIMEOUT_STATUS', 'gnu_time', 'parse_json', 'parse_pakcs'
  , 'parse_stats', 'parse_time', 'rss_source', 'run_command'
  ]

# The exit status of the timeout command when the child ran out of time.
TIMEOUT_STATUS = 124

# ru_maxrss is in kibibytes on Linux and in bytes on macOS.
RSS_UNIT = 1 if sys.platform == 'darwin' else 1024

# The first seven fields of sprite-exec --stats.  The collector seconds
# (gc_seconds) and, on a runtime built with the scheduler counters, more
# key=value pairs follow (see counters.py).
STATS_PATTERN = re.compile(
    r'^wall=\S+ cpu=\S+ steps=\S+ forks=\S+ collections=\S+ peak_rss=\S+'
    r' compile=\S+( \w+=\S+)*$'
  )
PAKCS_PATTERN = re.compile(
    r'Execution time: (\d+) msec\. / elapsed: (\d+) msec\.'
  )

_GNU_TIME = []

def gnu_time():
  '''The path of GNU time, or None when it is not installed.'''
  if not _GNU_TIME:
    path = shutil.which('time') or '/usr/bin/time'
    try:
      proc = subprocess.run(
          [path, '--version'], capture_output=True, text=True, timeout=30
        )
      found = 'GNU' in proc.stdout + proc.stderr
    except (OSError, subprocess.TimeoutExpired):
      found = False
    _GNU_TIME.append(path if found else None)
  return _GNU_TIME[0]


def rss_source():
  '''How the peak resident set is measured, for the record.'''
  if gnu_time():
    return 'GNU time'
  return 'wait4 (never below the resident set of the harness)'


class Run:
  '''The outcome of one child process.'''
  def __init__(
      self, cmd, wall, usage, returncode, stdout, stderr, peak_rss=None
    ):
    self.cmd = cmd
    self.wall = wall
    self.cpu = usage.ru_utime + usage.ru_stime
    # The peak of GNU time when it reported one; else the floored peak.
    self.peak_rss_exact = peak_rss is not None
    self.peak_rss = usage.ru_maxrss * RSS_UNIT if peak_rss is None else peak_rss
    self.returncode = returncode
    self.stdout = stdout
    self.stderr = stderr

  @property
  def timed_out(self):
    return self.returncode == TIMEOUT_STATUS

  @property
  def status(self):
    '''ok, fail, or timeout.'''
    if self.timed_out:
      return 'timeout'
    return 'ok' if self.returncode == 0 else 'fail'

  @property
  def error(self):
    '''One line about a failure: the status and the last line of stderr.'''
    if self.status == 'ok':
      return None
    if self.timed_out:
      return 'timed out'
    lines = [line.strip() for line in self.stderr.splitlines() if line.strip()]
    tail = lines[-1] if lines else ''
    if self.returncode < 0:
      what = 'killed by signal %d' % -self.returncode
    else:
      what = 'exit status %d' % self.returncode
    return '%s: %s' % (what, tail) if tail else what


def run_command(cmd, env=None, cwd=None, timeout=600, cap=None):
  '''
  Runs ``cmd`` to its end and returns a :class:`Run`.

  Args:
    env, cwd:
        The environment and the working directory of the child.
    timeout:
        Seconds after which the child and its descendants are killed.  The
        run then has the status ``timeout``.
    cap:
        A cap on the address space of the child, in bytes; None for none.
  '''
  wrapper = ['timeout', '-k', '5', '%g' % timeout]
  rssfile = None
  if gnu_time():
    handle, rssfile = tempfile.mkstemp(prefix='rss-', suffix='.txt')
    os.close(handle)
    wrapper += [gnu_time(), '-q', '-f', '%M', '-o', rssfile]
  if cap:
    wrapper += ['prlimit', '--as=%d' % cap]
  cmd = wrapper + list(cmd)
  try:
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
      start = time.perf_counter()
      proc = subprocess.Popen(
          cmd, env=env, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out
        , stderr=err, start_new_session=True
        )
      _, status, usage = os.wait4(proc.pid, 0)
      wall = time.perf_counter() - start
      returncode = os.waitstatus_to_exitcode(status)
      # Popen did not reap the child; tell it the status.
      proc.returncode = returncode
      if returncode == TIMEOUT_STATUS:
        _kill_session(proc.pid)
      out.seek(0)
      err.seek(0)
      return Run(
          cmd, wall, usage, returncode
        , out.read().decode('utf-8', 'replace')
        , err.read().decode('utf-8', 'replace')
        , peak_rss=_read_rss(rssfile)
        )
  finally:
    if rssfile is not None:
      try:
        os.unlink(rssfile)
      except OSError:
        pass


def _read_rss(rssfile):
  '''The peak in bytes that GNU time wrote, or None.'''
  if rssfile is None:
    return None
  try:
    with open(rssfile) as stream:
      lines = stream.read().split()
    return int(lines[-1]) * 1024
  except (OSError, ValueError, IndexError):
    return None


def _kill_session(pid):
  '''Kills what the timeout command left behind in the session of the child.'''
  try:
    os.killpg(pid, signal.SIGKILL)
  except (ProcessLookupError, PermissionError):
    pass


def parse_stats(stderr):
  '''
  The fields of the line that ``sprite-exec --stats`` prints, as a dict, or
  None when the line is absent.  The last such line of ``stderr`` counts.
  '''
  for line in reversed(stderr.splitlines()):
    line = line.strip()
    if STATS_PATTERN.match(line):
      fields = {}
      for item in line.split():
        key, value = item.split('=', 1)
        fields[key] = float(value) if '.' in value else int(value)
      return fields
  return None


def parse_time(stdout):
  '''The seconds that ``sprite-exec -t`` prints, or None.'''
  for line in reversed(stdout.split('\n')):
    line = line.strip()
    if line:
      try:
        return float(line)
      except ValueError:
        return None
  return None


def parse_pakcs(stdout):
  '''
  The run time and the elapsed time that PAKCS prints with ``:set +time``,
  in seconds, as the pair (cpu, wall); None when absent.
  '''
  found = PAKCS_PATTERN.findall(stdout)
  if not found:
    return None
  cpu, wall = found[-1]
  return int(cpu) / 1000.0, int(wall) / 1000.0


def parse_json(stdout):
  '''The JSON object on the last non-empty line of ``stdout``, or None.'''
  for line in reversed(stdout.splitlines()):
    line = line.strip()
    if line:
      try:
        value = json.loads(line)
      except ValueError:
        return None
      return value if isinstance(value, dict) else None
  return None
