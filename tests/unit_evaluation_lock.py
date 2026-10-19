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

@unittest.skipUnless(curry.flags['backend'] == 'cxx', 'C++ heap serialization')
class TestEvaluationLock(cytest.TestCase):
  def child(self, code):
    proc = cytest.run_in_subprocess(CHILD + code, 90, address_space=4 << 30)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout.splitlines(), ['ok'])

  def test_two_threads_keep_independent_queues_and_counts(self):
    self.child('''
serial = evaluator(100000)
assert run(serial) == [100000]
expected = serial.rts.steps_total
from curry.backends.cxx.curryrtbindings import _curryrtbindings as native
before = native._heap_status()
runs = [evaluator(100000), evaluator(100000)]
barrier = threading.Barrier(3)
values = [None, None]
errors = []
def evaluate(i):
  try:
    barrier.wait()
    values[i] = run(runs[i])
  except BaseException as error:
    errors.append(error)
threads = [threading.Thread(target=evaluate, args=(i,)) for i in range(2)]
for thread in threads: thread.start()
barrier.wait()
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
ev = evaluator(2000000)
stop = threading.Event()
ticks = []
def timer():
  while not stop.wait(0.001): ticks.append(time.monotonic())
thread = threading.Thread(target=timer)
thread.start()
try:
  assert run(ev) == [2000000]
finally:
  stop.set()
  thread.join()
assert len(ticks) >= 10, len(ticks)
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
