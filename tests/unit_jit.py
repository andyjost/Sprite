'''
Tests of the JIT of the C++ backend (backends/cxx/llvmjit.py; issue #65).

The JIT compiles the bytecode of an interpreted function to LLVM code in
process and swaps the step of its table.  Each goal below runs on the
interpreter and on the JIT, over every kind of opcode: the cases on
constructors and on literals of each kind (Int, big Int, Char, Float), the
nondeterminism of ?, a recursive let, a partial application, a failure, a
free variable and a string literal.  The file skips where the JIT is
unavailable: without llvmlite, or without the bitcode of the helpers that
CMake builds when it finds clang.
'''
import cytest # from ./lib; must be first
import curry, unittest
from curry import inspect
from curry.backends.cxx import curryrtbindings as curryrt, llvmjit

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

  def evaluate(self, **flags):
    curry.reset(backend='cxx', interpret='new', **flags)
    M = curry.compile(PROGRAM)
    results = {}
    for goal, _ in GOALS:
      results[goal] = sorted(curry.eval(curry.parse(goal, imports=[M])), key=repr)
    return results

  @cytest.hardreset
  def test_values_match_the_interpreter(self):
    expected = self.evaluate(jit=False)
    before = llvmjit.statistics()['functions']
    actual = self.evaluate(jit=True)
    self.assertGreater(llvmjit.statistics()['functions'], before)
    for goal, values in GOALS:
      self.assertEqual(expected[goal], values, goal)
      self.assertEqual(actual[goal], values, goal)

  @cytest.hardreset
  def test_a_jit_function_keeps_its_bytecode(self):
    '''The table reports the JIT step; inspect shows the bytecode it ran from.'''
    curry.reset(backend='cxx', interpret='new', jit=True, inline_budget=0)
    M = curry.compile('double :: Int -> Int\ndouble x = x + x')
    self.assertEqual(curry.eval(M.double(21)).one(), 42)
    self.assertTrue(curryrt.icurry_is_jit(M.double.info))
    self.assertFalse(curryrt.icurry_is_interpreted(M.double.info))
    text = inspect.getimpl(M.double)
    self.assertRegex(text.splitlines()[1], r'^bytecode: \d+ units')
    self.assertIn('RET_NODE', text)

  @cytest.hardreset
  def test_unavailable_jit_leaves_the_function_interpreted(self):
    '''A JIT that cannot run logs once and the module runs interpreted.'''
    import logging
    from curry.backends.cxx import materialize
    saved = llvmjit._jit, llvmjit._reason, materialize._JIT_WARNED
    try:
      llvmjit._jit, llvmjit._reason = None, 'a test'
      materialize._JIT_WARNED = False
      curry.reset(backend='cxx', interpret='new', jit=True)
      with self.assertLogs('curry.backends.cxx.materialize', level=logging.WARNING) as logs:
        M = curry.compile('double :: Int -> Int\ndouble x = x + x')
        self.assertEqual(curry.eval(M.double(21)).one(), 42)
      self.assertEqual(len(logs.records), 1)
      self.assertIn('a test', logs.output[0])
    finally:
      llvmjit._jit, llvmjit._reason, materialize._JIT_WARNED = saved
