import cytest # from ./lib; must be first
import curry
from curry import config, inspect
from curry.backends.cxx import curryrtbindings as curryrt
from curry.exceptions import EvaluationError, CurryIOError
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


REF_PROGRAM = '''
module PrimitiveRefs where
import Data.IORef
main :: IO Int
main = do r <- newIORef (error "initial value forced")
          writeIORef r (20 ? 21)
          x <- readIORef r
          writeIORef r 99
          return (x + x)
sharing :: IO (Int, Int)
sharing = do r <- newIORef (1 :: Int)
             x <- readIORef r
             writeIORef r (x + 1)
             y <- readIORef r
             return (x,y)
opaque :: IO (IORef Int)
opaque = newIORef (error "reference field forced")
'''

CALLS = []

def increment(value):
  CALLS.append(value)
  return value + 1

def broken():
  raise ValueError('primitive test failure')

class Unprintable(Exception):
  def __str__(self):
    raise ValueError('exception string failed')

def unprintable():
  raise Unprintable()

def interrupted():
  raise KeyboardInterrupt

def exited():
  raise SystemExit(23)


class TestPrimitives(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    for name, arity, function, monadic in [
        ('increment', 1, increment, False),
        ('echo', 1, lambda x: x, False),
        ('text', 1, lambda x: x, False),
        ('pair', 1, lambda x: x, False),
        ('floating', 1, lambda x: x, False),
        ('boolean', 1, lambda x: x, False),
        ('unit', 0, lambda: None, True),
        ('action', 1, increment, True),
        ('broken', 0, broken, False),
        ('interrupted', 0, interrupted, False),
        ('exited', 0, exited, True),
        ('brokenIO', 0, broken, True),
        ('unprintable', 0, unprintable, True)]:
      curryrt.register_primitive('RegisteredPrimitives.' + name,
          arity, function, monadic)

  def check_primitives(self):
    D = curry.import_('Curry.Compiler.Distribution')
    version = tuple(map(int, (Path(__file__).resolve().parent.parent /
        'VERSION').read_text().strip().split('a')[0].split('.')))
    for name in ('curryCompiler', 'curryRuntime'):
      self.assertEqual(curry.eval(D[name]).one(), 'sprite')
      for suffix, expected in zip(('MajorVersion', 'MinorVersion'), version):
        self.assertEqual(curry.eval(D[name + suffix]).one(), expected)
    self.assertEqual(curry.eval(D.curryCompilerRevisionVersion).one(), version[2])
    self.assertEqual(curry.eval(D.baseVersion).one(), config.currylib_version())
    self.assertEqual(curry.eval(D.installDir).one(), config.prefix())
    self.assertIn('registered C++ primitive', inspect.getimpl(D.curryCompiler))

    T = curry.import_('System.CPUTime')
    before = [curry.eval(T[name]).one() for name in ('getCPUTime', 'getElapsedTime')]
    deadline = time.process_time() + .025
    while time.process_time() < deadline:
      sum(range(1000))
    after = [curry.eval(T[name]).one() for name in ('getCPUTime', 'getElapsedTime')]
    for a, b in zip(before, after):
      self.assertGreaterEqual(a, 0)
      self.assertGreater(b, a)

    E = curry.import_('System.Environment')
    key = 'SPRITE_PRIMITIVE_ROUNDTRIP'
    old = os.environ.get(key)
    try:
      curry.eval(E.setEnv(key, 'primitive value')).one()
      self.assertEqual(curry.eval(E.getEnv(key)).one(), 'primitive value')
      curry.eval(E.unsetEnv(key)).one()
      self.assertEqual(curry.eval(E.getEnv(key)).one(), '')
    finally:
      if old is not None:
        curry.eval(E.setEnv(key, old)).one()
    with self.assertRaises(EvaluationError):
      curry.eval(E.setEnv('bad=name', 'value')).one()
    self.assertEqual(curry.eval(E.isWindows).one(), sys.platform == 'win32')
    self.assertEqual(curry.eval(E.getArgs).one(), sys.argv[1:])
    self.assertEqual(curry.eval(E.getProgName).one(), sys.argv[0])
    import socket
    self.assertEqual(curry.eval(E.getHostname).one(), socket.gethostname())
    self.assertIn('registered Python primitive', inspect.getimpl(E.getProgName))

    M = curry.compile(REF_PROGRAM)
    self.assertEqual(sorted(curry.eval(M.main)), [40, 42])
    self.assertEqual(curry.eval(M.sharing).one(), (1, 2))
    ref = curry.eval(M.opaque).one()
    self.assertEqual(curry.show(ref), '<IORef>')
    self.assertIn('<IORef>', str(ref._node))
    self.assertEqual(ref, ref)
    self.assertNotEqual(ref, curry.eval(M.opaque).one())

    R = curry.compile('''
module RegisteredPrimitives where
increment :: Int -> Int
increment external
echo :: [Int] -> [Int]
echo external
text :: String -> String
text external
pair :: (Int, Bool) -> (Int, Bool)
pair external
floating :: Float -> Float
floating external
boolean :: Bool -> Bool
boolean external
unit :: IO ()
unit external
action :: Int -> IO Int
action external
broken :: Int
broken external
interrupted :: Int
interrupted external
exited :: IO Int
exited external
brokenIO :: IO Int
brokenIO external
missing :: Int
missing external
unprintable :: IO Int
unprintable external
recovered :: IO Int
recovered = catch brokenIO (\\_ -> return 7)
''')
    self.assertEqual(curry.eval(R.increment(2 ** 80)).one(), 2 ** 80 + 1)
    self.assertEqual(curry.eval(R.echo([1, 2, 3])).one(), [1, 2, 3])
    self.assertEqual(curry.eval(R.text('abc\u00e4')).one(), 'abc\u00e4')
    self.assertEqual(curry.eval(R.pair((3, True))).one(), (3, True))
    self.assertEqual(curry.eval(R.floating(1.25)).one(), 1.25)
    self.assertEqual(curry.eval(R.boolean(True)).one(), True)
    self.assertEqual(curry.eval(R.unit).one(), ())
    count = len(CALLS)
    action = R.action(10)
    self.assertEqual(len(CALLS), count)
    self.assertEqual(curry.eval(action).one(), 11)
    self.assertEqual(len(CALLS), count + 1)
    for goal in (R.broken, R.brokenIO):
      with self.assertRaisesRegex(EvaluationError, 'primitive test failure'):
        curry.eval(goal).one()
    with self.assertRaises(CurryIOError):
      curry.eval(R.brokenIO).one()
    self.assertEqual(curry.eval(R.recovered).one(), 7)
    with self.assertRaisesRegex(CurryIOError, 'an exception of the primitive'):
      curry.eval(R.unprintable).one()
    with self.assertRaises(KeyboardInterrupt):
      curry.eval(R.interrupted).one()
    with self.assertRaises(SystemExit) as exit:
      curry.eval(R.exited).one()
    self.assertEqual(exit.exception.code, 23)
    with self.assertRaisesRegex(EvaluationError, 'not implemented'):
      curry.eval(R.missing).one()

  @cytest.with_flags(interpret='off')
  def test_compiled(self):
    self.check_primitives()

  @cytest.with_flags(interpret='all')
  def test_interpreted(self):
    self.check_primitives()

  def test_python_call_cost(self):
    E = curry.import_('System.Environment')
    # Includes Python API construction, evaluation and result conversion.
    count = 1000
    begin = time.perf_counter()
    for _ in range(count):
      curry.eval(E.getProgName).one()
    elapsed = time.perf_counter() - begin
    print('getProgName: %d calls, %.6f s, %.3f us/call (Python API)' %
        (count, elapsed, elapsed * 1e6 / count))

  @cytest.with_flags(jit='off')
  def test_python_call_cost_in_curry(self):
    for mode in ('off', 'all'):
      curry.reset(interpret=mode, jit='off')
      M = curry.compile('''
import System.Environment
loop :: Int -> IO ()
loop n = if n == 0 then return () else getProgName >> loop (n-1)
''')
      count = 1000
      curry.eval(M.loop(1)).one()
      class CountingArgs(list):
        reads = 0
        def __getitem__(self, index):
          self.reads += 1
          return super().__getitem__(index)
      original = sys.argv
      tracked = CountingArgs(original or ['primitive-test'])
      try:
        sys.argv = tracked
        curry.eval(M.loop(count)).one()
      finally:
        sys.argv = original
      self.assertEqual(tracked.reads, count)
      begin = time.perf_counter()
      curry.eval(M.loop(count)).one()
      elapsed = time.perf_counter() - begin
      print('getProgName: %d calls, %.6f s, %.3f us/call (Curry loop, %s)' %
          (count, elapsed, elapsed * 1e6 / count, mode))

  def test_registration_validation(self):
    with self.assertRaises(ValueError):
      curryrt.register_primitive('unqualified', 0, lambda: 1)
    with self.assertRaises(ValueError):
      curryrt.register_primitive('Test.bad', -1, lambda: 1)
    with self.assertRaises(TypeError):
      curryrt.register_primitive('Test.bad', 0, None)
    with self.assertRaises(ValueError):
      curryrt.register_primitive('RegisteredPrimitives.increment', 1, increment)

  def test_child_arguments(self):
    code = '''import curry, json
E = curry.import_('System.Environment')
print(json.dumps([curry.eval(E.getProgName).one(), curry.eval(E.getArgs).one()]))
'''
    result = subprocess.run([sys.executable, '-c', code, 'first', 'two words'],
        text=True, capture_output=True)
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(json.loads(result.stdout), ['-c', ['first', 'two words']])

  def test_sprite_exec(self):
    with tempfile.TemporaryDirectory() as directory:
      source = Path(directory) / 'PrimitiveRefs.curry'
      source.write_text(REF_PROGRAM)
      for mode in ('off', 'all'):
        env = dict(os.environ, SPRITE_INTERPRETER_FLAGS='backend:cxx,interpret:' + mode)
        result = subprocess.run([config.sprite_exec(), str(source)],
            env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(map(int, result.stdout.split())), [40, 42])
