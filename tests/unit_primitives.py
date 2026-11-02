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
modified :: IO Int
modified = do r <- newIORef (3 :: Int)
              modifyIORef r (+ 4)
              readIORef r
freeRef :: Int -> IO Int
freeRef n = do r <- newIORef x
               y <- readIORef r
               return (if y =:= n then y else failed)
  where x free
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
        ('textLength', 1, lambda s: len(s) if isinstance(s, str) else -1, False),
        ('character', 0, lambda: 'a', False),
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
    with self.assertRaisesRegex(EvaluationError, 'bad=name'):
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
    self.assertEqual(curry.eval(M.modified).one(), 7)
    self.assertEqual(curry.eval(M.freeRef(7)).one(), 7)
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
lazyList :: [Int]
lazyList = echo [1 + 2, 4 ? 5]
freeList :: [Int]
freeList = echo [x] where x free
text :: String -> String
text external
textLength :: String -> Int
textLength external
character :: Char
character external
characterCode :: Int
characterCode = ord character
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
    self.assertEqual(sorted(curry.eval(R.lazyList)), [[3, 4], [3, 5]])
    with self.assertRaisesRegex(curry.SuspensionError, 'Evaluation suspended'):
      curry.eval(R.freeList).one()
    self.assertEqual(curry.eval(R.textLength('x' * 5000)).one(), 5000)
    self.assertEqual(curry.eval(R.text('abc\u00e4')).one(), 'abc\u00e4')
    self.assertEqual(curry.eval(R.text('')).one(), '')
    self.assertEqual(curry.eval(R.textLength('')).one(), 0)
    self.assertEqual(curry.eval(R.character).one(), 'a')
    self.assertIsInstance(curry.eval(R.character).one(), curry.Char)
    self.assertEqual(curry.eval(R.characterCode).one(), 97)
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
    for mode in ('off', 'new', 'all'):
      curry.reset(interpret=mode, jit='off')
      M = curry.compile('''
import System.Environment
loop :: Int -> IO ()
loop n = if n == 0 then return () else getProgName >> loop (n-1)
''')
      count = 1000
      curry.eval(M.loop(1)).one()
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
    with self.assertRaisesRegex(ValueError, 'another shape: RegisteredPrimitives.increment'):
      curryrt.register_primitive('RegisteredPrimitives.increment', 2, increment)
    with self.assertRaisesRegex(ValueError, 'another shape: RegisteredPrimitives.increment'):
      curryrt.register_primitive('RegisteredPrimitives.increment', 1, increment, True)

    with self.assertRaisesRegex(
        ValueError, r'^primitive System\.CPUTime\.getCPUTime '
        r'is registered in C\+\+$'):
      curryrt.register_primitive('System.CPUTime.getCPUTime', 0, lambda: 0, True)

  def test_bare_runtime_state(self):
    curryrt.register_primitive('BarePrimitive.f', 0, lambda: 1)
    M = curry.compile('module BarePrimitive where\nf :: Int\nf external\n')
    interp = cytest.raw.interp()
    goal = cytest.raw.expr(M.f)
    istate = interp.backend.get_interpreter_state(interp)
    rts = curryrt.RuntimeStateBase(
        istate, goal, False, curryrt.NOLIMIT, 65536, 0)
    self.assertIsNone(rts.interp)
    try:
      with self.assertRaisesRegex(EvaluationError,
          'no interpreter owns this evaluation; primitives need one'):
        rts.next()
    finally:
      rts.close()

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
      for mode in ('off', 'new', 'all'):
        env = dict(os.environ, SPRITE_INTERPRETER_FLAGS='backend:cxx,interpret:' + mode)
        result = subprocess.run(cytest.tool_command([config.sprite_exec(), str(source)]),
            env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(map(int, result.stdout.split())), [40, 42])

  def test_registration_replacement_and_late(self):
    curry.reset()
    curryrt.register_primitive('ReplacementPrimitive.f', 0, lambda: 1)
    curryrt.register_primitive('ReplacementPrimitive.f', 0, lambda: 2)
    M = curry.compile('module ReplacementPrimitive where\nf :: Int\nf external\n')
    self.assertEqual(curry.eval(M.f).one(), 2)
    curryrt.register_primitive('ReplacementPrimitive.f', 0, lambda: 3)
    self.assertEqual(curry.eval(M.f).one(), 3)
    with self.assertRaisesRegex(ValueError, 'new primitive; register before the import'):
      curryrt.register_primitive('ReplacementPrimitive.newName', 0, lambda: 3)
    for arity, monadic in ((1, False), (0, True)):
      with self.assertRaisesRegex(ValueError, 'another shape: ReplacementPrimitive.f'):
        curryrt.register_primitive('ReplacementPrimitive.f', arity, lambda: 0, monadic)
    curry.reset()
    curryrt.register_primitive('ReplacementPrimitive.f', 0, lambda: 4)
    M = curry.compile('module ReplacementPrimitive where\nf :: Int\nf external\n')
    self.assertEqual(curry.eval(M.f).one(), 4)

  def test_registration_during_call(self):
    def replace():
      curryrt.register_primitive('ReentrantPrimitive.f', 0, lambda: 22)
      return 11
    curryrt.register_primitive('ReentrantPrimitive.f', 0, replace)
    M = curry.compile('module ReentrantPrimitive where\nf :: Int\nf external\n')
    self.assertEqual(curry.eval(M.f).one(), 11)
    self.assertEqual(curry.eval(M.f).one(), 22)

  def test_declared_result(self):
    curryrt.register_primitive('WrongPrimitive.f', 0, lambda: 'wrong')
    M = curry.compile('module WrongPrimitive where\nf :: Int\nf external\n')
    with self.assertRaisesRegex(EvaluationError, 'declared type Int'):
      curry.eval(M.f).one()

  def test_command_arguments(self):
    with tempfile.TemporaryDirectory() as directory:
      source = Path(directory) / 'PrimitiveArguments.curry'
      source.write_text('module PrimitiveArguments where\nimport System.Environment\n'
          'main :: IO (String, [String])\n'
          'main = do n <- getProgName; a <- getArgs; return (n,a)\n')
      result = subprocess.run(cytest.tool_command([config.sprite_exec(), str(source), 'first', 'two words']),
          text=True, capture_output=True)
      self.assertEqual(result.returncode, 0, result.stderr)
      self.assertEqual(result.stdout.strip(), '("PrimitiveArguments",["first","two words"])')
      for arguments in (['--', '-g'], ['-gfoo'], ['--go=main'], ['-ip'],
                        ['first', '--', '-g']):
        result = subprocess.run(cytest.tool_command([config.sprite_exec(), str(source)] + arguments),
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = arguments[1:] if arguments[0] == '--' else arguments
        self.assertEqual(result.stdout.strip(),
            '("PrimitiveArguments",[' + ','.join(json.dumps(x) for x in expected) + '])')
      M = curry.import_(str(source))
      saved = str(Path(directory) / 'saved')
      curry.save(M, saved, main='main')
      result = subprocess.run(([saved] if sys.platform == 'win32' else [sys.executable, saved]) + ['first', 'two words'],
          env=dict(os.environ, SPRITE_INTERPRETER_FLAGS='backend:cxx,interpret:new'),
          text=True, capture_output=True)
      self.assertEqual(result.returncode, 0, result.stderr)
      self.assertEqual(result.stdout.strip(), '("saved",["first","two words"])')

  def test_cached_registration_missing(self):
    with tempfile.TemporaryDirectory() as directory:
      source = Path(directory) / 'CachedPrimitive.curry'
      source.write_text('module CachedPrimitive where\nf :: Int\nf external\n')
      create = """import curry, json, sys
from curry.backends.cxx import curryrtbindings as rt, image
from curry.objects.handle import getHandle
curry.reset(interpret='off', jit='off')
rt.register_primitive('CachedPrimitive.f', 0, lambda: 42)
M = curry.import_(sys.argv[1])
assert curry.eval(M.f).one() == 42
from curry.backends.cxx.toolchain import input_record, Cpp2So
assert 'registry ["f"]' in Cpp2So(curry._interpreter_).product_facts(sys.argv[1])
assert input_record(curry._interpreter_, sys.argv[1])['registry'] == ['f']
assert image.read(image.filename(sys.argv[1]))['registry'] == ['f']
print(json.dumps([getHandle(M).sofilename, image.filename(sys.argv[1])]))
"""
      result = subprocess.run([sys.executable, '-c', create, str(source)],
          text=True, capture_output=True)
      self.assertEqual(result.returncode, 0, result.stderr)
      paths = json.loads(result.stdout)
      load = """import curry, sys
from curry.backends.cxx import curryrtbindings as rt
curry.reset(interpret='off', jit='off')
curry.import_('Prelude')
owner = rt.Module.find_or_create('CachedPrimitive')
try:
  if sys.argv[1] == 'image': rt.load_image(owner, sys.argv[2])
  else: rt.SharedCurryModule(sys.argv[2])
except Exception as error:
  assert 'primitive CachedPrimitive.f is not registered in this runtime' in str(error), str(error)
else:
  raise AssertionError('unregistered primitive accepted')
"""
      for kind, path in zip(('object', 'image'), paths):
        result = subprocess.run([sys.executable, '-c', load, kind, path],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
      # Normal imports must invalidate the cache and restore the external stub.
      for mode in ('off', 'new', 'all'):
        result = subprocess.run([sys.executable, '-c', create, str(source)],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        code = """import curry, sys
curry.reset(interpret=sys.argv[2], jit='off')
from curry.backends.cxx.toolchain import input_record, input_current
record = input_record(curry._interpreter_, sys.argv[1])
record['registry'] = ['f']
assert not input_current(record, sys.argv[1], curry._interpreter_)
M = curry.import_(sys.argv[1])
try: curry.eval(M.f).one()
except curry.EvaluationError as error: assert 'not implemented' in str(error)
else: raise AssertionError('external primitive succeeded')
"""
        result = subprocess.run([sys.executable, '-c', code, str(source), mode],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

      for mode in ('off', 'new', 'all'):
        build = """import curry, sys
curry.reset(interpret='off', jit='off')
M = curry.import_(sys.argv[1])
from curry.backends.cxx.toolchain import input_record
assert input_record(curry._interpreter_, sys.argv[1])['registry'] == []
"""
        result = subprocess.run([sys.executable, '-c', build, str(source)],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        code = """import curry, sys
from curry.backends.cxx import curryrtbindings as rt
curry.reset(interpret=sys.argv[2], jit='off')
from curry.backends.cxx import image
from curry.backends.cxx.toolchain import input_current
record = image.read(image.filename(sys.argv[1]))
assert record['registry'] == []
rt.register_primitive('CachedPrimitive.f', 0, lambda: 42)
assert not input_current(record, sys.argv[1], curry._interpreter_)
M = curry.import_(sys.argv[1])
assert curry.eval(M.f).one() == 42
assert image.read(image.filename(sys.argv[1]))['registry'] == ['f']
"""
        result = subprocess.run([sys.executable, '-c', code, str(source), mode],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

  def test_private_interpreter(self):
    from curry.interpreter import Interpreter
    interp = Interpreter(flags={'backend': 'cxx', 'interpret': 'all'})
    curryrt.register_primitive('PrivatePrimitive.f', 0, lambda: 'p')
    M = interp.compile('module PrivatePrimitive where\nf :: Char\nf external\n')
    self.assertNotIn('PrivatePrimitive', curry._interpreter_.modules)
    self.assertEqual(interp.eval(M.f).one(), 'p')

  def test_qualified_boundary_types(self):
    from curry.toolchain.flat2icurry import flatcurry as fc
    for name, value in [('Int', 1), ('Float', 1.0), ('Bool', True),
                        ('Char', 'a'), ('()', None), ('IO', None), ('String', '')]:
      with self.assertRaisesRegex(TypeError, 'unsupported primitive declared type'):
        curryrt._primitive_value(value, fc.TCons(('UserTypes', name), []))

  def test_integer_argument_limit(self):
    curryrt.register_primitive('LargePrimitive.f', 1, lambda n: 0)
    M = curry.compile('module LargePrimitive where\nf :: Int -> Int\nf external\n')
    old = sys.get_int_max_str_digits()
    try:
      sys.set_int_max_str_digits(640)
      with self.assertRaisesRegex(EvaluationError, 'primitive LargePrimitive.f:.*ValueError'):
        curry.eval(M.f(10 ** 700)).one()
    finally:
      sys.set_int_max_str_digits(old)

  def test_integer_result_limit(self):
    curryrt.register_primitive('LargeResultPrimitive.f', 0, lambda: 10 ** 700)
    M = curry.compile('module LargeResultPrimitive where\nf :: Int\nf external\n')
    old = sys.get_int_max_str_digits()
    try:
      sys.set_int_max_str_digits(640)
      with self.assertRaisesRegex(EvaluationError,
          r'primitive LargeResultPrimitive\.f:.*ValueError'):
        curry.eval(M.f).one()
    finally:
      sys.set_int_max_str_digits(old)
