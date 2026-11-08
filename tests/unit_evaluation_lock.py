'''The runtime serializes its heap while the Python host remains responsive.'''
import cytest # from ./lib; must be first
import curry, unittest

CHILD = '''
import cytest, curry, threading, time, os, signal
from curry.backends.generic.eval.evaluator import Evaluator
curry.reset(backend='cxx', interpret='off')
M = curry.import_('StackGuard')
from curry.backends.cxx import curryrtbindings as curryrt
def evaluator(n):
  return Evaluator(cytest.raw.interp(),
      cytest.raw.expr(M.lastOfRange, n, typed=True))
def run(ev):
  return [cytest.raw.interp().topython(v) for v in ev.evaluate()]
'''

class TestEvaluationLock(cytest.TestCase):
  def child(self, code):
    proc = cytest.run_in_subprocess(CHILD + code, 90, address_space=4 << 30)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout.splitlines(), ['ok'])

  def test_two_threads_keep_independent_queues_and_counts(self):
    self.child('''
owned = threading.Event()
release = threading.Event()
def counted(hold=False):
  def values():
    if hold:
      owned.set()
      assert release.wait(10)
    yield from range(100000)
  return Evaluator(cytest.raw.interp(),
      cytest.raw.expr(M.lengthInts, values(), typed=True))
serial = counted()
assert run(serial) == [100000]
expected = serial.rts.steps_total
from curry.backends.cxx.curryrtbindings import _curryrtbindings as native
before = native._heap_status()
runs = [counted(hold=True), counted()]
values = [None, None]
errors = []
def evaluate(i):
  try:
    values[i] = run(runs[i])
  except BaseException as error:
    errors.append(error)
threads = [threading.Thread(target=evaluate, args=(i,)) for i in range(2)]
threads[0].start()
assert owned.wait(10)
waits = native._test_heap_waits()
threads[1].start()
try:
  deadline = time.monotonic() + 10
  while native._test_heap_waits() == waits:
    assert time.monotonic() < deadline, 'second evaluation never waited'
    release.wait(.001)
finally:
  release.set()
  for thread in threads: thread.join()
assert not errors, errors
assert values == [[100000], [100000]], values
assert [ev.rts.steps_total for ev in runs] == [expected, expected]
assert native._heap_status()['waits'] > before['waits']
assert curry.stats()['steps'] == 3 * expected, curry.stats()
print('ok')
''')

  def test_python_timer_advances_during_native_search(self):
    self.child('''
from curry.backends.cxx.curryrtbindings import _curryrtbindings as native
# Force the native large-stack route and hold its startup until sampled.
curry.reset(backend='cxx', interpret='off', stack_limit=65536)
M = curry.import_('StackGuard')
ev = evaluator(2000000)
sampled = threading.Event()
errors = []
def timer():
  try:
    deadline = time.monotonic() + 10
    while not native._test_worker_startup_paused():
      assert time.monotonic() < deadline, 'native search never started'
      sampled.wait(.001)
    sampled.set()
  except BaseException as error:
    errors.append(error)
  finally:
    native._test_resume_worker_startup()
native._test_pause_worker_startup()
thread = threading.Thread(target=timer)
thread.start()
try:
  deep = Evaluator(cytest.raw.interp(), cytest.raw.expr(M.deep, 3000, typed=True))
  assert run(deep) == [3000]
  assert run(ev) == [2000000]
  assert sampled.wait(10), 'timer did not sample the native search'
finally:
  native._test_resume_worker_startup()
  thread.join()
assert not errors, errors
print('ok')
''')

  def test_python_generator_can_evaluate_again(self):
    self.child('''
P = curry.import_('Prelude')
def callback():
  for n in (10, 20, 30):
    value, = curry.eval(M.lastOfRange(n))
    yield value
value, = curry.eval(cytest.raw.expr(M.lengthInts, callback(), typed=True))
assert value == 3, value
print('ok')
''')

  @cytest.posix_only('uses POSIX os.kill(SIGINT) delivery')
  def test_interrupt_reaches_main_thread(self):
    self.child('''
# Preparation is complete before the signal is scheduled.
ev = Evaluator(cytest.raw.interp(), cytest.raw.expr(M.loop))
timer = threading.Timer(0.2, lambda: os.kill(os.getpid(), signal.SIGINT))
timer.start()
try:
  run(ev)
except KeyboardInterrupt:
  print('ok')
else:
  raise AssertionError('the evaluation ignored SIGINT')
finally:
  timer.join()
''')

  @cytest.posix_only('uses POSIX os.kill(SIGINT) delivery')
  def test_interrupt_while_waiting_for_heap(self):
    self.child('''
started = threading.Event()
finish = threading.Event()
P = curry.import_('Prelude')
def callback():
  started.set()
  finish.wait(5)
  yield 1
search = curry.eval(cytest.raw.expr(M.lengthInts, callback(), typed=True))
errors = []
def evaluate():
  try: assert next(search) == 1
  except BaseException as error: errors.append(error)
thread = threading.Thread(target=evaluate)
thread.start()
assert started.wait(5)
timer = threading.Timer(0.2, lambda: os.kill(os.getpid(), signal.SIGINT))
timer.start()
try:
  next(curry.eval(M.lastOfRange(10)))
except KeyboardInterrupt:
  print('ok')
else:
  raise AssertionError('the heap wait ignored SIGINT')
finally:
  finish.set()
  thread.join()
  timer.join()
assert not errors, errors
''')

  def test_callback_reenters_on_the_large_stack_worker(self):
    self.child('''
curry.reset(backend='cxx', interpret='off', stack_limit=65536)
M = curry.import_('StackGuard')
def callback():
  for i in range(3000):
    if i in (0, 1500):
      value, = curry.eval(M.lastOfRange(10))
      assert value == 10
    yield 1
ev = Evaluator(cytest.raw.interp(),
    cytest.raw.expr(M.lengthInts, callback(), typed=True))
assert run(ev) == [3000]
assert ev.rts._escalated
print('ok')
''')

  def test_worker_is_reused_across_resets(self):
    self.child('''
for i in range(10):
  curry.reset(backend='cxx', interpret='off', stack_limit=65536)
  M = curry.import_('StackGuard')
  ev = Evaluator(cytest.raw.interp(), cytest.raw.expr(M.deep, 3000, typed=True))
  assert run(ev) == [3000]
  assert ev.rts._escalated
print('ok')
''')

  def test_returned_graph_survives_concurrent_collection(self):
    self.child('''
N = curry.compile('values :: [Int]\\nvalues = [1..1000] ? [1001..2000]')
stop = threading.Event()
errors = []
def collect():
  try:
    while not stop.wait(0.001): curryrt.gc_collect()
  except BaseException as error: errors.append(error)
thread = threading.Thread(target=collect)
thread.start()
try:
  for i in range(10):
    assert list(curry.eval(N.values)) == [list(range(1, 1001)), list(range(1001, 2001))]
finally:
  stop.set()
  thread.join()
assert not errors, errors
print('ok')
''')

  @cytest.posix_only('uses POSIX os.kill(SIGINT) delivery')
  def test_interrupt_while_waiting_for_worker(self):
    self.child('''
curry.reset(backend='cxx', interpret='off', stack_limit=65536)
M = curry.import_('StackGuard')
ev = Evaluator(cytest.raw.interp(), cytest.raw.expr(M.deep, 1000000000, typed=True))
timer = threading.Timer(0.2, lambda: os.kill(os.getpid(), signal.SIGINT))
timer.start()
try:
  run(ev)
except KeyboardInterrupt:
  assert ev.rts._escalated
else:
  raise AssertionError('the worker wait ignored SIGINT')
finally:
  timer.join()
# The interrupted job has stopped before control returns to the host.
assert run(evaluator(10)) == [10]
print('ok')
''')
