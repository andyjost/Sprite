import cytest # from ./lib; must be first
import contextlib
import gc
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
import curry
from curry import config
from curry.backends.cxx import curryrtbindings as curryrt

SOURCE = Path('data/curry/libprims2').resolve()

class TestPrimitivesIO(cytest.TestCase):
  def run_child(self, command, timeout=120, **kwargs):
    # Unused stdin must be closed: a compiler or child must not wait on the
    # test runner's inherited pipe. communicate drains both output pipes.
    data = kwargs.pop('input', None)
    check = kwargs.pop('check', False)
    if data is None:
      kwargs.setdefault('stdin', subprocess.DEVNULL)
    else:
      kwargs['stdin'] = subprocess.PIPE
    if kwargs.pop('capture_output', False):
      kwargs['stdout'] = kwargs['stderr'] = subprocess.PIPE
    child = subprocess.Popen(command, close_fds=True, **kwargs)
    try:
      stdout, stderr = child.communicate(input=data, timeout=timeout)
    except subprocess.TimeoutExpired as error:
      child.kill()
      try:
        stdout, stderr = child.communicate(timeout=10)
      except subprocess.TimeoutExpired as drain_error:
        stdout = drain_error.stdout or error.stdout
        stderr = drain_error.stderr or error.stderr
        # A descendant can retain the pipes. Do not close a Windows pipe
        # while communicate's reader thread is blocked on it.
        child.wait(timeout=10)
      self.fail('child timed out: %r\nstdout: %r\nstderr: %r' %
                (command, stdout, stderr))
    result = subprocess.CompletedProcess(command, child.returncode, stdout, stderr)
    if check:
      result.check_returncode()
    return result

  def test_child_timeout_reports_output(self):
    script = "import time; print('child started', flush=True); time.sleep(60)"
    with self.assertRaisesRegex(AssertionError, 'child started'):
      self.run_child([sys.executable, '-c', script], timeout=1,
                     capture_output=True, text=True)

  def test_child_timeout_with_descendant_holding_output(self):
    with tempfile.TemporaryDirectory() as directory:
      stop = Path(directory) / 'stop'
      descendant = (
          'import pathlib, sys, time\n'
          'print("descendant started", flush=True)\n'
          'while not pathlib.Path(sys.argv[1]).exists(): time.sleep(.05)\n')
      script = (
          'import subprocess, sys, time\n'
          'subprocess.Popen([sys.executable, "-c", sys.argv[1], sys.argv[2]])\n'
          'time.sleep(60)\n')
      popen = subprocess.Popen
      children = []
      def launch(*args, **kwargs):
        child = popen(*args, **kwargs)
        children.append(child)
        return child
      try:
        start = time.monotonic()
        with unittest.mock.patch.object(subprocess, 'Popen', side_effect=launch):
          with self.assertRaisesRegex(AssertionError, 'child timed out') as raised:
            self.run_child([sys.executable, '-c', script, descendant, str(stop)],
                           timeout=1, capture_output=True, text=True)
        if sys.platform != 'win32':
          self.assertIn('descendant started', str(raised.exception))
        self.assertLess(time.monotonic() - start, 15)
        self.assertIsNotNone(children[0].returncode)
      finally:
        stop.touch()
        # EOF confirms that the descendant released its inherited output.
        for child in children:
          if child.poll() is None:
            child.kill()
          stdout, _ = child.communicate(timeout=10)
          self.assertIn('descendant started', stdout)

  def module(self):
    curry.path.insert(0, str(SOURCE))
    return curry.import_('PrimitiveIO')

  def check_io(self):
    M = self.module()
    IO = curry.import_('System.IO')
    with tempfile.TemporaryDirectory() as tmp:
      path = str(Path(tmp) / 'utf8-\u00e9.txt')
      text = 'a\u00e9\U0001f600'
      curry.eval(M.writeText(path, text)).one()
      curry.eval(M.appendText(path, 'z')).one()
      self.assertEqual(Path(path).read_bytes(), (text + 'z').encode())
      self.assertEqual(curry.eval(M.readText(path)).one(), text + 'z')
      self.assertEqual(curry.eval(M.seekText(path)).one(), 'z')
      self.assertEqual(curry.eval(M.absoluteText(path)).one(), 'a')
      self.assertTrue(curry.eval(M.identity(path)).one())
      self.assertEqual(curry.eval(M.properties(path)).one(), (True, False))
      self.assertEqual(curry.eval(M.ready(path)).one(), (True, 0))
      with self.assertRaisesRegex(curry.CurryIOError, 'closed'):
        curry.eval(M.closed(path)).one()
      Path(path).write_text('x')
      self.assertTrue(curry.eval(M.eof(path)).one())
      with self.assertRaises(curry.CurryIOError):
        curry.eval(IO.openFile(str(Path(tmp) / 'missing'), IO.ReadMode)).one()
      h = curry.eval(IO.openFile(path, IO.ReadMode)).one()
      self.assertEqual(curry.show(h), '<Handle>')
      self.assertEqual(h, h)
      gc.collect()
      curryrt.gc_collect()
      self.assertEqual(curry.eval(IO.hGetChar(h)).one(), 'x')
      with self.assertRaisesRegex(curry.CurryIOError, 'EOF'):
        curry.eval(IO.hGetChar(h)).one()
      curry.eval(IO.hFlush(h)).one()
      curry.eval(IO.hClose(h)).one()
      for operation in (IO.hGetChar, IO.hFlush, IO.hIsEOF, IO.hIsReadable,
                        IO.hIsWritable, IO.hIsTerminalDevice):
        with self.assertRaises(curry.CurryIOError):
          curry.eval(operation(h)).one()
    with tempfile.TemporaryDirectory() as tmp:
      path = str(Path(tmp) / 'finalized')
      h = curry.eval(IO.openFile(path, IO.WriteMode)).one()
      curry.eval(IO.hPutChar(h, curry.Char('x'))).one()
      del h
      gc.collect()
      curryrt.gc_collect()
      self.assertEqual(Path(path).read_bytes(), b'x')
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
      print('before', end='')
      curry.eval(M.output).one()
      print('after', end='')
    self.assertEqual(output.getvalue(), 'beforePHafter')
    errors = io.StringIO()
    with contextlib.redirect_stderr(errors):
      curry.eval(M.traceValue).one()
    self.assertIn('trace message', errors.getvalue())
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
      values = list(curry.eval(M.choiceOutput))
    self.assertEqual(len(values), 2)
    self.assertEqual(output.getvalue(), 'AB')
    with unittest.mock.patch('sys.stdin', io.StringIO('xy')):
      self.assertTrue(curry.eval(IO.hReady(IO.stdin)).one())
      self.assertEqual(curry.eval(M.stdInput).one(), ('x', 'y'))
    with unittest.mock.patch('sys.stdin', io.StringIO('\udce4x')):
      self.assertEqual(curry.eval(M.stdInput).one(), ('\ufffd', 'x'))
    for data in (b'\xc3a', b'\xc3', b'\xed\xa0\x80'):
      stream = io.TextIOWrapper(io.BytesIO(data), encoding='utf-8', errors='strict')
      with unittest.mock.patch('sys.stdin', stream):
        for expected in data.decode('utf-8', 'replace'):
          self.assertEqual(curry.eval(IO.hGetChar(IO.stdin)).one(), expected)
        with self.assertRaises(curry.CurryIOError):
          curry.eval(IO.hGetChar(IO.stdin)).one()
    with self.assertRaises(SystemExit) as caught:
      curry.eval(M.exitTest).one()
    self.assertEqual(caught.exception.code, 23)

  @cytest.with_flags(interpret='off')
  def test_compiled(self):
    self.check_io()

  @cytest.with_flags(interpret='all')
  def test_interpreted(self):
    self.check_io()

  def check_packages(self):
    M = self.module()
    D = curry.import_('System.Directory')
    P = curry.import_('System.Process')
    call = lambda function, *args: curry.eval(function(*args) if args else function).one()
    self.assertEqual(call(P.getPID), os.getpid())
    self.assertEqual(call(P.system, 'exit 7'), 7)
    start = time.monotonic()
    call(P.sleep, 1)
    self.assertGreaterEqual(time.monotonic() - start, .9)
    call(P.sleep, 0)
    with tempfile.TemporaryDirectory() as tmp:
      folder = str(Path(tmp) / 'folder')
      renamed = str(Path(tmp) / 'renamed')
      path = str(Path(tmp) / 'file')
      other = str(Path(tmp) / 'other')
      Path(path).write_bytes(b'abc')
      self.assertTrue(call(D.doesFileExist, path))
      self.assertFalse(call(D.doesDirectoryExist, path))
      self.assertFalse(call(D.doesFileExist, other))
      self.assertEqual(call(D.getFileSize, path), 3)
      self.assertAlmostEqual(call(M.modification, path), os.path.getmtime(path), delta=2)
      call(D.createDirectory, folder)
      self.assertTrue(call(D.doesDirectoryExist, folder))
      self.assertFalse(call(D.doesFileExist, folder))
      self.assertEqual(set(call(D.getDirectoryContents, tmp)), {'.', '..', 'file', 'folder'})
      call(D.renameDirectory, folder, renamed)
      call(D.renameFile, path, other)
      old = os.getcwd()
      try:
        call(D.setCurrentDirectory, renamed)
        self.assertEqual(Path(call(D.getCurrentDirectory)).resolve(), Path(renamed).resolve())
      finally:
        os.chdir(old)
      for function, argument in ((D.createDirectory, renamed), (D.removeFile, renamed),
                                 (D.removeDirectory, other), (D.getFileSize, path)):
        with self.assertRaises(curry.CurryIOError): call(function, argument)
      call(D.removeFile, other)
      call(D.removeDirectory, renamed)

  @cytest.with_flags(interpret='off')
  def test_packages_compiled(self):
    self.check_packages()

  @cytest.with_flags(interpret='all')
  def test_packages_interpreted(self):
    self.check_packages()

  def test_buffered_input_and_seek(self):
    self.module()
    IO = curry.import_('System.IO')
    for content in ('ab', '\u00e9b', '\U0001f600b'):
      for stream in (io.StringIO(content),
                     io.TextIOWrapper(io.BytesIO(content.encode()), encoding='utf-8')):
        with unittest.mock.patch('sys.stdin', stream):
          self.assertFalse(curry.eval(IO.hIsEOF(IO.stdin)).one())
          curry.eval(IO.hSeek(IO.stdin, IO.RelativeSeek, 0)).one()
          self.assertEqual(curry.eval(IO.hGetChar(IO.stdin)).one(), content[0])
    reader, writer = os.pipe()
    with os.fdopen(reader, 'r', encoding='utf-8') as stream, os.fdopen(writer, 'wb') as output:
      output.write(b'ab')
      output.flush()
      with unittest.mock.patch('sys.stdin', stream):
        self.assertEqual(stream.read(1), 'a')
        self.assertTrue(curry.eval(IO.hReady(IO.stdin)).one())
        self.assertEqual(curry.eval(IO.hGetChar(IO.stdin)).one(), 'b')
        self.assertFalse(curry.eval(IO.hReady(IO.stdin)).one())
    with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as stream:
      stream.write('ab')
      stream.seek(0)
      with unittest.mock.patch('sys.stdin', stream):
        for timeout in (0, -1):
          self.assertTrue(curry.eval(IO.hWaitForInput(IO.stdin, timeout)).one())
        self.assertEqual(curry.eval(IO.hGetChar(IO.stdin)).one(), 'a')
        self.assertEqual(curry.eval(IO.hGetChar(IO.stdin)).one(), 'b')
        self.assertTrue(curry.eval(IO.hWaitForInput(IO.stdin, -1)).one())

  def check_split_utf8_readiness(self):
    self.module()
    IO = curry.import_('System.IO')
    for prefix, suffix, expected in ((b'\xc3', b'\xa9b', '\u00e9'),
                                     (b'\xc2', b'\xa9b', '\u00a9'),
                                     (b'\xf0\x9f', b'\x98\x80b', '\U0001f600')):
      reader, writer = os.pipe()
      with os.fdopen(reader, 'r', encoding='utf-8', errors='strict') as stream, \
           os.fdopen(writer, 'wb', buffering=0) as output, \
           unittest.mock.patch('sys.stdin', stream):
        output.write(prefix)
        for repeat in range(2):
          self.assertFalse(curry.eval(IO.hReady(IO.stdin)).one())
        output.write(suffix)
        self.assertTrue(curry.eval(IO.hReady(IO.stdin)).one())
        self.assertEqual(curry.eval(IO.hGetChar(IO.stdin)).one(), expected)
        self.assertEqual(curry.eval(IO.hGetChar(IO.stdin)).one(), 'b')
        self.assertFalse(curry.eval(IO.hReady(IO.stdin)).one())
        output.close()
        self.assertTrue(curry.eval(IO.hIsEOF(IO.stdin)).one())

  @cytest.with_flags(interpret='off')
  def test_split_utf8_readiness_compiled(self):
    self.check_split_utf8_readiness()

  @cytest.with_flags(interpret='all')
  def test_split_utf8_readiness_interpreted(self):
    self.check_split_utf8_readiness()

  def test_native_shutdown_release_race(self):
    from curry.backends.cxx.curryrtbindings import _curryrtbindings
    self.assertTrue(_curryrtbindings._test_handle_shutdown_race())
    IO = curry.import_('System.IO')
    with tempfile.TemporaryDirectory() as tmp:
      path = str(Path(tmp) / 'shutdown')
      h = curry.eval(IO.openFile(path, IO.WriteMode)).one()
      curry.eval(IO.hPutChar(h, curry.Char('x'))).one()
      curryrt.shutdown_handles()
      self.assertEqual(Path(path).read_bytes(), b'x')
      for operation in (IO.hFlush, IO.hIsWritable):
        with self.assertRaisesRegex(curry.CurryIOError, 'closed'):
          curry.eval(operation(h)).one()
      curry.eval(IO.hClose(h)).one()

  @cytest.with_flags(interpret='off')
  def test_explicit_load_rejects_old_primitive_object(self):
    cxx = config.cxx_tool()
    if cxx is None:
      self.skipTest('no C++ compiler is installed')
    with tempfile.TemporaryDirectory() as tmp:
      source = Path(tmp) / 'OldDirectory.cpp'
      target = str(Path(tmp) / ('OldDirectory' + config.module_object_suffix()))
      source.write_text(
          '#include "curryrt/bom.hpp"\nusing namespace curryrt;\n'
          '#if defined(_WIN32)\n#define EXPORT __declspec(dllexport)\n'
          '#else\n#define EXPORT\n#endif\n'
          'extern "C" {\nextern EXPORT bom::Module const _bom_;\n'
          'EXPORT bom::Module const _bom_ = {2, "System.Directory", nullptr, '
          'nullptr, 0, nullptr, nullptr, 0, nullptr, 0, nullptr, 0};\n}\n')
      include = str(Path(config.installed_path('include')).resolve())
      command = [cxx, '-shared', '-fPIC', '-std=c++17', '-I' + include,
                 str(source), '-o', target]
      from curry.backends.cxx.toolchain import soname
      if sys.platform == 'darwin':
        command.append('-Wl,-install_name,' + soname('System.Directory', 20))
      elif os.name != 'nt':
        command.append('-Wl,-soname,' + soname('System.Directory', 20))
      if os.name == 'nt':
        command = [cxx, '/LD', '/std:c++17', '/EHsc', '/I' + include,
                   str(source), '/Fo' + str(Path(tmp) / 'OldDirectory.obj'),
                   '/link', '/OUT:' + target]
      self.run_child(command, check=True, capture_output=True, text=True)
      # Format 20 used record version 2. Rejection precedes any slot binding.
      # A fresh process has no previously mapped module with this name.
      script = """
import curry, sys
try:
  curry.load(sys.argv[1])
except curry.LoadError as error:
  assert 'version 2' in str(error), str(error)
else:
  raise AssertionError('explicit loading accepted an old-format object')
"""
      child = self.run_child([sys.executable, '-c', script, target],
          capture_output=True, text=True, env=dict(os.environ,
              SPRITE_INTERPRETER_FLAGS='backend:cxx,interpret:off,jit:off'))
      self.assertEqual(child.returncode, 0, child.stderr)
      with self.assertRaisesRegex(curry.LoadError, 'layout version 2'):
        curryrt.SharedCurryModule(target)

  @unittest.skipUnless(sys.platform == 'win32', 'Windows pipe probe')
  def test_windows_pipe_probe_error(self):
    import ctypes
    self.module()
    IO = curry.import_('System.IO')
    reader, writer = os.pipe()
    with os.fdopen(reader, 'r') as stream, os.fdopen(writer, 'w'):
      with unittest.mock.patch('sys.stdin', stream), \
           unittest.mock.patch.object(ctypes.windll.kernel32, 'PeekNamedPipe', return_value=0), \
           unittest.mock.patch.object(ctypes.windll.kernel32, 'GetLastError', return_value=5):
        with self.assertRaises(curry.CurryIOError):
          curry.eval(IO.hWaitForInput(IO.stdin, -1)).one()

  @unittest.skipUnless(sys.platform == 'win32', 'Windows legacy pipe buffering')
  def test_windows_legacy_buffered_pipe(self):
    self.module()
    IO = curry.import_('System.IO')
    reader, writer = os.pipe()
    with os.fdopen(reader, 'r', encoding='utf-8') as stream, os.fdopen(writer, 'wb') as output:
      output.write(b'ab')
      output.flush()
      self.assertEqual(stream.read(1), 'a')
      with unittest.mock.patch('sys.stdin', stream), \
           unittest.mock.patch.object(curryrt._os, 'get_blocking',
                                      side_effect=AttributeError, create=True):
        self.assertTrue(curry.eval(IO.hReady(IO.stdin)).one())
        self.assertEqual(curry.eval(IO.hGetChar(IO.stdin)).one(), 'b')
        self.assertFalse(curry.eval(IO.hReady(IO.stdin)).one())

  def test_stream_control_exceptions(self):
    self.module()
    IO = curry.import_('System.IO')
    Prelude = curry.import_('Prelude')
    class Output(io.StringIO):
      def write(self, text):
        raise exception
    for mode in ('off', 'all'):
      curry.reset(interpret=mode)
      IO = curry.import_('System.IO')
      Prelude = curry.import_('Prelude')
      for exception in (SystemExit(23), KeyboardInterrupt()):
        for action in (IO.hPutChar(IO.stdout, curry.Char('x')),
                       Prelude.putChar(curry.Char('x'))):
          with contextlib.redirect_stdout(Output()):
            with self.assertRaises(type(exception)) as caught:
              curry.eval(action).one()
          if isinstance(exception, SystemExit):
            self.assertEqual(caught.exception.code, 23)

  def test_open_handle_shutdown(self):
    script = """
import curry
import sys
IO = curry.import_('System.IO')
h = curry.eval(IO.openFile(sys.argv[1], IO.WriteMode)).one()
curry.eval(IO.hPutChar(h, curry.Char('x'))).one()
if sys.argv[2] == 'exit':
  curry.path.insert(0, sys.argv[3])
  P = curry.import_('System.Process')
  curry.eval(P.exitWith(23)).one()
"""
    with tempfile.TemporaryDirectory() as tmp:
      for mode in ('off', 'all'):
        for kind in ('normal', 'exit'):
          path = Path(tmp) / (mode + kind)
          child = self.run_child([sys.executable, '-c', script, str(path), kind,
                                  str(SOURCE)], capture_output=True, text=True,
              env=dict(os.environ, SPRITE_INTERPRETER_FLAGS='backend:cxx,interpret:' + mode))
          self.assertEqual(child.returncode, 23 if kind == 'exit' else 0, child.stderr)
          self.assertEqual(path.read_bytes(), b'x')

  def test_directory_symlinks(self):
    for mode in ('off', 'all'):
      curry.reset(interpret=mode)
      self.module()
      D = curry.import_('System.Directory')
      with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / 'target'
        target.mkdir()
        link = Path(tmp) / 'link'
        renamed = Path(tmp) / 'renamed'
        try:
          link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
          self.skipTest('symlinks cannot be created')
        curry.eval(D.renameFile(str(link), str(renamed))).one()
        self.assertTrue(renamed.is_symlink())
        curry.eval(D.removeFile(str(renamed))).one()
        self.assertFalse(renamed.is_symlink())
        self.assertTrue(target.is_dir())

  def test_shadowing_directory(self):
    script = """
import curry
import sys
curry.path.insert(0, sys.argv[1])
M = curry.import_('System.Directory')
assert curry.eval(M.getCurrentDirectory).one() == 'sentinel'
"""
    with tempfile.TemporaryDirectory() as tmp:
      source = Path(tmp) / 'System'
      source.mkdir()
      (source / 'Directory.curry').write_text(
          'module System.Directory where\n'
          'getCurrentDirectory :: IO String\n'
          'getCurrentDirectory = return "sentinel"\n')
      # A second import in a fresh process also exercises the persisted image.
      cases = [('off', 'off', 'auto'), ('all', 'off', 'auto'), ('all', 'eager', 'auto')]
      if config.cxx_tool():
        cases.append(('all', 'eager', 'cxx'))
      for mode, jit, backend in cases:
        for repeat in range(2):
          child = self.run_child([sys.executable, '-c', script, tmp],
              capture_output=True, text=True, env=dict(os.environ,
                  SPRITE_INTERPRETER_FLAGS='backend:cxx,interpret:%s,jit:%s,jit_backend:%s'
                      % (mode, jit, backend)))
          self.assertEqual(child.returncode, 0, child.stderr)

  def test_shadowing_unsafe_wrappers(self):
    script = """
import curry
import sys
# Bypass only the outer reserved-name guard to test primitive selection.
from curry.toolchain import _findcurry
_findcurry.reject_library_shadow = lambda *args: None
curry.path.insert(0, sys.argv[1])
M = curry.import_('System.IO.Unsafe')
assert curry.eval(M.isVar(0)).one() is True
assert curry.eval(M.identicalVar(0, 1)).one() is True
assert curry.eval(M.isGround(0)).one() is False
assert curry.eval(M.showAnyTerm(0)).one() == 'sentinel'
"""
    with tempfile.TemporaryDirectory() as tmp:
      source = Path(tmp) / 'System' / 'IO'
      source.mkdir(parents=True)
      (source / 'Unsafe.curry').write_text(
          'module System.IO.Unsafe where\n'
          'isVar :: Data a => a -> Bool\nisVar _ = True\n'
          'identicalVar :: Data a => a -> a -> Bool\nidenticalVar _ _ = True\n'
          'isGround :: Data a => a -> Bool\nisGround _ = False\n'
          'showAnyTerm :: _ -> String\nshowAnyTerm _ = "sentinel"\n')
      cases = [('off', 'off', 'auto'), ('all', 'off', 'auto'), ('all', 'eager', 'auto')]
      if config.cxx_tool():
        cases.append(('all', 'eager', 'cxx'))
      for mode, jit, backend in cases:
        for repeat in range(2):
          child = self.run_child([sys.executable, '-c', script, tmp],
              capture_output=True, text=True, env=dict(os.environ,
                  SPRITE_INTERPRETER_FLAGS='backend:cxx,interpret:%s,jit:%s,jit_backend:%s'
                      % (mode, jit, backend)))
          self.assertEqual(child.returncode, 0, child.stderr)

  def test_primitive_arity_mismatch(self):
    script = """
import curry
import sys
from curry.exceptions import EvaluationError
curry.path.insert(0, sys.argv[1])
M = curry.import_('System.Directory')
try:
  curry.eval(M.getCurrentDirectory(0)).one()
except EvaluationError as error:
  assert 'not implemented' in str(error), str(error)
else:
  raise AssertionError('mismatched primitive replaced the external')
"""
    with tempfile.TemporaryDirectory() as tmp:
      source = Path(tmp) / 'System'
      source.mkdir()
      (source / 'Directory.curry').write_text(
          'module System.Directory where\n'
          'getCurrentDirectory :: Int -> IO String\n'
          'getCurrentDirectory external\n')
      for mode in ('off', 'all'):
        for repeat in range(2):
          child = self.run_child([sys.executable, '-c', script, tmp],
              capture_output=True, text=True, env=dict(os.environ,
                  SPRITE_INTERPRETER_FLAGS='backend:cxx,interpret:' + mode))
          self.assertEqual(child.returncode, 0, child.stderr)

  def test_unsupported_builtin_arity(self):
    Prelude = curry.import_('Prelude')
    with self.assertRaisesRegex(curry.EvaluationError, 'is not used by Sprite'):
      curry.eval(Prelude.ifVar(1, 2, 3)).one()

  def test_upstream_directory_tests(self):
    self.module()
    # Test.Prop.returns is a CurryCheck placeholder in the pinned library.
    # Keep the upstream actions and assertions, supplying only its IO runner.
    source = (SOURCE / 'TestDirectory.curry').read_text().replace('import Test.Prop', '')
    source += '\nreturns :: Eq a => IO a -> a -> IO Bool\n'
    source += 'returns action expected = action >>= \\actual -> return (actual == expected)\n'
    for mode in ('off', 'all'):
      curry.reset(interpret=mode)
      curry.path.insert(0, str(SOURCE))
      module = curry.compile(source)
      with tempfile.TemporaryDirectory() as tmp:
        old = os.getcwd()
        try:
          os.chdir(tmp)
          for name in ('testCreateRenameDeleteFile', 'testCreateRenameDeleteDirectory',
                       'testGetSetDirectory', 'testGetDirectoryContents'):
            self.assertTrue(curry.eval(module[name]).one(), name)
        finally:
          os.chdir(old)

  def test_process_exit_and_pipe(self):
    M = self.module()
    for mode in ('off', 'all'):
      env = dict(os.environ, CURRYPATH=str(SOURCE),
          SPRITE_INTERPRETER_FLAGS='backend:cxx,interpret:' + mode)
      tool = [sys.executable, '-m', 'curry']
      child = self.run_child(tool + ['-g', 'exitTest', 'PrimitiveIO'], env=env,
          capture_output=True, text=True)
      self.assertEqual(child.returncode, 23, child.stderr)
      child = self.run_child(tool + ['-g', 'pipeTerminal', 'PrimitiveIO'], env=env,
          input='', capture_output=True, text=True)
      self.assertEqual(child.returncode, 0, child.stderr)
      self.assertIn('False', child.stdout)
      for goal, expected in (('pipeReady', 'True'), ('pipeReadyIndex', '0')):
        child = self.run_child(tool + ['-g', goal, 'PrimitiveIO'], env=env,
            input='x', capture_output=True, text=True)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(child.stdout.strip(), expected)
      child = self.run_child([sys.executable, '-m', 'curry.tools.icy',
          ':load', str(SOURCE / 'PrimitiveIO.curry')], env=env,
          input=':eval exitTest\n', capture_output=True, text=True)
      self.assertEqual(child.returncode, 23, child.stderr)
    curry.reset(interpret='off')
    curry.path.insert(0, str(SOURCE))
    M = curry.compile('import System.Process\nmain :: IO ()\nmain = exitWith 23\n')
    with tempfile.TemporaryDirectory() as tmp:
      saved = str(Path(tmp) / 'saved')
      curry.save(M, saved, main='main')
      child = self.run_child(([saved] if sys.platform == 'win32' else [sys.executable, saved]),
          env=dict(os.environ, CURRYPATH=str(SOURCE),
              SPRITE_INTERPRETER_FLAGS='backend:cxx,interpret:off'),
          capture_output=True, text=True)
      self.assertEqual(child.returncode, 23, child.stderr)

if __name__ == '__main__':
  unittest.main()
