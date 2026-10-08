'''
Tests for the test runner under lib/testrunner: the admission rules, the
watchdog and the allowance of the toolchain, the timeout, the manifest,
the selection rules, the fast tier, the report, the exit status, and the
prepare pass against a stand-in sprite-make.  The children are small
Python programs; no test here compiles Curry.
'''
import cytest # from ./lib; must be first
import testrunner
from testrunner import cli, prepare, procs, report, selection
from testrunner.manifest import FORMAT, Manifest
from testrunner.scheduler import INTERRUPT_SIGNALS, Job, Scheduler, pick
import io, json, os, re, shutil, signal, stat, subprocess, sys, tempfile
import threading, time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

PYTHON = sys.executable
MIB = 1024 ** 2
GIB = 1024 ** 3
# The watchdog polls fast in these tests.
POLL = 0.1

OK_OUTPUT = '''
test_a (mod.T.test_a) ... ok
test_b (mod.T.test_b) ... skipped 'why'

----------------------------------------------------------------------
Ran 2 tests in 0.004s

OK (skipped=1)
'''
FAILED_OUTPUT = '''
test_a ... FAIL
test_b ... ERROR
test_c ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.010s

FAILED (failures=1, errors=1)
'''

# A stand-in for sprite-make: -S prints the product directory; otherwise it
# writes the product of every module named on the command line, except the
# modules whose name begins with STUB_MAKE_FAIL of the environment ("bad"
# without it; the empty string fails every module and writes nothing), and
# exits with 1 when one of those was named, as sprite-make -k does.
STUB_MAKE = '''#!%(python)s
import os, sys
args = sys.argv[1:]
if args == ['-S']:
  sys.stdout.write('.curry/stub')
  sys.exit(0)
suffix = '.so' if '--so' in args else '.py'
fail = os.environ.get('STUB_MAKE_FAIL', 'bad')
status = 0
for name in [arg for arg in args if arg.endswith('.curry')]:
  directory, base = os.path.split(name)
  if base.startswith(fail):
    sys.stderr.write('stub-make: %%s: no good\\n' %% name)
    status = 1
    continue
  outdir = os.path.join(directory, '.curry', 'stub')
  os.makedirs(outdir, exist_ok=True)
  with open(os.path.join(outdir, base[:-len('.curry')] + suffix), 'w'):
    pass
sys.exit(status)
''' % {'python': sys.executable}

# A stand-in for the python of an installation: whatever the arguments, it
# prints the output of a passing unittest run and exits with 0.
STUB_PYTHON = '''#!%(python)s
import sys
sys.stderr.write(%(output)r)
''' % {'python': sys.executable, 'output': OK_OUTPUT}


def stub_installation(root):
  '''
  Writes a stand-in installation under ``root``: bin/python and
  bin/sprite-make (STUB_PYTHON and STUB_MAKE).  Returns ``root``.
  '''
  bindir = os.path.join(root, 'bin')
  os.makedirs(bindir, exist_ok=True)
  for name, script in ('python', STUB_PYTHON), ('sprite-make', STUB_MAKE):
    path = os.path.join(bindir, name)
    with open(path, 'w') as stream:
      stream.write(script)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
  return root


class FakeResult:
  '''What Manifest.update reads from a job.'''
  def __init__(self, duration, peak, tests=1, failures=0, completed=True):
    self.duration = duration
    self.peak = peak
    self.tests = tests
    self.failures = failures
    self.completed = completed


def stubjob(name, cap=GIB, backend='py', exclusive=False):
  '''A job that never runs; for the admission tests.'''
  return Job(
      name, backend, ['true'], cap=cap, timeout=None, logfile=None
    , exclusive=exclusive
    )


class TestPick(unittest.TestCase):
  '''The admission rules.'''

  def test_width(self):
    a, b = stubjob('a'), stubjob('b')
    self.assertIs(pick([a, b], [], 10 * GIB, 1), a)
    self.assertIsNone(pick([b], [a], 10 * GIB, 1))
    self.assertIs(pick([b], [a], 10 * GIB, 2), b)

  def test_floor_costs_width_where_the_budget_binds(self):
    '''
    The budget sums the caps, and the cap of a small file is the floor
    (MIN_CAP): a budget of 3.6 GB admits three files at the floor, where
    caps of twice a 200 MB peak would admit nine (the sentence in section
    10 of README).
    '''
    budget = int(3.6 * GIB)
    floor = testrunner.MIN_CAP
    self.assertEqual(floor, GIB)
    small = testrunner.CAP_FACTOR * 200 * testrunner.MIB
    for cap, admitted in (floor, 3), (small, 9):
      running = []
      pending = [stubjob('f%d' % i, cap=cap) for i in range(12)]
      while True:
        job = pick(pending, running, budget, 12)
        if job is None:
          break
        pending.remove(job)
        running.append(job)
      self.assertEqual(len(running), admitted, cap)

  def test_budget_admits_what_fits(self):
    running = [stubjob('r', cap=3 * GIB)]
    big = stubjob('big', 3 * GIB)
    mid = stubjob('mid', 2 * GIB)
    small = stubjob('small', GIB)
    # 3 + 3 > 5, 3 + 2 = 5 fits: the first that fits starts, not the first.
    self.assertIs(pick([big, mid, small], running, 5 * GIB, 8), mid)
    self.assertIs(pick([big, small], running, 5 * GIB, 8), small)
    self.assertIsNone(pick([big], running, 5 * GIB, 8))

  def test_budget_never_stalls(self):
    # Nothing runs: the first job starts whatever its cap.
    big = stubjob('big', 8 * GIB)
    self.assertIs(pick([big], [], GIB, 4), big)

  def test_longest_first(self):
    manifest = Manifest({
        'short.py': {'py': {'duration_s': 2}}
      , 'long.py': {'py': {'duration_s': 200}}
      })
    names = ['short.py', 'long.py', 'new.py']
    names.sort(key=lambda name: manifest.order_key(name, 'py'))
    # The longest first; a file without an entry is assumed to take the
    # median of the measured files (101 s here).
    self.assertEqual(names, ['long.py', 'new.py', 'short.py'])
    jobs = [stubjob(name) for name in names]
    self.assertIs(pick(jobs, [], 10 * GIB, 4), jobs[0])

  def test_sparse_manifest_order(self):
    '''
    With the committed seed, which measures four heavy files only, the
    heavy files start before the files without an entry, not after them.
    '''
    manifest = Manifest({
        'func_eqconstr.py': {'py': {'duration_s': 323}, 'cxx': {'duration_s': 323}}
      , 'unit_py_io.py': {'py': {'duration_s': 100}, 'cxx': {'duration_s': 100}}
      , 'unit_cxx_only.py': {'cxx': {'duration_s': 1}}
      })
    self.assertEqual(manifest.assumed_duration('py'), 211.5)
    self.assertEqual(manifest.assumed_duration('cxx'), 100)
    self.assertEqual(manifest.assumed_duration(), 100)
    names = ['unit_a.py', 'unit_py_io.py', 'unit_b.py', 'func_eqconstr.py']
    names.sort(key=lambda name: manifest.order_key(name, 'py'))
    self.assertEqual(
        names, ['func_eqconstr.py', 'unit_a.py', 'unit_b.py', 'unit_py_io.py']
      )
    # A backend without a measurement borrows the median of the others.
    manifest = Manifest({'a.py': {'cxx': {'duration_s': 50}}})
    self.assertEqual(manifest.assumed_duration('py'), 50)
    self.assertEqual(manifest.order_key('b.py', 'py'), (-50, 0))
    self.assertEqual(manifest.order_key('a.py', 'cxx'), (-50, 1))
    # Nothing measured: every file is equal, and the sort keeps the names.
    self.assertIsNone(Manifest().assumed_duration('py'))
    self.assertEqual(Manifest().order_key('a.py', 'py'), (0, 0))

  def test_exclusive(self):
    alone = stubjob('alone', exclusive=True)
    other = stubjob('other')
    running = [stubjob('r')]
    self.assertIsNone(pick([alone], running, 10 * GIB, 4))
    self.assertIs(pick([alone, other], running, 10 * GIB, 4), other)
    self.assertIs(pick([alone, other], [], 10 * GIB, 4), alone)
    self.assertIsNone(pick([other], [alone], 10 * GIB, 4))

  def test_one_file_on_one_backend_at_a_time(self):
    py = stubjob('a.py', backend='py')
    cxx = stubjob('a.py', backend='cxx')
    b = stubjob('b.py', backend='cxx')
    self.assertIs(pick([cxx, b], [py], 10 * GIB, 4), b)
    self.assertIs(pick([cxx], [b], 10 * GIB, 4), cxx)


class SchedulerTests(unittest.TestCase):
  '''A base: a log directory and a job builder.'''

  def setUp(self):
    self.logdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, self.logdir, ignore_errors=True)

  def pyjob(self, name, code, cap=GIB, timeout=None, backend='py'):
    return Job(
        name, backend, [PYTHON, '-c', code], cap=cap, timeout=timeout
      , logfile=os.path.join(self.logdir, backend, name + '.log')
      )

  def run_jobs(self, jobs, width=1, budget=16 * GIB, **kwds):
    sched = Scheduler(jobs, budget, width, poll=POLL, **kwds)
    sched.run()
    return sched


class TestScheduler(SchedulerTests):

  def test_statuses_counts_and_exit_status(self):
    good = self.pyjob('good.py', 'import sys; sys.stderr.write(%r)' % OK_OUTPUT)
    bad = self.pyjob(
        'bad.py', 'import sys; sys.stderr.write(%r); sys.exit(1)' % FAILED_OUTPUT
      )
    finished = []
    sched = self.run_jobs([good, bad], on_finish=finished.append)
    self.assertEqual([job.filename for job in finished], ['good.py', 'bad.py'])
    self.assertEqual(good.status, 'ok')
    self.assertEqual((good.tests, good.failures), (2, 0))
    self.assertTrue(good.completed)
    self.assertEqual(bad.status, 'FAILED')
    self.assertEqual((bad.tests, bad.failures), (3, 2))
    self.assertTrue(bad.completed)
    self.assertIsNotNone(good.peak)
    self.assertGreater(good.duration, 0)
    self.assertEqual(cli.exit_status([good]), 0)
    self.assertEqual(cli.exit_status([good, bad]), 1)
    self.assertEqual(cli.exit_status([good], interrupted=True), 130)
    with open(bad.logfile) as stream:
      self.assertIn('FAILED (failures=1, errors=1)', stream.read())
    text = report.summary(sched.jobs, sched.wall)
    self.assertIn('2 of 2 run, 1 failed', text)
    self.assertRegex(text, r'bad\.py\s+py\s+3\s+2\s+[\d.]+ s\s+\d+\s+FAILED')

  def test_advisory_job(self):
    '''
    An advisory job that exits with a nonzero status is incomplete, not
    failed: it has no say in the exit status, and the summary counts it in
    a clause of its own.
    '''
    good = self.pyjob('good.py', 'import sys; sys.stderr.write(%r)' % OK_OUTPUT)
    advice = Job(
        'prepare x', 'py', [PYTHON, '-c', 'import sys; sys.exit(1)'], cap=GIB
      , timeout=None, logfile=os.path.join(self.logdir, 'prepare-x.log')
      , advisory=True
      )
    sched = self.run_jobs([advice, good])
    self.assertEqual(advice.status, 'incomplete')
    self.assertEqual(advice.note, 'exit status 1')
    self.assertFalse(advice.ok)
    self.assertTrue(advice.completed)
    self.assertEqual(good.status, 'ok')
    self.assertEqual(cli.exit_status([advice, good]), 0)
    self.assertEqual(cli.exit_status([advice, good], interrupted=True), 130)
    line = report.format_status(advice)
    self.assertIn('incomplete', line)
    self.assertIn('prepare-x.log', line)
    text = report.summary(sched.jobs, sched.wall)
    self.assertIn('1 of 1 run, 0 failed, prepare: 1 of 1 incomplete', text)
    self.assertRegex(
        text, r'prepare x\s+py\s+-\s+-\s+[\d.]+ s\s+\d+\s+incomplete'
      )
    # Every advisory job passed: no clause.
    ok = Job(
        'prepare y', 'py', ['true'], cap=GIB, timeout=None, logfile=None
      , advisory=True
      )
    sched = self.run_jobs([ok, good])
    self.assertEqual(ok.status, 'ok')
    self.assertNotIn('prepare', report.summary(sched.jobs).splitlines()[-1])

  def test_exit_status_without_a_verdict(self):
    job = self.pyjob('exit.py', 'import sys; sys.exit(3)')
    self.run_jobs([job])
    self.assertEqual(job.status, 'FAILED')
    self.assertIsNone(job.tests)
    self.assertEqual(job.note, 'exit status 3')

  def test_crash(self):
    job = self.pyjob(
        'crash.py', 'import os, signal; os.kill(os.getpid(), signal.SIGSEGV)'
      )
    self.run_jobs([job])
    self.assertEqual(job.status, 'crashed')
    self.assertEqual(job.note, 'signal %d' % signal.SIGSEGV)
    self.assertFalse(job.completed)

  def test_watchdog_kills_a_file_over_its_cap(self):
    code = 'import time\nblock = b"x" * (200 * 1024 * 1024)\ntime.sleep(30)\n'
    job = self.pyjob('hog.py', code, cap=64 * MIB)
    start = time.monotonic()
    self.run_jobs([job])
    self.assertEqual(job.status, 'killed: memory')
    self.assertIn('cap 64 MB', job.note)
    self.assertGreater(job.peak, 64 * MIB)
    self.assertLess(time.monotonic() - start, 15)
    self.assertFalse(job.completed)
    self.assertIn('killed: memory', report.format_status(job))
    self.assertIn('hog.py.log', report.format_status(job))

  def toolchain_stub(self, name):
    '''
    A link to the interpreter under ``name``, so that a process started
    through it has that command name in /proc.
    '''
    path = os.path.join(self.logdir, name)
    os.symlink(PYTHON, path)
    return path

  # A child that starts a memory hog through a link and waits for it.
  HOG_THROUGH = (
      'import subprocess, sys\n'
      'subprocess.run([%r, "-c", "import time; b = b\'x\' * (200 << 20); '
      'time.sleep(%g)"])\n'
    )

  def test_toolchain_allowance(self):
    '''
    A session over the cap of its file is not killed while a process of the
    Curry toolchain runs in it and the sum stays within the allowance; the
    job notes the allowance and keeps the names of the tools it saw.  Over
    the allowance, the session is killed.
    '''
    tool = self.toolchain_stub('cc1plus')
    code = self.HOG_THROUGH % (tool, 1.5)
    job = self.pyjob('compiles.py', code, cap=64 * MIB)
    self.run_jobs([job], tool_cap=400 * MIB)
    self.assertEqual(job.status, 'ok', job.note)
    self.assertEqual(job.tools, {'cc1plus'})
    self.assertGreater(job.peak, 200 * MIB)
    self.assertEqual(job.note, 'over cap 64 MB while cc1plus ran')
    self.assertIn('while cc1plus ran', report.format_status(job))
    job = self.pyjob('compiles.py', self.HOG_THROUGH % (tool, 30), cap=64 * MIB)
    start = time.monotonic()
    self.run_jobs([job], tool_cap=100 * MIB)
    self.assertEqual(job.status, 'killed: memory')
    self.assertLess(time.monotonic() - start, 15)
    self.assertRegex(job.note, r'^\d+ MB > cap 100 MB with cc1plus running$')
    self.assertEqual(job.tools, {'cc1plus'})
    # A hog that is not a tool gets no allowance (the test above this one),
    # and a tool gets none when the scheduler runs without one.
    job = self.pyjob('compiles.py', self.HOG_THROUGH % (tool, 30), cap=64 * MIB)
    self.run_jobs([job], tool_cap=None)
    self.assertEqual(job.status, 'killed: memory')
    self.assertEqual(job.note, '%d MB > cap 64 MB' % round(job.peak / MIB))

  def test_timeout_kills_the_whole_session(self):
    # The child starts a grandchild in a new process group, as the timeout
    # command does, and sleeps.  The kill must reach the grandchild.
    code = (
        'import subprocess, sys, time\n'
        'child = subprocess.Popen(["sleep", "60"], process_group=0)\n'
        'sys.stdout.write("grandchild %d\\n" % child.pid)\n'
        'sys.stdout.flush()\n'
        'time.sleep(60)\n'
      )
    job = self.pyjob('slow.py', code, timeout=1)
    start = time.monotonic()
    self.run_jobs([job])
    self.assertEqual(job.status, 'killed: timeout')
    self.assertLess(time.monotonic() - start, 15)
    with open(job.logfile) as stream:
      match = re.search(r'grandchild (\d+)', stream.read())
    self.assertIsNotNone(match)
    grandchild = int(match.group(1))
    deadline = time.monotonic() + 5
    while procs.is_alive(grandchild) and time.monotonic() < deadline:
      time.sleep(0.05)
    self.assertFalse(procs.is_alive(grandchild))

  # A child that starts a session of its own, as the benchmark harness and
  # func_complete.py do, and sleeps.  Its session id is its own pid, so the
  # session match alone would miss it.
  SETSID_CHILD = (
      'import subprocess, sys, time\n'
      'child = subprocess.Popen(%s, start_new_session=True)\n'
      'sys.stdout.write("grandchild %%d\\n" %% child.pid)\n'
      'sys.stdout.flush()\n'
    )

  def grandchild_of(self, job):
    with open(job.logfile) as stream:
      match = re.search(r'grandchild (\d+)', stream.read())
    self.assertIsNotNone(match)
    return int(match.group(1))

  def assertDeadSoon(self, pid):
    deadline = time.monotonic() + 5
    while procs.is_alive(pid) and time.monotonic() < deadline:
      time.sleep(0.05)
    self.assertFalse(procs.is_alive(pid))

  def test_kill_reaches_a_child_in_its_own_session(self):
    code = self.SETSID_CHILD % '["sleep", "60"]' + 'time.sleep(60)\n'
    job = self.pyjob('setsid.py', code, timeout=1)
    self.run_jobs([job])
    self.assertEqual(job.status, 'killed: timeout')
    self.assertDeadSoon(self.grandchild_of(job))

  def test_memory_of_a_child_in_its_own_session_counts(self):
    hog = '["%s", "-c", "%s"]' % (
        PYTHON, "import time; b = b'x' * (200 << 20); time.sleep(60)"
      )
    code = self.SETSID_CHILD % hog + 'time.sleep(60)\n'
    job = self.pyjob('setsid-hog.py', code, cap=64 * MIB)
    self.run_jobs([job])
    self.assertEqual(job.status, 'killed: memory')
    self.assertGreater(job.peak, 64 * MIB)
    self.assertDeadSoon(self.grandchild_of(job))

  def test_orphan_in_its_own_session_dies_with_the_file(self):
    # The child starts a grandchild in a new session, lives long enough
    # for a poll to see it, and exits.  The grandchild loses its parent and
    # its session has no leader; the sweep after the file still finds it.
    code = self.SETSID_CHILD % '["sleep", "60"]' + 'time.sleep(0.6)\n'
    job = self.pyjob('orphan.py', code)
    self.run_jobs([job])
    self.assertEqual(job.status, 'ok')
    grandchild = self.grandchild_of(job)
    self.assertIn(grandchild, job.members)
    self.assertDeadSoon(grandchild)

  def test_scan_walks_the_parent_links(self):
    child = subprocess.Popen(
        [ PYTHON, '-c'
        , self.SETSID_CHILD % '["sleep", "60"]' + 'time.sleep(60)\n'
        ]
      , stdout=subprocess.PIPE, start_new_session=True
      )
    grandchild = None
    try:
      line = child.stdout.readline().decode()
      grandchild = int(line.split()[1])
      _, pids, comms = procs.scan_sessions([child.pid])[child.pid]
      self.assertIn(child.pid, pids)
      self.assertIn(grandchild, pids)
      self.assertEqual(sorted(comms), pids)
      self.assertEqual(comms[grandchild], 'sleep')
      self.assertNotEqual(os.getsid(grandchild), child.pid)
      # The leader gone, the roots of the last scan still find the rest.
      child.kill()
      child.wait()
      _, pids, _ = procs.scan_sessions([child.pid])[child.pid]
      self.assertNotIn(grandchild, pids)
      found = procs.scan_sessions([child.pid], roots={child.pid: [grandchild]})
      _, pids, _ = found[child.pid]
      self.assertIn(grandchild, pids)
      procs.kill_session(child.pid, roots=[grandchild])
      self.assertDeadSoon(grandchild)
    finally:
      roots = [] if grandchild is None else [grandchild]
      procs.kill_session(child.pid, roots=roots)
      child.stdout.close()

  def test_width_two_runs_two_at_once(self):
    jobs = [
        self.pyjob('s%d.py' % i, 'import time; time.sleep(1)') for i in range(2)
      ]
    sched = self.run_jobs(jobs, width=2)
    self.assertLess(sched.wall, 1.9)
    self.assertTrue(all(job.ok for job in jobs))
    jobs = [
        self.pyjob('t%d.py' % i, 'import time; time.sleep(1)') for i in range(2)
      ]
    sched = self.run_jobs(jobs, width=1)
    self.assertGreater(sched.wall, 1.9)

  def test_budget_serializes_two_big_files(self):
    jobs = [
        self.pyjob('b%d.py' % i, 'import time; time.sleep(1)', cap=3 * GIB)
        for i in range(2)
      ]
    sched = self.run_jobs(jobs, width=2, budget=4 * GIB)
    self.assertGreater(sched.wall, 1.9)

  def test_interrupt_kills_and_reports(self):
    running = self.pyjob('long.py', 'import time; time.sleep(60)')
    waiting = self.pyjob('wait.py', 'pass')
    before = {sig: signal.getsignal(sig) for sig in INTERRUPT_SIGNALS}
    # Two interrupts: the second lands during the final reap and changes
    # nothing.
    timers = [
        threading.Timer(delay, os.kill, args=(os.getpid(), signal.SIGINT))
        for delay in (0.5, 0.7)
      ]
    for timer in timers:
      timer.start()
    try:
      sched = self.run_jobs([running, waiting], width=1)
    finally:
      for timer in timers:
        timer.cancel()
    self.assertTrue(sched.interrupted)
    self.assertEqual(sched.interrupt_requested, signal.SIGINT)
    self.assertEqual(running.status, 'killed: interrupted')
    self.assertEqual(waiting.status, 'not run')
    self.assertFalse(procs.is_alive(running.pid))
    text = report.summary(sched.jobs, sched.wall, interrupted=True)
    self.assertIn('1 not run', text)
    self.assertIn('interrupted', text)
    self.assertEqual(cli.exit_status(sched.jobs, interrupted=True), 130)
    # The handlers of the run are gone with it.
    for sig in INTERRUPT_SIGNALS:
      self.assertIs(signal.getsignal(sig), before[sig])

  def test_hangup_and_term_end_the_run(self):
    for sig in (signal.SIGHUP, signal.SIGTERM):
      running = self.pyjob('long.py', 'import time; time.sleep(60)')
      timer = threading.Timer(0.3, os.kill, args=(os.getpid(), sig))
      timer.start()
      try:
        sched = self.run_jobs([running], width=1)
      finally:
        timer.cancel()
      self.assertTrue(sched.interrupted)
      self.assertEqual(sched.interrupt_requested, sig)
      self.assertEqual(running.status, 'killed: interrupted')
      self.assertFalse(procs.is_alive(running.pid))

  def test_interrupt_requested_before_the_start(self):
    # A flag set before the loop turns: nothing starts, nothing is lost.
    job = self.pyjob('never.py', 'import time; time.sleep(60)')
    sched = Scheduler([job], 16 * GIB, 1, poll=POLL)
    sched.interrupt_requested = signal.SIGTERM
    sched.run()
    self.assertTrue(sched.interrupted)
    self.assertEqual(job.status, 'not run')
    self.assertIsNone(job.pid)

  def test_echo_copies_the_output(self):
    job = self.pyjob('echo.py', 'print("hello from the child")')
    buffer = io.TextIOWrapper(io.BytesIO(), encoding='utf-8')
    saved = sys.stdout
    sys.stdout = buffer
    try:
      self.run_jobs([job], echo=True)
    finally:
      sys.stdout = saved
    buffer.flush()
    self.assertIn(b'hello from the child', buffer.buffer.getvalue())
    with open(job.logfile) as stream:
      self.assertIn('hello from the child', stream.read())

  def test_missing_command(self):
    job = Job(
        'none.py', 'py', ['/nonexistent/program'], cap=GIB, timeout=None
      , logfile=os.path.join(self.logdir, 'none.log')
      )
    self.run_jobs([job])
    self.assertEqual(job.status, 'error')
    self.assertTrue(job.finished)


class TestProcs(unittest.TestCase):

  def test_meminfo(self):
    info = procs.meminfo()
    self.assertGreater(info['MemTotal'], 0)
    self.assertGreater(procs.mem_available(), 0)
    self.assertGreaterEqual(procs.cpu_count(), 1)

  def test_scan_finds_this_session(self):
    sid = os.getsid(0)
    rss, pids, comms = procs.scan_sessions([sid])[sid]
    self.assertIn(os.getpid(), pids)
    self.assertGreater(rss, 0)
    self.assertTrue(procs.is_alive(os.getpid()))
    with open('/proc/self/comm') as stream:
      self.assertEqual(comms[os.getpid()], stream.read().strip())

  def test_toolchain_in(self):
    self.assertEqual(procs.toolchain_in([]), [])
    self.assertEqual(procs.toolchain_in(['python', 'sh']), [])
    self.assertEqual(
        procs.toolchain_in(['python', 'swipl', 'cc1plus', 'swipl'])
      , ['cc1plus', 'swipl']
      )
    for name in 'swipl', 'curry-frontend', 'pakcs-frontend', 'cc1plus', 'ld':
      self.assertIn(name, procs.TOOLS)
    self.assertNotIn('python', procs.TOOLS)


class TestManifest(unittest.TestCase):

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
    self.path = os.path.join(self.tmpdir, 'manifest.json')

  def test_round_trip(self):
    manifest = Manifest(path=self.path)
    size = {'measured_on_cores': 4, 'measured_on_mem_gb': 16}
    manifest.update(
        'a.py', 'py', FakeResult(12.34, 300 * MIB, tests=7, failures=1), size
      )
    manifest.update('a.py', 'cxx', FakeResult(5.0, 100 * MIB), size)
    manifest.save()
    loaded = Manifest.load(self.path)
    entry = loaded.entry('a.py', 'py')
    self.assertEqual(entry['duration_s'], 12.3)
    self.assertEqual(entry['peak_rss_mb'], 300)
    self.assertEqual((entry['tests'], entry['failures']), (7, 1))
    self.assertEqual(entry['measured_on_cores'], 4)
    self.assertEqual(entry['measured_on_mem_gb'], 16)
    self.assertEqual(loaded.duration('a.py', 'cxx'), 5.0)
    self.assertIsNone(loaded.entry('b.py', 'py'))
    with open(self.path) as stream:
      data = json.load(stream)
    self.assertEqual(data['format'], FORMAT)
    self.assertEqual(sorted(data), ['files', 'format'])

  def test_caps(self):
    manifest = Manifest({
        'small.py': {'py': {'duration_s': 1, 'peak_rss_mb': 100}}
      , 'mid.py': {'py': {'duration_s': 1, 'peak_rss_mb': 600}}
      , 'big.py': {'py': {'duration_s': 1, 'peak_rss_mb': 1024}}
      , 'nopeak.py': {'py': {'duration_s': 1, 'peak_rss_mb': None}}
      })
    # The floor is 1 GB: it covers the toolchain inside the test process
    # on a cold tree.  The allowance of the external tools is 2 GB.
    self.assertEqual(testrunner.MIN_CAP, GIB)
    self.assertEqual(testrunner.TOOL_CAP, 2 * GIB)
    self.assertEqual(manifest.cap('small.py', 'py'), testrunner.MIN_CAP)
    self.assertEqual(manifest.cap('mid.py', 'py'), 1200 * MIB)
    self.assertEqual(manifest.cap('big.py', 'py'), 2 * GIB)
    self.assertEqual(manifest.cap('nopeak.py', 'py'), testrunner.DEFAULT_CAP)
    self.assertEqual(manifest.cap('missing.py', 'py'), testrunner.DEFAULT_CAP)
    self.assertEqual(manifest.cap('small.py', 'cxx'), testrunner.DEFAULT_CAP)

  def test_peak_only_grows_and_a_kill_keeps_the_duration(self):
    manifest = Manifest()
    size = {'measured_on_cores': 1, 'measured_on_mem_gb': 1}
    manifest.update('a.py', 'py', FakeResult(10.0, 500 * MIB), size)
    manifest.update('a.py', 'py', FakeResult(20.0, 200 * MIB), size)
    entry = manifest.entry('a.py', 'py')
    self.assertEqual((entry['duration_s'], entry['peak_rss_mb']), (20.0, 500))
    manifest.update(
        'a.py', 'py', FakeResult(3.0, 900 * MIB, completed=False), size
      )
    entry = manifest.entry('a.py', 'py')
    self.assertEqual((entry['duration_s'], entry['peak_rss_mb']), (20.0, 900))
    # A run that ended by itself without a verdict (an ImportError, say)
    # measured nothing whole either: the duration stays.
    manifest.update(
        'a.py', 'py', FakeResult(0.5, 950 * MIB, tests=None, failures=None), size
      )
    entry = manifest.entry('a.py', 'py')
    self.assertEqual((entry['duration_s'], entry['peak_rss_mb']), (20.0, 950))
    self.assertEqual(entry['tests'], 1)

  def test_missing_and_wrong_format(self):
    self.assertEqual(Manifest.load(self.path).files, {})
    with open(self.path, 'w') as stream:
      json.dump({'format': FORMAT + 1, 'files': {}}, stream)
    self.assertRaises(ValueError, Manifest.load, self.path)

  def test_committed_manifest_loads(self):
    '''
    The shape of the committed manifest, not its numbers: a recalibration
    rewrites every number.  Every entry names a test file that exists and
    a known backend, holds fields of the format with values of the right
    kind, and the calibration has measured a duration and a peak on every
    backend (README, section 10).
    '''
    manifest = Manifest.load(testrunner.MANIFEST_FILE, missing_ok=False)
    files = set(selection.test_files())
    measured = {backend: 0 for backend in testrunner.BACKENDS}
    self.assertTrue(manifest.files)
    for name, entries in manifest.files.items():
      self.assertTrue(name.startswith(('unit_', 'func_')), name)
      self.assertIn(name, files)
      self.assertTrue(entries, name)
      for backend, entry in entries.items():
        self.assertIn(backend, testrunner.BACKENDS)
        self.assertLessEqual(set(entry), set(testrunner.manifest.FIELDS), name)
        for field in testrunner.manifest.FIELDS:
          value = entry.get(field)
          if value is None:
            continue
          self.assertIsInstance(value, (int, float), (name, field))
          self.assertNotIsInstance(value, bool, (name, field))
          self.assertGreaterEqual(value, 0, (name, field))
        duration, peak = entry.get('duration_s'), entry.get('peak_rss_mb')
        if duration is not None and peak is not None:
          measured[backend] += 1
          self.assertGreater(peak, 0, name)
          self.assertEqual(
              manifest.cap(name, backend)
            , max(testrunner.MIN_CAP, testrunner.CAP_FACTOR * peak * MIB)
            )
    for backend, count in measured.items():
      self.assertGreater(count, 0, backend)


FILES = sorted([
    'func_flat2icurry.py', 'func_kiel.py', 'func_math.py', 'unit_api.py'
  , 'unit_benchmarks.py', 'unit_cache.py', 'unit_compile.py'
  , 'unit_curry2icurry.py', 'unit_currylib.py', 'unit_cxx_gc.py'
  , 'unit_cxx_heap.py', 'unit_cxx_passthrough.py', 'unit_cxx_toolchain.py'
  , 'unit_cxx_variable.py', 'unit_expr.py'
  , 'unit_flat2icurry.py', 'unit_icurry.py', 'unit_inspect.py'
  , 'unit_loadsave.py', 'unit_optimize.py', 'unit_optimize_applies.py'
  , 'unit_plan.py', 'unit_prebuild.py', 'unit_product_cache.py'
  , 'unit_py_conversions.py', 'unit_py_evaluation.py', 'unit_py_io.py'
  , 'unit_utility.py'
  ])
CXX_FILES = [
    'unit_cxx_gc.py', 'unit_cxx_heap.py', 'unit_cxx_passthrough.py'
  , 'unit_cxx_toolchain.py', 'unit_cxx_variable.py'
  ]
TOOLCHAIN_FILES = [
    'func_flat2icurry.py', 'unit_cache.py', 'unit_compile.py'
  , 'unit_curry2icurry.py', 'unit_cxx_toolchain.py', 'unit_flat2icurry.py'
  , 'unit_product_cache.py'
  ]
API_FILES = [
    'unit_api.py', 'unit_expr.py', 'unit_py_conversions.py'
  , 'unit_py_evaluation.py'
  ]

def with_(names, *extra):
  return sorted(names + list(extra))

class TestSelection(unittest.TestCase):

  def test_test_files(self):
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    names = ['unit_b.py', 'func_a.py', 'unit_a.py', 'helper.py', 'unit_x.pyc']
    for name in names:
      with open(os.path.join(tmpdir, name), 'w'):
        pass
    self.assertEqual(
        selection.test_files(tmpdir), ['func_a.py', 'unit_a.py', 'unit_b.py']
      )
    self.assertIn('unit_runner.py', selection.test_files())

  def test_patterns(self):
    self.assertEqual(selection.match_patterns(FILES, []), FILES)
    self.assertEqual(selection.match_patterns(FILES, ['unit_cxx_*.py']), CXX_FILES)
    self.assertEqual(
        selection.match_patterns(FILES, ['unit_api.py', 'func_*'])
      , ['func_flat2icurry.py', 'func_kiel.py', 'func_math.py', 'unit_api.py']
      )
    self.assertEqual(selection.match_patterns(FILES, ['nothing']), [])

  def selected(self, paths):
    selected, notes = selection.select_changed(paths, FILES)
    return [item.filename for item in selected], selected, notes

  def test_rules(self):
    names, _, notes = self.selected(['src/cyrt/graph/node.cpp'])
    self.assertEqual(names, CXX_FILES)
    self.assertEqual(len(notes), 1)
    self.assertIn('the C++ runtime', notes[0])
    names, _, _ = self.selected(['src/python/backends/cxx/compiler.py'])
    self.assertEqual(names, CXX_FILES)
    names, _, _ = self.selected(['src/python/backends/py/eval/rts.py'])
    self.assertEqual(
        names, ['unit_py_conversions.py', 'unit_py_evaluation.py', 'unit_py_io.py']
      )
    names, _, _ = self.selected(['src/python/toolchain/_frontend.py'])
    self.assertEqual(names, with_(TOOLCHAIN_FILES, 'unit_plan.py'))
    names, _, _ = self.selected(['src/python/toolchain/plans.py'])
    self.assertIn('unit_plan.py', names)
    names, _, _ = self.selected(['curry/lib/Prelude.curry'])
    self.assertEqual(
        names, with_(TOOLCHAIN_FILES, 'unit_currylib.py', 'unit_prebuild.py')
      )
    names, _, _ = self.selected(['curry/Makefile'])
    self.assertIn('unit_prebuild.py', names)
    names, _, _ = self.selected(['src/python/icurry/json.py'])
    self.assertEqual(names, with_(TOOLCHAIN_FILES, 'unit_icurry.py'))
    names, _, _ = self.selected(['src/python/expressions.py'])
    self.assertEqual(names, API_FILES)
    names, _, _ = self.selected(['src/python/interpreter/eval.py'])
    self.assertEqual(names, with_(API_FILES, 'unit_loadsave.py'))
    names, _, _ = self.selected(['src/python/interpreter/optimize.py'])
    self.assertEqual(
        names, with_(API_FILES, 'unit_optimize.py', 'unit_optimize_applies.py')
      )
    names, _, _ = self.selected(['src/python/icurry/analysis/partials.py'])
    self.assertEqual(
        names
      , ['unit_icurry.py', 'unit_optimize.py', 'unit_optimize_applies.py']
      )
    names, _, _ = self.selected(['src/python/interpreter/loadsave.py'])
    self.assertIn('unit_loadsave.py', names)
    names, _, _ = self.selected(['src/python/inspect/__init__.py'])
    self.assertEqual(names, with_(API_FILES, 'unit_inspect.py'))

  def test_test_files_and_corpus(self):
    names, _, _ = self.selected(['tests/unit_expr.py'])
    self.assertEqual(names, ['unit_expr.py'])
    names, _, _ = self.selected(
        ['tests/func_kiel.py', 'tests/data/curry/math/foo.curry']
      )
    self.assertEqual(names, ['func_kiel.py', 'func_math.py'])
    # A corpus without a functional test of its own.
    names, _, notes = self.selected(['tests/data/curry/benchmarks/Hello.curry'])
    self.assertEqual(
        names
      , [ 'unit_benchmarks.py', 'unit_cxx_heap.py', 'unit_cxx_passthrough.py'
        , 'unit_cxx_variable.py'
        ]
      )
    self.assertIn('the benchmark programs', notes[0])
    names, _, _ = self.selected(['tests/data/curry/flat2icurry/Probe.curry'])
    self.assertEqual(
        names
      , ['func_flat2icurry.py', 'unit_curry2icurry.py', 'unit_flat2icurry.py']
      )
    # A module of the shared pool selects the test files that name it or a
    # module of the pool that imports it, with the check of the products of
    # the pool; a module that no test file names selects everything (issue
    # #99).
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    texts = {
        'unit_api.py': "M = curry.import_('Peano')\n"
      , 'unit_expr.py': "import PeanoExtra\n# the Peano-style numbers\n"
      , 'unit_inspect.py': "x = M.Peano.S\n"
      , 'unit_cache.py': "name = 'hello'\n"
      , 'unit_loadsave.py': "M = curry.import_('Deep')\n"
      }
    for name, text in texts.items():
      with open(os.path.join(tmpdir, name), 'w', encoding='utf-8') as stream:
        stream.write(text)
    self.assertEqual(
        selection.files_naming('Peano', FILES, tmpdir)
      , ['unit_api.py', 'unit_expr.py']
      )
    # The pool: Deep imports PeanoUser, which imports Peano; Other imports
    # Prelude alone, and Lone is imported by nobody.
    pool = os.path.join(tmpdir, 'pool')
    os.mkdir(pool)
    modules = {
        'Peano': 'module Peano where\ndata Nat = O | S Nat\n'
      , 'PeanoUser': 'module PeanoUser where\nimport qualified Peano\nx = 1\n'
      , 'Deep': 'module Deep where\nimport PeanoUser (x)\nimport Lone as L\n'
      , 'Other': 'import Prelude hiding (not)\ny = 2\n'
      , 'Lone': 'z = 3\n'
      }
    for name, text in modules.items():
      with open(os.path.join(pool, name + '.curry'), 'w', encoding='utf-8') as stream:
        stream.write(text)
    self.assertEqual(selection.pool_importers('Peano', pool), ['Deep', 'PeanoUser'])
    self.assertEqual(selection.pool_importers('Lone', pool), ['Deep'])
    self.assertEqual(selection.pool_importers('Deep', pool), [])
    self.assertEqual(selection.pool_importers('Peano', os.path.join(pool, 'none')), [])
    self.assertEqual(selection.POOL_CHECKS, ['func_flat2icurry.py'])
    # Peano is named by two files; Deep, an importer through PeanoUser, by a
    # third; the check of the products joins them.
    selected, notes = selection.select_changed(
        ['tests/data/curry/Peano.curry'], FILES, testdir=tmpdir, pooldir=pool
      )
    self.assertEqual(
        [item.filename for item in selected]
      , ['func_flat2icurry.py', 'unit_api.py', 'unit_expr.py', 'unit_loadsave.py']
      )
    self.assertEqual(
        notes
      , [ 'tests/data/curry/Peano.curry: the test files that name the module'
          ' or an importer (Deep PeanoUser) -> func_flat2icurry.py unit_api.py'
          ' unit_expr.py unit_loadsave.py'
        ]
      )
    self.assertEqual(
        selected[0].reasons
      , ['the check of the products of the pool (tests/data/curry/Peano.curry)']
      )
    self.assertEqual(
        selected[1].reasons
      , [ 'the test files that name the module or an importer (Deep PeanoUser)'
          ' (tests/data/curry/Peano.curry)'
        ]
      )
    self.assertEqual(selected[3].reasons, selected[1].reasons)
    # A module without an importer: the files that name it and the check.
    selected, notes = selection.select_changed(
        ['tests/data/curry/Deep.curry'], FILES, testdir=tmpdir, pooldir=pool
      )
    self.assertEqual(
        [item.filename for item in selected]
      , ['func_flat2icurry.py', 'unit_loadsave.py']
      )
    self.assertEqual(
        notes
      , [ 'tests/data/curry/Deep.curry: the test files that name the module'
          ' -> func_flat2icurry.py unit_loadsave.py'
        ]
      )
    self.assertIn(
        'the test files that name the module (tests/data/curry/Deep.curry)'
      , selected[1].reasons
      )
    # An importer that no test file names adds nothing; a module that
    # nobody names, with or without importers, selects everything.
    selected, notes = selection.select_changed(
        ['tests/data/curry/Lone.curry'], FILES, testdir=tmpdir, pooldir=pool
      )
    self.assertEqual(
        [item.filename for item in selected]
      , ['func_flat2icurry.py', 'unit_loadsave.py']
      )
    selected, notes = selection.select_changed(
        ['tests/data/curry/Other.curry'], FILES, testdir=tmpdir, pooldir=pool
      )
    self.assertEqual([item.filename for item in selected], FILES)
    self.assertIn('no test file names the module Other; selects everything', notes[0])
    selected, notes = selection.select_changed(
        ['tests/data/curry/Nobody.curry'], FILES, testdir=tmpdir, pooldir=pool
      )
    self.assertEqual([item.filename for item in selected], FILES)
    self.assertEqual(
        notes
      , [ 'tests/data/curry/Nobody.curry: no test file names the module '
          'Nobody; selects everything'
        ]
      )
    self.assertIn(
        'no test file names the module Nobody of tests/data/curry/Nobody.curry'
      , selected[0].reasons
      )
    # The real pool: the test of the C++ interpreter names its module, and
    # FunPatFreeArgSet imports FunPatFreeArg.
    self.assertIn(
        'unit_cxx_interp.py'
      , selection.files_naming('CxxInterp', selection.test_files())
      )
    self.assertIn('FunPatFreeArgSet', selection.pool_importers('FunPatFreeArg'))
    # A rule whose globs match no file: the policy for the unknown.
    names, selected, notes = self.selected(['tests/data/curry/nosuch/x.curry'])
    self.assertEqual(names, FILES)
    self.assertIn(
        'no test file matches func_nosuch*.py; selects everything', notes[0]
      )
    self.assertIn(
        'no test file matches func_nosuch*.py for '
        'tests/data/curry/nosuch/x.curry'
      , selected[0].reasons
      )
    names, _, _ = self.selected(['tests/unit_gone.py'])
    self.assertEqual(names, FILES)
    # The setup script and its environment file.
    selected, _ = selection.select_changed(
        ['scripts/setup-dev-machine.sh', 'conda/dev-environment.yml']
      , FILES + ['unit_setup_script.py', 'unit_conda.py']
      )
    self.assertEqual(
        [item.filename for item in selected], ['unit_setup_script.py']
      )

  def test_harness_and_unknown_select_everything(self):
    names, selected, notes = self.selected(['tests/lib/cytest/__init__.py'])
    self.assertEqual(names, FILES)
    self.assertIn(
        'the test harness (tests/lib/cytest/__init__.py)', selected[0].reasons
      )
    self.assertIn('everything (%d files)' % len(FILES), notes[0])
    files = FILES + ['unit_runner.py', 'unit_conda.py', 'unit_examples.py']
    selected, _ = selection.select_changed(
        ['tests/lib/benchmarks/run.py', 'tests/lib/testrunner/cli.py'], files
      )
    self.assertEqual(
        [item.filename for item in selected], ['unit_benchmarks.py', 'unit_runner.py']
      )
    selected, _ = selection.select_changed(
        ['conda/meta.yaml', 'examples/01-run-with-python/run'], files
      )
    self.assertEqual(
        [item.filename for item in selected], ['unit_conda.py', 'unit_examples.py']
      )
    names, selected, notes = self.selected(['Makefile'])
    self.assertEqual(names, FILES)
    self.assertIn('unknown', notes[0])
    self.assertIn('an unknown path changed: Makefile', selected[0].reasons)

  def test_ignored_paths(self):
    paths = [
        'docs/source/index.rst', 'README.md', 'TODO', '.github/workflows/ci.yml'
      , 'tests/README', 'tests/manifest.json'
      ]
    for path in paths:
      names, _, notes = self.selected([path])
      self.assertEqual(names, [], path)
      self.assertIn('selects nothing', notes[0])

  def test_reasons_accumulate(self):
    _, selected, _ = self.selected(
        ['src/cyrt/a.cpp', 'src/python/backends/cxx/b.py']
      )
    gc = [item for item in selected if item.filename == 'unit_cxx_gc.py'][0]
    self.assertEqual(len(gc.reasons), 2)

  def test_fast_tier(self):
    manifest = Manifest({
        'unit_api.py': {'py': {'duration_s': 2.0}, 'cxx': {'duration_s': 9.0}}
      , 'unit_compile.py': {'py': {'duration_s': 146}, 'cxx': {'duration_s': 150}}
      , 'unit_expr.py': {'py': {'duration_s': 4.9}}
      })
    files = ['unit_api.py', 'unit_compile.py', 'unit_expr.py', 'unit_new.py']
    self.assertEqual(
        selection.fast_tier(files, ['py'], manifest, 5.0)
      , ['unit_api.py', 'unit_expr.py', 'unit_new.py']
      )
    self.assertEqual(
        selection.fast_tier(files, ['cxx'], manifest, 5.0)
      , ['unit_expr.py', 'unit_new.py']
      )
    # Both backends: a file must be fast on every backend of the run; a
    # backend without an entry counts as fast.
    self.assertEqual(
        selection.fast_tier(files, ['py', 'cxx'], manifest, 5.0)
      , ['unit_expr.py', 'unit_new.py']
      )
    self.assertEqual(
        selection.fast_tier(files, ['py'], manifest, 1.0), ['unit_new.py']
      )

  def test_fast_tier_leaves_out_the_corpus_owners(self):
    '''
    A functional test, and a file that CORPUS names, compiles a corpus of
    its own on a cold tree; the manifest measures warm trees.  So it is not
    in the fast tier, however fast its entry, and whether it has one.
    '''
    manifest = Manifest({
        'func_math.py': {'py': {'duration_s': 2.0}, 'cxx': {'duration_s': 2.0}}
      , 'unit_cxx_variable.py':
          {'py': {'duration_s': 1.0}, 'cxx': {'duration_s': 1.0}}
      , 'unit_expr.py': {'py': {'duration_s': 0.5}, 'cxx': {'duration_s': 0.5}}
      })
    files = [
        'func_math.py', 'func_new.py', 'unit_benchmarks.py'
      , 'unit_cxx_variable.py', 'unit_expr.py', 'unit_new.py'
      ]
    for backends in ['py'], ['cxx'], ['py', 'cxx']:
      self.assertEqual(
          selection.fast_tier(files, backends, manifest, 5.0)
        , ['unit_expr.py', 'unit_new.py']
        )
    for name in (
        'func_math.py', 'func_new.py', 'unit_benchmarks.py'
      , 'unit_cxx_variable.py'
      ):
      self.assertTrue(selection.compiles_corpus(name), name)
    for name in 'unit_expr.py', 'unit_new.py', 'unit_func_parts.py':
      self.assertFalse(selection.compiles_corpus(name), name)
    # The owners come from CORPUS, and they exist.
    owners = prepare.corpus_owners()
    self.assertIn('unit_cxx_variable.py', owners)
    self.assertIn('unit_benchmarks.py', owners)
    self.assertEqual(owners, sorted(set(owners)))
    existing = set(selection.test_files())
    for name in owners:
      self.assertIn(name, existing)
      self.assertTrue(selection.compiles_corpus(name))
    # The committed manifest and the real files: no functional test and no
    # owner is in the fast tier, whatever the threshold.
    tier = selection.fast_tier(
        sorted(existing), list(testrunner.BACKENDS)
      , Manifest.load(testrunner.MANIFEST_FILE), 10 ** 6
      )
    self.assertTrue(tier)
    self.assertEqual([n for n in tier if selection.compiles_corpus(n)], [])
    self.assertEqual([n for n in tier if n.startswith('func_')], [])

  def test_exclusive_files_exist(self):
    files = set(selection.test_files())
    for name in selection.EXCLUSIVE:
      self.assertIn(name, files)

  def test_changed_paths_runs_git(self):
    try:
      paths = selection.changed_paths('HEAD')
    except RuntimeError as exc:
      self.skipTest(str(exc))
    self.assertIsInstance(paths, list)
    self.assertEqual(paths, sorted(set(paths)))


class TestReport(unittest.TestCase):

  def test_parse_unittest(self):
    counts = report.parse_unittest(OK_OUTPUT)
    self.assertEqual(
        counts, {'tests': 2, 'failures': 0, 'skipped': 1, 'verdict': 'OK'}
      )
    counts = report.parse_unittest(FAILED_OUTPUT)
    self.assertEqual(
        (counts['tests'], counts['failures'], counts['verdict']), (3, 2, 'FAILED')
      )
    counts = report.parse_unittest('Traceback (most recent call last):\nImportError: x\n')
    self.assertEqual(
        (counts['tests'], counts['failures'], counts['verdict']), (None, None, None)
      )
    counts = report.parse_unittest('Ran 1 test in 0.001s\n\nOK\n')
    self.assertEqual((counts['tests'], counts['failures']), (1, 0))

  def test_header_and_summary(self):
    jobs = [stubjob('a.py'), stubjob('b.py', backend='cxx')]
    text = report.header(
        jobs, 2, 8 * GIB, 600, '/x/.cache/runner', available=16 * GIB
      )
    self.assertIn(
        '2 files on cxx+py, width 2, budget 8.0 GB (of 16.0 GB available), '
        'timeout 600 s'
      , text
      )
    text = report.summary(jobs)
    self.assertIn('file', text.splitlines()[0])
    self.assertIn('0 of 2 run, 0 failed, 2 not run', text)

  def test_tail(self):
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    path = os.path.join(tmpdir, 'x.log')
    with open(path, 'w') as stream:
      stream.write('\n'.join(str(i) for i in range(100)))
    self.assertEqual(report.tail(path, 3), '97\n98\n99')
    self.assertEqual(report.tail(os.path.join(tmpdir, 'none.log')), '')


class TestCli(unittest.TestCase):

  def test_defaults(self):
    args = cli.parse_args([])
    self.assertEqual(args.jobs, testrunner.DEFAULT_JOBS)
    # The width without -j is auto since the calibration of the manifest.
    self.assertEqual(testrunner.DEFAULT_JOBS, 'auto')
    self.assertEqual(args.timeout, testrunner.DEFAULT_TIMEOUT)
    self.assertIsNone(args.fast)
    self.assertIsNone(args.changed)
    self.assertIsNone(args.backend)
    args = cli.parse_args(
        ['-j', 'auto', '--fast', '--changed', '--backend', 'both', 'unit_a.py']
      )
    self.assertEqual(args.jobs, 'auto')
    self.assertEqual(args.fast, testrunner.DEFAULT_FAST_SECONDS)
    self.assertEqual(args.changed, 'HEAD')
    self.assertEqual(args.pattern, ['unit_a.py'])
    args = cli.parse_args(['--fast', '2.5', '--changed', 'master', '-j', '3'])
    self.assertEqual((args.fast, args.changed, args.jobs), (2.5, 'master', 3))
    with redirect_stderr(io.StringIO()):
      self.assertRaises(SystemExit, cli.parse_args, ['-j', '0'])

  def test_default_width_may_be_auto(self):
    '''The help reads the default width, a count or 'auto'.'''
    for jobs in (1, 4, 'auto'):
      args = cli.parse_args([], jobs=jobs)
      self.assertEqual(args.jobs, jobs)
      text = cli.build_parser(jobs).format_help()
      self.assertIn('[default: %s]' % jobs, text)
      self.assertIn(
          'up to the core count' if jobs == 'auto' else '%s at a time' % jobs
        , cli.epilog(jobs)
        )
    args = cli.parse_args(['-j', '2'], jobs='auto')
    self.assertEqual(args.jobs, 2)

  def test_installed_backend(self):
    '''
    The backend of a run that names none: the default of the installation
    (sysconfig/default_backend, which configure --with-default-backend
    writes), else the constant of the runner.  The listing of such a run
    shows it.
    '''
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    home = stub_installation(tmpdir)
    self.assertEqual(cli.installed_backend(home), testrunner.DEFAULT_BACKEND)
    self.assertEqual(testrunner.DEFAULT_BACKEND, 'cxx')
    os.makedirs(os.path.join(home, 'sysconfig'))
    sysconfig = os.path.join(home, 'sysconfig', 'default_backend')
    for value, expected in [
        ('py\n', 'py'), ('cxx', 'cxx'), ('', testrunner.DEFAULT_BACKEND)
      , ('llvm\n', testrunner.DEFAULT_BACKEND)
      ]:
      with open(sysconfig, 'w') as stream:
        stream.write(value)
      self.assertEqual(cli.installed_backend(home), expected, value)
    env = {k: v for k, v in os.environ.items() if k != 'SPRITE_INTERPRETER_FLAGS'}
    env['SPRITE_HOME'] = home
    for value in 'py', 'cxx':
      with open(sysconfig, 'w') as stream:
        stream.write(value + '\n')
      out = io.StringIO()
      with mock.patch.dict(os.environ, env, clear=True), redirect_stdout(out):
        status = cli.main(['--list', 'unit_runner.py'])
      self.assertEqual(status, 0)
      self.assertRegex(out.getvalue(), r'(?m)^%s\s+unit_runner\.py' % value)
      # The flag wins over the installation.
      env['SPRITE_INTERPRETER_FLAGS'] = 'backend:' + ('cxx' if value == 'py' else 'py')
      out = io.StringIO()
      with mock.patch.dict(os.environ, env, clear=True), redirect_stdout(out):
        status = cli.main(['--list', 'unit_runner.py'])
      del env['SPRITE_INTERPRETER_FLAGS']
      self.assertEqual(status, 0)
      self.assertNotRegex(out.getvalue(), r'(?m)^%s\s+unit_runner\.py' % value)
    # The real installation records a backend.
    sprite_home = os.environ.get('SPRITE_HOME')
    if sprite_home:
      self.assertIn(cli.installed_backend(sprite_home), testrunner.BACKENDS)

  def test_flags(self):
    self.assertEqual(cli.flag_backend('backend:cxx'), 'cxx')
    self.assertEqual(cli.flag_backend('debug:1,backend:py'), 'py')
    self.assertIsNone(cli.flag_backend(None))
    self.assertEqual(
        cli.with_backend('debug:1,backend:py', 'cxx'), 'backend:cxx,debug:1'
      )
    self.assertEqual(cli.with_backend('', 'py'), 'backend:py')

  def test_environment(self):
    base = {
        'PATH': '/bin', 'CURRYPATH': '/extra'
      , 'PYTHONPATH': testrunner.TESTDIR + '/lib/'
      }
    env = cli.environment('/sprite', 'cxx', base)
    self.assertEqual(env['SPRITE_HOME'], '/sprite')
    self.assertEqual(env['SPRITE_INTERPRETER_FLAGS'], 'backend:cxx')
    # The rotation of the C++ backend in step mode; a value of the
    # environment of the run wins.
    self.assertEqual(env['SPRITE_ROTATION'], 'steps:65536')
    self.assertNotIn('SPRITE_ROTATION', base)
    timed = cli.environment(
        '/sprite', 'cxx', dict(base, SPRITE_ROTATION='time:10ms')
      )
    self.assertEqual(timed['SPRITE_ROTATION'], 'time:10ms')
    # An empty value counts as unset.
    empty = cli.environment('/sprite', 'cxx', dict(base, SPRITE_ROTATION=''))
    self.assertEqual(empty['SPRITE_ROTATION'], 'steps:65536')
    self.assertEqual(
        env['CURRYPATH']
      , os.path.join(testrunner.TESTDIR, 'data', 'curry') + ':/extra'
      )
    # The lib directory is already on the path, under another spelling.
    self.assertEqual(env['PYTHONPATH'], testrunner.TESTDIR + '/lib/')
    self.assertEqual(
        env['SPRITE_CACHE_FILE']
      , os.path.join(testrunner.TESTDIR, '.cache', 'icurry.db')
      )
    self.assertNotIn('SPRITE_CACHE_FILE', base)
    # The product cache beside the ICurry cache; a value of the environment
    # of the run wins, the empty string included (it turns the cache off).
    self.assertEqual(
        env['SPRITE_PRODUCT_CACHE']
      , os.path.join(testrunner.TESTDIR, '.cache', 'products')
      )
    self.assertNotIn('SPRITE_PRODUCT_CACHE', base)
    shared = cli.environment(
        '/sprite', 'cxx', dict(base, SPRITE_PRODUCT_CACHE='/shared/products')
      )
    self.assertEqual(shared['SPRITE_PRODUCT_CACHE'], '/shared/products')
    off = cli.environment('/sprite', 'cxx', dict(base, SPRITE_PRODUCT_CACHE=''))
    self.assertEqual(off['SPRITE_PRODUCT_CACHE'], '')

  def test_backstop(self):
    self.assertEqual(cli.backstop_prefix(GIB, setting='unlimited'), [])
    prefix = cli.backstop_prefix(GIB, setting='1048576')
    if prefix:
      self.assertEqual(prefix, ['prlimit', '--as=%d' % GIB])
    prefix = cli.backstop_prefix(3 * GIB, setting='')
    if prefix:
      limit = int(prefix[1].split('=')[1])
      self.assertLessEqual(limit, 9 * GIB)
      self.assertGreater(limit, 0)

  def test_test_job(self):
    manifest = Manifest(
        {'unit_a.py': {'py': {'duration_s': 7, 'peak_rss_mb': 1000}}}
      )
    env = {'A': '1'}
    job = cli.test_job('unit_a.py', 'py', '/sprite', manifest, 60, '/logs', env)
    self.assertEqual(
        job.argv[-5:]
      , ['unittest', 'discover', '-v', testrunner.TESTDIR, 'unit_a.py']
      )
    self.assertIn('/sprite/bin/python', job.argv)
    self.assertEqual(job.cap, 2000 * MIB)
    self.assertEqual(job.hint, 7)
    self.assertEqual(job.logfile, '/logs/py/unit_a.py.log')
    self.assertEqual(job.cwd, testrunner.TESTDIR)
    self.assertIs(job.env, env)
    self.assertFalse(job.exclusive)
    job = cli.test_job(
        'unit_currylib.py', 'cxx', '/sprite', manifest, 60, '/logs', env
      )
    self.assertTrue(job.exclusive)
    self.assertEqual(job.cap, testrunner.DEFAULT_CAP)

  def test_list(self):
    out = io.StringIO()
    with redirect_stdout(out):
      status = cli.main(['--list', 'unit_runner.py', 'unit_currylib.py'])
    self.assertEqual(status, 0)
    text = out.getvalue()
    self.assertIn('unit_runner.py', text)
    self.assertIn('runs alone', text)
    out = io.StringIO()
    with redirect_stdout(out):
      status = cli.main(['--list', '--backend', 'both', 'unit_runner.py'])
    self.assertEqual(status, 0)
    self.assertRegex(out.getvalue(), r'cxx\s+unit_runner\.py')
    self.assertRegex(out.getvalue(), r'py\s+unit_runner\.py')

  def test_prepare_pass_is_advisory(self):
    '''
    A run with --prepare against a stand-in installation whose sprite-make
    fails every module: the pass ends incomplete, its line and the summary
    line name the modules without a product, the test file runs and
    passes, and the exit status is 0.  The stand-in python prints a passing
    unittest run, so no test runs here, and the stand-in sprite-make writes
    nothing into the tree.
    '''
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    home = stub_installation(os.path.join(tmpdir, 'install'))
    logdir = os.path.join(tmpdir, 'logs')
    manifest = os.path.join(tmpdir, 'manifest.json')
    Manifest({}, manifest).save()
    pool = prepare.modules('data/curry')
    self.assertTrue(pool)
    out = io.StringIO()
    environment = {'SPRITE_HOME': home, 'STUB_MAKE_FAIL': ''}
    with mock.patch.dict(os.environ, environment), redirect_stdout(out):
      status = cli.main([
          '--prepare', '--manifest', manifest, '--logdir', logdir
        , '--backend', 'cxx', 'unit_runner.py'
        ])
    text = out.getvalue()
    self.assertEqual(status, 0, text)
    lines = text.splitlines()
    # The pass: its line, then the summary line of the pass.
    passline = [
        line for line in lines
             if line.startswith('[') and 'prepare data/curry ' in line
      ]
    self.assertIn('incomplete', passline[0])
    self.assertEqual(len(passline), 1, text)
    self.assertIn(
        'exit status 1; %d of %d modules without a product: '
      % (len(pool), len(pool))
      , passline[0]
      )
    self.assertIn('prepare-data-curry.log', passline[0])
    summary = [line for line in lines if line.startswith('prepare: ')]
    self.assertEqual(len(summary), 1, text)
    self.assertTrue(
        summary[0].startswith(
            'prepare: %d modules in 1 directory on cxx; %d without a product: '
          % (len(pool), len(pool))
          )
      , summary[0]
      )
    self.assertIn('%s (cxx)' % pool[0], summary[0])
    self.assertTrue(summary[0].endswith('; the tests that need them report it'))
    # The test file ran after the pass and passed.
    self.assertRegex(text, r'ok\s+cxx\s+unit_runner\.py\s+2 tests')
    self.assertIn('1 of 1 run, 0 failed, prepare: 1 of 1 incomplete', text)
    self.assertRegex(
        text, r'prepare data/curry\s+cxx\s+-\s+-\s+[\d.]+ s\s+\d+\s+incomplete'
      )
    # The log of the pass holds the messages of the stand-in.
    with open(os.path.join(logdir, 'cxx', 'prepare-data-curry.log')) as stream:
      self.assertIn('stub-make: ', stream.read())
    pool_products = os.path.join(testrunner.TESTDIR, 'data', 'curry', '.curry')
    self.assertFalse(os.path.exists(os.path.join(pool_products, 'stub')))

  def test_nothing_selected(self):
    # A pattern that matches no file is a mistake, not an empty run.
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
      status = cli.main(['no_such_file.py'])
    self.assertEqual(status, 2)
    self.assertIn('no test file matches no_such_file.py', err.getvalue())
    with redirect_stdout(out), redirect_stderr(err):
      status = cli.main(['--list', 'unit_prelud.py'])
    self.assertEqual(status, 2)
    # A selection that the fast tier empties is a legitimate outcome.  The
    # manifest names both backends: the run takes the backend of the
    # environment, and a backend without an entry counts as fast.
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    manifest = os.path.join(tmpdir, 'manifest.json')
    Manifest(
        {'unit_runner.py': {'py': {'duration_s': 100}, 'cxx': {'duration_s': 100}}}
      , manifest
      ).save()
    out = io.StringIO()
    with redirect_stdout(out):
      status = cli.main(['--fast', '--manifest', manifest, 'unit_runner.py'])
    self.assertEqual(status, 0)
    self.assertIn('no file selected', out.getvalue())

  def test_prepare_only(self):
    '''
    --prepare-only runs the prepare pass alone and exits with its status.
    The pass is a stub, a small Python program with the status under test;
    the test jobs are stubs that would write a marker, and none runs.
    '''
    self.assertFalse(cli.parse_args([]).prepare_only)
    self.assertTrue(cli.parse_args(['--prepare-only']).prepare_only)
    logdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, logdir, ignore_errors=True)
    marker = os.path.join(logdir, 'a-test-file-ran')
    calls = []
    def pass_jobs(status):
      def stub(args, names, backends, sprite_home):
        calls.append((list(names), list(backends), args.logdir))
        return [
            Job(
                'prepare data/curry', backend
              , [PYTHON, '-c', 'import sys; sys.exit(%d)' % status]
              , cap=GIB, timeout=60, exclusive=True
              , logfile=os.path.join(logdir, backend, 'prepare-data-curry.log')
              )
            for backend in backends
          ]
      return stub
    def test_job(filename, backend, sprite_home, manifest, timeout, _, env):
      return Job(
          filename, backend, [PYTHON, '-c', 'open(%r, "w").close()' % marker]
        , cap=GIB, timeout=60
        , logfile=os.path.join(logdir, backend, filename + '.log')
        )
    for status in (0, 1):
      out = io.StringIO()
      with mock.patch.object(cli, 'prepare_pass_jobs', pass_jobs(status)), \
           mock.patch.object(cli, 'test_job', test_job), redirect_stdout(out):
        result = cli.main([
            '--prepare-only', '--backend', 'cxx', '--logdir', logdir
          , 'unit_runner.py'
          ])
      self.assertEqual(result, status)
      text = out.getvalue()
      self.assertIn('runner: prepare pass, 1 directory on cxx', text)
      self.assertRegex(
          text, r'\[1/1\] %s\s+cxx\s+prepare data/curry'
                % ('ok' if status == 0 else 'FAILED')
        )
      self.assertIn('1 of 1 run, %d failed' % status, text)
    self.assertEqual(calls, [(['unit_runner.py'], ['cxx'], logdir)] * 2)
    self.assertFalse(os.path.exists(marker))
    # --list shows the directories of the pass and no test file.
    out = io.StringIO()
    with redirect_stdout(out):
      result = cli.main(
          ['--list', '--prepare-only', '--backend', 'cxx', 'unit_runner.py']
        )
    self.assertEqual(result, 0)
    text = out.getvalue()
    self.assertRegex(text, r'cxx\s+prepare data/curry\s.*prepare pass')
    self.assertNotIn('unit_runner.py', text)


class TestPrepare(unittest.TestCase):

  def test_directories(self):
    dirs = [entry[0] for entry in prepare.directories(['unit_api.py'])]
    self.assertEqual(dirs, ['data/curry'])
    dirs = [
        entry[0] for entry in
        prepare.directories(['func_kiel.py', 'unit_cxx_variable.py'])
      ]
    self.assertEqual(
        dirs, ['data/curry', 'data/curry/benchmarks', 'data/curry/kiel']
      )
    for directory, _, _ in prepare.CORPUS:
      path = os.path.join(testrunner.TESTDIR, directory)
      self.assertTrue(os.path.isdir(path), directory)

  def test_modules(self):
    files = prepare.modules('data/curry')
    self.assertIn('data/curry/hello.curry', files)
    self.assertNotIn('data/curry/badimport.curry', files)
    # The product directory ends with the suffix too, and helloExternal
    # declares an external that no backend resolves.
    self.assertNotIn('data/curry/.curry', files)
    self.assertNotIn('data/curry/helloExternal.curry', files)
    self.assertTrue(all(name.endswith('.curry') for name in files))
    self.assertEqual(files, sorted(files))
    self.assertEqual(prepare.modules('data/curry/nosuch'), [])
    # The two programs that need the Curry preprocessor are left to the
    # benchmark harness.
    benchmarks = prepare.modules('data/curry/benchmarks')
    self.assertIn('data/curry/benchmarks/Last.curry', benchmarks)
    self.assertNotIn('data/curry/benchmarks/PokerChoice.curry', benchmarks)
    self.assertNotIn('data/curry/benchmarks/PokerFree.curry', benchmarks)

  def test_jobs(self):
    env = {'CURRYPATH': '/pool', 'PATH': '/bin'}
    jobs = prepare.jobs(
        ['func_kiel.py'], ['cxx', 'py'], '/sprite', env, '/logs', cap=GIB
      , timeout=None, prefix=['prlimit', '--as=1'], subdir='.curry/x'
      )
    self.assertEqual([job.backend for job in jobs], ['cxx', 'cxx', 'py', 'py'])
    self.assertTrue(all(isinstance(job, prepare.PrepareJob) for job in jobs))
    self.assertTrue(all(job.advisory for job in jobs))
    self.assertEqual(
        [job.filename for job in jobs]
      , ['prepare data/curry', 'prepare data/curry/kiel'] * 2
      )
    kiel = jobs[1]
    # Without -q: the line of sprite-make about the product cache must
    # reach the log (cache_counts).
    self.assertEqual(
        kiel.argv[:7]
      , ['prlimit', '--as=1', '/sprite/bin/sprite-make', '-k', '-c', '-z', '--so']
      )
    self.assertNotIn('-q', kiel.argv)
    self.assertTrue(
        all(name.startswith('data/curry/kiel/') for name in kiel.argv[7:])
      )
    self.assertEqual(kiel.env['CURRYPATH'], ':'.join([
        os.path.join(testrunner.TESTDIR, 'data/curry/kiel/lib')
      , os.path.join(testrunner.TESTDIR, 'data/curry/kiel'), '/pool'
      ]))
    self.assertTrue(kiel.exclusive)
    self.assertEqual(kiel.logfile, '/logs/cxx/prepare-data-curry-kiel.log')
    self.assertEqual(jobs[3].argv[6], '--py')
    # The modules of the job and their products, per backend.
    self.assertEqual(kiel.directory, 'data/curry/kiel')
    self.assertEqual(kiel.modules, kiel.argv[7:])
    self.assertIn('data/curry/kiel/UseConc1.curry', kiel.modules)
    self.assertEqual(
        kiel.product('data/curry/kiel/UseConc1.curry')
      , os.path.join(
            testrunner.TESTDIR, 'data/curry/kiel', '.curry/x', 'UseConc1.so'
          )
      )
    self.assertEqual(
        jobs[3].product('data/curry/kiel/UseConc1.curry')
      , os.path.join(
            testrunner.TESTDIR, 'data/curry/kiel', '.curry/x', 'UseConc1.py'
          )
      )
    # Without a product directory the products are unknown.
    unknown = prepare.jobs(
        ['func_kiel.py'], ['cxx'], '/sprite', env, '/logs', cap=GIB
      , timeout=None
      )[0]
    self.assertIsNone(unknown.subdir)
    self.assertIsNone(unknown.product('data/curry/kiel/UseConc1.curry'))
    self.assertIsNone(unknown.missing())

  def test_products_under_interpret(self):
    '''
    Under the interpreter flag interpret set to new or all, sprite-make --so
    ends at the JSON (the runtime interprets the module), so the JSON is the
    product the pass looks for on the C++ backend; the Python backend keeps
    its .py.  The flags are those of the environment of the job, which
    cli.main sets after the job is made.
    '''
    self.assertEqual(prepare.interpret_flag(None), 'off')
    self.assertEqual(prepare.interpret_flag('backend:cxx'), 'off')
    self.assertEqual(prepare.interpret_flag('backend:cxx,interpret:new'), 'new')
    self.assertEqual(prepare.interpret_flag(' interpret : all ,debug:1'), 'all')
    self.assertEqual(prepare.product_suffixes('cxx'), ('.so',))
    self.assertEqual(prepare.product_suffixes('py'), ('.py',))
    self.assertEqual(prepare.product_suffixes('py', 'interpret:new'), ('.py',))
    for mode in 'new', 'all':
      self.assertEqual(
          prepare.product_suffixes('cxx', 'interpret:' + mode)
        , prepare.JSON_PRODUCTS
        )
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    testdir = os.path.join(tmpdir, 'tests')
    pool = os.path.join(testdir, 'data', 'curry')
    products = os.path.join(pool, '.curry', 'x')
    os.makedirs(products)
    for name in 'a.curry', 'b.curry', 'a.json.z', 'b.so':
      with open(os.path.join(pool if name.endswith('.curry') else products, name), 'w'):
        pass
    def job(backend, flags):
      env = {} if flags is None else {'SPRITE_INTERPRETER_FLAGS': flags}
      return prepare.jobs(
          ['unit_x.py'], [backend], '/sprite', env, '/logs', cap=GIB
        , timeout=None, testdir=testdir, subdir='.curry/x'
        )[0]
    plain = job('cxx', None)
    self.assertEqual(plain.missing(), ['data/curry/a.curry'])
    self.assertEqual(
        plain.product('data/curry/a.curry'), os.path.join(products, 'a.so')
      )
    for flags in 'backend:cxx,interpret:new', 'interpret:all':
      new = job('cxx', flags)
      self.assertEqual(new.flags, flags)
      self.assertEqual(new.missing(), ['data/curry/b.curry'], flags)
      self.assertEqual(
          new.products('data/curry/a.curry')
        , [os.path.join(products, 'a.json.z'), os.path.join(products, 'a.json')]
        )
      self.assertEqual(
          new.product('data/curry/a.curry'), os.path.join(products, 'a.json.z')
        )
    # The environment that cli.main gives the job carries the flags of the
    # run; the Python backend is not concerned.
    late = job('cxx', None)
    late.env = cli.environment(
        '/sprite', 'cxx', base={'SPRITE_INTERPRETER_FLAGS': 'interpret:new'}
      )
    self.assertEqual(late.missing(), ['data/curry/b.curry'])
    self.assertEqual(
        job('py', 'interpret:new').missing()
      , ['data/curry/a.curry', 'data/curry/b.curry']
      )
    # The note after a pass that did not end well names the module that
    # lacks its JSON, not every module.
    late.status = 'incomplete'
    late.note = 'exit status 1'
    late.on_finished()
    self.assertEqual(
        late.note, 'exit status 1; 1 of 2 modules without a product: b.curry'
      )
    unknown = job('cxx', 'interpret:new')
    unknown.subdir = None
    self.assertEqual(unknown.products('data/curry/a.curry'), [])
    self.assertIsNone(unknown.product('data/curry/a.curry'))
    self.assertIsNone(unknown.missing())

  def test_prune_product_cache(self):
    '''
    After the pass the runner prunes its own product cache: the digest
    directories of other runtimes go, the ones of the installed runtime
    stay.  A cache the environment named, a cache turned off and a cache
    that does not exist are left alone.
    '''
    sprite_home = os.environ.get('SPRITE_HOME')
    if not sprite_home:
      self.skipTest('needs SPRITE_HOME')
    python = os.path.join(sprite_home, 'bin', 'python')
    proc = subprocess.run(
        [ python, '-B', '-c'
        , 'from curry.backends.cxx import toolchain\n'
          'print(toolchain.object_digest() or "")'
        ]
      , capture_output=True, text=True, timeout=120
      )
    current = proc.stdout.strip()
    if proc.returncode != 0 or not current:
      self.skipTest('the installation has no runtime headers')
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    root = os.path.join(tmpdir, 'products')
    for digest in current, 'fedcba9876543210':
      os.makedirs(os.path.join(root, digest, 'a' * 64))
    env = dict(os.environ, SPRITE_PRODUCT_CACHE=root)
    # Another cache than the runner's own: left alone.
    self.assertIsNone(prepare.prune_product_cache(sprite_home, env))
    self.assertIsNone(
        prepare.prune_product_cache(sprite_home, dict(env, SPRITE_PRODUCT_CACHE=''))
      )
    with mock.patch.object(prepare, 'DEFAULT_PRODUCT_CACHE', root):
      self.assertEqual(prepare.prune_product_cache(sprite_home, env), (1, 0))
      self.assertEqual(os.listdir(root), [current])
      self.assertEqual(prepare.prune_product_cache(sprite_home, env), (0, 0))
      shutil.rmtree(root)
      self.assertIsNone(prepare.prune_product_cache(sprite_home, env))
    self.assertEqual(
        prepare.DEFAULT_PRODUCT_CACHE
      , os.path.join(testrunner.TESTDIR, '.cache', 'products')
      )

  def test_cache_counts(self):
    '''
    The pass reads the line of sprite-make about the product cache from
    the log of a job: its note and the summary line say how many products
    came from the cache.  Without the line nothing is said.
    '''
    self.assertIsNone(prepare.cache_counts(''))
    self.assertIsNone(prepare.cache_counts('sprite-make: product cache: x\n'))
    text = 'made A\nsprite-make: product cache: 37 restored, 6 stored\n'
    self.assertEqual(prepare.cache_counts(text), (37, 6))
    # Several lines (a parallel run that relayed the lines of its children).
    text += 'sprite-make: product cache: 1 restored, 0 stored\n'
    self.assertEqual(prepare.cache_counts(text), (38, 6))
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    testdir = os.path.join(tmpdir, 'tests')
    pool = os.path.join(testdir, 'data', 'curry')
    os.makedirs(pool)
    for name in 'a.curry', 'b.curry', 'c.curry':
      open(os.path.join(pool, name), 'w').close()
    def job(logtext):
      logfile = os.path.join(tmpdir, 'prepare-%d.log' % len(os.listdir(tmpdir)))
      with open(logfile, 'w') as stream:
        stream.write(logtext)
      made = prepare.jobs(
          ['unit_x.py'], ['cxx'], '/sprite', {}, '/logs', cap=GIB, timeout=None
        , testdir=testdir, subdir='.curry/x'
        )[0]
      made.logfile = logfile
      made.status = 'ok'
      made.finished = True
      return made
    quiet = job('made a\n')
    quiet.on_finished()
    self.assertIsNone(quiet.restored)
    self.assertEqual(quiet.note, '')
    warm = job('sprite-make: product cache: 2 restored, 1 stored\n')
    warm.on_finished()
    self.assertEqual((warm.restored, warm.stored), (2, 1))
    self.assertEqual(warm.note, '2 of 3 from the product cache')
    # A directory that did not end well keeps both details.
    partial = job('sprite-make: product cache: 1 restored, 0 stored\n')
    partial.status = 'incomplete'
    partial.note = 'exit status 1'
    partial.on_finished()
    self.assertEqual(
        partial.note
      , 'exit status 1; 1 of 3 from the product cache; 3 of 3 modules without '
        'a product: a.curry, b.curry, c.curry'
      )
    # Each job here stands for one directory, so two jobs count as two.
    self.assertEqual(
        prepare.summary([warm])
      , 'prepare: 3 modules in 1 directory on cxx, 2 from the product cache, '
        'every product present'
      )
    self.assertEqual(
        prepare.summary([quiet]), 'prepare: 3 modules in 1 directory on cxx, '
        'every product present'
      )
    self.assertEqual(
        prepare.summary([quiet, warm])
      , 'prepare: 6 modules in 2 directories on cxx, 2 from the product cache, '
        'every product present'
      )
    self.assertTrue(
        prepare.summary([warm, partial]).startswith(
            'prepare: 6 modules in 2 directories on cxx, 3 from the product '
            'cache; 3 without a product: '
          )
      )

  def test_rewrite_counts(self):
    '''
    The pass reads the line of sprite-make about the pairs made before the
    binding rewrite that the run translated again (issue #101): the note
    of the job and the summary line repeat the count, beside the counts of
    the product cache.  Without the line nothing is said.
    '''
    self.assertIsNone(prepare.rewrite_counts(''))
    self.assertIsNone(prepare.rewrite_counts('sprite-make: pre-rewrite pairs: x\n'))
    text = 'made A\nsprite-make: pre-rewrite pairs: 2 translated again\n'
    self.assertEqual(prepare.rewrite_counts(text), (2, 0))
    text += 'sprite-make: pre-rewrite pairs: 1 translated again\n'
    self.assertEqual(prepare.rewrite_counts(text), (3, 0))
    text += 'sprite-make: pre-rewrite pairs: 0 translated again, 2 from the ICurry cache\n'
    self.assertEqual(prepare.rewrite_counts(text), (3, 2))
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    testdir = os.path.join(tmpdir, 'tests')
    pool = os.path.join(testdir, 'data', 'curry')
    os.makedirs(pool)
    for name in 'a.curry', 'b.curry', 'c.curry':
      open(os.path.join(pool, name), 'w').close()
    def job(logtext):
      logfile = os.path.join(tmpdir, 'prepare-%d.log' % len(os.listdir(tmpdir)))
      with open(logfile, 'w') as stream:
        stream.write(logtext)
      made = prepare.jobs(
          ['unit_x.py'], ['cxx'], '/sprite', {}, '/logs', cap=GIB, timeout=None
        , testdir=testdir, subdir='.curry/x'
        )[0]
      made.logfile = logfile
      made.status = 'ok'
      made.finished = True
      made.on_finished()
      return made
    quiet = job('made a\n')
    self.assertIsNone(quiet.refreshed)
    self.assertIsNone(quiet.served)
    self.assertEqual(quiet.note, '')
    one = job('sprite-make: pre-rewrite pairs: 1 translated again\n')
    self.assertEqual((one.refreshed, one.served), (1, 0))
    self.assertEqual(one.note, '1 pre-rewrite pair translated again')
    served = job(
        'sprite-make: pre-rewrite pairs: 0 translated again, 1 from the ICurry cache\n'
      )
    self.assertEqual((served.refreshed, served.served), (0, 1))
    self.assertEqual(served.note, '1 pre-rewrite pair from the ICurry cache')
    both = job(
        'sprite-make: product cache: 2 restored, 1 stored\n'
        'sprite-make: pre-rewrite pairs: 2 translated again\n'
      )
    self.assertEqual((both.restored, both.stored, both.refreshed), (2, 1, 2))
    self.assertEqual(
        both.note
      , '2 of 3 from the product cache; 2 pre-rewrite pairs translated again'
      )
    self.assertEqual(
        prepare.summary([one])
      , 'prepare: 3 modules in 1 directory on cxx, 1 pre-rewrite pair '
        'translated again, every product present'
      )
    self.assertEqual(
        prepare.summary([quiet, one, both])
      , 'prepare: 9 modules in 3 directories on cxx, 2 from the product cache, '
        '3 pre-rewrite pairs translated again, every product present'
      )
    self.assertEqual(
        prepare.summary([one, served])
      , 'prepare: 6 modules in 2 directories on cxx, 1 pre-rewrite pair '
        'translated again, 1 pre-rewrite pair from the ICurry cache, every '
        'product present'
      )

  def test_preprocessor_lacking(self):
    '''
    A module whose source names a preprocessor the PATH lacks, and whose
    log shows that the front end could not run it, is without a product as
    any other: the pass fails, and the note adds the cause and the remedy
    (poker_four_of_a_kind of smap, currypp, in the nightly functional
    shards before the workflow extracted the overlay archive).  Another
    failure of such a module, or the tool on the PATH, gets no such hint.
    '''
    self.assertIsNone(prepare.preprocessor('/no/such/file.curry'))
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    testdir = os.path.join(tmpdir, 'tests')
    corpus = os.path.join(testdir, 'data', 'curry', 'smap')
    products = os.path.join(corpus, '.curry', 'x')
    os.makedirs(products)
    def write(name, text):
      with open(os.path.join(corpus, name), 'w') as stream:
        stream.write(text)
    write('plain.curry', 'main = 1\n')
    write(
        'poker.curry'
      , '{-# OPTIONS_CYMAKE -F --pgmF=currypp --optF=defaultrules #-}\n'
        '{-# OPTIONS_CYMAKE -Wnone #-}\nmain = 2\n'
      )
    write('front.curry', '{-# OPTIONS_FRONTEND -F --pgmF tool-x #-}\n')
    self.assertIsNone(prepare.preprocessor(os.path.join(corpus, 'plain.curry')))
    self.assertEqual(
        prepare.preprocessor(os.path.join(corpus, 'poker.curry')), 'currypp'
      )
    self.assertEqual(
        prepare.preprocessor(os.path.join(corpus, 'front.curry')), 'tool-x'
      )
    os.remove(os.path.join(corpus, 'front.curry'))
    # The log of the front end that could not run the tool, as the nightly
    # job printed it, and the log of a failure after the ICurry step.
    shell = (
        'sprite-make: while running curry-frontend --flat poker:\n'
        'sprite-make: /bin/sh: 1: currypp: not found\n'
        'sprite-make: \n'
        'sprite-make: Error:\n'
        'sprite-make: Preprocessor exited with exit code 127\n'
      )
    other = (
        'make: *** No rule to make target poker.so: prerequisite is the '
        'wrong type or is unreadable: poker.cpp\n'
      )
    self.assertTrue(prepare.preprocessor_failed(shell, 'currypp'))
    self.assertTrue(
        prepare.preprocessor_failed('Preprocessor exited with exit code 1\n', 'x')
      )
    self.assertFalse(prepare.preprocessor_failed('g++: not found\n', 'currypp'))
    self.assertFalse(prepare.preprocessor_failed(other, 'currypp'))
    self.assertFalse(prepare.preprocessor_failed('', 'currypp'))
    # The products the archive supplies, and the object of the other module.
    for name in 'plain.so', 'poker.icy', 'poker.json.z':
      open(os.path.join(products, name), 'w').close()
    # A PATH with a stand-in currypp, and one without.
    bindir = os.path.join(tmpdir, 'bin')
    os.makedirs(bindir)
    tool = os.path.join(bindir, 'currypp')
    with open(tool, 'w') as stream:
      stream.write('#!/bin/sh\n')
    os.chmod(tool, 0o755)
    nowhere = os.path.join(tmpdir, 'none')
    logfile = os.path.join(tmpdir, 'prepare.log')
    def job(path, log, status='FAILED'):
      made = [
          job for job in prepare.jobs(
              ['func_smap.py'], ['cxx'], '/sprite', {'PATH': path}, '/logs'
            , cap=GIB, timeout=None, testdir=testdir, subdir='.curry/x'
            )
          if job.directory == 'data/curry/smap'
        ][0]
      with open(logfile, 'w') as stream:
        stream.write(log)
      made.logfile = logfile
      # Under --prepare-only the jobs are not advisory (cli.prepare_pass_jobs).
      made.advisory = status == 'incomplete'
      made.status = status
      made.returncode = 1
      made.note = 'exit status 1'
      made.finished = True
      made.on_finished()
      return made
    lacking = job(nowhere, shell)
    self.assertEqual(
        lacking.modules
      , ['data/curry/smap/plain.curry', 'data/curry/smap/poker.curry']
      )
    self.assertEqual(lacking.lacking, {'data/curry/smap/poker.curry': 'currypp'})
    self.assertEqual(lacking.status, 'FAILED')
    self.assertEqual(
        lacking.note
      , 'exit status 1; 1 of 2 modules without a product: poker.curry; '
        'poker.curry needs currypp, which the PATH lacks; make overlay after '
        'make stage supplies its products'
      )
    self.assertEqual(cli.exit_status([lacking]), 1)
    self.assertEqual(
        prepare.summary([lacking])
      , 'prepare: 2 modules in 1 directory on cxx; 1 without a product: '
        'data/curry/smap/poker.curry (cxx); the tests that need them report it'
      )
    # An advisory job (--prepare) keeps its status as well.
    self.assertEqual(job(nowhere, shell, 'incomplete').status, 'incomplete')
    # A failure after the ICurry step is not blamed on the tool.
    plain = job(nowhere, other)
    self.assertEqual(plain.lacking, {})
    self.assertEqual(plain.status, 'FAILED')
    self.assertEqual(
        plain.note
      , 'exit status 1; 1 of 2 modules without a product: poker.curry'
      )
    # With currypp on the PATH the module could have been made.
    present = job(bindir, shell)
    self.assertEqual(present.lacking, {})
    self.assertEqual(
        present.note
      , 'exit status 1; 1 of 2 modules without a product: poker.curry'
      )
    self.assertEqual(cli.exit_status([present]), 1)
    # A second module without a product is named beside it.
    os.remove(os.path.join(products, 'plain.so'))
    both = job(nowhere, shell)
    self.assertEqual(both.lacking, {'data/curry/smap/poker.curry': 'currypp'})
    self.assertEqual(
        both.note
      , 'exit status 1; 2 of 2 modules without a product: plain.curry, '
        'poker.curry; poker.curry needs currypp, which the PATH lacks; make '
        'overlay after make stage supplies its products'
      )
    self.assertEqual(
        prepare.summary([both])
      , 'prepare: 2 modules in 1 directory on cxx; 2 without a product: '
        'data/curry/smap/plain.curry (cxx), data/curry/smap/poker.curry '
        '(cxx); the tests that need them report it'
      )

  def test_product_subdir(self):
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    home = stub_installation(tmpdir)
    self.assertEqual(prepare.product_subdir(home), '.curry/stub')
    self.assertIsNone(prepare.product_subdir(os.path.join(tmpdir, 'none')))
    # The real installation names a directory under .curry.
    sprite_home = os.environ.get('SPRITE_HOME')
    make = os.path.join(sprite_home or '', 'bin', 'sprite-make')
    if sprite_home and os.path.isfile(make):
      subdir = prepare.product_subdir(sprite_home)
      self.assertIsNotNone(subdir)
      self.assertTrue(subdir.startswith('.curry/'), subdir)

  def test_advisory_pass(self):
    '''
    The pass with a stand-in sprite-make over a corpus of three modules,
    one of which does not compile: the job of the directory ends
    incomplete and names the module; the summary line sums it up; a
    second pass over good modules alone ends ok.
    '''
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    home = stub_installation(os.path.join(tmpdir, 'install'))
    testdir = os.path.join(tmpdir, 'tests')
    pool = os.path.join(testdir, 'data', 'curry')
    os.makedirs(pool)
    for name in 'good.curry', 'bad.curry', 'other.curry':
      with open(os.path.join(pool, name), 'w'):
        pass
    logdir = os.path.join(tmpdir, 'logs')
    # The job reads the interpreter flags of its environment: under
    # interpret:new or interpret:all it expects the JSON of a module, which
    # the stand-in does not write.  The pass under test is the plain one.
    env = dict(os.environ)
    env.pop('SPRITE_INTERPRETER_FLAGS', None)
    def run(backends):
      jobs = prepare.jobs(
          ['unit_x.py'], backends, home, env, logdir, cap=GIB, timeout=60
        , testdir=testdir, subdir=prepare.product_subdir(home)
        )
      Scheduler(jobs, 16 * GIB, 1, poll=POLL).run()
      return jobs
    jobs = run(['cxx', 'py'])
    self.assertEqual(len(jobs), 2)
    for job in jobs:
      self.assertEqual(job.status, 'incomplete', job.note)
      self.assertEqual(job.modules, [
          'data/curry/bad.curry', 'data/curry/good.curry'
        , 'data/curry/other.curry'
        ])
      self.assertEqual(job.missing(), ['data/curry/bad.curry'])
      self.assertEqual(
          job.note, 'exit status 1; 1 of 3 modules without a product: bad.curry'
        )
      self.assertIn('incomplete', report.format_status(job))
    products = os.path.join(pool, '.curry', 'stub')
    self.assertTrue(os.path.isfile(os.path.join(products, 'good.so')))
    self.assertTrue(os.path.isfile(os.path.join(products, 'good.py')))
    self.assertEqual(
        prepare.summary(jobs)
      , 'prepare: 3 modules in 1 directory on cxx+py; 2 without a product: '
        'data/curry/bad.curry (cxx), data/curry/bad.curry (py); the tests that '
        'need them report it'
      )
    self.assertEqual(cli.exit_status(jobs), 0)
    self.assertIn('prepare: 2 of 2 incomplete', report.summary(jobs))
    # Many names are cut short.
    for i in range(10):
      with open(os.path.join(pool, 'bad%d.curry' % i), 'w'):
        pass
    job = run(['py'])[0]
    self.assertEqual(len(job.missing()), 11)
    self.assertRegex(
        job.note
      , r'11 of 13 modules without a product: bad\.curry, bad0\.curry, '
        r'.*and 5 more$'
      )
    # The good modules alone: ok, no note, and a quiet summary line.
    for name in os.listdir(pool):
      if name.startswith('bad'):
        os.unlink(os.path.join(pool, name))
    jobs = run(['py'])
    self.assertEqual(jobs[0].status, 'ok')
    self.assertEqual(jobs[0].note, '')
    self.assertEqual(jobs[0].missing(), [])
    self.assertEqual(
        prepare.summary(jobs)
      , 'prepare: 2 modules in 1 directory on py, every product present'
      )
    self.assertEqual(prepare.summary([]), 'prepare: nothing to make')
    # A pass whose products are unknown says so.
    jobs = prepare.jobs(
        ['unit_x.py'], ['py'], home, env, logdir, cap=GIB, timeout=60
      , testdir=testdir
      )
    jobs[0].argv = [PYTHON, '-c', 'import sys; sys.exit(1)']
    Scheduler(jobs, 16 * GIB, 1, poll=POLL).run()
    self.assertEqual(jobs[0].status, 'incomplete')
    self.assertEqual(jobs[0].note, 'exit status 1; see the log')
    self.assertEqual(
        prepare.summary(jobs)
      , 'prepare: 2 modules in 1 directory on py; 1 directory did not end '
        'well, products unknown: see the log; the tests that need them '
        'report it'
      )


if __name__ == '__main__':
  unittest.main()
