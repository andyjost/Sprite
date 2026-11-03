'''Fork fences protect detached cleanup and completion drains (#188).'''
import cytest # from ./lib; must be first
import os, subprocess, sys, unittest

CHILD = r'''
import cytest, curry, os, signal, threading, time, traceback
from curry.backends.cxx import curryrtbindings as rt
native = rt._curryrtbindings
curry.reset(backend='cxx', jit='off')
native._heap_drain()
errors = []
def checked(action):
  try:
    action()
  except BaseException as error:
    errors.append(error)
def until(predicate):
  deadline = time.monotonic() + 10
  while not predicate():
    assert time.monotonic() < deadline, 'handshake timed out'
    time.sleep(0.001)
def join(thread):
  thread.join(10)
  assert not thread.is_alive(), 'thread did not finish'
  assert not errors, errors

native._test_pause_drain()
def enqueue():
  for _ in range(7):
    native._test_dispose()
def transaction():
  thread = threading.Thread(target=lambda: checked(enqueue))
  thread.start()
  join(thread)
  assert native._heap_pending_count() == 7
native._metadata_call(transaction)
# This drain detaches all seven actions while owning the heap.
drain = threading.Thread(target=lambda: checked(native._test_run_drain))
drain.start()
until(native._test_drain_paused)
assert native._heap_pending_count() == 0

def resume():
  # Stay native: Python suspends its other threads around os.fork.
  native._test_resume_at_fork()
resumer = threading.Thread(target=lambda: checked(resume))
resumer.start()
until(native._test_resumer_ready)
pid = os.fork()
if pid == 0:
  signal.alarm(15)
  try:
    assert native._test_applied() == 7, 'detached actions lost at fork'
    assert native._heap_pending_count() == 0
    native._heap_drain()
    assert native._test_applied() == 7, 'cleanup applied twice'
    os._exit(0)
  except BaseException:
    traceback.print_exc()
    os._exit(1)
try:
  _, status = os.waitpid(pid, 0)
finally:
  native._test_resume_drain()
  join(resumer)
  join(drain)
assert os.waitstatus_to_exitcode(status) == 0
assert native._test_applied() == 7
assert native._heap_pending_count() == 0
'''

class TestHeapForkDrain(cytest.TestCase):
  @unittest.skipUnless(hasattr(os, 'fork'), 'requires os.fork')
  def test_fork_during_detached_drain(self):
    try:
      result = subprocess.run([sys.executable, '-c', CHILD],
          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=45)
    except subprocess.TimeoutExpired as error:
      self.fail('fork/drain child timed out and was reaped: %s' % error.stderr)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

  def check_native_hook(self, expression):
    code = ('import cytest, curry; '
            'from curry.backends.cxx import curryrtbindings as rt; '
            'assert rt._curryrtbindings.' + expression)
    result = subprocess.run([sys.executable, '-c', code],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

  def test_completion_drain(self):
    self.check_native_hook('_test_completion(False)')

  def test_retirement_drain(self):
    self.check_native_hook('_test_completion(True)')

  @unittest.skipUnless(hasattr(os, 'fork'), 'requires os.fork')
  def test_child_drain_fence(self):
    self.check_native_hook('_test_child_fence()')
