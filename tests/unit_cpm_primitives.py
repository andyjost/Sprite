"""Small reproducers from properties exercised by the CPM index."""
import cytest # from ./lib; must be first
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import curry
from curry import config


SOURCE = Path('data/curry/libprims2').resolve()
BINARY = Path('data/curry/cpm_index').resolve()
ALL_VALUES = '''module Control.AllValues where
allValues :: a -> [a]
allValues external
oneValue :: a -> Maybe a
oneValue external
coin :: Int
coin = 0
coin = 1
values :: [Int]
values = allValues (coin + coin)
value :: Maybe Int
value = oneValue (coin + coin)
'''


class TestCPMPackagePrimitives(cytest.TestCase):
  @cytest.posix_only('uses shell quoting for the child command')
  def test_command_streams(self):
    import shlex
    curry.path.insert(0, str(BINARY))
    module = curry.compile('''import System.IO
import System.IOExts
run :: String -> IO (String, String)
run command = do
  (hi,ho,he) <- execCmd command
  hPutStrLn hi "hello"
  hClose hi
  ready <- hWaitForInputs [ho,he] 5000
  output <- hGetContents ho
  errors <- hGetContents he
  hClose ho
  hClose he
  return (show ready ++ ":" ++ output, errors)
''')
    script = "import sys; print(sys.stdin.read().upper(), end=''); print('error', file=sys.stderr)"
    command = shlex.quote(sys.executable) + ' -c ' + shlex.quote(script)
    for _ in range(4):
      output, errors = curry.eval(module.run(command)).one()
      self.assertIn(output, ('0:HELLO\n', '1:HELLO\n'))
      self.assertEqual(errors, 'error\n')

  def test_closed_command_is_reaped_at_next_close_or_launch(self):
    from curry.backends.cxx import curryrtbindings as bindings
    import shlex
    for operation, trigger in [('exec', 'close'), ('connect', 'launch')]:
      with self.subTest(operation=operation, trigger=trigger):
        script = 'import time; time.sleep(.2)'
        command = (subprocess.list2cmdline([sys.executable, '-c', script])
                   if sys.platform == 'win32' else
                   'exec ' + shlex.quote(sys.executable) + ' -c ' + shlex.quote(script))
        before = set(bindings._command_processes)
        tokens = list(map(int, bindings._standard_stream(0, operation, command, 0).split()))
        process, = bindings._command_processes - before
        try:
          started = time.monotonic()
          for token in tokens:
            bindings._standard_stream(token, 'prim_hClose', '', 0)
          self.assertLess(time.monotonic() - started, .15)
          # Let the child exit without a test-side poll/wait reaping it.
          time.sleep(.5)
          if trigger == 'close':
            bindings._standard_stream(tokens[0], 'prim_hClose', '', 0)
          else:
            later = list(map(int, bindings._standard_stream(0, operation, command, 0).split()))
            for token in later:
              bindings._standard_stream(token, 'release', '', 0)
          self.assertNotIn(process, bindings._command_processes)
          if sys.platform == 'win32':
            import ctypes
            flags = ctypes.c_ulong()
            self.assertFalse(ctypes.windll.kernel32.GetHandleInformation(
                ctypes.c_void_p(int(process._handle)), ctypes.byref(flags)))
          else:
            with self.assertRaises(ChildProcessError):
              os.waitpid(process.pid, os.WNOHANG)
        finally:
          for token in tokens:
            bindings._standard_stream(token, 'release', '', 0)
          process.wait(timeout=5)

  def test_shutdown_isolates_child_errors_and_waits_outside_lock(self):
    from curry.backends.cxx import curryrtbindings as b
    from unittest import mock
    broken, stubborn, healthy = mock.Mock(), mock.Mock(), mock.Mock()
    broken.poll.side_effect = RuntimeError('cannot inspect child')
    stubborn.poll.return_value = None
    healthy.poll.return_value = 0
    def wait(timeout):
      self.assertEqual(timeout, 1)
      self.assertFalse(b._command_lock._is_owned())
    healthy.wait.side_effect = wait
    def timeout_wait(timeout):
      wait(timeout)
      raise subprocess.TimeoutExpired('child', timeout)
    stubborn.wait.side_effect = timeout_wait
    processes = {broken, stubborn, healthy}
    def signal_child(process, kill=False):
      if process is stubborn: raise OSError('signal failed')
    with mock.patch.object(b, '_command_processes', processes), \
         mock.patch.object(b, '_command_pending', processes.copy()), \
         mock.patch.object(b, '_command_streams', {}), \
         mock.patch.object(b, '_signal_command', side_effect=signal_child) as signal_command, \
         mock.patch.object(b, 'shutdown_handles'), \
         mock.patch.object(b._curryrtbindings, '_heap_drain'):
      b._shutdown_native()
      signal_command.assert_any_call(healthy)
      healthy.wait.assert_called_once_with(timeout=1)
      signal_command.assert_any_call(stubborn, kill=True)
      self.assertEqual(stubborn.wait.call_count, 2)
      self.assertNotIn(healthy, processes)

  def test_windows_command_is_assigned_before_resume_and_terminated_as_job(self):
    from curry.backends.cxx import curryrtbindings as b
    from curry.utility import windowsjob
    from unittest import mock
    import io
    kernel, job, process = mock.Mock(), mock.Mock(), mock.Mock()
    process.stdin, process.stdout, process.stderr = (io.StringIO() for _ in range(3))
    process.poll.return_value = 0
    process._handle = mock.Mock()
    process._handle.__int__ = lambda self: 42
    def resume(handle):
      self.assertIs(process._command_job, job)
      return 0
    kernel.NtResumeProcess.side_effect = resume
    with mock.patch.object(sys, 'platform', 'win32'), \
         mock.patch('ctypes.WinDLL', return_value=kernel, create=True), \
         mock.patch.object(windowsjob, 'WindowsJob', return_value=job) as make_job, \
         mock.patch.object(subprocess, 'Popen', return_value=process) as launch, \
         mock.patch.object(b, '_command_processes', set()), \
         mock.patch.object(b, '_command_pending', set()), \
         mock.patch.object(b, '_command_owners', {}), \
         mock.patch.object(b, '_command_streams', {}), \
         mock.patch.object(b, 'shutdown_handles'), \
         mock.patch.object(b._curryrtbindings, '_heap_drain'):
      b._standard_stream(0, 'exec', 'command', 0)
      self.assertEqual(launch.call_args.kwargs['creationflags'], 0x4)
      make_job.assert_called_once_with(process)
      kernel.NtResumeProcess.assert_called_once_with(42)
      b._shutdown_native()
      self.assertEqual(job.terminate.call_count, 2)
      job.close.assert_called_once_with()
      self.assertFalse(b._command_processes)
      self.assertFalse(b._command_pending)
      process._handle.Close.assert_called_once_with()
      self.assertTrue(process.stdin.closed)

  def _run_lifecycle_subprocess(self, script, timeout):
    # Kill the whole group on regression, including children ignoring SIGTERM.
    process = subprocess.Popen([sys.executable, '-c', script],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True)
    try:
      stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
      from testrunner import procs
      procs.kill_session(process.pid, reason='timeout')
      stdout, stderr = process.communicate(timeout=2)
      self.fail('command lifecycle timed out: ' + stdout + stderr)
    self.assertEqual(process.returncode, 0, stdout + stderr)
    return stdout

  @cytest.posix_only('uses POSIX signals and shell children')
  def test_shutdown_bounds_termination_and_closes_open_handles(self):
    started = time.monotonic()
    output = self._run_lifecycle_subprocess('''
import atexit, os, shlex, sys
if sys.platform.startswith('linux'):
  import ctypes
  assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0
def verify():
  assert all(s.closed for s in streams)
  assert not b._command_processes
  assert not b._command_streams
  assert all(p.returncode is not None for p in processes)
  if sys.platform.startswith('linux'):
    while True:
      try: os.waitpid(-1, 0)
      except ChildProcessError: break
  print('shutdown complete')
atexit.register(verify)
from curry.backends.cxx import curryrtbindings as b
script = "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); print('ready', flush=True); time.sleep(60)"
command = shlex.quote(sys.executable) + ' -c ' + shlex.quote(script) + '; :'
for operation in ('exec', 'connect'):
  tokens = list(map(int, b._standard_stream(0, operation, command, 0).split()))
  reader = tokens[1] if operation == 'exec' else tokens[0]
  assert b._command_streams[reader].readline() == 'ready\\n'
  writer = b._command_streams[tokens[0]]
  if operation == 'connect': writer = writer.writer
  fd = writer.fileno()
  os.set_blocking(fd, False)
  try:
    while True: os.write(fd, b'x' * 4096)
  except BlockingIOError:
    pass
  finally:
    os.set_blocking(fd, True)
  writer.write('buffered input')
streams = list(b._command_streams.values())
processes = list(b._command_processes)

''', timeout=8)
    self.assertIn('shutdown complete', output)
    self.assertLess(time.monotonic() - started, 7)

  @cytest.posix_only('uses POSIX full pipes and shell children')
  def test_exit_with_discards_open_command_input(self):
    output = self._run_lifecycle_subprocess('''
import atexit, os, sys, time
from pathlib import Path
if sys.platform.startswith('linux'):
  import ctypes
  assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0
def verify():
  assert time.monotonic() - started < 3
  assert all(s.closed for s in streams)
  assert not b._command_processes
  if sys.platform.startswith('linux'):
    while True:
      try: os.waitpid(-1, 0)
      except ChildProcessError: break
  print('exitWith complete')
atexit.register(verify)
import curry
from curry.backends.cxx import curryrtbindings as b
curry.path.insert(0, str(Path('data/curry/cpm_index').resolve()))
module = curry.compile("import System.IO\\nimport System.IOExts\\nlaunch :: String -> IO (Handle,Handle,Handle)\\nlaunch = execCmd\\n")
handles = curry.eval(module.launch('sleep 600; :')).one()
process, = b._command_processes
writer = process.stdin
os.set_blocking(writer.fileno(), False)
try:
  while True: os.write(writer.fileno(), b'x' * 4096)
except BlockingIOError:
  pass
os.set_blocking(writer.fileno(), True)
writer.write('buffered input')
streams = list(b._command_streams.values())
started = time.monotonic()
b._exit_with(0)
''', timeout=15)
    self.assertIn('exitWith complete', output)

  @cytest.posix_only('uses POSIX process groups and shell children')
  def test_shutdown_kills_shell_descendants_with_full_pipe(self):
    output = self._run_lifecycle_subprocess('''
import os, sys, time
from curry.backends.cxx import curryrtbindings as b
# Adopt orphaned grandchildren on Linux so this test reaps them as well.
if sys.platform.startswith('linux'):
  import ctypes
  assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0
for operation in ('exec', 'connect'):
  command = 'sleep 600 & child=$!; echo $child; wait $child; :'
  tokens = list(map(int, b._standard_stream(0, operation, command, 0).split()))
  reader = b._command_streams[tokens[1] if operation == 'exec' else tokens[0]]
  child = int(reader.readline())
  writer = b._command_streams[tokens[0]]
  if operation == 'connect': writer = writer.writer
  os.set_blocking(writer.fileno(), False)
  try:
    while True: os.write(writer.fileno(), b'x' * 4096)
  except BlockingIOError:
    pass
  os.set_blocking(writer.fileno(), True)
  writer.write('buffered input')
  started = time.monotonic()
  b._shutdown_native()
  assert time.monotonic() - started < 3
  if sys.platform.startswith('linux'):
    os.waitpid(child, 0)
  deadline = time.monotonic() + 2
  while True:
    try: os.kill(child, 0)
    except ProcessLookupError: break
    assert time.monotonic() < deadline, 'surviving descendant'
    time.sleep(.01)
# Exercise the review's foreground shell command literally as well.
b._standard_stream(0, 'connect', 'sleep 600; :', 0)
b._shutdown_native()
if sys.platform.startswith('linux'):
  while True:
    try: os.waitpid(-1, 0)
    except ChildProcessError: break
print('descendants reaped')
''', timeout=8)
    self.assertIn('descendants reaped', output)

  @cytest.posix_only('uses POSIX full pipes and signals')
  def test_shutdown_discards_buffer_even_when_termination_fails(self):
    output = self._run_lifecycle_subprocess('''
import os, signal, sys, time
from unittest import mock
from curry.backends.cxx import curryrtbindings as b
if sys.platform.startswith('linux'):
  import ctypes
  assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0
tokens = list(map(int, b._standard_stream(0, 'exec', 'sleep 600; :', 0).split()))
process, = b._command_processes
assert os.getpgid(process.pid) == process.pid
writer = b._command_streams[tokens[0]]
os.set_blocking(writer.fileno(), False)
try:
  while True: os.write(writer.fileno(), b'x' * 4096)
except BlockingIOError:
  pass
os.set_blocking(writer.fileno(), True)
writer.write('unflushed input')
try:
  with mock.patch.object(b, '_signal_command', side_effect=OSError('refused')):
    started = time.monotonic()
    b._shutdown_native()
    assert time.monotonic() - started < 3
    assert writer.closed
    assert not b._command_streams
finally:
  os.killpg(process.pid, signal.SIGKILL)
  process.wait(timeout=1)
  if sys.platform.startswith('linux'):
    while True:
      try: os.waitpid(-1, 0)
      except ChildProcessError: break
b._shutdown_native()
print('buffer discarded')
''', timeout=6)
    self.assertIn('buffer discarded', output)

  @cytest.posix_only('uses fork and POSIX command quoting')
  def test_fork_resets_command_ownership_and_lock(self):
    output = self._run_lifecycle_subprocess('''
import os, shlex, sys, threading
from curry.backends.cxx import curryrtbindings as b
command = 'exec ' + shlex.quote(sys.executable) + ' -c ' + shlex.quote('import time; time.sleep(.2)')
tokens = list(map(int, b._standard_stream(0, 'exec', command, 0).split()))
for token in tokens: b._standard_stream(token, 'release', '', 0)
# Fork while another thread owns the registry lock, when present.
lock = getattr(b, '_command_lock', getattr(b, '_command_condition', None))
ready, release = threading.Event(), threading.Event()
def hold():
  with lock:
    ready.set()
    release.wait(5)
worker = threading.Thread(target=hold)
worker.start()
ready.wait(5)
pid = os.fork()
if pid == 0:
  try:
    assert not b._command_pending
    assert not b._command_processes
    own = list(map(int, b._standard_stream(0, 'exec', command, 0).split()))
    for token in own: b._standard_stream(token, 'release', '', 0)
    b._shutdown_native()
    assert not b._command_processes
    os._exit(0)
  except BaseException:
    os._exit(1)
release.set()
worker.join(5)
_, status = os.waitpid(pid, 0)
b._shutdown_native()
assert os.waitstatus_to_exitcode(status) == 0, status
print('fork complete')
''', timeout=10)
    self.assertIn('fork complete', output)

  @cytest.posix_only('the broken pipe reproducer uses POSIX command quoting')
  def test_buffered_broken_pipe_retirement_drains_every_handle(self):
    result = cytest.run_in_subprocess('''
import gc, shlex, sys
import curry
from curry.backends.cxx import curryrtbindings as bindings
curry.path.insert(0, str(__import__('pathlib').Path('data/curry/cpm_index').resolve()))
module = curry.compile("""import System.IO
import System.IOExts
launch :: String -> IO (Handle,Handle,Handle)
launch = execCmd
""")
io = curry.import_('System.IO')
before = set(bindings._command_streams)
command = 'exec ' + shlex.quote(sys.executable) + ' -c ' + shlex.quote('pass')
handles = curry.eval(module.launch(command)).one()
process = next(iter(bindings._command_processes))
process.wait()
curry.eval(io.hPutChar(handles[0], curry.Char('x'))).one()
del handles
gc.collect()
bindings.gc_collect()
assert curry.eval(io.hIsWritable(io.stdout)).one()
assert set(bindings._command_streams) == before, bindings._command_streams
print('retirement drained')
''', timeout=30)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    self.assertIn('retirement drained', result.stdout)
    self.assertIn('Hosted stream finalizer failed', result.stderr)
    self.assertIn('BrokenPipeError', result.stderr)

  def test_binary_file_roundtrip(self):
    curry.path.insert(0, str(BINARY))
    binary = curry.import_('System.IO.BinaryFile')
    io = curry.import_('System.IO')
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'bytes.bin'
      h = curry.eval(binary.openBinaryFile(str(path), io.WriteMode)).one()
      for byte in (0, 127, 128, 255):
        curry.eval(binary.hPutByte(h, byte)).one()
      curry.eval(io.hClose(h)).one()
      self.assertEqual(path.read_bytes(), bytes([0, 127, 128, 255]))
      h = curry.eval(binary.openBinaryFile(str(path), io.AppendMode)).one()
      curry.eval(binary.hPutByte(h, 65)).one()
      curry.eval(io.hClose(h)).one()
      h = curry.eval(binary.openBinaryFile(str(path), io.ReadMode)).one()
      self.assertEqual([curry.eval(binary.hGetByte(h)).one() for _ in range(5)],
                       [0, 127, 128, 255, 65])
      self.assertTrue(curry.eval(io.hIsEOF(h)).one())
      self.assertEqual(curry.eval(binary.hGetByte(h)).one(), -1)
      curry.eval(io.hClose(h)).one()

  def test_binary_file_rejects_wrong_streams_and_bytes(self):
    curry.path.insert(0, str(BINARY))
    binary = curry.import_('System.IO.BinaryFile')
    io = curry.import_('System.IO')
    with tempfile.TemporaryDirectory() as directory:
      path = str(Path(directory) / 'bytes.bin')
      h = curry.eval(binary.openBinaryFile(path, io.WriteMode)).one()
      for byte in (-1, 256, 10**50):
        with self.assertRaises(curry.CurryIOError):
          curry.eval(binary.hPutByte(h, byte)).one()
      with self.assertRaises(curry.CurryIOError):
        curry.eval(io.hPutChar(h, curry.Char('x'))).one()
      curry.eval(io.hClose(h)).one()
      with self.assertRaises(curry.CurryIOError):
        curry.eval(binary.hGetByte(h)).one()
      h = curry.eval(io.openFile(path, io.ReadMode)).one()
      with self.assertRaises(curry.CurryIOError):
        curry.eval(binary.hGetByte(h)).one()
      curry.eval(io.hClose(h)).one()

  @cytest.posix_only('the reduced package property uses cat')
  def test_bidirectional_command_stream(self):
    curry.path.insert(0, str(BINARY))
    module = curry.compile('''import System.IO
import System.IOExts
goal :: IO (Bool,Bool,Bool,String)
goal = do
  handle <- connectToCommand "cat"
  readable <- hIsReadable handle
  writable <- hIsWritable handle
  hPutStrLn handle "hello"
  hFlush handle
  ready <- hWaitForInput handle 5000
  line <- hGetLine handle
  hClose handle
  hClose handle
  return (readable,writable,ready,line)
''')
    self.assertEqual(curry.eval(module.goal).one(), (True, True, True, 'hello'))

  @unittest.expectedFailure
  def test_named_global_storage(self):
    module = curry.compile('''module Data.Global where
  data GlobalT a = GlobalT String
  prim_globalT :: String -> a -> GlobalT a
  prim_globalT external
  prim_readGlobalT :: GlobalT a -> IO a
  prim_readGlobalT external
  prim_writeGlobalT :: GlobalT a -> a -> IO ()
  prim_writeGlobalT external
  counter :: GlobalT Int
  counter = prim_globalT "CPM.counter" 0
  goal :: IO (Int,Int)
  goal = do
    before <- prim_readGlobalT counter
    prim_writeGlobalT counter 42
    after <- prim_readGlobalT counter
    return (before,after)
''')
    self.assertEqual(curry.eval(module.goal).one(), (0, 42))

  @unittest.expectedFailure
  def test_global_variable_storage(self):
    module = curry.compile('''module GlobalVariable where
  data GVar a = GVarDef a | GVarValue () a
  prim_readGVar :: GVar a -> IO a
  prim_readGVar external
  prim_writeGVar :: GVar a -> a -> IO ()
  prim_writeGVar external
  counter :: GVar Int
  counter = GVarDef 0
  goal :: IO Int
  goal = do
    prim_writeGVar counter 42
    prim_readGVar counter
''')
    self.assertEqual(curry.eval(module.goal).one(), 42)

  def test_random_seed_clock(self):
    curry.path.insert(0, str(SOURCE))
    module = curry.compile('''import Data.Time
clock :: IO Int
clock = getClockTime >>= return . clockTimeToInt
''')
    before = int(time.time())
    seconds = curry.eval(module.clock).one()
    self.assertLessEqual(before, seconds)
    self.assertLessEqual(seconds, int(time.time()))

  def test_random_seed_utc_conversion(self):
    curry.path.insert(0, str(SOURCE))
    module = curry.compile('''import Data.Time
utc :: Int -> [Int]
utc seconds =
  let t = toUTCTime (read ("CTime (" ++ show seconds ++ ")"))
  in [ctYear t, ctMonth t, ctDay t, ctHour t, ctMin t, ctSec t, ctTZ t]
''')
    for seconds, expected in [
        (-1, [1969, 12, 31, 23, 59, 59, 0]),
        (0, [1970, 1, 1, 0, 0, 0, 0]),
        (951782400, [2000, 2, 29, 0, 0, 0, 0]),
        (1709251199, [2024, 2, 29, 23, 59, 59, 0])]:
      with self.subTest(seconds=seconds):
        self.assertEqual(curry.eval(module.utc(seconds)).one(), expected)

  @unittest.expectedFailure
  def test_legacy_package_source_lookup(self):
    curry.path.insert(0, str(SOURCE))
    module = curry.compile('''import Curry.Compiler.Distribution
import System.Directory
sourceAvailable :: IO Bool
sourceAvailable = doesFileExist (installDir ++ "/lib/Prelude.curry")
''')
    self.assertTrue(curry.eval(module.sourceAvailable).one())

  @unittest.expectedFailure
  def test_all_values_foreign_search(self):
    module = curry.compile(ALL_VALUES)
    self.assertEqual(curry.eval(module.values).one(), [0, 1, 1, 2])

  @unittest.expectedFailure
  def test_one_value_foreign_search(self):
    module = curry.compile(ALL_VALUES)
    self.assertEqual(curry.show(curry.eval(module.value).one()), 'Just 0')

  @unittest.expectedFailure
  def test_legacy_findall_foreign_search(self):
    module = curry.compile(ALL_VALUES.replace('Control.AllValues', 'Control.Findall'))
    self.assertEqual(curry.eval(module.values).one(), [0, 1, 1, 2])

  @unittest.expectedFailure
  def test_strong_search_keeps_unbound_results(self):
    module = curry.compile('''module Control.Search.SearchTree.Unsafe where
allNormalForms :: a -> [a]
allNormalForms external
goal :: Int
goal = length (allNormalForms (id (_ :: Bool)))
''')
    self.assertEqual(curry.eval(module.goal).one(), 1)

  @unittest.expectedFailure
  def test_base_package_startup_with_prelude_source(self):
    with tempfile.TemporaryDirectory() as directory:
      shutil.copyfile(config.installed_path('curry', 'Prelude.curry'),
                      Path(directory) / 'Prelude.curry')
      result = subprocess.run([sys.executable, '-c', 'import curry; curry.reset()'],
          env=dict(os.environ, CURRYPATH=directory), text=True,
          capture_output=True, timeout=120)
      self.assertEqual(result.returncode, 0, result.stderr)

  @unittest.expectedFailure
  def test_setfunctions_package_reserved_source(self):
    with tempfile.TemporaryDirectory() as directory:
      target = Path(directory) / 'Control'
      target.mkdir()
      shutil.copyfile(config.installed_path('curry', 'Control', 'SetFunctions.curry'),
                      target / 'SetFunctions.curry')
      result = subprocess.run([sys.executable, '-c',
          "import curry; curry.import_('Control.SetFunctions')"],
          env=dict(os.environ, CURRYPATH=directory), text=True,
          capture_output=True, timeout=120)
      self.assertEqual(result.returncode, 0, result.stderr)
