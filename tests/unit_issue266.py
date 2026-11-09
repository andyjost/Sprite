"""Closed Data.Global definitions are independent of caller scheduling (#266)."""
import cytest # from ./lib; must be first
import os
from unittest import mock


SOURCE = '''
import Control.SetFunctions
initialize :: Int -> IO Int
initialize x = if x == 1 then publish x else publish x
publish :: Int -> IO Int
publish x = readGlobalT (globalT "Closed.competing" (slow 2000 x))
slow :: Int -> Int -> Int
slow n x = if n == 0 then x else slow (n-1) x
competing :: IO Int
competing = initialize x where x = 1 ? 2
binding :: IO Int
binding = x =:= 42 &> readGlobalT (globalT "Closed.binding" (x+1)) where x free
choice :: GlobalT Int
choice = if x == 2 then globalT "Closed.choice" (x+1) else failed
  where x = 1 ? 2
freeValue :: GlobalT [Int]
freeValue = globalT "Closed.free" [x] where x free
nested :: GlobalT Int
nested = x =:= 42 &> globalT "Closed.nested"
  (head (sortValues (set1 id x))) where x free
captured :: GlobalT (Bool -> [Int])
captured = globalT "Closed.captured" (const [x]) where x free
constant :: GlobalT Int
constant = globalT "Closed.constant" 42
argument :: Int -> GlobalT Int
argument n = globalT "Closed.argument" (n+1)
normal :: [Int] -> GlobalT [Int]
normal xs = globalT "Closed.normal" xs
function :: (Int -> Int) -> GlobalT (Int -> Int)
function f = globalT "Closed.function" f
plus :: Int -> Int -> Int
plus n x = n+x
other :: Int -> Int
other x = x+1
shared, independent :: GlobalT (Bool -> (Int,Int))
shared = globalT "Closed.sharing" (const (x,x)) where x = 0 ? 1
independent = globalT "Closed.sharing" (const (0 ? 1, 0 ? 1))
unbound :: Int
unbound = x where x free
internal :: GlobalT Int
internal = globalT "Closed.internal" unbound
coin :: Int
coin external
hidden :: GlobalT Bool
hidden = globalT "Closed.hidden" (isEmpty (set0 coin))
'''


def check(case, mode):
  import curry
  from unit_cpm_primitives import NAMED_GLOBALS
  # Keep unbound as a call inside the capsule: inlining it into internal
  # would move the free-variable declaration into the caller.
  curry.reset(interpret=mode, jit='off', checker=True,
              rotation=os.environ['SPRITE_ROTATION'],
              **({'inline_budget': 0} if case == 'internal' else {}))
  source = NAMED_GLOBALS.replace('data GlobalT',
      'import Control.SetFunctions\ndata GlobalT')
  # The raw bridge deliberately returns the same retained graph, so this
  # checks ownership after an independent evaluation, not allocation age.
  from curry.backends.cxx import curryrtbindings as native
  coin = cytest.raw.expr(cytest.raw.choice(0, 1))
  native._register_primitive('Data.Global.coin', 0, lambda interp: coin)
  module = curry.compile(source + SOURCE.replace('import Control.SetFunctions\n', ''))

  def rejects(goal, key):
    try:
      list(curry.eval(goal))
    except curry.EvaluationError as error:
      assert str(error) == ('Data.Global: the initial value of global '
                            + key + ' depends on its caller'), str(error)
    else:
      raise AssertionError('caller-dependent initializer succeeded')

  if case in ('competing', 'binding', 'choice', 'freeValue', 'nested', 'captured'):
    key = 'free' if case == 'freeValue' else case
    rejects(getattr(module, case), 'Closed.' + key)
  elif case == 'definitions':
    for values in ([21, 42], [21, 42]):
      handle = curry.eval(module.normal(values)).one()
      assert curry.eval(module.readGlobalT(handle)).one() == values
    rejects(module.normal([21, 43]), 'Closed.normal')
    assert curry.eval(module.readGlobalT(handle)).one() == [21, 42]
  elif case == 'functions':
    for _ in range(2):
      curry.eval(module.function(module.plus(1))).one()
    rejects(module.function(module.plus(2)), 'Closed.function')
    # Distinct heads are distinct definitions even with equal behavior.
    rejects(module.function(module.other), 'Closed.function')
  elif case in ('sharing', 'sharing_reverse'):
    first, second = ((module.shared, module.independent) if case == 'sharing'
                     else (module.independent, module.shared))
    curry.eval(first).one()
    rejects(second, 'Closed.sharing')
  elif case == 'internal':
    try:
      list(curry.eval(module.internal))
    except curry.SuspensionError as error:
      assert 'depends on its caller' not in str(error), str(error)
    else:
      raise AssertionError('internal free variable did not suspend')
  elif case == 'hidden':
    assert sorted(int(curry.show(x)) for x in cytest.raw.values(coin)) == [0, 1]
    assert curry.eval(module.readGlobalT(module.hidden)).one() is False
  elif case == 'deterministic':
    assert curry.eval(module.readGlobalT(module.constant)).one() == 42
    for _ in range(2):
      assert curry.eval(module.readGlobalT(module.argument(41))).one() == 42
    # A write changes contents, not the definition checked at reentry.
    curry.eval(module.writeGlobalT(module.constant, 23)).one()
    assert curry.eval(module.readGlobalT(module.constant)).one() == 23
  else:
    raise AssertionError(case)


class TestIssue266(cytest.TestCase):
  def child(self, case, rotation='steps:1000'):
    for mode in ('all', 'off'):
      with self.subTest(case=case, mode=mode, rotation=rotation):
        with mock.patch.dict(os.environ, {'SPRITE_ROTATION': rotation}):
          proc = cytest.run_in_subprocess(
              'from unit_issue266 import check\ncheck(%r, %r)' % (case, mode),
              timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

  def test_competing_short_rotation(self):
    self.child('competing', 'steps:1000')

  def test_competing_long_rotation(self):
    self.child('competing', 'steps:1000000')

  def test_callers_binding(self):
    self.child('binding')

  def test_callers_choice(self):
    self.child('choice')

  def test_free_variable(self):
    self.child('freeValue')

  def test_nested_capsule(self):
    self.child('nested')

  def test_function_capture(self):
    self.child('captured')

  def test_equal_and_different_definitions(self):
    self.child('definitions')

  def test_function_definitions(self):
    self.child('functions')

  def test_top_level_and_deterministic_argument(self):
    self.child('deterministic')

  def test_shared_top_level_choice_after_enumeration(self):
    self.child('hidden')

  def test_function_capture_sharing(self):
    self.child('sharing')
    self.child('sharing_reverse')

  def test_internal_free_variable_suspends(self):
    self.child('internal')
