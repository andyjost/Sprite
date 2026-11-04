'''Finalization under the JIT lock must never wait for the heap (#182).'''
import cytest # from ./lib; must be first
import os, pathlib, subprocess, sys, tempfile, unittest
from curry.backends.cxx import llvmjit

CHILD = r'''
import cytest, curry, gc, threading
from curry.backends.cxx import llvmjit, curryrtbindings as rt
native = rt._curryrtbindings
curry.reset(backend='cxx', jit='off')
gc.collect()
gc.disable()
errors = []
def checked(action):
  try:
    action()
  except BaseException as error:
    errors.append(error)
def finish(thread):
  thread.join(10)
  assert not thread.is_alive(), 'finalizer waited for the heap'
  assert not errors, errors

def cycle():
  term = curry.term(123456789)
  state = rt.InterpreterState()
  rts = rt.RuntimeStateBase(state, term._node, False, rt.NOLIMIT, 65536, 0)
  module = rt.Module.find_or_create('FinalizationOrphan')
  values = [term, state, rts, module]
  values.append(values)

# Own the wrappers on their collecting thread: free-threaded Python can
# otherwise hand their last decrefs back to the creating thread.
def cycle_collector():
  ready = threading.Event()
  collect = threading.Event()
  def worker():
    cycle()
    ready.set()
    assert collect.wait(10)
    gc.collect()
  thread = threading.Thread(target=lambda: checked(worker))
  thread.start()
  assert ready.wait(10)
  return thread, collect

# Waits use events only; no sleep establishes the lock interleaving.
def collect_under_jit_lock(action):
  locked = threading.Event()
  heap = threading.Event()
  def collect():
    cycle()
    with llvmjit._lock:
      locked.set()
      assert heap.wait(10)
      gc.collect()
  thread = threading.Thread(target=lambda: checked(collect))
  thread.start()
  assert locked.wait(10)
  def transaction():
    heap.set()
    action()
  native._metadata_call(transaction)
  finish(thread)
  native._heap_drain()
  assert native._heap_pending_count() == 0
'''


class TestHeapFinalization(cytest.TestCase):
  def child(self, code, *args):
    # subprocess.run kills and reaps the child on timeout, including when a
    # native finalizer has left a non-daemon Python thread stuck.
    try:
      result = subprocess.run([sys.executable, '-c', CHILD + code, *args],
          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
    except subprocess.TimeoutExpired as error:
      self.fail('finalization child timed out (and was reaped): %s' % error.stderr)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

  @unittest.skipUnless(llvmjit.available(), 'requires LLVM')
  def test_deterministic_resolver_lock_cycle(self):
    self.child('''
# The original #182 reproducer, also collecting both heap-owned state types.
llvmjit._get()
collect_under_jit_lock(lambda: llvmjit._resolve_cached(0))
''')

  @unittest.skipUnless(llvmjit.available(), 'requires LLVM')
  def test_actual_reset_lock_cycle(self):
    self.child('''
collect_under_jit_lock(lambda: curry.reset(jit='off'))
assert list(curry.eval(curry.term(7))) == [7]
''')

  def test_acquisition_drains_roots_and_states(self):
    self.child('''
roots = rt.gc_num_roots()
queues = rt.gc_queue_count()
thread, collect = cycle_collector()
assert rt.gc_queue_count() == queues + 1
# A worker must finish collecting while the main thread still owns the heap.
def transaction():
  collect.set()
  finish(thread)
  assert native._heap_pending_count() >= 4
native._metadata_call(transaction)
# The count query does not acquire the heap; the next ordinary binding does.
assert native._heap_pending_count() >= 4
assert rt.gc_queue_count() == queues
assert rt.gc_num_roots() == roots
assert native._heap_pending_count() == 0
''')

  def test_finalization_on_heap_owner(self):
    self.child('''
roots = rt.gc_num_roots()
queues = rt.gc_queue_count()
cycle()
assert rt.gc_queue_count() == queues + 1
def transaction():
  # Finalizers on the heap owner must acquire recursively and clean up now.
  with llvmjit._lock:
    gc.collect()
  assert native._heap_pending_count() == 0
  assert rt.gc_queue_count() == queues
  assert rt.gc_num_roots() == roots
native._metadata_call(transaction)
''')

  def test_reset_drains_and_discards_stale_removal(self):
    self.child('''
term = curry.term(987654321)
node = term._node
roots = rt.gc_root_count(node)
def transaction():
  # Model a removal from a replaced heap, at an address also rooted in the
  # current heap. Applying it would silently remove the live term's root.
  thread = threading.Thread(target=lambda: checked(
      lambda: native._test_defer_stale_root(node)))
  thread.start()
  finish(thread)
  assert native._heap_pending_count() == 1
  curry.reset(jit='off')
  assert native._heap_pending_count() == 0
native._metadata_call(transaction)
assert rt.gc_root_count(node) == roots
rt.gc_collect()
assert rt.gc_root_count(node) == roots
assert '987654321' in str(node)
''')

  def test_shutdown_drains_before_late_finalizers(self):
    self.child('''
thread, collect = cycle_collector()
def transaction():
  collect.set()
  finish(thread)
  assert native._heap_pending_count() >= 4
  rt._shutdown_native()
  assert native._heap_pending_count() == 0
native._metadata_call(transaction)
# The real atexit hook runs a second time; retained roots and synchronization
# also support wrappers destroyed after it, during Python teardown.
late_term = curry.term(7777777)
# Leave actual pending work for the registered atexit shutdown hook.
import atexit
atexit.unregister(rt._shutdown_native)
def after_shutdown():
  if native._heap_pending_count():
    import os
    os._exit(91)
atexit.register(after_shutdown)
atexit.register(rt._shutdown_native)
thread, collect = cycle_collector()
def leave_pending():
  collect.set()
  finish(thread)
  assert native._heap_pending_count() >= 4
native._metadata_call(leave_pending)
assert native._heap_pending_count() >= 4
''')

  @unittest.skipUnless(llvmjit.available(), 'requires LLVM')
  def test_cached_call_during_collecting_hot_compile(self):
    with tempfile.TemporaryDirectory(prefix='sprite-finalization-') as work:
      source = pathlib.Path(work) / 'FinalizationCache.curry'
      source.write_text('''module FinalizationCache where
fib :: Int -> Int
fib n = if n < 2 then n else fib (n-1) + fib (n-2)
''')
      self.child('''
import os, sys
# Attach the images without eagerly compiling a cold Prelude. Only fib
# needs a persistent object for the resolver in the next child.
os.environ['SPRITE_JIT_THRESHOLD'] = '1000000000'
curry.reset(interpret='all', jit='hot', jit_backend='llvm')
M = curry.import_(sys.argv[1])
assert rt.icurry_hot_threshold() == 1000000000
llvmjit.compile(M.fib.info, 'FinalizationCache.fib')
assert rt.icurry_is_jit(M.fib.info)
''', str(source))
      self.child('''
import os, sys
from unittest import mock
# Prevent the real hot thread from racing the event-controlled compile.
os.environ['SPRITE_JIT_THRESHOLD'] = '1000000000'
curry.reset(interpret='all', jit='hot', jit_backend='llvm')
M = curry.import_(sys.argv[1])
assert rt.icurry_hot_threshold() == 1000000000
assert not rt.icurry_is_jit(M.fib.info)
Hot = curry.compile('hot :: Int -> Int\\nhot n = n + 1\\n')
assert rt.icurry_hot_threshold() == 1000000000
jit = llvmjit._jit
batch = jit.compile_batch
locked = threading.Event()
heap = threading.Event()
def collecting_batch(*args, **kwds):
  assert llvmjit._lock.locked()
  locked.set()
  assert heap.wait(10)
  gc.collect()
  return batch(*args, **kwds)
def compile_hot():
  cycle()
  info = Hot.hot.info
  llvmjit._compile_groups(jit, [(info, jit.names[rt.icurry_address(info)])], post=True)
with mock.patch.object(jit, 'compile_batch', side_effect=collecting_batch):
  thread = threading.Thread(target=lambda: checked(compile_hot))
  thread.start()
  assert locked.wait(10)
  def resolve():
    heap.set()
    address = llvmjit._resolve_cached(rt.icurry_address(M.fib.info))
    assert address, 'cached function was not resolved'
  native._metadata_call(resolve)
  finish(thread)
assert list(curry.eval(M.fib(12))) == [144]
assert rt.icurry_is_jit(M.fib.info)
assert jit.linked > 0
assert not jit.errors, jit.last_error
''', str(source))
