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
