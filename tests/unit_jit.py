'''
Tests of the JIT of the C++ backend (backends/cxx/llvmjit.py; issue #65).

The JIT compiles the bytecode of an interpreted function to LLVM code in
process and swaps the step of its table.  Each goal below runs on the
interpreter and on the JIT, over every kind of opcode: the cases on
constructors and on literals of each kind (Int, big Int, Char, Float), the
nondeterminism of ?, a recursive let, a partial application, a failure, a
free variable and a string literal.  The file skips where the JIT is
unavailable: without llvmlite (the extra curry[jit]), or without the
bitcode of the helpers that CMake builds when it finds clang.
'''
import cytest # from ./lib; must be first
import curry, os, tempfile, unittest
from curry import inspect
from curry.backends.cxx import curryrtbindings as curryrt, llvmjit
from unittest import mock

PROGRAM = r'''
fib :: Int -> Int
fib n = if n < 2 then n else fib (n - 1) + fib (n - 2)

-- Case expressions: rules with a catch-all would overlap and give two values.
classify :: Int -> String
classify n = case n of
  0 -> "zero"
  1 -> "one"
  10000000000000000000000 -> "big"
  _ -> "many"

small :: Int -> Int
small n = case n of
  0 -> 10
  1 -> 11
  _ -> 0

vowel :: Char -> Bool
vowel c = case c of
  'a' -> True
  'e' -> True
  _ -> False

half :: Float -> Int
half x = case x of
  0.5 -> 1
  1.5 -> 3
  _ -> 0

coin :: Int
coin = 1 ? 2

cycled :: [Int]
cycled = let xs = 1 : 2 : xs in take 5 xs

incAll :: [Int] -> [Int]
incAll = map (+1)

firstOf :: [Int] -> Int
firstOf (x:_) = x

bound3 :: Int
bound3 = let x free in x =:= 3 &> x

greeting :: String
greeting = "hello"
'''

GOALS = [
    ('fib 20', [6765])
  , ('classify 0', ['zero']), ('classify 1', ['one'])
  , ('classify 10000000000000000000000', ['big']), ('classify 7', ['many'])
  , ('small 1', [11]), ('small 5', [0])
  , ("vowel 'a'", [True]), ("vowel 'x'", [False])
  , ('half 1.5', [3]), ('half 2.5', [0])
  , ('coin', [1, 2]), ('cycled', [[1, 2, 1, 2, 1]])
  , ('incAll [1, 2, 3]', [[2, 3, 4]]), ('firstOf []', []), ('bound3', [3])
  , ('greeting', ['hello'])
  ]

class TestJIT(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    if not llvmjit.available():
      raise unittest.SkipTest('the JIT is unavailable in this installation')

  def evaluate(self, jit):
    curry.reset(backend='cxx', interpret='new', jit=jit, jit_backend='llvm')
    M = curry.compile(PROGRAM)
    results = {}
    for goal, _ in GOALS:
      results[goal] = sorted(curry.eval(curry.parse(goal, imports=[M])), key=repr)
    return results

  @cytest.hardreset
  def test_values_match_the_interpreter(self):
    expected = self.evaluate('off')
    before = llvmjit.statistics()['functions']
    actual = self.evaluate('eager')
    self.assertGreater(llvmjit.statistics()['functions'], before)
    for goal, values in GOALS:
      self.assertEqual(expected[goal], values, goal)
      self.assertEqual(actual[goal], values, goal)

  @cytest.hardreset
  def test_a_jit_function_keeps_its_bytecode(self):
    '''The table reports the JIT step; inspect shows the bytecode it ran from.'''
    curry.reset(backend='cxx', interpret='new', inline_budget=0, jit='eager', jit_backend='llvm')
    M = curry.compile('double :: Int -> Int\ndouble x = x + x')
    self.assertEqual(curry.eval(M.double(21)).one(), 42)
    self.assertTrue(curryrt.icurry_is_jit(M.double.info))
    self.assertFalse(curryrt.icurry_is_interpreted(M.double.info))
    text = inspect.getimpl(M.double)
    self.assertRegex(text.splitlines()[1], r'^bytecode: \d+ units')
    self.assertIn('RET_NODE', text)

  @cytest.hardreset
  def test_hot_tier_compiles_a_hot_function(self):
    '''A function that reaches the threshold is compiled on the JIT thread.'''
    import time
    for _ in range(2):
      with mock.patch.dict(os.environ, {'SPRITE_JIT_THRESHOLD': '5'}):
        curry.reset(backend='cxx', interpret='new', inline_budget=0, jit='hot', jit_backend='llvm')
        M = curry.compile(PROGRAM)
      before = llvmjit.statistics()['hot']
      self.assertEqual(curry.eval(M.fib(15)).one(), 610)
      # The thread compiles the hot functions; the swap is applied at a
      # safepoint of a scheduler, at the latest before the next evaluation.
      deadline = time.monotonic() + 30
      while llvmjit.statistics()['hot'] == before and time.monotonic() < deadline:
        time.sleep(0.02)
      self.assertGreater(llvmjit.statistics()['hot'], before)
      self.assertEqual(curry.eval(M.fib(15)).one(), 610)
      self.assertTrue(curryrt.icurry_is_jit(M.fib.info))

  @cytest.hardreset
  def test_unavailable_jit_leaves_the_function_interpreted(self):
    '''A JIT that cannot run logs once and the module runs interpreted.'''
    import logging
    from curry.backends.cxx import materialize
    saved = llvmjit._jit, llvmjit._reason, materialize._JIT_WARNED
    try:
      llvmjit._jit, llvmjit._reason = None, 'a test'
      materialize._JIT_WARNED = False
      curry.reset(backend='cxx', interpret='new', jit='eager', jit_backend='auto')
      with self.assertLogs('curry.backends.cxx.materialize', level=logging.WARNING) as logs:
        M = curry.compile('double :: Int -> Int\ndouble x = x + x')
        self.assertEqual(curry.eval(M.double(21)).one(), 42)
      self.assertEqual(len(logs.records), 1)
      self.assertIn('a test', logs.output[0])
    finally:
      llvmjit._jit, llvmjit._reason, materialize._JIT_WARNED = saved


class TestSelection(cytest.TestCase):
  @cytest.hardreset
  def test_defaults_and_retirement(self):
    from curry.interpreter.flags import get_default_flags
    defaults = get_default_flags()
    self.assertEqual(defaults['jit'], 'hot')
    self.assertEqual(defaults['jit_backend'], 'auto')
    self.assertEqual(defaults['interpret'], 'all' if os.name == 'nt' else 'new')
    with self.assertRaisesRegex(curry.FlagError, 'jit:hot.*jit_backend:cxx'):
      curry.reset(interpret=''.join(('tier', 'ed')))
    with mock.patch.dict(os.environ, {'SPRITE_INTERPRETER_FLAGS': 'interpret:' + ''.join(('tier', 'ed'))}):
      with self.assertRaisesRegex(curry.FlagError, 'jit:hot.*jit_backend:cxx'):
        curry.reset(backend='cxx')

  def missing_llvm(self):
    from curry.backends.cxx import jit
    real = jit.importlib.import_module
    def importing(name, *args, **kwds):
      if name == 'llvmlite':
        raise ImportError('test missing llvmlite')
      return real(name, *args, **kwds)
    return mock.patch.object(jit.importlib, 'import_module', side_effect=importing)

  @cytest.hardreset
  def test_auto_selection_and_forced_errors(self):
    from curry.backends.cxx import jit
    from curry import config
    with mock.patch.object(jit.importlib, 'import_module', return_value=mock.Mock(__version__='0.50.0')):
      curry.reset(jit_backend='auto')
      self.assertEqual(jit.backend(cytest.raw.interp()), 'llvm')
    with self.missing_llvm():
      with mock.patch.object(config, 'cxx_tool', return_value='c++'):
        with mock.patch.object(jit.sys, 'platform', 'linux'):
          curry.reset(jit_backend='auto')
          self.assertEqual(jit.backend(cytest.raw.interp()), 'cxx')
      with self.assertRaisesRegex(curry.FlagError, r'pip install curry\[jit\]'):
        curry.reset(jit_backend='llvm')
    with mock.patch.object(config, 'cxx_tool', return_value=None):
      with self.assertRaisesRegex(curry.FlagError, r'C\+\+ compiler'):
        curry.reset(jit_backend='cxx')
    with mock.patch.object(jit.sys, 'platform', 'win32'):
      with self.assertRaisesRegex(curry.FlagError, 'Windows'):
        curry.reset(jit_backend='cxx')

  @cytest.hardreset
  def test_forced_llvm_requires_usable_helpers(self):
    from curry.backends.cxx import jit
    with mock.patch.object(jit.importlib, 'import_module', return_value=mock.Mock(__version__='0.50.0')):
      with mock.patch.object(llvmjit, '_get', side_effect=llvmjit.Unavailable('missing helpers')):
        with self.assertRaisesRegex(curry.FlagError, r'jit_backend:llvm.*missing helpers.*curry\[jit\]'):
          curry.reset(jit_backend='llvm')

  @cytest.hardreset
  def test_no_backend_notice_once(self):
    from curry.backends.cxx import jit
    from curry import config
    with mock.patch.object(jit, '_warned', False), self.missing_llvm():
      with mock.patch.object(config, 'cxx_tool', return_value=None):
        with self.assertLogs('curry.backends.cxx.jit', level='WARNING') as logs:
          for _ in range(2):
            curry.reset(interpret='new', jit='hot', jit_backend='auto')
            M = curry.compile('double :: Int -> Int\ndouble x = x + x')
            self.assertEqual(curry.eval(M.double(21)).one(), 42)
            self.assertTrue(curryrt.icurry_is_interpreted(M.double.info))
        self.assertEqual(len(logs.records), 1)
        self.assertIn('jit: no backend, interpreter only', logs.output[0])


class TestGxx(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    from curry import config
    if os.name == 'nt' or config.cxx_tool() is None:
      raise unittest.SkipTest('cxx needs a C++ compiler')

  @cytest.hardreset
  def test_eager_text(self):
    curry.reset(interpret='new', jit='eager', jit_backend='cxx', inline_budget=0)
    with self.assertLogs('curry.backends.cxx.tiered', level='INFO') as logs:
      M = curry.compile('double :: Int -> Int\ndouble x = x + x')
    self.assertEqual(curry.eval(M.double(21)).one(), 42)
    self.assertFalse(curryrt.icurry_is_interpreted(M.double.info))
    self.assertTrue(any('jit eager: module' in line for line in logs.output))
    # Expression modules also participate in eager compilation.
    self.assertEqual(curry.eval(curry.parse('double 21', imports=[M])).one(), 42)
    from curry.objects.handle import getHandle
    expression = cytest.raw.interp()._expression_modules[-1]
    self.assertIsNotNone(getHandle(expression).sofilename)

  @cytest.hardreset
  def test_hot_text_waits_for_threshold(self):
    import time
    from curry.backends.cxx import tiered
    with mock.patch.dict(os.environ, {'SPRITE_JIT_THRESHOLD': '5'}):
      curry.reset(interpret='new', jit='hot', jit_backend='cxx', inline_budget=0)
      M = curry.compile('double :: Int -> Int\ndouble x = x + x')
    self.assertEqual(tiered.status()['queued'], 0)
    self.assertEqual(tiered.status()['running'], 0)
    for i in range(4):
      self.assertEqual(curry.eval(M.double(i)).one(), 2 * i)
    self.assertTrue(curryrt.icurry_is_interpreted(M.double.info))
    self.assertEqual(curry.eval(M.double(21)).one(), 42)
    self.assertTrue(tiered.wait(120, cytest.raw.interp()))
    self.assertFalse(curryrt.icurry_is_interpreted(M.double.info))
    self.assertEqual(curry.eval(M.double(21)).one(), 42)

  @cytest.hardreset
  def test_hot_compile_failure_stays_interpreted(self):
    from curry.backends.cxx import tiered
    with mock.patch.dict(os.environ, {
        'SPRITE_JIT_THRESHOLD': '1', 'CXXFLAGS': '-fno-such-flag-of-sprite'
        }):
      curry.reset(interpret='new', jit='hot', jit_backend='cxx', inline_budget=0)
      M = curry.compile('double :: Int -> Int\ndouble x = x + x')
    before = tiered.status()['failed_modules']
    with self.assertLogs('curry.backends.cxx.tiered', level='INFO') as logs:
      self.assertEqual(curry.eval(M.double(21)).one(), 42)
      self.assertTrue(tiered.wait(120, cytest.raw.interp()))
    self.assertEqual(tiered.status()['failed_modules'], before + 1)
    self.assertTrue(curryrt.icurry_is_interpreted(M.double.info))
    self.assertTrue(any('compile failed:' in line for line in logs.output))
    self.assertEqual(curry.eval(M.double(21)).one(), 42)

  @cytest.hardreset
  def test_aot_replaces_a_previous_llvm_step(self):
    if not llvmjit.available():
      self.skipTest('LLVM is unavailable')
    from curry.objects.handle import getHandle
    with tempfile.TemporaryDirectory(prefix='sprite-jit-aot-') as work:
      filename = os.path.join(work, 'JitAotReuse.curry')
      with open(filename, 'w') as stream:
        stream.write('module JitAotReuse where\nf :: Int -> Int\nf x = x + 1\n')
      curry.reset(interpret='new', jit='eager', jit_backend='llvm')
      M = curry.import_(filename)
      address = M.f.info.address
      self.assertTrue(curryrt.icurry_is_jit(M.f.info))
      curry.reset(interpret='off', jit='off', jit_backend='cxx')
      M = curry.import_(filename)
      self.assertIsNotNone(getHandle(M).sofilename)
      self.assertEqual(M.f.info.address, address)
      self.assertFalse(curryrt.icurry_is_jit(M.f.info))
      self.assertEqual(curry.eval(M.f(41)).one(), 42)

  @cytest.hardreset
  def test_current_aot_loads_whatever_jit_says(self):
    from curry.objects.handle import getHandle
    for backend in ('cxx', 'llvm') if llvmjit.available() else ('cxx',):
      for mode in ('new', 'off'):
        for tier in ('off', 'hot', 'eager'):
          curry.reset(interpret=mode, jit=tier, jit_backend=backend)
          M = curry.import_('Prelude')
          self.assertIsNotNone(getHandle(M).sofilename, (mode, tier))
          self.assertFalse(curryrt.icurry_is_interpreted(M.map.info))
