'''
Tests for the test runner under lib/testrunner: the admission rules, the
watchdog, the timeout, the manifest, the selection rules, the fast tier,
the report, and the exit status.  The children are small Python programs;
no test here compiles Curry.
'''
import cytest # from ./lib; must be first
import testrunner
from testrunner import cli, prepare, procs, report, selection
from testrunner.manifest import FORMAT, Manifest
from testrunner.scheduler import INTERRUPT_SIGNALS, Job, Scheduler, pick
import io, json, os, re, shutil, signal, subprocess, sys, tempfile, threading, time
import unittest
from contextlib import redirect_stderr, redirect_stdout

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
      _, pids = procs.scan_sessions([child.pid])[child.pid]
      self.assertIn(child.pid, pids)
      self.assertIn(grandchild, pids)
      self.assertNotEqual(os.getsid(grandchild), child.pid)
      # The leader gone, the roots of the last scan still find the rest.
      child.kill()
      child.wait()
      _, pids = procs.scan_sessions([child.pid])[child.pid]
      self.assertNotIn(grandchild, pids)
      found = procs.scan_sessions([child.pid], roots={child.pid: [grandchild]})
      _, pids = found[child.pid]
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
    rss, pids = procs.scan_sessions([sid])[sid]
    self.assertIn(os.getpid(), pids)
    self.assertGreater(rss, 0)
    self.assertTrue(procs.is_alive(os.getpid()))


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
      , 'big.py': {'py': {'duration_s': 1, 'peak_rss_mb': 1024}}
      , 'nopeak.py': {'py': {'duration_s': 1, 'peak_rss_mb': None}}
      })
    self.assertEqual(manifest.cap('small.py', 'py'), testrunner.MIN_CAP)
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
    manifest = Manifest.load(testrunner.MANIFEST_FILE, missing_ok=False)
    # The calibration run fills the durations and the peaks (README,
    # section 10); the longest file of the suite has a duration and a
    # peak on both backends.
    for backend in testrunner.BACKENDS:
      self.assertGreater(manifest.duration('func_eqconstr.py', backend), 0)
      self.assertGreater(manifest.peak('func_eqconstr.py', backend), 0)
    for name, entries in manifest.files.items():
      self.assertTrue(name.startswith(('unit_', 'func_')), name)
      for backend, entry in entries.items():
        self.assertIn(backend, testrunner.BACKENDS)
        self.assertEqual(sorted(entry), sorted(testrunner.manifest.FIELDS))


FILES = sorted([
    'func_flat2icurry.py', 'func_kiel.py', 'func_math.py', 'unit_api.py'
  , 'unit_benchmarks.py', 'unit_cache.py', 'unit_compile.py'
  , 'unit_curry2icurry.py', 'unit_currylib.py', 'unit_cxx_gc.py'
  , 'unit_cxx_toolchain.py', 'unit_cxx_variable.py', 'unit_expr.py'
  , 'unit_flat2icurry.py', 'unit_icurry.py', 'unit_inspect.py'
  , 'unit_loadsave.py', 'unit_plan.py', 'unit_prebuild.py'
  , 'unit_py_conversions.py', 'unit_py_evaluation.py', 'unit_py_io.py'
  , 'unit_utility.py'
  ])
CXX_FILES = ['unit_cxx_gc.py', 'unit_cxx_toolchain.py', 'unit_cxx_variable.py']
TOOLCHAIN_FILES = [
    'func_flat2icurry.py', 'unit_cache.py', 'unit_compile.py'
  , 'unit_curry2icurry.py', 'unit_cxx_toolchain.py', 'unit_flat2icurry.py'
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
    self.assertEqual(names, ['unit_benchmarks.py', 'unit_cxx_variable.py'])
    self.assertIn('the benchmark programs', notes[0])
    names, _, _ = self.selected(['tests/data/curry/flat2icurry/Probe.curry'])
    self.assertEqual(
        names
      , ['func_flat2icurry.py', 'unit_curry2icurry.py', 'unit_flat2icurry.py']
      )
    # A rule whose globs match no file: the policy for the unknown.
    names, selected, notes = self.selected(['tests/data/curry/nosuch/x.curry'])
    self.assertEqual(names, FILES)
    self.assertIn(
        'no test file matches func_nosuch.py; selects everything', notes[0]
      )
    self.assertIn(
        'no test file matches func_nosuch.py for '
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
    self.assertIn(testrunner.DEFAULT_JOBS, [1, 'auto'])
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
    '''The planned flip of DEFAULT_JOBS to 'auto' must not break the help.'''
    for jobs in (1, 4, 'auto'):
      args = cli.parse_args([], jobs=jobs)
      self.assertEqual(args.jobs, jobs)
      text = cli.build_parser(jobs).format_help()
      self.assertIn('[default: %s]' % jobs, text)
      self.assertIn('%s at a time' % jobs, cli.epilog(jobs))
    args = cli.parse_args(['-j', '2'], jobs='auto')
    self.assertEqual(args.jobs, 2)

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
      , timeout=None, prefix=['prlimit', '--as=1']
      )
    self.assertEqual([job.backend for job in jobs], ['cxx', 'cxx', 'py', 'py'])
    self.assertEqual(
        [job.filename for job in jobs]
      , ['prepare data/curry', 'prepare data/curry/kiel'] * 2
      )
    kiel = jobs[1]
    self.assertEqual(
        kiel.argv[:8]
      , [ 'prlimit', '--as=1', '/sprite/bin/sprite-make', '-k', '-q', '-c'
        , '-z', '--so'
        ]
      )
    self.assertTrue(
        all(name.startswith('data/curry/kiel/') for name in kiel.argv[8:])
      )
    self.assertEqual(kiel.env['CURRYPATH'], ':'.join([
        os.path.join(testrunner.TESTDIR, 'data/curry/kiel/lib')
      , os.path.join(testrunner.TESTDIR, 'data/curry/kiel'), '/pool'
      ]))
    self.assertTrue(kiel.exclusive)
    self.assertEqual(kiel.logfile, '/logs/cxx/prepare-data-curry-kiel.log')
    self.assertEqual(jobs[3].argv[7], '--py')


if __name__ == '__main__':
  unittest.main()
