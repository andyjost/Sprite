'''Process fork ownership and the idle/busy boundary (REVASTRA1 5/8/9/10/13).'''
import cytest # from ./lib; must be first
import os, signal, subprocess, sys, unittest
from curry.backends.cxx import llvmjit


PREAMBLE = r'''
import cytest, curry, os, signal, sys, tempfile, threading, time, traceback
from curry.backends.cxx import curryrtbindings as rt, tiered, llvmjit
from curry.objects.handle import getHandle
native = rt._curryrtbindings
curry.reset(interpret='all', jit='off', rotation='time:1ms')

def until(predicate):
  deadline = time.monotonic() + 10
  while not predicate():
    assert time.monotonic() < deadline, 'handshake timed out'
    time.sleep(.001)

def rejected(action):
  try:
    action()
  except BaseException as error:
    assert type(error).__name__ == 'ForkError', repr(error)
    assert 'Sprite was busy when the process forked' in str(error), str(error)
    assert isinstance(error, curry.exceptions.ForkError)
  else:
    raise AssertionError('busy child accepted a Sprite call')

def fork_check(action):
  pid = os.fork()
  if pid == 0:
    status = 0
    try:
      action()
    except BaseException:
      traceback.print_exc()
      status = 1
    # Run Python and native exit handlers without unwinding parent-only
    # finally blocks below the fork helper.
    import atexit, ctypes
    atexit._run_exitfuncs()
    ctypes.CDLL(None).exit(status)
  wait_child(pid)

def wait_child(pid):
  deadline = time.monotonic() + 3
  while True:
    done, status = os.waitpid(pid, os.WNOHANG)
    if done:
      assert os.waitstatus_to_exitcode(status) == 0, ('child failed', status)
      return
    if time.monotonic() >= deadline:
      os.kill(pid, signal.SIGKILL)
      os.waitpid(pid, 0)
      raise AssertionError('fork child timed out after 3 seconds (reaped)')
    time.sleep(.005)

def submit(argv, name='ForkJob'):
  rt.tiered_submit(curry._interpreter_._its, name, argv, [], '', '', '', [])
'''


@cytest.posix_only('requires os.fork and POSIX file descriptors')
class TestProcessFork(cytest.TestCase):
  def run_case(self, code, timeout=90):
    process = subprocess.Popen([sys.executable, '-c', PREAMBLE + code],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True)
    try:
      stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
      os.killpg(process.pid, signal.SIGKILL)
      stdout, stderr = process.communicate()
      self.fail('scenario timed out and was reaped: ' + stdout + stderr)
    self.assertEqual(process.returncode, 0, stdout + stderr)

  def test_idle_compile_worker_is_fresh(self):
    self.run_case(r'''
submit([sys.executable, '-c', 'pass'])
assert rt.tiered_wait(10)
rt.tiered_results()
def child():
  submit([sys.executable, '-c', 'pass'])
  while not rt.tiered_wait(.1):
    pass
fork_check(child)
submit([sys.executable, '-c', 'pass'])
assert rt.tiered_wait(10), 'parent worker stopped'
''')

  def test_busy_compile_never_kills_parent_compiler(self):
    self.run_case(r'''
ready_r, ready_w = os.pipe()
resume_r, resume_w = os.pipe()
os.set_inheritable(ready_w, True)
os.set_inheritable(resume_r, True)
command = ('import os; os.write(%d, b"ready"); os.read(%d, 1); '
    'os.write(%d, b"done")' % (ready_w, resume_r, ready_w))
submit([sys.executable, '-c', command])
assert os.read(ready_r, 5) == b'ready'
os.close(ready_w)
def child():
  rejected(rt.tiered_cancel)
  rejected(curry.reset)
try:
  fork_check(child)
  assert rt.tiered_status()['running'] == 1, 'child killed parent compiler'
finally:
  os.write(resume_w, b'x')
  assert rt.tiered_wait(10)
  rt.tiered_poll()
  results = rt.tiered_results()
  # Completion acknowledgement proves the compiler survived child exit.
  assert os.read(ready_r, 4) == b'done', 'child killed parent compiler'
  for fd in (ready_r, resume_r, resume_w):
    os.close(fd)
assert curry.eval(curry.term(42)).one() == 42
''')

  def test_busy_python_compilation_rejects_child(self):
    self.run_case(r'''
import importlib
compilation = importlib.import_module('curry.interpreter.compile')
original = compilation._module_source
entered, resume = threading.Event(), threading.Event()
errors, modules = [], []
def blocked_source(*args):
  entered.set()
  assert resume.wait(10)
  return original(*args)
def compile_module():
  try:
    modules.append(curry.compile('answer :: Int\nanswer = 42'))
  except BaseException as error:
    errors.append(error)
compilation._module_source = blocked_source
thread = threading.Thread(target=compile_module)
thread.start()
assert entered.wait(10)
try:
  fork_check(lambda: rejected(curry.reset))
finally:
  resume.set()
  thread.join(10)
  compilation._module_source = original
assert not thread.is_alive() and not errors, errors
assert curry.eval(modules[0].answer).one() == 42
''')

  def test_busy_jit_cache_reader_rejects_before_read_lock(self):
    self.run_case(r'''
stream = tempfile.TemporaryFile()
stream.write(b'cache')
stream.flush()
index = llvmjit._IndexedObjects('cache', [dict()], stream)
entered, resume = threading.Event(), threading.Event()
pread = os.pread
errors = []
def blocked_read(fd, size, offset):
  entered.set()
  assert resume.wait(10)
  return pread(fd, size, offset)
def reader():
  try:
    assert index.read_at(0, 5) == b'cache'
  except BaseException as error:
    errors.append(error)
os.pread = blocked_read
thread = threading.Thread(target=reader)
thread.start()
assert entered.wait(10)
def child():
  rejected(lambda: index.read_at(0, 5))
  rejected(index.close)
  rejected(lambda: curry.eval(curry.term(1)).one())
try:
  fork_check(child)
finally:
  resume.set()
  thread.join(10)
  os.pread = pread
assert not thread.is_alive() and not errors, errors
assert index.read_at(0, 5) == b'cache'
index.close()
assert curry.eval(curry.term(42)).one() == 42
''')

  def test_busy_native_open_exits_without_handle_mutex(self):
    self.run_case(r'''
module = curry.compile('open :: String -> IO Handle\nopen p = openFile p ReadMode',
    imports=['System.IO'])
directory = tempfile.mkdtemp()
fifo = os.path.join(directory, 'input')
os.mkfifo(fifo)
errors = []
def opener():
  try:
    curry.eval(module.open(fifo)).one()
  except BaseException as error:
    errors.append(error)
thread = threading.Thread(target=opener)
thread.start()
# No writer exists: once the mutex is held, open cannot complete.
until(native._test_handle_mutex_held)
def child():
  rejected(lambda: curry.term(1))
  rejected(rt.shutdown_handles)
try:
  fork_check(child)
finally:
  writer = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
  thread.join(10)
  os.close(writer)
  os.unlink(fifo)
  os.rmdir(directory)
assert not thread.is_alive() and not errors, errors
rt.shutdown_handles()
assert curry.eval(curry.term(42)).one() == 42
''')

  def test_dynamic_directory_belongs_to_creating_process(self):
    for collect in (False, True):
      with self.subTest(collect=collect):
        self.run_case(r'''
module = curry.compile('answer :: Int\nanswer = 42')
icur = getHandle(module).icurry
directory = icur.metadata['all.tmpd']
def child():
  if %r:
    icur._finalizer_()
fork_check(child)
assert os.path.isdir(directory), 'child removed parent dynamic directory'
assert curry.eval(module.answer).one() == 42
icur._finalizer_()
assert not os.path.exists(directory), 'parent finalizer did not remove directory'
''' % collect)

  def test_callback_fork_stops_interrupted_evaluation(self):
    self.run_case(r'''
module = curry.compile('loop :: Int\nloop = loop\nfair :: [Int] -> Int\n'
    'fair (x:_) = loop ? x')
parent = os.getpid()
children = []
directory = getHandle(module).icurry.metadata['all.tmpd']
def values():
  pid = os.fork()
  if pid:
    children.append(pid)
  else:
    # Return straight into the interrupted native evaluation.
    pass
  yield 42
try:
  value = next(curry.eval(module.fair(iter(values()))))
except BaseException as error:
  if os.getpid() == parent:
    raise
  assert type(error).__name__ == 'ForkError', repr(error)
  assert 'Sprite was busy when the process forked' in str(error)
  for action in (curry.reset, curry.stats, lambda: curry.term(1),
      lambda: curry.compile('x = True'), lambda: curry.import_('Prelude')):
    rejected(action)
  import gc
  gc.collect()
  sys.exit(0)
else:
  assert os.getpid() == parent, 'child continued an interrupted evaluation'
  assert value == 42
assert len(children) == 1
wait_child(children[0])
assert os.path.isdir(directory), 'busy child removed parent source'
assert curry.eval(curry.term(7)).one() == 7
''')

  @unittest.skipUnless(llvmjit.available(), 'requires the LLVM JIT')
  def test_idle_child_restarts_hot_jit(self):
    self.run_case(r'''
os.environ['SPRITE_JIT_THRESHOLD'] = '1'
original_loop = llvmjit._hot_loop
parked, resume = threading.Event(), threading.Event()
def parked_loop():
  parked.set()
  assert resume.wait(10)
# Park the existing worker outside Sprite work, at a deterministic idle point.
llvmjit._hot_loop = parked_loop
curry.reset(interpret='all', jit='hot', jit_backend='llvm')
module = curry.compile('inc :: Int -> Int\ninc x = x + 1')
assert parked.wait(10)
parent_worker = llvmjit._hot_thread
llvmjit._hot_loop = original_loop
goal = module.inc(41)
# Leave a hot request queued in the parent; the child must count afresh.
assert curry.eval(module.inc(1)).one() == 2
def child():
  assert curry.eval(goal).one() == 42
  def compiled():
    rt.icurry_apply_posted()
    return rt.icurry_is_jit(module.inc.info)
  until(compiled)
  assert llvmjit._hot_thread is not parent_worker
  assert llvmjit._hot_thread.is_alive()
try:
  fork_check(child)
finally:
  resume.set()
  parent_worker.join(10)
assert not parent_worker.is_alive()
curry.reset(jit='off')
assert curry.eval(curry.term(7)).one() == 7
''')

  @unittest.skipUnless(llvmjit.available(), 'requires the LLVM JIT')
  def test_idle_child_evaluates_compiles_and_jits(self):
    self.run_case(r'''
assert llvmjit.available(), 'test requires the installed LLVM JIT'
module = curry.compile('plus :: Int -> Int\nplus x = x + 1')
# Retain completed code, and start then park the existing workers.
llvmjit.compile(module.plus.info, module.__name__ + '.plus')
assert rt.icurry_is_jit(module.plus.info)
assert curry.eval(module.plus(1)).one() == 2
submit([sys.executable, '-c', 'pass'])
assert rt.tiered_wait(10)
def child():
  assert curry.eval(module.plus(2)).one() == 3
  fresh = curry.compile('answer :: Int\nanswer = 42')
  llvmjit.compile(fresh.answer.info, fresh.__name__ + '.answer')
  assert rt.icurry_is_jit(fresh.answer.info)
  assert curry.eval(fresh.answer).one() == 42
  assert rt.ticker_status()['started'], 'idle child did not start its ticker'
  submit([sys.executable, '-c', 'pass'])
  while not rt.tiered_wait(.1):
    pass
fork_check(child)
assert curry.eval(module.plus(3)).one() == 4
''')
