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
          child = subprocess.run([sys.executable, '-c', script, str(path), kind,
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
          child = subprocess.run([sys.executable, '-c', script, tmp],
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
          child = subprocess.run([sys.executable, '-c', script, tmp],
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
      tool = str(Path(config.prefix()) / 'bin' / 'sprite-exec')
      child = subprocess.run([tool, '-g', 'exitTest', 'PrimitiveIO'], env=env,
          capture_output=True, text=True)
      self.assertEqual(child.returncode, 23, child.stderr)
      child = subprocess.run([tool, '-g', 'pipeTerminal', 'PrimitiveIO'], env=env,
          input='', capture_output=True, text=True)
      self.assertEqual(child.returncode, 0, child.stderr)
      self.assertIn('False', child.stdout)
      for goal, expected in (('pipeReady', 'True'), ('pipeReadyIndex', '0')):
        child = subprocess.run([tool, '-g', goal, 'PrimitiveIO'], env=env,
            input='x', capture_output=True, text=True)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(child.stdout.strip(), expected)
      child = subprocess.run([sys.executable, '-m', 'curry.tools.icy',
          ':load', str(SOURCE / 'PrimitiveIO.curry')], env=env,
          input=':eval exitTest\n', capture_output=True, text=True)
      self.assertEqual(child.returncode, 23, child.stderr)
    curry.reset(interpret='off')
    curry.path.insert(0, str(SOURCE))
    M = curry.compile('import System.Process\nmain :: IO ()\nmain = exitWith 23\n')
    with tempfile.TemporaryDirectory() as tmp:
      saved = str(Path(tmp) / 'saved')
      curry.save(M, saved, main='main')
      child = subprocess.run([sys.executable, saved],
          env=dict(os.environ, CURRYPATH=str(SOURCE),
              SPRITE_INTERPRETER_FLAGS='backend:cxx,interpret:off'),
          capture_output=True, text=True)
      self.assertEqual(child.returncode, 23, child.stderr)

if __name__ == '__main__':
  unittest.main()
