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

The instructions need perf.  ``perf stat -e instructions:u`` counts the
user-space instructions that the command and its descendants retire, a
number that does not depend on the load of the machine and compares across
machines of one architecture.  perf wraps the command itself, inside the
other wrappers, so the count covers the command tree only.  perf costs a few
milliseconds of CPU time per run, so a run under perf has wall and CPU
seconds that are not comparable with a run without it; the harness counts
the instructions in one more repetition after the measured ones and keeps
the measured seconds free of perf.

perf stat exits with status 0 when its command died of a signal, and says
so in text only.  So a shell runs between perf and the command
(PERF_SHIM): it waits for the command and exits with its status, which is
128 plus the signal number after a signal death, as every shell reports
it.  perf returns that status, and the harness maps a status above 128
back to the negative number that wait reports (perf_status).  Nothing is
read from the text perf prints.  The shell costs about 0.2 million
instructions, which the count includes; python -c pass retires about 600
million.
'''

import json, os, re, shutil, signal, subprocess, sys, tempfile, time

__all__ = [
    'PERF_EVENT', 'PERF_SHIM', 'Run', 'TIMEOUT_STATUS', 'gnu_time'
  , 'instructions_source', 'parse_json', 'parse_pakcs', 'parse_perf'
  , 'parse_stats', 'parse_time', 'perf', 'perf_status', 'rss_source'
  , 'run_command'
  ]

# The exit status of the timeout command when the child ran out of time.
TIMEOUT_STATUS = 124

# ru_maxrss is in kibibytes on Linux and in bytes on macOS.
RSS_UNIT = 1 if sys.platform == 'darwin' else 1024

# The event that perf counts: instructions retired in user space.
PERF_EVENT = 'instructions:u'

# The shell between perf and the command: it runs the command, waits, and
# exits with its status.  Two commands, so that no shell replaces itself
# with the command (then perf would see the signal again, and hide it).
PERF_SHIM = ['sh', '-c', '"$@"; exit $?', 'sh']

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
_PERF = []

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


def perf():
  '''
  The path of perf when ``perf stat -e instructions:u`` counts on this
  machine, or None: perf is not installed, the kernel refuses it, or the
  processor has no such counter.  Detected once, with a run of ``true``.
  '''
  return _detect_perf()[0]


def instructions_source():
  '''How the instructions are counted, or why they are not, for the record.'''
  return _detect_perf()[1]


def _detect_perf():
  if not _PERF:
    _PERF.append(_probe_perf())
  return _PERF[0]


def _probe_perf():
  path = shutil.which('perf')
  if path is None:
    return None, 'not measured: perf is not installed'
  cmd = [path, 'stat', '-e', PERF_EVENT, '-x,', '--', 'true']
  try:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    version = subprocess.run(
        [path, '--version'], capture_output=True, text=True, timeout=60
      ).stdout.strip().splitlines()
  except (OSError, subprocess.TimeoutExpired) as exc:
    return None, 'not measured: perf failed: %s' % exc
  if proc.returncode == 0 and parse_perf(proc.stderr):
    return path, 'perf stat -e %s (%s)' % (
        PERF_EVENT, version[0] if version else 'perf'
      )
  lines = [
      line.strip() for line in proc.stderr.splitlines()
          if line.strip() and line.strip().lower() != 'error:'
    ]
  why = lines[0] if lines else 'exit status %d' % proc.returncode
  return None, 'not measured: perf %s failed: %s' % (' '.join(cmd[1:5]), why)


class Run:
  '''The outcome of one child process.'''
  def __init__(
      self, cmd, wall, usage, returncode, stdout, stderr, peak_rss=None
    , instructions=None, perf=False
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
    # Whether the command ran under perf, and the instructions it counted.
    self.perf = perf
    self.instructions = instructions

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


def run_command(cmd, env=None, cwd=None, timeout=600, cap=None, perf=None):
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
    perf:
        The path of perf to count the instructions of the command and its
        descendants with; None for no count.
  '''
  wrapper = ['timeout', '-k', '5', '%g' % timeout]
  rssfile = perffile = None
  if gnu_time():
    handle, rssfile = tempfile.mkstemp(prefix='rss-', suffix='.txt')
    os.close(handle)
    wrapper += [gnu_time(), '-q', '-f', '%M', '-o', rssfile]
  if cap:
    wrapper += ['prlimit', '--as=%d' % cap]
  if perf:
    handle, perffile = tempfile.mkstemp(prefix='perf-', suffix='.txt')
    os.close(handle)
    wrapper += [perf, 'stat', '-e', PERF_EVENT, '-x,', '-o', perffile, '--']
    wrapper += PERF_SHIM
  command = list(cmd)
  cmd = wrapper + command
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
      stderr = err.read().decode('utf-8', 'replace')
      if perf:
        returncode = perf_status(returncode)
      return Run(
          cmd, wall, usage, returncode
        , out.read().decode('utf-8', 'replace'), stderr
        , peak_rss=_read_rss(rssfile)
        , instructions=_read_perf(perffile), perf=perf is not None
        )
  finally:
    for filename in rssfile, perffile:
      if filename is not None:
        try:
          os.unlink(filename)
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


def _read_perf(perffile):
  '''The instructions that perf stat wrote, or None.'''
  if perffile is None:
    return None
  try:
    with open(perffile) as stream:
      return parse_perf(stream.read())
  except OSError:
    return None


def perf_status(returncode):
  '''
  The status of a command run under perf, from the status of the chain.
  The shell of PERF_SHIM reports a signal death as 128 plus the signal
  number; that reads back as the negative number wait reports.  A command
  that exits with such a status by itself reads the same, as in every
  shell.  A status above 128 that names no signal of this machine (255,
  say) stays as it is.  The status of the timeout command (TIMEOUT_STATUS)
  is below 128.
  '''
  if 128 < returncode < 256 and returncode - 128 in signal.valid_signals():
    return 128 - returncode
  return returncode


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


def parse_perf(text):
  '''
  The instructions that ``perf stat -x,`` counted: the sum of the values of
  the instruction events in the CSV ``text`` (a hybrid processor reports one
  line per kind of core).  None when perf counted none, as in "<not
  counted>" and "<not supported>", or when the line is absent.
  '''
  total = None
  for line in text.splitlines():
    fields = line.split(',')
    if len(fields) < 3 or 'instructions' not in fields[2]:
      continue
    try:
      value = int(fields[0].strip())
    except ValueError:
      continue
    total = value if total is None else total + value
  return total


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
