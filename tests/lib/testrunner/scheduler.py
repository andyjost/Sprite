'''
Admission under the budget and the width, the watchdog, and the run loop.

A :class:`Job` is one command: a test file on one backend, or one directory
of the prepare pass.  The :class:`Scheduler` starts the jobs that
:func:`pick` admits, reaps them with ``wait4`` (which also gives the peak of
the leader), and asks a :class:`Watchdog` thread to poll the sessions of the
running jobs every half second.  The watchdog sums the resident sets of the
processes of each session, records the peak, and kills the session when the
sum exceeds the cap of the job or the job runs past its timeout.

Every job runs in a session of its own.  So the kill reaches the compilers
and the children the tests start, even the ones that the ``timeout`` command
moved to another process group, and the ones that started a session of
their own (see procs.scan_sessions and procs.kill_session).

While the scheduler runs in the main thread, SIGINT, SIGTERM, and SIGHUP
only set a flag, and the run loop raises KeyboardInterrupt at its next
turn.  So an interrupt never lands inside the start of a job, where a
leader could be lost, and a second Ctrl-C during the final reap changes
nothing.
'''

import os, signal, subprocess, sys, threading, time
from . import POLL_SECONDS, MIB
from . import procs, report

__all__ = ['INTERRUPT_SIGNALS', 'Job', 'Scheduler', 'Watchdog', 'pick']

# The signals that end a run as Ctrl-C does: the children are killed, the
# partial summary is printed, and the exit status is 130.  SIGHUP is here
# because the children run in sessions of their own, so a closed terminal
# would leave them running if the runner died of it.
INTERRUPT_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)

class Job:
  '''One command with its limits and, after the run, its outcome.'''

  def __init__(
      self, filename, backend, argv, cap, timeout, logfile, cwd=None, env=None
    , exclusive=False, hint=None
    ):
    self.filename = filename
    self.backend = backend
    self.argv = list(argv)
    self.cap = cap
    self.timeout = timeout
    self.logfile = logfile
    self.cwd = cwd
    self.env = env
    self.exclusive = exclusive
    # The manifest duration, for the order and the listing.
    self.hint = hint
    # The outcome.
    self.proc = None
    self.pid = None
    self.started = None
    self.duration = None
    self.peak = None
    self.returncode = None
    self.status = 'pending'
    self.note = ''
    self.tests = None
    self.failures = None
    self.kill_reason = None
    self.finished = False
    # The pids of the job's processes at the last poll: the roots of the
    # next scan, so a process whose parent ended stays with the job.
    self.members = set()
    self._pump = None

  def __repr__(self):
    return 'Job(%r, %r, %s)' % (self.filename, self.backend, self.status)

  @property
  def completed(self):
    '''True when the command ended by itself, with a status of its own.'''
    return self.finished and self.kill_reason is None \
       and self.returncode is not None and self.returncode >= 0

  @property
  def ok(self):
    return self.status == 'ok'

  def record_peak(self, rss):
    if rss is not None and (self.peak is None or rss > self.peak):
      self.peak = rss


def pick(pending, running, budget, width):
  '''
  The first pending job that may start now, or None.  ``pending`` is in the
  order of preference (longest first).  A job starts when fewer than
  ``width`` jobs run, no exclusive job runs, no other backend runs the same
  file, and the caps of the running jobs plus its own stay within
  ``budget``.  When nothing runs, the first job that the other rules allow
  starts whatever its cap, so a run never stalls.
  '''
  if len(running) >= width:
    return None
  if any(job.exclusive for job in running):
    return None
  used = sum(job.cap for job in running)
  files = set(job.filename for job in running)
  for job in pending:
    if job.exclusive and running:
      continue
    if job.filename in files:
      continue
    if running and used + job.cap > budget:
      continue
    return job
  return None


class Watchdog(threading.Thread):
  '''
  Polls the sessions of the running jobs.  Records the peak of each and kills
  a session over its cap or past its timeout.  The scheduler's lock covers
  each tick, so a job is never reaped while the watchdog looks at it.
  '''

  def __init__(self, scheduler, poll=POLL_SECONDS):
    super().__init__(name='watchdog', daemon=True)
    self.scheduler = scheduler
    self.poll = poll
    self.stopped = threading.Event()

  def run(self):
    while not self.stopped.wait(self.poll):
      with self.scheduler.lock:
        self.tick()

  def stop(self):
    self.stopped.set()

  def tick(self, now=None):
    '''One poll.  Call it with the scheduler's lock held.'''
    running = [job for job in self.scheduler.running if job.pid is not None]
    if not running:
      return
    found = procs.scan_sessions(
        [job.pid for job in running]
      , roots={job.pid: job.members for job in running}
      )
    now = time.monotonic() if now is None else now
    for job in running:
      rss, pids = found[job.pid]
      job.members = set(pids)
      job.record_peak(rss)
      if job.kill_reason is not None:
        continue
      if job.cap is not None and rss > job.cap:
        job.kill_reason = 'memory'
        job.note = '%d MB > cap %d MB' % (round(rss / MIB), round(job.cap / MIB))
        procs.kill_session(job.pid, roots=job.members)
      elif job.timeout is not None and now - job.started > job.timeout:
        job.kill_reason = 'timeout'
        job.note = 'after %g s' % job.timeout
        procs.kill_session(job.pid, roots=job.members)


class Scheduler:
  '''
  Runs jobs under a budget and a width.

  Args:
    jobs:
        The jobs, in the order of preference.
    budget:
        The sum of the caps of the jobs that may run at once, in bytes.
    width:
        How many jobs may run at once.
    poll:
        The seconds between two polls of the loop and of the watchdog.
    on_start, on_finish:
        Called with a job when it starts and when it finishes.
    echo:
        Copy the output of each job to standard output as it comes, besides
        the log.  Meant for a width of one.
    inherit_stdin:
        Let the jobs read the standard input of the runner.  Meant for a
        width of one, so a breakpoint in a test gets the terminal.
  '''

  def __init__(
      self, jobs, budget, width, poll=POLL_SECONDS, on_start=None
    , on_finish=None, echo=False, inherit_stdin=False
    ):
    self.pending = list(jobs)
    self.running = []
    self.done = []
    self.budget = budget
    self.width = max(1, width)
    self.poll = poll
    self.on_start = on_start
    self.on_finish = on_finish
    self.echo = echo
    self.inherit_stdin = inherit_stdin
    self.lock = threading.RLock()
    self.interrupted = False
    # The signal that asked for the end of the run, or None.
    self.interrupt_requested = None
    self.wall = None

  @property
  def jobs(self):
    return self.done + self.running + self.pending

  def run(self):
    '''Runs every job.  Returns the jobs in the order they finished.'''
    start = time.monotonic()
    watchdog = Watchdog(self, self.poll)
    watchdog.start()
    saved = self._install_handlers()
    try:
      while self.pending or self.running:
        self._check_interrupt()
        self.admit()
        self._check_interrupt()
        self.reap()
        if self.pending or self.running:
          time.sleep(self.poll)
    except KeyboardInterrupt:
      self.interrupted = True
      self.kill_all('interrupted')
      while True:
        try:
          self.reap(block=True)
          break
        except KeyboardInterrupt:
          continue
    finally:
      self._restore_handlers(saved)
      watchdog.stop()
      watchdog.join()
      self.wall = time.monotonic() - start
    return self.done

  def _install_handlers(self):
    '''
    Routes INTERRUPT_SIGNALS to a flag while the run lasts.  Only the main
    thread may set handlers; elsewhere the default handlers stay.
    '''
    if threading.current_thread() is not threading.main_thread():
      return None
    saved = {}
    for signum in INTERRUPT_SIGNALS:
      try:
        saved[signum] = signal.signal(signum, self._on_signal)
      except (OSError, ValueError):
        pass
    return saved

  def _restore_handlers(self, saved):
    for signum, handler in (saved or {}).items():
      try:
        signal.signal(signum, handler)
      except (OSError, ValueError, TypeError):
        pass

  def _on_signal(self, signum, frame):
    self.interrupt_requested = signum

  def _check_interrupt(self):
    if self.interrupt_requested is not None:
      raise KeyboardInterrupt

  def admit(self):
    '''Starts the jobs that may start now.'''
    while self.interrupt_requested is None:
      with self.lock:
        job = pick(self.pending, self.running, self.budget, self.width)
        if job is None:
          return
        self.pending.remove(job)
        if not self.running and job.cap is not None and job.cap > self.budget:
          job.note = 'cap above the budget'
        failed = None
        try:
          self.start(job)
        except OSError as exc:
          job.finished = True
          job.status = 'error'
          job.note = str(exc)
          job.duration = 0.0
          self.done.append(job)
          failed = job
        finally:
          # A job whose leader exists is running, whatever interrupted the
          # start after the fork.
          if job.proc is not None and not job.finished:
            self.running.append(job)
      if failed is not None:
        if self.on_finish:
          self.on_finish(failed)
      elif self.on_start:
        self.on_start(job)

  def start(self, job):
    '''Starts one job in a session of its own, with its output in its log.'''
    if job.logfile:
      os.makedirs(os.path.dirname(job.logfile), exist_ok=True)
      log = open(job.logfile, 'wb')
    else:
      log = open(os.devnull, 'wb')
    try:
      stdin = None if self.inherit_stdin else subprocess.DEVNULL
      stdout = subprocess.PIPE if self.echo else log
      job.started = time.monotonic()
      job.proc = subprocess.Popen(
          job.argv, cwd=job.cwd, env=job.env, stdin=stdin, stdout=stdout
        , stderr=subprocess.STDOUT, start_new_session=True
        )
      job.pid = job.proc.pid
      if self.echo:
        job._pump = threading.Thread(
            target=_pump, args=(job.proc.stdout, log), daemon=True
          )
        job._pump.start()
        log = None
    finally:
      if log is not None:
        log.close()

  def reap(self, block=False):
    '''
    Collects the jobs that ended.  With ``block``, waits for every running
    job; use it after a kill.
    '''
    finished = []
    with self.lock:
      for job in list(self.running):
        flags = 0 if block else os.WNOHANG
        try:
          pid, status, usage = os.wait4(job.pid, flags)
        except ChildProcessError:
          pid, status, usage = job.pid, 0, None
        if pid == 0:
          continue
        self._finish(job, status, usage)
        self.running.remove(job)
        self.done.append(job)
        finished.append(job)
    for job in finished:
      if self.on_finish:
        self.on_finish(job)

  def _finish(self, job, status, usage):
    job.duration = time.monotonic() - job.started
    job.returncode = os.waitstatus_to_exitcode(status)
    # Popen did not reap the child; tell it the status.
    job.proc.returncode = job.returncode
    if usage is not None:
      job.record_peak(usage.ru_maxrss * 1024)
    # Whatever the leader left behind in its session goes now, so the next
    # job finds the machine as it was and the log pipe closes.
    procs.kill_session(job.pid, roots=job.members)
    if job._pump is not None:
      job._pump.join(timeout=5)
    job.finished = True
    counts = report.parse_unittest(report.tail(job.logfile, 10 ** 6)) \
             if job.logfile else {'tests': None, 'failures': None}
    job.tests = counts['tests']
    job.failures = counts['failures']
    if job.kill_reason is not None:
      job.status = 'killed: ' + job.kill_reason
    elif job.returncode == 0:
      job.status = 'ok'
    elif job.returncode > 0:
      job.status = 'FAILED'
      if job.failures is None:
        job.note = 'exit status %d' % job.returncode
    else:
      job.status = 'crashed'
      job.note = 'signal %d' % -job.returncode

  def kill_all(self, reason):
    '''Kills every running job.  ``reason`` becomes its kill reason.'''
    with self.lock:
      for job in self.running:
        if job.kill_reason is None:
          job.kill_reason = reason
        procs.kill_session(job.pid, roots=job.members)
      for job in self.pending:
        job.status = 'not run'


def _pump(source, log):
  '''Copies the output of a job to its log and to standard output.'''
  out = getattr(sys.stdout, 'buffer', None)
  try:
    while True:
      chunk = source.read1(65536) if hasattr(source, 'read1') else source.read(65536)
      if not chunk:
        break
      log.write(chunk)
      log.flush()
      if out is not None:
        out.write(chunk)
        out.flush()
  finally:
    log.close()
    source.close()
