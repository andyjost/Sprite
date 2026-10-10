'''
Tests for the rotation modes of the C++ backend (src/cyrt/ticker.hpp; the
flag ``rotation`` in curry.interpreter.flags; issues #68 and #69).

The scheduler rotates its queue of alternatives at a safepoint, after a
completed rewrite step.  In time mode, the default of the tools, a ticker
thread sets one byte every quantum and the safepoint polls it.  In step
mode, which the test runner, the benchmark harness and the CI jobs set
through SPRITE_ROTATION, the safepoint counts the steps and rotates every N
of them, so the exact counters of a search reproduce between runs.

The tests that evaluate in time mode run in a child process under prlimit
and timeout (cytest.run_in_subprocess), because a regression spins inside
C++.  A test that measures wall time has a generous bound and says why:
another process of the machine can delay the ticker thread or the child.
The design numbers (a value within three quanta) are measured by hand and
recorded in the TODO entry and the measurement table of Gate K.  The
failure paths of the ticker (a thread that cannot start, a quantum of zero)
and a fork with an evaluation in flight use the bindings ticker_enter and
ticker_leave, which do what the outermost scheduler does on entry and exit.

In the stress mode of the collector (SPRITE_GC_STRESS=1) a collection
follows every step and marks the live state of a search.  The test of the
pinned counters keeps its psort 8 half there (16929 steps in under a
second) and skips its countQueens 8 half: that search takes 2.1 million
steps, and the stress mode repeats the counters of the default mode
(TestStress of unit_cxx_gc.py).  The repeat test takes a board of six
there.  An evaluation
of fair in step mode costs about thirty seconds there, because the sums of
its loop stay live.
'''
import cytest # from ./lib; must be first
from curry.interpreter import flags
from curry.interpreter import Interpreter
import curry, json, os, subprocess, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))

# The cap on the address space of a child, in bytes, and the time it may
# take.  A child loads the test modules from the shared products.
ADDRESS_SPACE = 2 << 30
TIMEOUT = 120

# The wall seconds a value beside a diverging alternative may take in time
# mode.  The design bound is three quanta (30 ms).  The test bound is
# generous: the child starts the ticker thread at its first evaluation, and
# a loaded machine delays the thread and the child.  The measured latency is
# recorded in the TODO entry, not pinned here.
GENEROUS_SECONDS = 5.0

# The quantum of the tests, and the seconds a parked ticker must stay quiet.
QUANTUM_MS = 10
IDLE_SECONDS = 2.0

STEP_MODE = 'steps:65536'
TIME_MODE = 'time:%dms' % QUANTUM_MS

ONLY_CXX = unittest.skipIf(
    curry.flags['backend'] != 'cxx'
  , 'the rotation modes belong to the C++ backend; the Python backend keeps '
    'its step budget'
  )

# A child on the C++ backend in the rotation mode %(mode)r with the rewrite
# test module imported.  ``report`` prints one JSON line.
CHILD = '''
import curry, json, os, sys, time
curry.reload(
    {'backend': 'cxx', 'rotation': %(mode)r, 'defaultconverter': 'topython'}
  )
from curry.backends.cxx import cyrtbindings as cyrt
M = curry.import_('CxxRewrite')
def report(**fields):
  sys.stdout.write(json.dumps(fields) + '\\n')
  sys.stdout.flush()
def ticker_thread():
  """The task id of the ticker thread, or None."""
  for tid in os.listdir('/proc/self/task'):
    with open('/proc/self/task/%%s/comm' %% tid) as stream:
      if stream.read().strip() == 'cyrt-ticker':
        return tid
  return None
def context_switches(tid):
  """The voluntary and involuntary context switches of a thread."""
  switches = {}
  with open('/proc/self/task/%%s/status' %% tid) as stream:
    for line in stream:
      key, _, value = line.partition(':')
      if key.endswith('ctxt_switches'):
        switches[key] = int(value)
  return switches
def wait_until(predicate, seconds):
  deadline = time.monotonic() + seconds
  while time.monotonic() < deadline:
    if predicate():
      return True
    time.sleep(0.001)
  return predicate()
'''

def run_child(testcase, mode, code):
  '''
  Runs ``code`` after CHILD in a child in rotation mode ``mode`` and returns
  the JSON lines it printed, as dicts.
  '''
  proc = cytest.run_in_subprocess(
      CHILD % {'mode': mode} + code, TIMEOUT, address_space=ADDRESS_SPACE
    )
  testcase.assertEqual(
      proc.returncode, 0
    , 'the child ended with status %s; stdout:\n%s\nstderr:\n%s'
          % (proc.returncode, proc.stdout, proc.stderr)
    )
  return [json.loads(line) for line in proc.stdout.splitlines() if line]


class TestRotationSetting(cytest.TestCase):
  '''The setting ``rotation`` parses, defaults, and reaches the flags.'''

  def test_parse_time(self):
    self.assertEqual(flags.parse_rotation('time:10ms'), ('time', 10000000))
    self.assertEqual(flags.parse_rotation('time:1s'), ('time', 10**9))
    self.assertEqual(flags.parse_rotation('time:250us'), ('time', 250000))
    self.assertEqual(flags.parse_rotation('time:2.5ms'), ('time', 2500000))
    self.assertEqual(flags.parse_rotation('time:500ns'), ('time', 500))
    self.assertEqual(flags.parse_rotation(' time : 10ms '), ('time', 10000000))

  def test_parse_steps(self):
    self.assertEqual(flags.parse_rotation('steps:65536'), ('steps', 65536))
    self.assertEqual(flags.parse_rotation('steps:1'), ('steps', 1))
    self.assertEqual(flags.parse_rotation('steps:1000'), ('steps', 1000))
    # The largest count the runtime holds.
    self.assertEqual(
        flags.parse_rotation('steps:%d' % (2 ** 63 - 1)), ('steps', 2 ** 63 - 1)
      )

  def test_parse_errors(self):
    for text in [
        '', 'bogus', 'time', 'time:', 'time:10', 'time:0ms', 'time:-1ms'
      , 'time:ms', 'time:10 minutes', 'time:infms', 'time:nans', 'time:1e30s'
      , 'steps', 'steps:', 'steps:0', 'steps:-1', 'steps:65536x', 'steps:1e4'
      , 'steps:%d' % 2 ** 63, 'steps:99999999999999999999999'
      , 'ticks:10ms', None, 65536
      ]:
      with self.assertRaisesRegex(
          ValueError, 'bad rotation setting .*expected time:<N>ms or steps:<N>'
        , msg=repr(text)
        ):
        flags.parse_rotation(text)

  def test_default_is_time_mode(self):
    '''
    The default of the flag is time mode with a quantum of 10 ms.  The test
    files run in the mode of SPRITE_ROTATION: cytest sets step mode before
    the first import of curry unless the environment names a mode, as the
    runner and the CI script do.  A child without the variable gets the
    default.
    '''
    self.assertEqual(flags.FLAG_INFO['rotation'][1], 'time:10ms')
    self.assertIn('SPRITE_ROTATION', os.environ)
    self.assertEqual(curry.flags['rotation'], os.environ['SPRITE_ROTATION'])
    code = '''
import os
os.environ.pop('SPRITE_ROTATION', None)
os.environ.pop('SPRITE_INTERPRETER_FLAGS', None)
import curry
print(curry.flags['rotation'])
'''
    proc = cytest.run_in_subprocess(code, TIMEOUT)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout.strip(), 'time:10ms')

  def test_environment_precedence(self):
    '''
    SPRITE_ROTATION sets the flag below SPRITE_INTERPRETER_FLAGS, whose
    value keeps the colon of the setting, and the flags of a reload win.
    '''
    code = '''
import os
os.environ['SPRITE_ROTATION'] = 'steps:100'
os.environ['SPRITE_INTERPRETER_FLAGS'] = 'backend:%s'
import curry
print(curry.flags['rotation'])
curry.reload({'rotation': 'steps:7'})
print(curry.flags['rotation'])
os.environ['SPRITE_INTERPRETER_FLAGS'] = 'backend:%s,rotation:time:5ms'
curry.reload()
print(curry.flags['rotation'])
''' % (curry.flags['backend'], curry.flags['backend'])
    proc = cytest.run_in_subprocess(code, TIMEOUT)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout.split(), ['steps:100', 'steps:7', 'time:5ms'])

  def test_empty_variable_counts_as_unset(self):
    '''
    An empty SPRITE_ROTATION is the same as an unset one: the interpreter
    takes its default, and cytest, the runner and the harness set step
    mode over it, so an empty value cannot run the tests in time mode
    without a word.
    '''
    code = '''
import os
os.environ['SPRITE_ROTATION'] = ''
import curry
print(curry.flags['rotation'])
'''
    proc = cytest.run_in_subprocess(code, TIMEOUT)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout.strip(), 'time:10ms')
    code = '''
import os
os.environ['SPRITE_ROTATION'] = ''
import cytest
import curry
print(os.environ['SPRITE_ROTATION'], curry.flags['rotation'])
'''
    proc = cytest.run_in_subprocess(code, TIMEOUT)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout.split(), ['steps:65536', 'steps:65536'])

  def test_bad_setting_is_an_error(self):
    '''A bad value fails when the interpreter is made, with the sentence.'''
    with self.assertRaisesRegex(ValueError, "bad rotation setting 'bogus'"):
      Interpreter(flags={'rotation': 'bogus'})
    code = '''
import os
os.environ['SPRITE_ROTATION'] = 'time:10'
import curry
'''
    proc = cytest.run_in_subprocess(code, TIMEOUT)
    self.assertNotEqual(proc.returncode, 0)
    self.assertIn("bad rotation setting 'time:10'", proc.stderr)


@ONLY_CXX
class TestStepMode(cytest.TestCase):
  '''Step mode: the cadence of 65536 completed steps and exact counters.'''

  def steps_and_forks(self, goal, *args):
    before = curry.stats()
    values = list(curry.eval(goal, *args, converter='topython'))
    after = curry.stats()
    return (
        values, after['steps'] - before['steps']
      , after['forks'] - before['forks']
      )

  # The counters of countQueens 8 under the two settings of the flag
  # setfunction_failures.  A permutation of the program holds a failure (the
  # second rule of ndinsert has no case for []), and the capsule of unsafe
  # demands it.  Under 'escape', the default since 2026-10-10, that demand
  # fails the set function at once, where 'encapsulate' runs the other
  # alternatives of the capsule first; so the search takes fewer steps and
  # forks under 'escape', and the values are the same.
  COUNT_QUEENS_COUNTERS = {
      'escape': (2020742, 461457)
    , 'encapsulate': (2112920, 511484)
    }

  def check_count_queens(self, setting):
    '''countQueens 8 under one setting of setfunction_failures.'''
    if cytest.GC_STRESS:
      self.skipTest(
          'collector stress mode: countQueens 8 takes 2.1 million steps over '
          'the live state of its search; the stress mode repeats the counters '
          'of the default mode'
        )
    self.assertEqual(curry.flags['setfunction_failures'], setting)
    G = curry.import_('CxxGc')
    values, steps, forks = self.steps_and_forks(G.countQueens, 8)
    self.assertEqual(values, [92])
    self.assertEqual((steps, forks), self.COUNT_QUEENS_COUNTERS[setting])

  @cytest.with_flags(rotation=STEP_MODE)
  def test_counters_of_a_search(self):
    '''
    The counters of a search program under the cadence of 65536 steps, as
    they were before time mode existed.  countQueens 8 crosses about 31
    rotation periods with queues of several configurations inside its set
    functions; its steps and forks moved when the cadence last moved (the
    T4 entry of the TODO), when the inliner landed (the O2 and O3 entry:
    fewer steps, so the rotations fall elsewhere and the forks move with
    them), and when the default of setfunction_failures moved to 'escape'
    (the entry of 2026-10-10; COUNT_QUEENS_COUNTERS).  psort 8 ends within
    one period.  The stress mode of the collector checks psort 8 and skips
    countQueens 8.
    '''
    G = curry.import_('CxxGc')
    values, steps, forks = self.steps_and_forks(G.psort, 8)
    self.assertEqual(values, [[1, 2, 3, 4, 5, 6, 7, 8]])
    self.assertEqual((steps, forks), (16929, 1636))
    self.check_count_queens('escape')

  @cytest.with_flags(rotation=STEP_MODE, setfunction_failures='encapsulate')
  def test_counters_of_a_search_under_encapsulate(self):
    '''
    The same search under 'encapsulate', the default until 2026-10-10: the
    counters that test_counters_of_a_search pinned before the default
    moved.
    '''
    self.check_count_queens('encapsulate')

  @cytest.with_flags(rotation=STEP_MODE)
  def test_counters_repeat(self):
    '''
    Two evaluations of one search take the same steps and forks.  The board
    is seven, or six in the stress mode of the collector: countQueens 6
    crosses one rotation period (73967 steps) in about six seconds there,
    and countQueens 7 takes minutes.
    '''
    n, count = (6, 4) if cytest.GC_STRESS else (7, 40)
    G = curry.import_('CxxGc')
    first = self.steps_and_forks(G.countQueens, n)
    second = self.steps_and_forks(G.countQueens, n)
    self.assertEqual(first, second)
    self.assertEqual(first[0], [count])

  def test_no_ticker(self):
    '''Step mode never starts the ticker thread.'''
    lines = run_child(self, STEP_MODE, '''
value = next(curry.eval(M.fair))
report(value=value, status=cyrt.ticker_status(), thread=ticker_thread())
''')
    (line,) = lines
    self.assertEqual(line['value'], 42)
    self.assertFalse(line['status']['started'])
    self.assertEqual(line['status']['ticks'], 0)
    self.assertIsNone(line['thread'])

  def test_cadence(self):
    '''
    A loop beside a value yields the value after one period: the steps of
    the evaluation are a little above 65536, and a cadence of 1000 steps
    yields after about 1000.
    '''
    lines = run_child(self, STEP_MODE, '''
for mode in ['steps:65536', 'steps:1000']:
  curry.reload(
      {'backend': 'cxx', 'rotation': mode, 'defaultconverter': 'topython'}
    )
  M = curry.import_('CxxRewrite')
  before = curry.stats()['steps']
  value = next(curry.eval(M.fair))
  report(mode=mode, value=value, steps=curry.stats()['steps'] - before)
''')
    self.assertEqual([line['value'] for line in lines], [42, 42])
    self.assertGreaterEqual(lines[0]['steps'], 65536)
    self.assertLess(lines[0]['steps'], 65536 + 64)
    self.assertGreaterEqual(lines[1]['steps'], 1000)
    self.assertLess(lines[1]['steps'], 1000 + 64)


@ONLY_CXX
class TestTimeMode(cytest.TestCase):
  '''Time mode: the ticker thread, the value beside a diverging loop.'''

  def test_value_beside_a_diverging_alternative(self):
    '''
    fair = loop 0 ? 42: an endless loop of in-place steps beside a value.
    The ticker gives the alternative its turn within a quantum, so the
    value comes after a few steps of the loop in wall time, not after 65536
    steps.  The bound on the seconds is generous (see GENEROUS_SECONDS).
    '''
    lines = run_child(self, TIME_MODE, '''
next(curry.eval(M.plusOne, 1))  # the first evaluation starts the ticker
before = curry.stats()['steps']
t0 = time.monotonic()
value = next(curry.eval(M.fair))
seconds = time.monotonic() - t0
report(
    value=value, seconds=seconds, steps=curry.stats()['steps'] - before
  , status=cyrt.ticker_status()
  )
''')
    (line,) = lines
    self.assertEqual(line['value'], 42)
    self.assertLess(line['seconds'], GENEROUS_SECONDS)
    self.assertTrue(line['status']['started'])
    self.assertGreaterEqual(line['status']['ticks'], 1)
    self.assertEqual(line['status']['quantum_ns'], QUANTUM_MS * 10**6)

  def test_ticker_parks_when_idle(self):
    '''
    After an evaluation the thread parks within a quantum, and a parked
    thread has no wakeups: its ticks and its context switches do not move
    over IDLE_SECONDS.  The count of context switches of the thread comes
    from /proc/self/task; it is exact, where the CPU time of a thread has
    the resolution of a clock tick.
    '''
    lines = run_child(self, TIME_MODE, '''
value = next(curry.eval(M.fair))
tid = ticker_thread()
parked = wait_until(lambda: cyrt.ticker_status()['parked'], 1.0)
status0 = cyrt.ticker_status()
# The thread shows parked before its wait blocks: it releases the mutex
# inside the wait and may be preempted on the way to the kernel.  The count
# of its switches is taken once two reads a few milliseconds apart agree.
def settled_switches(tid):
  previous = context_switches(tid)
  for _ in range(200):
    time.sleep(0.005)
    current = context_switches(tid)
    if current == previous:
      return current
    previous = current
  return current
switches0 = settled_switches(tid)
time.sleep(%(idle)r)
status1 = cyrt.ticker_status()
switches1 = context_switches(tid)
# A running evaluation ticks again.
before = status1['ticks']
for _ in range(3):
  next(curry.eval(M.fair))
report(
    value=value, tid=tid, parked=parked, status0=status0, status1=status1
  , switches0=switches0, switches1=switches1
  , ticks_after=cyrt.ticker_status()['ticks'] - before
  )
''' % {'idle': IDLE_SECONDS})
    (line,) = lines
    self.assertEqual(line['value'], 42)
    self.assertIsNotNone(line['tid'], 'no thread named cyrt-ticker')
    self.assertTrue(line['parked'], line['status0'])
    self.assertEqual(line['status0']['active'], 0)
    self.assertEqual(line['status1']['ticks'], line['status0']['ticks'])
    self.assertEqual(line['switches1'], line['switches0'])
    self.assertTrue(line['status1']['parked'])
    self.assertGreaterEqual(line['ticks_after'], 3)

  def test_fork_child_rotates(self):
    '''
    A thread does not survive fork.  A child of os.fork after an evaluation
    starts a ticker of its own at its first evaluation, so fair yields 42
    there as well, in time mode, within the generous bound.  The forked
    child ends itself with an alarm, so a regression cannot leave a spinning
    process behind the timeout of the test.
    '''
    lines = run_child(self, TIME_MODE, '''
import signal
next(curry.eval(M.fair))
status_parent = cyrt.ticker_status()
r, w = os.pipe()
pid = os.fork()
if pid == 0:
  os.close(r)
  signal.alarm(60)
  status0 = cyrt.ticker_status()
  t0 = time.monotonic()
  value = next(curry.eval(M.fair))
  seconds = time.monotonic() - t0
  os.write(w, json.dumps({
      'value': value, 'seconds': seconds, 'status0': status0
    , 'status1': cyrt.ticker_status(), 'thread': ticker_thread()
    }).encode())
  os.close(w)
  os._exit(0)
os.close(w)
chunks = []
while True:
  chunk = os.read(r, 4096)
  if not chunk:
    break
  chunks.append(chunk)
_, status = os.waitpid(pid, 0)
report(
    parent=status_parent, exit_status=status
  , child=json.loads(b''.join(chunks).decode() or 'null')
  )
''')
    (line,) = lines
    self.assertEqual(line['exit_status'], 0)
    self.assertTrue(line['parent']['started'])
    child = line['child']
    self.assertIsNotNone(child, 'the forked child reported nothing')
    # The fresh state of the child: no thread, no ticks, before its first
    # evaluation.
    self.assertFalse(child['status0']['started'])
    self.assertEqual(child['status0']['ticks'], 0)
    self.assertEqual(child['status0']['active'], 0)
    self.assertEqual(child['value'], 42)
    self.assertLess(child['seconds'], GENEROUS_SECONDS)
    self.assertTrue(child['status1']['started'])
    self.assertGreaterEqual(child['status1']['ticks'], 1)
    self.assertIsNotNone(child['thread'])

  def test_fork_child_with_an_evaluation_in_flight(self):
    '''
    The count of the evaluations in flight at a fork carries over to the
    child, and none of them has a ticker there.  An evaluation entered in
    the child while that count is positive (a Python callback inside a
    step that evaluates, a second interpreter) starts the ticker all the
    same, because the state of the child has no thread; before the fix
    only a count of zero started it, and fair spun in the child.  The
    parent holds the count with ticker_enter, as the outermost scheduler
    of an evaluation in flight would.
    '''
    lines = run_child(self, TIME_MODE, '''
import signal
next(curry.eval(M.plusOne, 1))  # the first evaluation starts the ticker
cyrt.ticker_enter(%(quantum_ns)d)
status_parent = cyrt.ticker_status()
r, w = os.pipe()
pid = os.fork()
if pid == 0:
  os.close(r)
  signal.alarm(60)
  status0 = cyrt.ticker_status()
  t0 = time.monotonic()
  value = next(curry.eval(M.fair))
  seconds = time.monotonic() - t0
  status1 = cyrt.ticker_status()
  cyrt.ticker_leave()
  os.write(w, json.dumps({
      'value': value, 'seconds': seconds, 'status0': status0
    , 'status1': status1, 'thread': ticker_thread()
    }).encode())
  os.close(w)
  os._exit(0)
os.close(w)
chunks = []
while True:
  chunk = os.read(r, 4096)
  if not chunk:
    break
  chunks.append(chunk)
_, status = os.waitpid(pid, 0)
cyrt.ticker_leave()
report(
    parent=status_parent, exit_status=status
  , child=json.loads(b''.join(chunks).decode() or 'null')
  , parent_after=cyrt.ticker_status()
  )
''' % {'quantum_ns': QUANTUM_MS * 10**6})
    (line,) = lines
    self.assertEqual(line['exit_status'], 0)
    self.assertTrue(line['parent']['started'])
    self.assertEqual(line['parent']['active'], 1)
    self.assertEqual(line['parent_after']['active'], 0)
    child = line['child']
    self.assertIsNotNone(child, 'the forked child reported nothing')
    # The carried-over count, no thread, no ticks.
    self.assertFalse(child['status0']['started'])
    self.assertEqual(child['status0']['active'], 1)
    self.assertEqual(child['status0']['ticks'], 0)
    self.assertEqual(child['value'], 42)
    self.assertLess(child['seconds'], GENEROUS_SECONDS)
    self.assertTrue(child['status1']['started'])
    self.assertGreaterEqual(child['status1']['ticks'], 1)
    self.assertEqual(child['status1']['active'], 1)
    self.assertIsNotNone(child['thread'])

  def test_thread_start_failure_keeps_the_count(self):
    '''
    When the ticker thread cannot start, the evaluation fails with an error
    that names the ticker and step mode, and the count of the evaluations
    in flight is unchanged, so the next evaluation tries again instead of
    running without a rotation for the life of the process (the count was
    left at one, and no later evaluation started or woke a thread).  The
    child forbids new tasks with RLIMIT_NPROC after its imports: the user
    has more than one task already, so a clone fails with EAGAIN.  The
    modules are interpreted (interpret:new), so no compile forks.  Where
    the limit is not enforced (a privileged user) the thread starts and the
    test skips.
    '''
    lines = run_child(self, TIME_MODE, '''
import resource
curry.reload({
    'backend': 'cxx', 'rotation': %(time)r, 'defaultconverter': 'topython'
  , 'interpret': 'new'
  })
M = curry.import_('CxxRewrite')
resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
def attempt():
  try:
    return {'value': next(curry.eval(M.plusOne, 1)), 'error': None}
  except RuntimeError as error:
    return {'value': None, 'error': str(error)}
first = attempt()
status_first = cyrt.ticker_status()
second = attempt()
status_second = cyrt.ticker_status()
report(
    first=first, status_first=status_first, second=second
  , status_second=status_second, thread=ticker_thread()
  )
# Step mode needs no thread.
curry.reload({
    'backend': 'cxx', 'rotation': %(steps)r, 'defaultconverter': 'topython'
  , 'interpret': 'new'
  })
M = curry.import_('CxxRewrite')
report(value=next(curry.eval(M.fair)), status=cyrt.ticker_status())
''' % {'time': TIME_MODE, 'steps': STEP_MODE})
    first, second = lines
    if first['first']['error'] is None:
      self.assertTrue(first['status_first']['started'])
      self.skipTest('RLIMIT_NPROC is not enforced for this user')
    for attempt in [first['first'], first['second']]:
      self.assertIsNone(attempt['value'])
      self.assertIn('cannot start the ticker thread of time mode', attempt['error'])
      self.assertIn('SPRITE_ROTATION=steps:65536', attempt['error'])
    for status in [first['status_first'], first['status_second']]:
      self.assertFalse(status['started'])
      self.assertEqual(status['active'], 0)
      self.assertEqual(status['ticks'], 0)
    self.assertIsNone(first['thread'])
    self.assertEqual(second['value'], 42)
    self.assertFalse(second['status']['started'])

  def test_zero_quantum_is_an_error(self):
    '''
    A ticker with no quantum would never release its mutex.  The runtime
    state refuses time mode with a quantum of zero, and so does the count
    of the ticker; the Python side never passes one (parse_rotation gives
    at least one nanosecond).
    '''
    from curry.backends.cxx import cyrtbindings as cyrt
    interp = curry.getInterpreter()
    istate = interp.backend.get_interpreter_state(interp)
    M = curry.import_('CxxRewrite')
    goal = curry.expr(M.plusOne, 1)
    with self.assertRaisesRegex(ValueError, 'quantum above zero'):
      cyrt.RuntimeStateBase(
          istate, goal, False, cyrt.SETF_LAZY, cyrt.SETF_FAILURES_ENCAPSULATE
        , cyrt.NOLIMIT, 0, 0
        )
    with self.assertRaisesRegex(ValueError, 'quantum above zero'):
      cyrt.ticker_enter(0)
    # The other combinations construct: step mode needs no quantum.
    for steps, quantum_ns in [(65536, 0), (0, 10**7), (65536, 10**7)]:
      rts = cyrt.RuntimeStateBase(
          istate, goal, False, cyrt.SETF_LAZY, cyrt.SETF_FAILURES_ENCAPSULATE
        , cyrt.NOLIMIT, steps, quantum_ns
        )
      del rts

  def test_deterministic_evaluation_takes_the_same_steps(self):
    '''
    A queue of one configuration has nothing to rotate, so a deterministic
    evaluation takes the same steps in both modes.
    '''
    lines = run_child(self, TIME_MODE, '''
S = curry.import_('StackGuard')
results = {}
for mode in ['time:10ms', 'steps:65536']:
  curry.reload(
      {'backend': 'cxx', 'rotation': mode, 'defaultconverter': 'topython'}
    )
  S = curry.import_('StackGuard')
  before = curry.stats()['steps']
  value = list(curry.eval(S.lastOfRange, 200000))
  results[mode] = [value, curry.stats()['steps'] - before]
report(results=results)
''')
    (line,) = lines
    results = line['results']
    self.assertEqual(results['time:10ms'][0], [200000])
    self.assertEqual(results['time:10ms'], results['steps:65536'])


@ONLY_CXX
class TestRotationTestsInBothModes(cytest.TestCase):
  '''
  The rotation tests of the other files hold in both modes.  They need a
  rotation, not a cadence: a diverging alternative or a deep one beside a
  value, and the step additivity across rotations.  Each mode runs them in
  a child process of its own with the mode in SPRITE_ROTATION, which the
  files read through cytest.
  '''
  TESTS = [
      'unit_cxx_rewrite.TestRewrite.test_rotation_without_forward_nodes'
    , 'unit_cxx_rewrite.TestRewrite.test_collections_without_forward_nodes'
    , 'unit_cxx_stack.TestStackGuard.test_stuck_alternative_keeps_finite_one'
    , 'unit_cxx_stack.TestStackGuard.'
      'test_nested_queue_unwinds_to_enclosing_queue'
    , 'unit_cxx_stack.TestStackGuard.'
      'test_diverging_setfunction_does_not_starve_others'
    , 'unit_cxx_stack.TestStackGuard.test_nested_queue_rotates_in_place'
    , 'unit_cxx_stack.TestStackGuard.test_setfunction_in_every_iteration'
    , 'unit_cxx_stack.TestStackGuard.test_interrupted_steps_are_not_counted'
    ]

  def run_tests(self, mode):
    env = dict(os.environ, SPRITE_ROTATION=mode, PYTHONIOENCODING='utf-8')
    cmd = ['timeout', str(3 * TIMEOUT), sys.executable, '-B', '-m', 'unittest']
    proc = subprocess.run(
        cmd + self.TESTS, cwd=HERE, env=env, capture_output=True, text=True
      )
    self.assertEqual(
        proc.returncode, 0
      , 'the tests failed in mode %s; stdout:\n%s\nstderr:\n%s'
            % (mode, proc.stdout, proc.stderr)
      )
    self.assertIn('Ran %d tests' % len(self.TESTS), proc.stderr)
    self.assertIn('OK', proc.stderr.splitlines()[-1])

  def test_time_mode(self):
    self.run_tests(TIME_MODE)

  def test_step_mode(self):
    self.run_tests(STEP_MODE)
