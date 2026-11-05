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
  @unittest.expectedFailure
  def test_bidirectional_command_stream(self):
    curry.path.insert(0, str(BINARY))
    module = curry.compile('''import System.IO
import System.IOExts
goal :: IO String
goal = do
  handle <- connectToCommand "cat"
  hPutStrLn handle "hello"
  hFlush handle
  line <- hGetLine handle
  hClose handle
  return line
''')
    self.assertEqual(curry.eval(module.goal).one(), 'hello')

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
  def test_base_package_startup_with_prelude_source(self):
    with tempfile.TemporaryDirectory() as directory:
      shutil.copyfile(config.installed_path('curry', 'Prelude.curry'),
                      Path(directory) / 'Prelude.curry')
      result = subprocess.run([sys.executable, '-c', 'import curry; curry.reset()'],
          env=dict(os.environ, CURRYPATH=directory), text=True,
          capture_output=True, timeout=120)
      self.assertEqual(result.returncode, 0, result.stderr)
