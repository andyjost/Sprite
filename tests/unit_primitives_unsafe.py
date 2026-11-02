import cytest # from ./lib; must be first
import curry
from curry.backends.cxx import curryrtbindings as curryrt
from curry.exceptions import EvaluationError
import math
import subprocess
import sys


PROGRAM = r'''
module UnsafePrimitives where
import System.IO.Unsafe
import Data.IORef
import Control.SetFunctions

data Tree = Leaf Int | Fork Tree Tree
data Operator = Int :*: Int

variables :: (Bool,Bool,Bool,Bool,Bool)
variables = (isVar (x::Int), identicalVar x x, identicalVar x y,
             isGround [x], isGround [1::Int]) where x,y free
bound :: (Bool,Bool,Bool)
bound = (isVar (1::Int), identicalVar (1::Int) 1, isGround [1::Int])
branches :: [(Int,Bool)]
branches = [if x =:= (1::Int) then (0,p) else failed] ? [(1,p)]
  where x free
        p = isVar x
branchesReverse :: [(Int,Bool)]
branchesReverse = [(1,p)] ? [if x =:= (1::Int) then (0,p) else failed]
  where x free
        p = isVar x
generatedBranches :: (Int,Bool)
generatedBranches = (if x then (0,p) else (1,p)) ? (2,p)
  where x free
        p = isVar x
groundBranches :: (Int,Bool)
groundBranches = (if x =:= (1::Int) then (0,p) else failed) ? (1,p)
  where x free
        p = isGround [x]
identityBranches :: (Int,Bool)
identityBranches = (if x =:= (1::Int) then (0,p) else failed) ? (1,p)
  where x free
        p = identicalVar x x
shownBranches :: (Int,String)
shownBranches = (if x =:= (1::Int) then (0,p) else failed) ? (1,p)
  where x free
        p = showAnyTerm [x]
expressionBranches :: (Int,String)
expressionBranches = (if x =:= (1::Int) then (0,p) else failed) ? (1,p)
  where x free
        p = showAnyExpression [x]
compareBranches :: (Int,Ordering)
compareBranches = (if x =:= (1::Int) then (0,p) else failed) ? (1,p)
  where x free
        p = compareAnyTerm x 1
alias :: Bool
alias = if (x::Int) =:= y then identicalVar x y else failed where x,y free

counter :: Int
counter = unsafePerformIO (do
  r <- newIORef (0::Int)
  let x = unsafePerformIO (do
        n <- readIORef r
        writeIORef r (n+1)
        return (n+1))
  let y = x + x
  return (y + unsafePerformIO (readIORef r)))
failedAction :: Int
failedAction = unsafePerformIO (failed :: IO Int)
raisingAction :: Int
raisingAction = unsafePerformIO (error "unsafe action raised" :: IO Int)

suspended :: Int
suspended = spawnConstraint (x == 7) (if x =:= 7 then x else failed)
  where x free
unboundSuspension :: Int
unboundSuspension = spawnConstraint (x == 7) x where x free
setSuspension :: [Int]
setSuspension = sortValues (set0 (spawnConstraint (x == 7) x)) where x free
nestedSuspension :: [Int]
nestedSuspension = spawnConstraint (x == 7) [if x =:= 7 then x else failed]
  where x free
falseConstraint :: Int
falseConstraint = spawnConstraint False (error "false constraint evaluated its value")
loop :: Bool
loop = loop
divergent :: Int
divergent = spawnConstraint loop 9

orders :: [Ordering]
orders = [compareAnyTerm (1::Int) 2, compareAnyTerm (2::Int) 1,
          compareAnyTerm (2^80::Int) (2^80), compareAnyTerm False True,
          compareAnyTerm (Leaf 1) (Fork (Leaf 0) (Leaf 0)),
          compareAnyTerm (1.25::Float) 1.5, compareAnyTerm 'z' 'a',
          compareAnyTerm x x, compareAnyTerm x (1::Int)] where x free
varOrder :: Bool
varOrder = compareAnyTerm (x::Int) y /= EQ && compareAnyTerm x y /= compareAnyTerm y x
  where x,y free
functionOrder :: Ordering
functionOrder = compareAnyTerm (id :: Int -> Int) id
functionArguments :: Ordering
functionArguments = compareAnyTerm ((+) (1::Int)) ((+) 2)

shownAliases :: String
shownAliases = if (x::Int) =:= y then showAnyTerm (x,y) else failed
  where x,y free
shown :: String
shown = showAnyTerm (Fork (Leaf (1+2)) (Leaf 4))
shownFree :: String
shownFree = showAnyTerm (x::Int,x,y::Int) where x,y free
shownExpression :: String
shownExpression = showAnyExpression (Leaf (1+2))
roundTrip :: Tree
roundTrip = readAnyUnqualifiedTerm ["UnsafePrimitives","Prelude"]
              (showAnyTerm (Fork (Leaf (-12)) (Leaf (2^80))))
roundTripList :: [Int]
roundTripList = readAnyUnqualifiedTerm ["Prelude"] (showAnyTerm [1,2,3::Int])
roundTripString :: String
roundTripString = readAnyUnqualifiedTerm ["Prelude"] (showAnyTerm "a\n\"\\")
unicodeRoundTrip :: String
unicodeRoundTrip = readAnyUnqualifiedTerm ["Prelude"]
                    (showAnyTerm [chr 228,'1',chr 0,'2'])
readFloat :: String -> Float
readFloat = readAnyUnqualifiedTerm ["Prelude"]
readChar :: String -> [(Char,String)]
readChar = readsAnyUnqualifiedTerm ["Prelude"]
readInt :: String -> [(Int,String)]
readInt = readsAnyUnqualifiedTerm ["Prelude"]
readWholeInt :: String -> Int
readWholeInt = readAnyUnqualifiedTerm ["Prelude"]
roundTripVariables :: Bool
roundTripVariables = case readsAnyUnqualifiedTerm ["Prelude"] "(_a,_a) tail" of
                       [((x,y),s)] -> identicalVar (x::Int) y && s == " tail"
                       _ -> False
badParse :: Bool
badParse = null (readsAnyUnqualifiedTerm ["Prelude"] "NoSuchConstructor")
shownOperator :: String
shownOperator = showAnyTerm (1 :*: 2)
roundTripOperator :: Operator
roundTripOperator = readAnyUnqualifiedTerm ["UnsafePrimitives"]
                     (showAnyTerm (1 :*: 2))
parenthesizedOperator :: Operator
parenthesizedOperator = readAnyUnqualifiedTerm ["UnsafePrimitives"] "(:*:) 1 2"
partialList :: Bool
partialList = case readsAnyUnqualifiedTerm ["Prelude"] "1:_a" of
                [(v,"")] -> not (isGround (v::[Int]))
                _ -> False
moduleFilter :: Bool
moduleFilter = null (readsAnyUnqualifiedTerm ["Prelude"] "Leaf 1")
'''


class TestUnsafePrimitives(cytest.TestCase):
  def check_primitives(self):
    M = curry.compile(PROGRAM)
    self.assertEqual(curry.eval(M.variables).one(), (True, True, False, False, True))
    self.assertEqual(curry.eval(M.bound).one(), (False, False, True))
    for name in ('branches', 'branchesReverse'):
      self.assertEqual(sorted(curry.eval(M[name])), [[(0, False)], [(1, True)]])
    self.assertEqual(sorted(curry.eval(M.generatedBranches)),
        [(0, False), (1, False), (2, True)])
    self.assertEqual(sorted(curry.eval(M.groundBranches)), [(0, True), (1, False)])
    self.assertEqual(sorted(curry.eval(M.identityBranches)), [(0, False), (1, True)])
    self.assertEqual(curry.eval(M.alias).one(), True)
    for name in ('shownBranches', 'expressionBranches'):
      self.assertEqual(sorted(curry.eval(M[name])), [(0, '[1]'), (1, '[_a]')])
    self.assertEqual(sorted((i, curry.show(v)) for i, v in curry.eval(M.compareBranches)),
        [(0, 'EQ'), (1, 'LT')])
    U = curry.import_('System.IO.Unsafe')
    for lhs, rhs, expected in ((float('nan'), 1.0, 'GT'),
                                (float('nan'), float('nan'), 'EQ'),
                                (-0.0, 0.0, 'EQ')):
      self.assertEqual(curry.show(curry.eval(U.compareAnyTerm(lhs, rhs)).one()), expected)
    self.assertEqual(curry.eval(M.counter).one(), 3)
    self.assertEqual(list(curry.eval(M.failedAction)), [])
    with self.assertRaisesRegex(EvaluationError, 'unsafe action raised'):
      curry.eval(M.raisingAction).one()
    self.assertEqual(curry.eval(M.suspended).one(), 7)
    self.assertEqual(curry.eval(M.nestedSuspension).one(), [7])
    self.assertEqual(list(curry.eval(M.falseConstraint)), [])
    self.assertEqual([curry.show(x) for x in curry.eval(M.orders).one()],
        ['LT', 'GT', 'EQ', 'LT', 'LT', 'LT', 'GT', 'EQ', 'LT'])
    self.assertTrue(curry.eval(M.varOrder).one())
    self.assertEqual(curry.show(curry.eval(M.functionOrder).one()), 'EQ')
    self.assertEqual(curry.show(curry.eval(M.functionArguments).one()), 'LT')
    self.assertEqual(curry.eval(M.shown).one(), 'Fork (Leaf 3) (Leaf 4)')
    self.assertEqual(curry.eval(M.shownFree).one(), '(_a, _a, _b)')
    self.assertEqual(curry.eval(M.shownAliases).one(), '(_a, _a)')
    expression = curry.eval(M.shownExpression).one()
    self.assertIn('Leaf', expression)
    self.assertIn('1 2', expression)
    self.assertNotEqual(expression, 'Leaf 3')
    self.assertEqual(curry.show(curry.eval(M.roundTrip).one()),
        'Fork (Leaf (-12)) (Leaf 1208925819614629174706176)')
    self.assertEqual(curry.eval(M.roundTripList).one(), [1, 2, 3])
    self.assertEqual(curry.eval(M.roundTripString).one(), 'a\n"\\')
    self.assertEqual(curry.eval(M.unicodeRoundTrip).one(), '\u00e41\x002')
    for text in ("'a '", "'a\t'", "'ab'", "'a", "''", "'\\n '"):
      self.assertEqual(list(curry.eval(M.readChar(text)).one()), [], repr(text))
    for text, expected in (("'a' tail", [('a', ' tail')]),
                           ("' '", [(' ', '')]), ("'\\n'", [('\n', '')])):
      self.assertEqual(curry.eval(M.readChar(text)).one(), expected)
    for suffix in ('\x00junk', '\x00', ' \x00junk'):
      self.assertEqual(curry.eval(M.readInt('1' + suffix)).one(), [(1, suffix)])
      with self.assertRaisesRegex(EvaluationError, 'unmatched string after term'):
        curry.eval(M.readWholeInt('1' + suffix)).one()
    self.assertTrue(math.isnan(curry.eval(M.readFloat('NaN')).one()))
    for text, expected in (('Infinity', float('inf')),
                           ('-Infinity', -float('inf')), ('(-1.25e-5)', -1.25e-5)):
      self.assertEqual(curry.eval(M.readFloat(text)).one(), expected)
    self.assertEqual(curry.eval(M.shownOperator).one(), ':*: 1 2')
    for name in ('roundTripOperator', 'parenthesizedOperator'):
      self.assertEqual(curry.show(curry.eval(M[name]).one()), '1 :*: 2')
    for name in ('roundTripVariables', 'partialList', 'badParse', 'moduleFilter'):
      self.assertTrue(curry.eval(M[name]).one())

  @cytest.with_flags(interpret='off', jit='off')
  def test_compiled(self):
    self.check_primitives()

  @cytest.with_flags(interpret='all', jit='off')
  def test_interpreted(self):
    self.check_primitives()

  @cytest.hardreset
  def test_jit_io(self):
    curry.reset(interpret='new', jit='eager', jit_backend='cxx', inline_budget=0)
    with self.assertLogs('curry.backends.cxx.tiered', level='INFO') as logs:
      M = curry.compile(PROGRAM)
    self.assertTrue(any('jit eager: module' in line for line in logs.output))
    self.assertFalse(curryrt.icurry_is_interpreted(M.counter.info))
    self.assertEqual(curry.eval(M.counter).one(), 3)
    self.assertEqual(list(curry.eval(M.failedAction)), [])
    with self.assertRaisesRegex(EvaluationError, 'unsafe action raised'):
      curry.eval(M.raisingAction).one()

  def test_unbound_constraint(self):
    M = curry.compile(PROGRAM)
    code = '''import curry, sys
curry.reset(interpret=sys.argv[2], jit='off')
M = curry.import_(sys.argv[1])
try:
  list(curry.eval(M[sys.argv[3]]))
except curry.SuspensionError:
  print('suspended', flush=True)
else:
  raise AssertionError('expected suspension')
'''
    for mode in ('off', 'all'):
      for name in ('unboundSuspension', 'setSuspension'):
        result = subprocess.run([sys.executable, '-c', code, M.__file__, mode, name],
            text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'suspended')

  def test_divergent_constraint(self):
    # Compile before timing: the timeout measures evaluation alone.
    M = curry.compile(PROGRAM)
    for mode in ('off', 'all'):
      code = '''import curry, sys
curry.reset(interpret=sys.argv[2], jit='off')
M = curry.import_(sys.argv[1])
print('ready', flush=True)
print(curry.eval(M.divergent).one(), flush=True)
'''
      process = subprocess.Popen([sys.executable, '-c', code, M.__file__, mode],
          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      try:
        with self.assertRaises(subprocess.TimeoutExpired) as timeout:
          process.communicate(timeout=3)
        self.assertIn(b'ready', timeout.exception.stdout)
      finally:
        process.kill()
        process.communicate()
