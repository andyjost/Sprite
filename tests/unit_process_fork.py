'''Process fork ownership and the idle/busy boundary (REVASTRA1 5/8/9/10/13).'''
import cytest # from ./lib; must be first
import os, signal, subprocess, sys, unittest
from curry.backends.cxx import llvmjit


PREAMBLE = r'''
import cytest, curry, contextlib, os, shutil, signal, sys, tempfile, threading, time, traceback
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

def wait_child(pid, exitcode=0):
  deadline = time.monotonic() + 3
  while True:
    done, status = os.waitpid(pid, os.WNOHANG)
    if done:
      assert os.waitstatus_to_exitcode(status) == exitcode, ('child failed', status)
      return
    if time.monotonic() >= deadline:
      os.kill(pid, signal.SIGKILL)
      os.waitpid(pid, 0)
      raise AssertionError('fork child timed out after 3 seconds (reaped)')
    time.sleep(.005)

def submit(argv, name='ForkJob'):
  rt.tiered_submit(curry._interpreter_._its, name, argv, [], '', '', '', [])

@contextlib.contextmanager
def fork_directory():
  owner = os.getpid()
  work = tempfile.mkdtemp()
  try:
    yield work
  finally:
    if os.getpid() == owner:
      shutil.rmtree(work)

def during(action, target, attribute, matches=lambda *a, **k: True):
  from unittest import mock
  original = getattr(target, attribute)
  entered, resume = threading.Event(), threading.Event()
  results, errors = [], []
  def pause(*args, **kwds):
    if matches(*args, **kwds) and not entered.is_set():
      entered.set()
      assert resume.wait(10), 'parent operation was not released'
    return original(*args, **kwds)
  def run():
    try:
      results.append(action())
    except BaseException as error:
      traceback.print_exc()
      errors.append(error)
  with mock.patch.object(target, attribute, pause):
    thread = threading.Thread(target=run)
    thread.start()
    try:
      assert entered.wait(10), ('operation did not reach', attribute, errors)
      def child():
        rejected(curry.reset)
        rejected(curry._interpreter_.stats)
      fork_check(child)
    finally:
      resume.set()
      thread.join(30)
  assert not thread.is_alive() and not errors, errors
  return results[0]
'''


ENTRY_FIXTURE = r'''
from curry.utility import locking
from curry.objects.results import Results
module = curry.compile('import Sprite.Stream\n'
    'out :: [Int] -> IO ()\nout xs = yield (head xs) >> yield (43 :: Int)')
interp = curry._interpreter_
term = curry.term(7)
other = curry.term(7)
# Warm the cached signature and module-symbol paths before the fork.
assert str(interp.typeof(term))
held = module.out
closed_results = curry.eval(term)
closed_results.close()
unstarted_results = curry.eval(term)
closed_stream = curry.stream(module.out([42]))
closed_stream.close()
unstarted_stream = curry.stream(module.out([42]))
children, failures = [], []
parent = os.getpid()

def entries():
  actions = []
  for kind in ('results', 'stream'):
    for state in ('active', 'closed', 'unstarted'):
      value = globals()[state + '_' + kind]
      actions.extend(((state + ' ' + kind + ' next', lambda v=value: next(v)),
          (state + ' ' + kind + ' close', value.close)))
      if kind == 'results':
        actions.append((state + ' results one', value.one))
  actions.extend((('interpreter stats', interp.stats),
      ('interpreter typeof', lambda: interp.typeof(term)),
      ('term str', lambda: str(term)), ('term repr', lambda: repr(term)),
      ('term equality', lambda: term == other), ('term hash', lambda: hash(term)),
      ('module attribute', lambda: module.out),
      ('module item', lambda: module['out']),
      ('term metadata', lambda: held.signature)))
  return actions
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

  def test_child_does_not_close_parent_command(self):
    self.command_fork(native_close=False)

  def test_child_rejects_parent_native_command_handle(self):
    self.command_fork(native_close=True)

  def command_fork(self, native_close):
    self.run_case(r"""
import shlex
from pathlib import Path
curry.path.insert(0, str(Path('data/curry/cpm_index').resolve()))
module = curry.compile('import System.IO\nimport System.IOExts\n'
    'launch :: String -> IO (Handle,Handle,Handle)\nlaunch = execCmd\n'
    'close :: Handle -> IO ()\nclose = hClose\n')
script = 'import sys; print("ready", flush=True); print(sys.stdin.read(4), flush=True)'
command = 'exec ' + shlex.quote(sys.executable) + ' -c ' + shlex.quote(script)
handles = curry.eval(module.launch(command)).one()
process, = rt._command_processes
assert process.stdout.readline() == 'ready\n'
tokens = list(rt._command_streams)
process.stdin.write('STOP')
try:
  def child():
    if NATIVE_CLOSE:
      try:
        curry.eval(module.close(handles[0])).one()
      except Exception as error:
        assert 'handle belongs to another process' in str(error), str(error)
      else:
        raise AssertionError('child closed parent native command handle')
    else:
      rt._standard_stream(tokens[0], 'release', '', 0)
    own = list(map(int, rt._standard_stream(0, 'exec', 'exit 0', 0).split()))
    for token in own:
      rt._standard_stream(token, 'release', '', 0)
    assert not set(tokens).intersection(rt._command_streams), 'inherited command streams'
  fork_check(child)
  assert process.poll() is None, 'child stopped parent command'
  process.stdin.flush()
  assert process.stdout.readline() == 'STOP\n'
  for token in tokens:
    rt._standard_stream(token, 'release', '', 0)
  process.wait(timeout=3)
  rt._reap_commands()
  assert process not in rt._command_processes
finally:
  rt._shutdown_native()
""".replace('NATIVE_CLOSE', repr(native_close)))

  def test_child_leaves_retired_parent_command_alive(self):
    self.run_case(r"""
import gc, shlex
from pathlib import Path
curry.path.insert(0, str(Path('data/curry/cpm_index').resolve()))
module = curry.compile('import System.IO\nimport System.IOExts\n'
    'launch :: String -> IO (Handle,Handle,Handle)\nlaunch = execCmd\n')
command = 'exec ' + shlex.quote(sys.executable) + ' -c ' + shlex.quote(
    'import sys; print("ready", flush=True); sys.stdin.read()')
handles = curry.eval(module.launch(command)).one()
process, = rt._command_processes
assert process.stdout.readline() == 'ready\n'
tokens = list(rt._command_streams)
del handles
gc.collect()
rt.gc_collect()
try:
  def child():
    assert not rt._command_processes and not rt._command_pending
    own = curry.eval(module.launch('exit 0')).one()
    del own
    gc.collect()
    rt.gc_collect()
  fork_check(child)
  assert process.poll() is None, 'child retired parent command'
  for token in tokens:
    rt._standard_stream(token, 'release', '', 0)
  process.wait(timeout=3)
  rt._reap_commands()
  assert process not in rt._command_processes
finally:
  rt._shutdown_native()
""")

  def test_signal_fork_during_command_retirement(self):
    self.command_cleanup_fork('retirement')

  def test_signal_fork_during_explicit_command_close(self):
    self.command_cleanup_fork('close')

  def test_signal_fork_during_command_reap(self):
    self.command_cleanup_fork('reap')

  def test_signal_fork_during_command_shutdown(self):
    self.command_cleanup_fork('shutdown')

  def test_full_command_pipe_close_and_flush_are_interruptible(self):
    for operation in ('prim_hClose', 'prim_hFlush'):
      with self.subTest(operation=operation):
        self.run_case('operation = %r\n' % operation + r"""
import select, shlex
command = 'exec ' + shlex.quote(sys.executable) + ' -c ' + shlex.quote(
    'import signal; signal.pause()')
tokens = list(map(int, rt._standard_stream(0, 'exec', command, 0).split()))
process, = rt._command_processes
descriptor = process.stdin.fileno()
os.set_blocking(descriptor, False)
try:
  while True:
    os.write(descriptor, b'x' * 4096)
except BlockingIOError:
  pass
finally:
  os.set_blocking(descriptor, True)
process.stdin.write('STOP')
read_end, write_end = os.pipe()
watchdog = os.fork()
if watchdog == 0:
  os.close(write_end)
  ready = select.select([read_end], [], [], 3)[0]
  if not ready:
    os.write(2, b'full-pipe operation timed out after 3 seconds (command killed)\n')
    os.killpg(process.pid, signal.SIGKILL)
  os._exit(0 if ready else 1)
os.close(read_end)
class Interrupted(Exception): pass
def interrupt(signum, frame):
  raise Interrupted()
previous = signal.signal(signal.SIGALRM, interrupt)
started = time.monotonic()
try:
  # TextIOWrapper.close can flush again through BufferedWriter.close after
  # the first flush raises, so interrupt both attempts.
  signal.setitimer(signal.ITIMER_REAL, .1, .1)
  try:
    rt._standard_stream(tokens[0], operation, '', 0)
  except Interrupted:
    pass
finally:
  signal.setitimer(signal.ITIMER_REAL, 0)
  signal.signal(signal.SIGALRM, previous)
  elapsed = time.monotonic() - started
  os.close(write_end)
  # The watchdog bounds the failure too, and always exits before cleanup.
  try:
    wait_child(watchdog)
  finally:
    rt._shutdown_native()
assert elapsed < 2.5, 'full-pipe operation timed out'
""")

  def test_timed_command_wait_with_blocking_popen_waiter(self):
    for timeout in (0, .1):
      with self.subTest(timeout=timeout):
        self.run_case('timeout = %r\n' % timeout + r"""
import subprocess
from unittest import mock
process = subprocess.Popen([sys.executable, '-c',
    'import sys; sys.stdin.read(); raise SystemExit(37)'], stdin=subprocess.PIPE)
process._command_creator_pid = os.getpid()
entered, finished = threading.Event(), threading.Event()
results, errors = [], []
original = process._try_wait
def observed_wait(flags):
  if flags == 0:
    assert process._waitpid_lock.locked(), 'ordinary waiter did not hold lock'
    entered.set()
  return original(flags)
def waiter():
  try:
    results.append(process.wait())
  except BaseException as error:
    errors.append(error)
def end_command():
  # Bound the failure too: master's blocking lock waits until this closes stdin.
  if not finished.wait(3):
    process.stdin.close()
ordinary = threading.Thread(target=waiter)
watchdog = threading.Thread(target=end_command)
try:
  with mock.patch.object(process, '_try_wait', observed_wait):
    watchdog.start()
    ordinary.start()
    assert entered.wait(3), 'ordinary waiter did not reach blocking waitpid'
    started = time.monotonic()
    timed_out = False
    try:
      rt._wait_command(process, timeout=timeout)
    except subprocess.TimeoutExpired as error:
      timed_out = True
      assert error.cmd == process.args and error.timeout == timeout
    elapsed = time.monotonic() - started
    assert timed_out, ('timed wait blocked until watchdog ended command', elapsed)
    assert timeout <= elapsed < timeout + .5, ('timed wait missed deadline', elapsed)
finally:
  finished.set()
  if watchdog.ident is not None:
    watchdog.join(3)
  process.stdin.close()
  if ordinary.ident is not None:
    ordinary.join(3)
    if ordinary.is_alive():
      process.kill()
      ordinary.join(3)
  process.wait(timeout=3)
assert not watchdog.is_alive() and not ordinary.is_alive(), 'waiter timed out'
assert not errors, errors
assert results == [37] and process.returncode == 37, (results, process.returncode)
assert rt._wait_command(process, timeout=1) == 37
""", timeout=15)

  def test_concurrent_command_waiters_preserve_exit_status(self):
    self.run_case(r"""
import subprocess
from unittest import mock
process = subprocess.Popen([sys.executable, '-c', 'raise SystemExit(37)'])
process._command_creator_pid = os.getpid()
entered, resume, attempted = threading.Event(), threading.Event(), threading.Event()
results, errors = [], []
class ObservedLock:
  def __init__(self, lock):
    self.lock = lock
  def acquire(self, *args, **kwargs):
    if threading.current_thread() is second:
      attempted.set()
    return self.lock.acquire(*args, **kwargs)
  def release(self):
    self.lock.release()
  def __enter__(self):
    self.acquire()
    return self
  def __exit__(self, *args):
    self.release()
process._waitpid_lock = ObservedLock(process._waitpid_lock)
original = rt._command_call
def paused(process, operation, *args, **kwargs):
  result = original(process, operation, *args, **kwargs)
  if operation is os.waitpid and result[0]:
    entered.set()
    assert resume.wait(3), 'status publication was not released'
  return result
def waiter():
  try:
    results.append(rt._wait_command(process, timeout=3))
  except BaseException as error:
    errors.append(error)
first = threading.Thread(target=waiter)
second = threading.Thread(target=waiter)
try:
  with mock.patch.object(rt, '_command_call', paused):
    first.start()
    assert entered.wait(3), 'first waiter did not reap command'
    second.start()
    # Keep the reaped status unpublished until the second waiter tries the lock.
    assert attempted.wait(3), 'second waiter did not attempt waiter lock'
    resume.set()
    first.join(3)
    second.join(3)
  assert not first.is_alive() and not second.is_alive(), 'waiter timed out'
  assert not errors, errors
  assert results == [37, 37] and process.returncode == 37, (results, process.returncode)
finally:
  resume.set()
  for thread in (first, second):
    if thread.ident is not None:
      thread.join(3)
  if process.returncode is None:
    process.kill()
  process.wait(timeout=3)
""")

  def command_cleanup_fork(self, point):
    self.run_case('point = %r\n' % point + r"""
import atexit, inspect, select, shlex
from unittest import mock
command = 'exec ' + shlex.quote(sys.executable) + ' -c ' + shlex.quote(
    'import sys; print("ready", flush=True); '
    'print(repr(sys.stdin.read()), flush=True)')
tokens = list(map(int, rt._standard_stream(0, 'exec', command, 0).split()))
process, = rt._command_processes
def command_line():
  assert select.select([process.stdout], [], [], 3)[0], 'command output timed out'
  return process.stdout.readline()
assert command_line() == 'ready\n'
owners = dict(rt._command_owners)
# No newline: input remains in the parent's TextIOWrapper until it flushes.
process.stdin.write('STOP')
parent = os.getpid()
children = []
class ParentPaused(BaseException): pass

def handler(signum, frame):
  child = os.fork()
  if child:
    children.append(child)
    wait_child(child)
    # Inspect the command before resuming any parent cleanup.
    raise ParentPaused()
  # The child returns into the interrupted cleanup with its inherited locals.

if point == 'close':
  target = rt._standard_stream.__wrapped__
  needle = 'if stream is not None:'
  action = lambda: rt._standard_stream(tokens[0], 'prim_hClose', '', 0)
elif point == 'retirement':
  target = rt._signal_command
  needle = '_os.killpg'
  rt._command_owners.clear()
  rt._command_owners[tokens[-1]] = process
  action = lambda: rt._retire_command(tokens[-1])
elif point == 'reap':
  target = rt._reap_commands.__wrapped__
  needle = 'if _command_exited(process):'
  rt._command_pending.add(process)
  action = rt._reap_commands
else:
  target = getattr(rt, '_shutdown_commands', rt._shutdown_native)
  target = getattr(target, '__wrapped__', target)
  needle = 'for process in processes:'
  action = rt._shutdown_native
source, first = inspect.getsourcelines(target)
line, = [first + i for i, text in enumerate(source) if needle in text]
fired = []
def trace(frame, event, arg):
  if frame.f_code is target.__code__ and event == 'line' and frame.f_lineno == line:
    sys.settrace(None)
    fired.append(True)
    signal.raise_signal(signal.SIGUSR1)
  return trace

previous = signal.signal(signal.SIGUSR1, handler)
try:
  # Force retirement's exit-observation branch while keeping its command live.
  with mock.patch.object(rt, '_command_exited', return_value=True):
    sys.settrace(trace)
    try:
      action()
    except curry.exceptions.ForkError:
      assert os.getpid() != parent
    except ParentPaused:
      assert os.getpid() == parent
    finally:
      sys.settrace(None)
    if os.getpid() != parent:
      status = 0
      try:
        rejected(curry.reset)
        atexit._run_exitfuncs()
      except BaseException:
        traceback.print_exc()
        status = 1
      os._exit(status)
  assert fired and len(children) == 1, 'signal hook did not fork'
  assert process.poll() is None, 'child cleanup stopped parent command'
  rt._command_owners.update(owners)
  process.stdin.flush()
  process.stdin.close()
  # A child close/flush would deliver its buffered STOP too, yielding STOPSTOP.
  assert command_line() == "'STOP'\n", 'child flushed inherited input'
  for token in tokens:
    rt._standard_stream(token, 'release', '', 0)
  process.wait(timeout=3)
  rt._reap_commands()
  assert process not in rt._command_processes
  assert all(stream.closed for stream in (process.stdin, process.stdout, process.stderr))
finally:
  sys.settrace(None)
  signal.signal(signal.SIGUSR1, previous)
  rt._shutdown_native()
""")

  def test_busy_stock_analysis_receipt_check(self):
    self.run_case(r"""
from pathlib import Path
from unittest import mock
from curry.toolchain import _analysisproducts
from curry import config
import hashlib
with fork_directory() as work:
  library = Path(work)
  source = library / 'ForkReceipt.curry'
  source.write_text('module ForkReceipt where\nanswer = True\n')
  output = Path('.curry') / config.analysis_subdir()
  products = library / output
  products.mkdir(parents=True)
  (products / 'ForkReceipt.source').write_text(hashlib.sha256(source.read_bytes()).hexdigest())
  (products / 'ForkReceipt.fcy').write_text('')
  (products / 'ForkReceipt.fint').write_text('')
  with mock.patch.object(config, 'system_curry_path', return_value=work):
    assert during(lambda: _analysisproducts.shipped_request(
        ['--flat', '-o', str(output), 'ForkReceipt']), Path, 'read_bytes')
""")

  def test_busy_image_load_attachment(self):
    self.run_case(r"""
from curry.backends.cxx import image
from curry.toolchain import _curry2icurry
with fork_directory() as work:
  source = os.path.join(work, 'ForkAttach.curry')
  with open(source, 'w') as stream:
    stream.write('module ForkAttach where\nanswer :: Int\nanswer = 42\n')
  icy = _curry2icurry.curry2icurry(source, curry.path)
  during(lambda: image.load(curry._interpreter_, icy), image, 'attach')
""")

  def test_busy_callback_public_entries_reject_before_shortcuts(self):
    self.busy_public_entries(held_lock=False)

  def test_busy_callback_fork_error_precedes_reentrancy(self):
    self.busy_public_entries(held_lock=True)

  def busy_public_entries(self, held_lock):
    self.run_case(ENTRY_FIXTURE + 'held_lock = %r\n' % held_lock + r'''
import contextlib

def values():
  assert active_results._busy and active_stream._busy
  # In the second case both predicates apply. Keep consumption locks held
  # too, proving that entry rejects before attempting those inherited locks.
  with contextlib.ExitStack() as scopes:
    if held_lock:
      scopes.enter_context(locking.Lock())
      scopes.enter_context(active_results._lock)
      scopes.enter_context(active_stream._lock)
    for label, action in entries():
      try:
        fork_check(lambda: rejected(action))
      except AssertionError as error:
        failures.append((label, str(error)))
  yield 42

active_stream = curry.stream(module.out(iter(values())))
# Both public iterator classes are executing when the native callback forks.
active_results = Results(active_stream, 'active stream evaluation')
assert next(active_results) == 42
assert os.getpid() == parent, 'child continued the evaluation'
active_results.close()
assert curry.eval(term).one() == 7
assert not failures, failures
''')

  def test_idle_child_public_entries_keep_working(self):
    self.run_case(ENTRY_FIXTURE + r'''
active_results = curry.eval(curry.choice(40, 41, 42))
active_stream = curry.stream(module.out([42]))
assert next(active_results) == 40
assert next(active_stream) == 42
expected_text, expected_repr, expected_hash = str(term), repr(term), hash(term)

def child():
  assert interp.stats() is not None
  assert str(interp.typeof(term))
  assert str(term) == expected_text
  assert repr(term) == expected_repr
  assert term == other and hash(term) == expected_hash
  assert module.out is not None and module['out'] is not None
  assert held.signature
  assert next(active_results) == 41
  assert next(active_stream) == 43
  assert next(unstarted_results) == 7
  assert next(unstarted_stream) == 42
  assert list(closed_results) == [] and list(closed_stream) == []
  for value in (active_results, active_stream, unstarted_results,
                unstarted_stream, closed_results, closed_stream):
    value.close()
  from curry.toolchain import _str2module
  with _str2module._dirs_lock:
    try:
      interp.stats()
    except curry.ReentrancyError:
      pass
    else:
      raise AssertionError('idle child lost directory lock tracking')
  assert curry.eval(term).one() == 7

fork_check(child)
assert next(active_results) == 41
assert next(active_stream) == 43
active_results.close()
active_stream.close()
assert curry.eval(term).one() == 7
''')

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

  def test_busy_loader_inputs_include_make_and_direct_import(self):
    self.run_case(r'''
from curry import toolchain
from curry.toolchain import _findcurry, plans
with fork_directory() as work:
  source = os.path.join(work, 'ForkInputs.curry')
  with open(source, 'w') as stream:
    stream.write('module ForkInputs where\nanswer :: Int\nanswer = 42\n')
  plan = plans.makeplan(flags=plans.MAKE_ICURRY)
  during(lambda: toolchain.makecurry(plan, source, curry.path, is_sourcefile=True),
      _findcurry, 'loader_inputs')
  # Use the interpreter entry directly, with no package-level work scope.
  module = during(lambda: curry._interpreter_.import_(source, is_sourcefile=True),
      _findcurry, 'loader_inputs')
  assert curry.eval(module.answer).one() == 42
''')

  def test_busy_image_rebuild_from_changed_interfaces(self):
    self.run_case(r'''
from curry.backends.cxx import image
from curry.toolchain import _curry2icurry, _filenames
with fork_directory() as work:
  leaf = os.path.join(work, 'ForkLeaf.curry')
  source = os.path.join(work, 'ForkImage.curry')
  def write(path, text):
    with open(path, 'w') as stream:
      stream.write(text)
  write(leaf, 'module ForkLeaf where\nanswer :: Int\nanswer = 1\n')
  write(source, 'module ForkImage where\nimport ForkLeaf\nanswer = ForkLeaf.answer\n')
  icy = _curry2icurry.curry2icurry(source, [work] + curry.path, use_cache=False)
  write(leaf, 'module ForkLeaf where\nanswer :: Bool\nanswer = True\n')
  _curry2icurry.curry2icurry(leaf, [work] + curry.path, use_cache=False)
  path, header = during(
      lambda: image.ensure(curry._interpreter_, icy, [work] + curry.path),
      _curry2icurry, 'curry2icurry')
  assert os.path.isfile(path) and header['name'] == 'ForkImage'
  assert os.path.isfile(_filenames.icurryfilename(source))
''')

  def test_busy_direct_frontend_working_views(self):
    self.run_case(r'''
from curry.toolchain import _frontend, _system
with fork_directory() as work:
  for route in ('flat', 'icy'):
    source = os.path.join(work, 'ForkView' + route + '.curry')
    with open(source, 'w') as stream:
      stream.write('module ForkView%s where\nanswer :: Int\nanswer = 42\n' % route)
    output = os.path.join(work, 'output.icy')
    def action():
      if route == 'flat':
        return _frontend.curry2flat(source, curry.path)
      return _frontend.curry2icurry(source, output, curry.path)
    during(action, _system, 'pexec')
    assert os.path.isfile(_frontend.flatcurryfile(source))
''')

  def test_busy_direct_converter_private_icurry_view(self):
    self.run_case(r'''
import shutil
from curry import config
from curry.toolchain import _curry2icurry, _destination
if config.icurry_tool() is not None:
  with fork_directory() as work:
    source = os.path.join(work, 'ForkConvert.curry')
    with open(source, 'w') as stream:
      stream.write('module ForkConvert where\nanswer :: Int\nanswer = 42\n')
    converter = _curry2icurry.Curry2ICurryConverter(curry2icurry='icurry', use_cache=False)
    product = during(lambda: converter.convert(source, curry.path), shutil, 'copy2',
        matches=lambda src, dst, **kw: 'sprite-icurry-' in dst)
    assert os.path.isfile(product)
else:
  # The direct converter must still count preparation on the default route.
  with fork_directory() as work:
    source = os.path.join(work, 'ForkConvert.curry')
    with open(source, 'w') as stream:
      stream.write('module ForkConvert where\nanswer :: Int\nanswer = 42\n')
    converter = _curry2icurry.Curry2ICurryConverter(use_cache=False)
    product = during(lambda: converter.convert(source, curry.path), _destination, 'select')
    assert os.path.isfile(product)
''')

  def test_busy_source_free_private_cpp_copy(self):
    self.run_case(r'''
import shutil
from unittest import mock
from curry.backends.cxx import toolchain
from curry.toolchain import _destination
module = curry.compile('answer :: Int\nanswer = 42', name='ForkSourceFree')
with fork_directory() as work:
  cpp = os.path.join(work, 'ForkSourceFree.cpp')
  curry._interpreter_.save(module, cpp, module_main=False, interfaces=True)
  original = _destination.needs_private
  def private(filename, products):
    return filename == cpp or original(filename, products)
  with mock.patch.object(_destination, 'needs_private', private):
    product = during(lambda: toolchain.Cpp2So(curry._interpreter_)(cpp, curry.path),
        shutil, 'copyfile', matches=lambda src, dst, **kw:
            src == cpp and os.sep + '.curry' + os.sep in dst)
  assert os.path.isfile(product) and not product.startswith(work + os.sep)
''')

  def test_busy_saved_receipt_publication_and_load_verification(self):
    self.run_case(r'''
from curry import cache
from curry.backends.cxx import loader
from curry.interpreter import loadsave
module = curry.compile('answer :: Int\nanswer = 42', name='ForkSaved')
with fork_directory() as work:
  product = os.path.join(work, 'saved' + curry.config.module_object_suffix())
  curry.save(module, product)
  during(lambda: loadsave.record_saved_imports(curry._interpreter_, module, product),
      cache, 'write_file', matches=lambda path, *args: path.endswith('.imports'))
  curry.reset(interpret='new', jit='off')
  loaded = during(lambda: loader.load_module(curry._interpreter_, product, fresh=True),
      loadsave, 'verify_saved_imports')
  assert curry.eval(loaded.answer).one() == 42
''')

  def test_idle_child_private_image_destinations_are_fresh(self):
    self.run_case(r'''
from curry.backends.cxx import image
interp = curry._interpreter_
source = os.path.join(curry.config.system_curry_path(), 'Prelude.curry')
parent_image = image._private_path(interp, source)
parent_directory = tiered._state.tmpdir
assert parent_image.startswith(parent_directory + os.sep)
bindings = tiered._state.bindings.copy()
def child():
  assert tiered._state.tmpdir is None
  assert tiered._state.bindings == bindings
  child_image = image._private_path(interp, source)
  assert not child_image.startswith(parent_directory + os.sep)
  assert child_image.startswith(tiered._state.tmpdir + os.sep)
  assert os.path.isdir(parent_directory)
fork_check(child)
assert os.path.isdir(parent_directory)
assert image._private_path(interp, source) == parent_image
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

  def test_signal_fork_during_worker_startup(self):
    self.run_case(r'''
from curry.backends.generic.eval.evaluator import Evaluator
curry.reset(interpret='all', jit='off', stack_limit=65536, worker_stack=64 << 20)
module = curry.import_('StackGuard')
parent = os.getpid()
children, received = [], []
def handler(signum, frame):
  assert native._test_worker_startup_paused(), 'worker published readiness'
  received.append(signum)
  pid = os.fork()
  if pid:
    children.append(pid)
    native._test_resume_worker_startup()
signal.signal(signal.SIGUSR1, handler)
def send_signal():
  until(native._test_worker_startup_paused)
  os.kill(parent, signal.SIGUSR1)
native._test_pause_worker_startup()
sender = threading.Thread(target=send_signal)
sender.start()
try:
  ev = Evaluator(cytest.raw.interp(),
      cytest.raw.expr(module.deep, 3000, typed=True))
  try:
    answers = [cytest.raw.interp().topython(value) for value in ev.evaluate()]
  except curry.ForkError as error:
    assert os.getpid() != parent, 'parent received ForkError'
    assert 'Sprite was busy when the process forked' in str(error), str(error)
    os._exit(0)
  if os.getpid() != parent:
    os._exit(2) # The interrupted child must raise ForkError.
finally:
  if os.getpid() == parent:
    native._test_resume_worker_startup()
    sender.join(10)
    for pid in children:
      wait_child(pid)
assert not sender.is_alive(), 'signal sender did not finish'
assert received == [signal.SIGUSR1] and len(children) == 1, (received, children)
assert ev.rts._escalated and answers == [3000], answers
assert curry.eval(curry.term(7)).one() == 7
''')

  def test_worker_callback_fork_ends_with_error(self):
    self.worker_callback_fork(full_pipe=False)

  def test_worker_callback_fork_with_full_stderr_exits(self):
    self.worker_callback_fork(full_pipe=True)

  def worker_callback_fork(self, full_pipe):
    setup = r'''
# Fill stderr before the fork and restore blocking mode on its shared open
# file description. The parent must not drain it until the child is reaped.
os.set_blocking(error_w, False)
filled = 0
while True:
  try:
    filled += os.write(error_w, b'x' * 4096)
  except BlockingIOError:
    break
# Fill any remainder smaller than an atomic chunk as well.
while True:
  try:
    filled += os.write(error_w, b'x')
  except BlockingIOError:
    break
os.set_blocking(error_w, True)
assert filled > 0
# A bounded report must also handle an inherited ignored, blocked alarm.
signal.signal(signal.SIGALRM, signal.SIG_IGN)
signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
''' if full_pipe else ''
    check = r'''
  assert os.get_blocking(error_w), 'child changed the shared descriptor flags'
  os.close(error_w)
  error = b''
  while True:
    chunk = os.read(error_r, 4096)
    if not chunk:
      break
    error += chunk
  assert error[:filled] == b'x' * filled, len(error)
''' if full_pipe else r'''
  os.close(error_w)
  error = os.read(error_r, 4096).decode()
  assert 'ForkError: Sprite was busy when the process forked' in error, error
'''
    self.run_case(r'''
from curry.backends.generic.eval.evaluator import Evaluator
curry.reset(interpret='all', jit='off', stack_limit=65536, worker_stack=64 << 20)
module = curry.compile('deep :: Int -> [Int] -> Int\n'
    'deep n xs = length [1..n] + head xs')
caller = threading.get_ident()
parent = os.getpid()
children = []
error_r, error_w = os.pipe()
''' + setup + r'''
def values():
  # The strict first operand exhausts the caller's stack before head demands us.
  assert ev.rts._escalated, 'callback ran before escalation'
  assert threading.get_ident() != caller, 'callback ran on caller stack'
  pid = os.fork()
  if pid:
    children.append(pid)
  else:
    os.close(error_r)
    os.dup2(error_w, 2)
    os.close(error_w)
  yield 42
ev = Evaluator(cytest.raw.interp(),
    cytest.raw.expr(module.deep, 3000, iter(values()), typed=True))
answers = [cytest.raw.interp().topython(value) for value in ev.evaluate()]
assert os.getpid() == parent, 'worker child continued evaluation'
assert answers == [3042], answers
assert len(children) == 1
try:
  # No Python evaluation caller survives in this child: terminate with the error.
  wait_child(children[0], exitcode=1)
''' + check + r'''
finally:
  os.close(error_r)
assert curry.eval(curry.term(7)).one() == 7
''')

  def test_busy_queued_hot_request_rejects_child(self):
    self.run_case(r'''
module = curry.compile('inc :: Int -> Int\ninc x = x + 1\n'
    'dec :: Int -> Int\ndec x = x - 1')
# Drive the native hot queue without starting LLVM's consumer.
rt.icurry_set_hot_threshold(curry._interpreter_._its, 1)
assert curry.eval(module.inc(1)).one() == 2
fork_check(lambda: rejected(curry.reset))
hot = rt.icurry_take_hot()
assert hot, 'no hot request queued'
del hot
# Dropping the dequeued tickets must release their work record.
fork_check(lambda: curry.eval(curry.term(7)).one())
assert curry.eval(module.inc(41)).one() == 42
# Reset also drops requests still in the native queue.
assert curry.eval(module.dec(43)).one() == 42
fork_check(lambda: rejected(curry.reset))
curry.reset(interpret='all', jit='off')
fork_check(lambda: curry.eval(curry.term(7)).one())
''')

  def test_busy_dequeued_hot_request_rejects_child(self):
    self.run_case(r'''
from types import SimpleNamespace
module = curry.compile('inc :: Int -> Int\ninc x = x + 1')
rt.icurry_set_hot_threshold(curry._interpreter_._its, 1)
assert curry.eval(module.inc(1)).one() == 2
entered, resume = threading.Event(), threading.Event()
take_hot, compile_groups = rt.icurry_take_hot, llvmjit._compile_groups
class Stopped(BaseException): pass
def paused_take():
  hot = take_hot()
  if not hot:
    raise Stopped()
  entered.set()
  assert resume.wait(10)
  return hot
# Exercise the real loop through its dequeue hook, without requiring LLVM.
rt.icurry_take_hot = paused_take
llvmjit._compile_groups = lambda *args, **kwds: []
llvmjit._jit = SimpleNamespace(hot=0, errors=0, last_error=None)
llvmjit._hot_enabled = True
errors = []
def consume():
  try:
    llvmjit._hot_loop()
  except Stopped:
    pass
  except BaseException as error:
    errors.append(error)
thread = threading.Thread(target=consume)
thread.start()
assert entered.wait(10), 'hot loop did not dequeue'
try:
  fork_check(lambda: rejected(curry.reset))
finally:
  resume.set()
  thread.join(10)
  rt.icurry_take_hot = take_hot
  llvmjit._compile_groups = compile_groups
  llvmjit._hot_enabled = False
  llvmjit._jit = None
assert not thread.is_alive() and not errors, errors
# A compile that drops the work must also finish its busy record.
fork_check(lambda: curry.eval(curry.term(7)).one())
assert curry.eval(module.inc(41)).one() == 42
''')

  def test_completed_cxx_hot_request_is_idle(self):
    self.run_case(r'''
module = curry.compile('identity :: Int -> Int\nidentity x = x')
# An armed native job owns this table. A failed compiler command completes
# without changing its step, so a second threshold can exercise the same table.
rt.cxx_arm(curry._interpreter_._its, module.__name__,
    [sys.executable, '-c', 'raise SystemExit(1)'], [], '', '', '',
    [('identity', '', module.identity.info)])
for threshold in (1, 2):
  rt.icurry_set_hot_threshold(curry._interpreter_._its, threshold)
  assert curry.eval(module.identity(42)).one() == 42
  assert rt.tiered_wait(10)
  rt.tiered_poll()
  assert not rt.icurry_take_hot(), 'C++ request also queued for LLVM'
  fork_check(lambda: curry.eval(curry.term(7)).one())
''')

  def test_unowned_cxx_library_hot_request_is_idle(self):
    self.run_case(r'''
os.environ['SPRITE_JIT_THRESHOLD'] = '2'
curry.reset(interpret='all', jit='hot', jit_backend='cxx', inline_budget=0)
prelude = curry.import_('Prelude')
assert rt.icurry_is_interpreted(prelude.length.info)
assert rt.icurry_hot_threshold(curry._interpreter_._its) == 2
# Prelude is deliberately unarmed by the C++ backend. Its recursive length
# crosses the threshold without an LLVM consumer running in this process.
assert llvmjit._hot_thread is None
assert curry.eval(prelude.length(list(range(8)))).one() == 8
assert tiered.wait(timeout=30, interp=curry._interpreter_)
assert rt.icurry_is_interpreted(prelude.length.info)
def child():
  assert curry.eval(curry.term(42)).one() == 42
  assert curry.eval(prelude.length(list(range(8)))).one() == 8
fork_check(child)
assert not rt.icurry_take_hot(), 'unowned C++ library request queued for LLVM'
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
