'''
Tests for tiered execution on the C++ backend.

Under the interpreter flag ``interpret`` set to 'tiered', the default, a
module without a compiled object is interpreted at once, a child process
compiles it in the background, and the runtime swaps the functions of the
module to the compiled code when the object is ready
(curry.backends.cxx.tiered, src/cyrt/tiered.hpp).  The tests write a fresh
module to a temporary directory, so every import starts without an object.
'''
import cytest # from ./lib; must be first
from cytest.logging import capture_log
from curry import common, config, inspect
from curry.backends.cxx import compiler, cyrtbindings as cyrt, tiered
from curry.objects.handle import getHandle
from curry.utility.binding import binding
import curry, gc, itertools, logging, os, shutil, subprocess, tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
BENCHMARKS = os.path.join(HERE, 'data', 'curry', 'benchmarks')

# The cap on the address space of a child, in bytes, and the time it may
# take.
ADDRESS_SPACE = 2 << 30
TIMEOUT = 120

# The time a background compile may take.
COMPILE_SECONDS = 120

ONLY_CXX = unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )

MODULE = '''
module %(name)s where

data Shape = Circle Int | Rect Int Int | Dot
  deriving (Eq, Show)

area :: Shape -> Int
area (Circle r) = 3 * r * r
area (Rect w h) = w * h
area Dot        = 0

mk :: Int -> Shape
mk n = if n == 0 then Dot else Rect n (n + 1)

same :: Shape -> Shape -> Bool
same a b = a == b

shapes :: Int -> [Shape]
shapes n = map mk [0 .. n]

total :: Int -> Int
total n = foldr (+) 0 (map area (shapes n))

-- A loop of many steps in place, for a swap during an evaluation.
loop :: Int -> Int
loop n = if n == 0 then 0 else loop (n - 1)

-- Three values, one per alternative.
choices :: Int -> Int
choices n = area (mk n) ? total n ? loop n
'''

# A call the inliner would replace by its body: with the inliner off, viaCall
# costs one rewrite step more than direct.
BUDGET_MODULE = '''
module %(name)s where

s :: Int -> Int -> Int
s x y = y + x

direct :: Int
direct = 1 + 2

viaCall :: Int
viaCall = s 1 2
'''

def steps():
  '''The rewrite steps taken by the evaluations of the interpreter.'''
  return curry.getInterpreter()._evaluation_totals.steps


@ONLY_CXX
class TieredTestCase(cytest.TestCase):
  '''A temporary source directory with one fresh module per import.'''
  counter = itertools.count()

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-tiered-test-')
    self.switch('tiered')

  def switch(self, mode, **flags):
    '''
    Reloads the interpreter with the flag ``interpret`` set to ``mode``, and
    ``flags``, and puts the source directory on its path: the imports of a
    module are found through the path of the interpreter.  The caller drops
    its module objects first (see unit_cxx_interp.switch).
    '''
    gc.collect()
    curry.reload(dict(flags, backend='cxx', interpret=mode))
    # The old interpreter is garbage now; its modules go before a module of
    # the same name is made again.
    gc.collect()
    curry.path.insert(0, self.tmpdir)

  def tearDown(self):
    # No compile may run while the directory goes.
    tiered.cancel()
    tiered.wait(10)
    gc.collect()
    shutil.rmtree(self.tmpdir, ignore_errors=True)
    super().tearDown()

  def write_module(self, text=MODULE):
    '''Writes a module with a new name.  Returns the name.'''
    name = 'CxxTiered%d' % next(self.counter)
    with open(os.path.join(self.tmpdir, name + '.curry'), 'w') as stream:
      stream.write(text % {'name': name})
    return name

  def import_module(self, name):
    return curry.import_(name)

  def fresh_module(self, text=MODULE):
    return self.import_module(self.write_module(text))

  def sofile(self, name):
    return os.path.join(
        self.tmpdir, '.curry', config.intermediate_subdir(), name + '.so'
      )

  def edit_module(self, name, text):
    '''Writes a new text for the module ``name``.'''
    with open(os.path.join(self.tmpdir, name + '.curry'), 'w') as stream:
      stream.write(text % {'name': name})

  def value(self, *args):
    '''The first value of a goal, as a Curry node.'''
    return next(curry.eval(*args, converter=None))

  def py(self, *args):
    '''The first value of a goal, as a Python object.'''
    return next(curry.eval(*args, converter='topython'))

  def stamp(self, name):
    '''The ABI stamp of the object: written after a compile ends.'''
    return self.sofile(name) + '.abi'

  def wait(self):
    self.assertTrue(
        tiered.wait(COMPILE_SECONDS, curry.getInterpreter())
      , 'the background compile did not end in %s s' % COMPILE_SECONDS
      )


class TestSwap(TieredTestCase):
  '''
  A fresh module is interpreted at once.  Its functions run compiled after
  the background compile, in the same process, with the same values and
  steps.
  '''
  @cytest.hardreset
  def test_swap(self):
    self.assertEqual(curry.flags['interpret'], 'tiered')
    M = self.fresh_module()
    name = M.__name__
    h = getHandle(M)
    # Interpreted at once, with the compile queued.
    self.assertIsNone(h.icurry.metadata.get('cxx.shlib'))
    for f in M.area, M.mk, M.same, M.total, M.loop:
      self.assertTrue(cyrt.icurry_is_interpreted(f.info), f.name)
    before = tiered.status()
    swapped_stat = curry.stats()['swapped']
    # Values of the interpreted tier.
    v1 = self.value(M.mk, 3)
    self.assertEqual(str(v1), 'Rect 3 4')
    n0 = steps()
    self.assertEqual(self.py(M.total, 4), 2 + 6 + 12 + 20)
    steps_interpreted = steps() - n0
    # The swap.
    self.wait()
    after = tiered.status()
    self.assertEqual(after['swapped_modules'], before['swapped_modules'] + 1)
    self.assertEqual(after['failed_modules'], before['failed_modules'])
    nfunctions = len(h.icurry.functions)
    self.assertGreaterEqual(
        after['swapped_functions'] - before['swapped_functions'], 5
      )
    self.assertLessEqual(
        after['swapped_functions'] - before['swapped_functions'], nfunctions
      )
    for f in M.area, M.mk, M.same, M.total, M.loop:
      self.assertFalse(cyrt.icurry_is_interpreted(f.info), f.name)
    # The stats line counts the swapped functions.
    self.assertEqual(
        curry.stats()['swapped'] - swapped_stat
      , after['swapped_functions'] - before['swapped_functions']
      )
    # The object is on record and on disk.
    self.assertTrue(os.path.isfile(self.sofile(name)))
    self.assertIsNotNone(h.icurry.metadata.get('cxx.shlib'))
    self.assertEqual(
        os.path.realpath(h.sofilename), os.path.realpath(self.sofile(name))
      )
    # Values of the compiled tier: the same, in the same steps.
    v2 = self.value(M.mk, 3)
    self.assertEqual(str(v2), 'Rect 3 4')
    n0 = steps()
    self.assertEqual(self.py(M.total, 4), 40)
    self.assertEqual(steps() - n0, steps_interpreted)
    # One table per symbol: the compiled code binds to the tables the
    # interpreter made (the shim), so a value of each tier has the same
    # constructor, isa holds, and the two compare equal.
    self.assertEqual(v2.info.address, v1.info.address)
    self.assertEqual(v2.info.address, M.Rect.info.address)
    self.assertTrue(inspect.isa(v2, M.Rect))
    self.assertTrue(inspect.isa(v2, curry.type(name + '.Shape')))
    self.assertIs(self.py(M.same, v1, v2), True)
    self.assertIs(self.py(M.same, v2, self.value(M.mk, 3)), True)
    self.assertIs(self.py(M.same, v1, self.value(M.mk, 4)), False)
    # The bytecode stays with the table.
    self.assertIsNone(cyrt.icurry_bytecode(M.area.info))

  @cytest.hardreset
  def test_swap_within_an_evaluation(self):
    # The evaluation of choices yields three values from three
    # alternatives.  After the first value, the swap is applied while the
    # evaluation waits; the remaining alternatives run compiled, and the
    # evaluation ends with the same values.
    M = self.fresh_module()
    expected = sorted(str(v) for v in curry.eval(M.choices, 4))
    self.assertEqual(expected, ['0', '20', '40'])
    N = self.fresh_module()
    values = curry.eval(N.choices, 4)
    first = next(values)
    self.assertTrue(cyrt.icurry_is_interpreted(N.choices.info))
    self.wait()
    self.assertFalse(cyrt.icurry_is_interpreted(N.choices.info))
    self.assertFalse(cyrt.icurry_is_interpreted(N.loop.info))
    rest = list(values)
    self.assertEqual(sorted(str(v) for v in [first] + rest), expected)

  @cytest.hardreset
  def test_swap_at_a_safepoint(self):
    # A long evaluation: the scheduler applies the compile at its periodic
    # safepoint, so the loop finishes compiled.  The compile must end
    # before the loop does; when it does not (a loaded machine), the poll
    # at the end of the evaluation applies it instead, the test proves
    # nothing and says so.
    M = self.fresh_module()
    before = tiered.status()['applied_in_evaluation']
    self.assertEqual(self.py(M.loop, 16000000), 0)
    after = tiered.status()
    if after['applied_in_evaluation'] == before:
      self.wait()
      self.skipTest('the compile took longer than the evaluation')
    self.assertEqual(after['applied_in_evaluation'], before + 1)
    self.assertFalse(cyrt.icurry_is_interpreted(M.loop.info))
    self.assertEqual(self.py(M.loop, 10), 0)

  @cytest.hardreset
  def test_module_imports_fresh_module(self):
    # A fresh module imports another: both are interpreted, the import
    # compiles first, and both are swapped.  Compiled code of the second
    # makes nodes with the tables of the first.
    first = self.write_module()
    second = self.write_module(
        'module %%(name)s where\nimport %(first)s\n'
        'biggest :: Int -> Int\n'
        'biggest n = foldr max 0 (map area (shapes n))\n'
        'build :: Int -> Shape\nbuild n = mk n\n' % {'first': first}
      )
    N = self.import_module(second)
    M = curry.import_(first)
    self.assertTrue(cyrt.icurry_is_interpreted(N.biggest.info))
    self.assertTrue(cyrt.icurry_is_interpreted(M.area.info))
    self.assertEqual(self.py(N.biggest, 4), 20)
    self.wait()
    self.assertFalse(cyrt.icurry_is_interpreted(N.biggest.info))
    self.assertFalse(cyrt.icurry_is_interpreted(M.area.info))
    self.assertEqual(self.py(N.biggest, 4), 20)
    v = self.value(N.build, 2)
    self.assertEqual(str(v), 'Rect 2 3')
    self.assertTrue(inspect.isa(v, M.Rect))
    self.assertIs(self.py(M.same, v, self.value(M.mk, 2)), True)

  @cytest.hardreset
  def test_tables_survive_a_reload(self):
    # After a reload, a module of the same name takes its tables back, so
    # the shim stays valid and the second incarnation is swapped as well.
    name = self.write_module()
    M = self.import_module(name)
    address = M.area.info.address
    self.wait()
    self.assertFalse(cyrt.icurry_is_interpreted(M.area.info))
    shims = tiered.status()['shims']
    M = None
    self.switch('tiered')
    # The object exists now, so a plain import loads it compiled.  Remove
    # it: the module is interpreted again, from the JSON beside the
    # generated file, and the compile starts from that file.  The shim of
    # the first incarnation serves; no warning is logged.
    os.unlink(self.sofile(name))
    os.unlink(self.stamp(name))
    with capture_log('curry.backends.cxx.tiered') as log:
      M = self.import_module(name)
      self.assertEqual(M.area.info.address, address)
      self.assertTrue(cyrt.icurry_is_interpreted(M.area.info))
      self.assertEqual(self.py(M.area, self.value(M.mk, 3)), 12)
      self.wait()
    self.assertEqual(log.data[logging.WARNING], [])
    self.assertEqual(tiered.status()['shims'], shims)
    self.assertFalse(cyrt.icurry_is_interpreted(M.area.info))
    self.assertEqual(self.py(M.area, self.value(M.mk, 3)), 12)

  @cytest.hardreset
  def test_edited_module_swaps_to_its_new_code(self):
    # After an edit that keeps the shape of the module, a reload imports
    # the new source: the module is interpreted, and the swap installs the
    # new object, not the object of the first incarnation, which stays
    # mapped under the same path.
    text = 'module %%(name)s where\nbump :: Int -> Int\nbump x = x + %d\n'
    name = self.write_module(text % 1)
    M = self.import_module(name)
    address = M.bump.info.address
    self.assertEqual(self.py(M.bump, 1), 2)
    self.wait()
    self.assertFalse(cyrt.icurry_is_interpreted(M.bump.info))
    self.assertEqual(self.py(M.bump, 1), 2)
    M = None
    self.edit_module(name, text % 2)
    self.switch('tiered')
    M = self.import_module(name)
    self.assertEqual(M.bump.info.address, address)
    self.assertTrue(cyrt.icurry_is_interpreted(M.bump.info))
    self.assertEqual(self.py(M.bump, 1), 3)
    before = tiered.status()
    self.wait()
    after = tiered.status()
    self.assertEqual(after['swapped_modules'], before['swapped_modules'] + 1)
    self.assertFalse(cyrt.icurry_is_interpreted(M.bump.info))
    self.assertEqual(self.py(M.bump, 1), 3)
    self.assertEqual(M.bump.info.address, address)

  @cytest.hardreset
  def test_edited_import_keeps_a_dependent_interpreted(self):
    # A dependent with a current object is not loaded from it while an
    # import runs without an object: its object names the object of the
    # import as a needed library, and the dynamic linker would map the
    # stale file.  The dependent is interpreted, its compile waits behind
    # the compile of the import, and both swap to the new code.
    base_text = 'module %%(name)s where\ng :: Int -> Int\ng x = x + %d\n'
    base = self.write_module(base_text % 1)
    dep = self.write_module(
        'module %%(name)s where\nimport %s\nh :: Int -> Int\nh x = g x\n'
        % base
      )
    D = self.import_module(dep)
    B = curry.import_(base)
    self.assertEqual(self.py(D.h, 1), 2)
    self.wait()
    self.assertFalse(cyrt.icurry_is_interpreted(D.h.info))
    self.assertFalse(cyrt.icurry_is_interpreted(B.g.info))
    self.assertTrue(os.path.isfile(self.stamp(dep)))
    D = B = None
    self.edit_module(base, base_text % 2)
    self.switch('tiered')
    D = self.import_module(dep)
    B = curry.import_(base)
    self.assertTrue(cyrt.icurry_is_interpreted(B.g.info))
    self.assertTrue(cyrt.icurry_is_interpreted(D.h.info))
    self.assertIsNone(getHandle(D).icurry.metadata.get('cxx.shlib'))
    self.assertEqual(self.py(B.g, 1), 3)
    self.assertEqual(self.py(D.h, 1), 3)
    self.wait()
    self.assertFalse(cyrt.icurry_is_interpreted(B.g.info))
    self.assertFalse(cyrt.icurry_is_interpreted(D.h.info))
    self.assertEqual(self.py(B.g, 1), 3)
    self.assertEqual(self.py(D.h, 1), 3)

  @cytest.hardreset
  def test_string_module_made_again_after_a_reset(self):
    # A module compiled from a string is interpreted and makes no library,
    # so a module of the same name after a reset is not refused (compare
    # unit_compile.testReusedModuleNameIsAnError under interpret:off): it
    # takes the tables of the first back and runs its own code.
    first = curry.compile('f :: Int\nf = 1', modulename='TieredDup')
    address = first.f.info.address
    self.assertEqual(self.py(first.f), 1)
    first = None
    curry.reset()
    second = curry.compile('f :: Int\nf = 2', modulename='TieredDup')
    self.assertEqual(second.f.info.address, address)
    self.assertEqual(self.py(second.f), 2)


class TestPolicy(TieredTestCase):
  '''What is compiled in the background, and what happens when it fails.'''

  @cytest.hardreset
  def test_failure_stays_interpreted(self):
    # A flag the compiler refuses reaches the child through CXXFLAGS.
    before = tiered.status()
    failed_stat = curry.stats()['failed_compiles']
    with binding(os.environ, 'CXXFLAGS', '-fno-such-flag-of-sprite'):
      with capture_log('curry.backends.cxx.tiered') as log:
        M = self.fresh_module()
        self.assertEqual(self.py(M.area, self.value(M.mk, 2)), 6)
        self.wait()
        self.assertEqual(self.py(M.area, self.value(M.mk, 2)), 6)
    after = tiered.status()
    self.assertEqual(after['failed_modules'], before['failed_modules'] + 1)
    self.assertEqual(curry.stats()['failed_compiles'], failed_stat + 1)
    self.assertEqual(after['swapped_modules'], before['swapped_modules'])
    self.assertTrue(cyrt.icurry_is_interpreted(M.area.info))
    self.assertFalse(os.path.exists(self.stamp(M.__name__)))
    warnings = log.data[logging.WARNING]
    self.assertEqual(len(warnings), 1)
    self.assertIn('stays interpreted', warnings[0])
    self.assertIn('no-such-flag-of-sprite', warnings[0])

  @cytest.hardreset
  def test_strings_and_expressions_stay_interpreted(self):
    before = tiered.status()
    S = curry.compile(
        'double :: Int -> Int\ndouble x = x + x\n', mode='module'
      )
    self.assertTrue(cyrt.icurry_is_interpreted(S.double.info))
    e = curry.compile('double 21', mode='expr', imports=[S])
    self.assertEqual(next(curry.eval(e, converter='topython')), 42)
    self.assertTrue(tiered.wait(10))
    after = tiered.status()
    self.assertEqual(after['queued'], 0)
    self.assertEqual(after['swapped_modules'], before['swapped_modules'])
    self.assertEqual(after['failed_modules'], before['failed_modules'])
    self.assertTrue(cyrt.icurry_is_interpreted(S.double.info))

  @cytest.hardreset
  def test_reset_cancels(self):
    # A reset unloads the module, so its compile is dropped: a running
    # compile is killed and leaves no stamped object, and a compile that
    # ended before the reset is never applied.
    M = self.fresh_module()
    name = M.__name__
    before = tiered.status()
    M = None
    curry.reset()
    self.assertTrue(tiered.wait(10))
    after = tiered.status()
    self.assertEqual(after['queued'], 0)
    self.assertEqual(after['swapped_modules'], before['swapped_modules'])
    self.assertEqual(after['failed_modules'], before['failed_modules'])
    if before['queued'] + before['running']:
      self.assertFalse(os.path.exists(self.stamp(name)))

  @cytest.hardreset
  def test_compiled_module_loads_compiled(self):
    # A module with a current object is not interpreted (as under 'new').
    name = self.write_module()
    M = self.import_module(name)
    self.wait()
    M = None
    self.switch('tiered')
    M = self.import_module(name)
    self.assertIsNotNone(getHandle(M).icurry.metadata.get('cxx.shlib'))
    self.assertFalse(cyrt.icurry_is_interpreted(M.area.info))
    self.assertEqual(self.py(M.total, 2), 8)
    prelude = curry.import_('Prelude')
    self.assertIsNotNone(getHandle(prelude).icurry.metadata.get('cxx.shlib'))
    self.assertFalse(cyrt.icurry_is_interpreted(prelude.map.info))

  @cytest.hardreset
  def test_nondet_io_argument_error(self):
    # An interpreted module that applies readFile of the compiled Prelude
    # to a nondeterministic name raises the nondeterminism error, as
    # compiled code and a program interpreted whole (interpret:all) do.
    # It raised ValueError('bad Curry string') while the primitive behind
    # prim_readFile carried the display name "readFile" and shadowed the
    # Curry function in the symbol table of the compiled Prelude (the dated
    # TODO entry on the primitives' names).  The compile is cancelled, so
    # the module stays interpreted.
    M = self.fresh_module(
        'module %(name)s where\nmain :: IO String\n'
        'main = readFile ("a.txt" ? "b.txt")\n'
      )
    tiered.cancel()
    self.assertTrue(cyrt.icurry_is_interpreted(M.main.info))
    with self.assertRaises(curry.EvaluationError) as cm:
      list(curry.eval(M.main))
    self.assertIn('non-determinism', str(cm.exception))

  @cytest.hardreset
  def test_budget_reaches_the_child(self):
    '''
    The background compile runs under the inline budget of the interpreter
    (the flag inline_budget), so the code it swaps in is the code the
    interpreter ran: with the inliner off, a call costs the same steps
    before and after the swap.  It did not, and the swap replaced the code
    of a module interpreted with the inliner off by code compiled under
    the default budget.
    '''
    self.switch('tiered', inline_budget=0)
    self.assertEqual(curry.flags['inline_budget'], 0)
    env = dict(
        item.split('=', 1)
          for item in tiered._environment(curry.getInterpreter())
      )
    self.assertIn(
        'inline_budget:0', env['SPRITE_INTERPRETER_FLAGS'].split(',')
      )
    M = self.fresh_module(BUDGET_MODULE)
    self.assertTrue(cyrt.icurry_is_interpreted(M.viaCall.info))
    n0 = steps()
    self.assertEqual(self.py(M.direct), 3)
    direct = steps() - n0
    n0 = steps()
    self.assertEqual(self.py(M.viaCall), 3)
    interpreted = steps() - n0
    self.assertEqual(interpreted, direct + 1)
    self.wait()
    self.assertFalse(cyrt.icurry_is_interpreted(M.viaCall.info))
    n0 = steps()
    self.assertEqual(self.py(M.viaCall), 3)
    self.assertEqual(steps() - n0, interpreted)
    # Under the default budget the call is inlined on both tiers.
    self.switch('tiered')
    env = dict(
        item.split('=', 1)
          for item in tiered._environment(curry.getInterpreter())
      )
    self.assertIn(
        'inline_budget:4', env['SPRITE_INTERPRETER_FLAGS'].split(',')
      )
    N = self.fresh_module(BUDGET_MODULE)
    n0 = steps()
    self.assertEqual(self.py(N.viaCall), 3)
    self.assertEqual(steps() - n0, direct)
    self.wait()
    self.assertFalse(cyrt.icurry_is_interpreted(N.viaCall.info))
    n0 = steps()
    self.assertEqual(self.py(N.viaCall), 3)
    self.assertEqual(steps() - n0, direct)

  def test_sprite_make_compiles(self):
    # An explicit compile writes the object under the flag.
    name = self.write_module()
    env = dict(os.environ)
    env['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx,interpret:tiered'
    env['CURRYPATH'] = self.tmpdir
    cmd = [
        'prlimit', '--as=%d' % ADDRESS_SPACE, 'timeout', str(TIMEOUT)
      , config.installed_path('bin', 'sprite-make'), '--so', '-z', name
      ]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertTrue(os.path.isfile(self.sofile(name)))


@ONLY_CXX
class TestPrograms(cytest.TestCase):
  '''
  A fresh copy of a benchmark program under sprite-exec: the values and the
  steps of the compiled code, and no object left behind by a program that
  ends before its compile.
  '''
  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-tiered-exec-')

  def tearDown(self):
    shutil.rmtree(self.tmpdir, ignore_errors=True)
    super().tearDown()

  def run_child(self, program, mode, currypath, **extra):
    # The child collects at every step only when asked: a program of a few
    # million steps does not end in time otherwise.
    env = dict(os.environ)
    env['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx,interpret:%s' % mode
    env['CURRYPATH'] = currypath
    env.pop('SPRITE_GC_STRESS', None)
    env.update(extra)
    cmd = [
        'prlimit', '--as=%d' % ADDRESS_SPACE, 'timeout', str(TIMEOUT)
      , config.installed_path('bin', 'sprite-exec'), '--stats', '-m', program
      ]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.last_stderr = proc.stderr
    stats = dict(
        item.split('=', 1)
          for item in proc.stderr.strip().splitlines()[-1].split()
      )
    return proc.stdout.strip(), int(stats['steps'])

  def test_fresh_program(self):
    expected = self.run_child('Fib', 'off', BENCHMARKS)
    shutil.copy(os.path.join(BENCHMARKS, 'Fib.curry'), self.tmpdir)
    self.assertEqual(self.run_child('Fib', 'tiered', self.tmpdir), expected)
    sofile = os.path.join(
        self.tmpdir, '.curry', config.intermediate_subdir(), 'Fib.so'
      )
    # The program ends before its compile; the compile is cancelled, so no
    # finished object (one with its ABI stamp) is left behind.
    self.assertFalse(os.path.exists(sofile + '.abi'))
    # The run was interpreted from the JSON.
    self.assertTrue(os.path.exists(sofile[:-3] + '.json.z'))

  def test_failed_compile_is_logged(self):
    # A compile that fails during the evaluation of a program is reported
    # on the standard error of sprite-exec, once, and counted in the stats
    # line; the program ends with the values of the interpreter.  Tak1
    # runs long enough for the child to fail first.
    expected = self.run_child('Tak1', 'off', BENCHMARKS)
    shutil.copy(os.path.join(BENCHMARKS, 'Tak1.curry'), self.tmpdir)
    actual = self.run_child(
        'Tak1', 'tiered', self.tmpdir, CXXFLAGS='-fno-such-flag-of-sprite'
      )
    self.assertEqual(actual, expected)
    stderr = self.last_stderr
    self.assertEqual(stderr.count('stays interpreted'), 1, stderr)
    self.assertIn('no-such-flag-of-sprite', stderr)
    stats = stderr.strip().splitlines()[-1]
    self.assertIn(' swapped=0 ', stats)
    self.assertIn(' failed_compiles=1', stats)


class TestNoCompiler(TieredTestCase):
  '''
  An installation without a C++ compiler (config.cxx_tool() is None): a
  fresh module stays interpreted, no object is written, and one notice names
  the first such module, once per process, with the setting of the flag
  that selects the interpreter without a compile.  interpret:new and
  interpret:all select the behaviour without the notice.
  '''
  def setUp(self):
    super().setUp()
    # The notice is once per process; each test starts afresh.
    tiered._state.warned.discard('nocxx')
    self.addCleanup(tiered._state.warned.discard, 'nocxx')

  def run_without_compiler(self):
    '''
    Imports two fresh modules with the compiler patched away and evaluates
    a goal of each.  Returns the modules and the warnings logged.
    '''
    with mock.patch.object(config, 'cxx_tool', return_value=None):
      with capture_log('curry.backends.cxx.tiered') as log:
        M = self.fresh_module()
        self.assertEqual(next(curry.eval(M.total, 3, converter='topython')), 20)
        N = self.fresh_module()
        self.assertEqual(next(curry.eval(N.total, 2, converter='topython')), 8)
    self.assertTrue(cyrt.icurry_is_interpreted(M.total.info))
    self.assertTrue(cyrt.icurry_is_interpreted(N.total.info))
    tiered.wait(10)
    self.assertFalse(os.path.exists(self.sofile(M.__name__)))
    self.assertFalse(os.path.exists(self.sofile(N.__name__)))
    return M, N, log.data[logging.WARNING]

  def test_notice_once(self):
    M, N, warnings = self.run_without_compiler()
    self.assertEqual(len(warnings), 1, warnings)
    notice, = warnings
    self.assertIn('no C++ compiler is installed at', notice)
    self.assertIn(config.installed_path('tools', 'cxx'), notice)
    self.assertIn('module %r and the modules after it run interpreted' % M.__name__, notice)
    self.assertNotIn(N.__name__, notice)
    # The setting named: new where the Prelude loaded from its object (a
    # fresh module has no generated file), else all.  The flag is added to
    # the variable, not set in place of it.
    setting = 'new' if tiered._prelude_compiled(curry.getInterpreter()) else 'all'
    self.assertIn(
        'add interpret:%s to SPRITE_INTERPRETER_FLAGS' % setting, notice
      )
    self.assertNotIn('SPRITE_INTERPRETER_FLAGS=', notice)
    self.assertEqual(notice.count('\n'), 0)
    # A third module in the same process adds no second notice.
    with mock.patch.object(config, 'cxx_tool', return_value=None):
      with capture_log('curry.backends.cxx.tiered') as log:
        self.fresh_module()
    self.assertEqual(log.data[logging.WARNING], [])

  def test_notice_setting(self):
    '''
    The setting the notice names.  interpret:new where the Prelude loaded
    from its object and the module has no current generated file: it keeps
    the compiled library.  interpret:all where the Prelude is interpreted
    (the library objects are stale, and new would compile them) or a
    current generated file lies beside the module (new would compile it).
    '''
    interp = curry.getInterpreter()
    with mock.patch.object(config, 'cxx_tool', return_value=None):
      with capture_log('curry.backends.cxx.tiered'):
        M = self.fresh_module()
    imodule = getHandle(M).icurry
    self.assertFalse(tiered._current_source(imodule))
    compiled = tiered._prelude_compiled(interp)
    self.assertEqual(
        tiered._interpreter_setting(interp, imodule)
      , 'new' if compiled else 'all'
      )
    with mock.patch.object(tiered, '_prelude_compiled', return_value=False):
      self.assertEqual(tiered._interpreter_setting(interp, imodule), 'all')
    cppfile = os.path.join(
        self.tmpdir, '.curry', config.intermediate_subdir(), M.__name__ + '.cpp'
      )
    with mock.patch.object(tiered, '_prelude_compiled', return_value=True):
      # A generated file of the current format is compiled under new.
      with open(cppfile, 'w') as stream:
        stream.write('// FORMAT: %d\n' % compiler.FORMAT_VERSION)
      self.assertTrue(tiered._current_source(imodule))
      self.assertEqual(tiered._interpreter_setting(interp, imodule), 'all')
      # A generated file of another format is stale: interpreted under new.
      with open(cppfile, 'w') as stream:
        stream.write('// FORMAT: %d\n' % (compiler.FORMAT_VERSION + 1))
      self.assertFalse(tiered._current_source(imodule))
      self.assertEqual(tiered._interpreter_setting(interp, imodule), 'new')

  def test_flag_silences_the_notice(self):
    for mode in 'new', 'all':
      self.switch(mode)
      tiered._state.warned.discard('nocxx')
      M, N, warnings = self.run_without_compiler()
      self.assertEqual(warnings, [], mode)


# The sequence of the API study's probe (P55) for a child process: the
# import of a module whose object is stale queues its compile, and
# curry.load of that object returns the module of the import.
CHILD_LOAD = r'''
import curry
curry.path.insert(0, %(tmpdir)r)
M = curry.import_(%(name)r)
M2 = curry.load(%(sofile)r)
print(M2 is M)
print(next(curry.eval(M.total, 4, converter='topython')))
print('exiting normally')
'''

# The save-then-load sequence of the Quickstart ("Saving Compiled Curry") for
# a child process: the import, curry.save, sprite-make --so in a shell, then
# curry.load of the object.
#
# The sequence of the review of issue #109 for a child process: the object
# of a module that ran interpreted, loaded after a reset.  The tables of
# the interpreted module are kept for the process and its shim names them;
# the object bound to them, and once the new module released the object
# the tables pointed into unmapped memory (the next use crashed, status
# 139).  The loader refuses the object, and the module imports and runs on.
RESET_LOAD = r'''
import gc
import curry
from curry.backends.cxx import tiered
curry.path.insert(0, %(tmpdir)r)
M = curry.import_(%(name)r)
tiered.cancel()
print(tiered.has_shim(%(name)r))
del M
gc.collect()
curry.reset()
curry.path.insert(0, %(tmpdir)r)
try:
  curry.load(%(sofile)r)
except curry.exceptions.DynloadError as exc:
  print('refused' if 'runs, or ran, interpreted' in str(exc) else str(exc))
else:
  print('not refused')
M = curry.import_(%(name)r)
print(next(curry.eval(M.total, 4, converter='topython')))
print('exiting normally')
'''
QUICKSTART = r'''
import os, subprocess
import curry
os.chdir(%(tmpdir)r)
curry.path.insert(0, '.')
M = curry.import_(%(name)r)
curry.save(M, %(name)r + '.cpp', module_main=False)
# The import started a compile of the module in the background, which
# writes the products sprite-make --so writes.  The two compiles would
# write M.cpp and M.so at once, and one could read a torn file; a session
# at the keyboard reaches the shell long after the compile ended.  So the
# compile ends first here.  The load during the compile is the test
# test_load_during_the_compile_exits_cleanly.
from curry.backends.cxx import tiered
tiered.wait()
subprocess.run(
    [%(make)r, '--so', %(name)r + '.curry'], check=True
  , env=dict(os.environ, CURRYPATH='.')
  )
M2 = curry.load(os.path.join('.curry', %(subdir)r, %(name)r + '.so'))
print(M2 is M)
print(next(curry.eval(M.bump, 1, converter='topython')))
print('exiting normally')
'''


class TestLoadDuringCompile(TieredTestCase):
  '''
  curry.load of the object of a module while its background compile runs,
  and of the object of a module that stays interpreted (issue #109).  The
  object binds to the live tables of the interpreted module through its
  shim, so a load that dropped the object (the import returned the module
  of the import, and nothing kept the library) left the tables pointing
  into unmapped memory: the process ended at the next use of the module, or
  at its exit in Module::clear.  The loader waits for the compile and loads
  the object the compile wrote, and it refuses the object of a module that
  stays interpreted.
  '''
  def compile_by_hand(self, name):
    '''
    Compiles a module with sprite-make, as the Quickstart does.  Returns
    the object.
    '''
    env = dict(os.environ)
    env['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx,interpret:tiered'
    env['CURRYPATH'] = self.tmpdir
    cmd = [
        'prlimit', '--as=%d' % ADDRESS_SPACE, 'timeout', str(TIMEOUT)
      , config.installed_path('bin', 'sprite-make'), '--so', '-z', name
      ]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertTrue(os.path.isfile(self.sofile(name)))
    return self.sofile(name)

  def make_stale(self, name):
    '''Moves the source of a module past its object, so the object is stale.'''
    source = os.path.join(self.tmpdir, name + '.curry')
    st = os.stat(source)
    newer = max(st.st_mtime_ns, os.stat(self.sofile(name)).st_mtime_ns) + 1
    os.utime(source, ns=(st.st_atime_ns, newer))

  def run_child(self, code):
    with binding(
        os.environ, 'SPRITE_INTERPRETER_FLAGS', 'backend:cxx,interpret:tiered'
      ):
      proc = cytest.run_in_subprocess(code, TIMEOUT, address_space=ADDRESS_SPACE)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    return proc

  @cytest.hardreset
  def test_load_waits_for_the_compile(self):
    name = self.write_module()
    self.compile_by_hand(name)
    self.make_stale(name)
    M = self.import_module(name)
    self.assertTrue(tiered.pending(name))
    self.assertTrue(cyrt.icurry_is_interpreted(M.area.info))
    before = tiered.status()
    with capture_log('curry.backends.cxx.loader', 'curry.backends.cxx.tiered') as log:
      M2 = curry.load(self.sofile(name))
    self.assertIs(M2, M)
    self.assertFalse(tiered.pending(name))
    after = tiered.status()
    self.assertEqual(after['swapped_modules'], before['swapped_modules'] + 1)
    self.assertEqual(after['failed_modules'], before['failed_modules'])
    self.assertFalse(cyrt.icurry_is_interpreted(M.area.info))
    self.assertEqual(
        os.path.realpath(getHandle(M).sofilename)
      , os.path.realpath(self.sofile(name))
      )
    infos = log.data[logging.INFO]
    self.assertTrue(
        any('Waiting for the background compile of module %s' % name in line
            for line in infos)
      , infos
      )
    self.assertEqual(log.data[logging.WARNING], [])
    self.assertEqual(self.py(M.total, 2), 8)

  @cytest.hardreset
  def test_load_waits_after_a_reset(self):
    # The registry names the kept library of the first incarnation after a
    # reset, and the second incarnation runs interpreted with a compile
    # pending: the load waits for that compile all the same, and returns a
    # module loaded from its object.
    name = self.write_module()
    M = self.import_module(name)
    self.wait()
    self.assertFalse(cyrt.icurry_is_interpreted(M.area.info))
    self.assertIsNotNone(cyrt.SharedCurryModule.find_sofilename(name))
    M = None
    self.switch('tiered')
    self.make_stale(name)
    M = self.import_module(name)
    self.assertTrue(tiered.pending(name))
    self.assertTrue(cyrt.icurry_is_interpreted(M.area.info))
    with capture_log('curry.backends.cxx.loader', 'curry.backends.cxx.tiered') as log:
      M2 = curry.load(self.sofile(name))
    self.assertIs(M2, M)
    self.assertFalse(tiered.pending(name))
    self.assertFalse(cyrt.icurry_is_interpreted(M.area.info))
    self.assertTrue(
        any('Waiting for the background compile of module %s' % name in line
            for line in log.data[logging.INFO])
      , log.data[logging.INFO]
      )
    self.assertEqual(log.data[logging.WARNING], [])
    self.assertEqual(self.py(M.total, 2), 8)

  def test_reset_then_load_is_refused(self):
    name = self.write_module()
    self.compile_by_hand(name)
    self.make_stale(name)
    proc = self.run_child(RESET_LOAD % dict(
        tmpdir=self.tmpdir, name=name, sofile=self.sofile(name)
      ))
    self.assertEqual(
        proc.stdout.splitlines(), ['True', 'refused', '40', 'exiting normally']
      , proc.stderr
      )

  def test_load_during_the_compile_exits_cleanly(self):
    # The process ended with a core dump at exit (status 139).
    name = self.write_module()
    self.compile_by_hand(name)
    self.make_stale(name)
    proc = self.run_child(CHILD_LOAD % dict(
        tmpdir=self.tmpdir, name=name, sofile=self.sofile(name)
      ))
    self.assertEqual(
        proc.stdout.splitlines(), ['True', '40', 'exiting normally'], proc.stderr
      )

  def test_quickstart_sequence_twice(self):
    # The sequence of the Quickstart, run again after an edit of the source:
    # the second run meets the background compile of the first import and
    # loads the object it wrote.  A new process reads the edited source.
    text = 'module %%(name)s where\nbump :: Int -> Int\nbump x = x + %d\n'
    name = self.write_module(text % 1)
    code = lambda: QUICKSTART % dict(
        tmpdir=self.tmpdir, name=name
      , make=config.installed_path('bin', 'sprite-make')
      , subdir=config.intermediate_subdir()
      )
    proc = self.run_child(code())
    self.assertEqual(
        proc.stdout.splitlines(), ['True', '2', 'exiting normally'], proc.stderr
      )
    self.edit_module(name, text % 2)
    proc = self.run_child(code())
    self.assertEqual(
        proc.stdout.splitlines(), ['True', '3', 'exiting normally'], proc.stderr
      )

  @cytest.hardreset
  def test_interpreted_module_refuses_its_object(self):
    # The module stays interpreted: no compiler for the background compile.
    # An object made by hand afterwards cannot be loaded over it, and the
    # module runs on.
    self.addCleanup(tiered._state.warned.discard, 'nocxx')
    with mock.patch.object(config, 'cxx_tool', return_value=None):
      with capture_log('curry.backends.cxx.tiered'):
        M = self.fresh_module()
    name = M.__name__
    self.assertTrue(cyrt.icurry_is_interpreted(M.area.info))
    self.assertFalse(tiered.pending(name))
    self.assertTrue(tiered.has_shim(name))
    sofile = self.compile_by_hand(name)
    with self.assertRaises(curry.exceptions.DynloadError) as cm:
      curry.load(sofile)
    self.assertIn('runs, or ran, interpreted in this process', str(cm.exception))
    self.assertIsNone(cyrt.SharedCurryModule.find_sofilename(name))
    self.assertTrue(cyrt.icurry_is_interpreted(M.area.info))
    self.assertEqual(self.py(M.total, 2), 8)

  def test_import_after_reset_takes_the_object(self):
    # The import plan is exempt from that refusal.  After a reset the module
    # has no library registered while its tables are kept; an import of the
    # name finds the current object and loads it, as it did before the
    # refusal existed (func_goal_defaulting.py imports after a reset in
    # every test).
    self.addCleanup(tiered._state.warned.discard, 'nocxx')
    with mock.patch.object(config, 'cxx_tool', return_value=None):
      with capture_log('curry.backends.cxx.tiered'):
        M = self.fresh_module()
    name = M.__name__
    self.assertTrue(cyrt.icurry_is_interpreted(M.area.info))
    sofile = self.compile_by_hand(name)
    del M
    curry.reset()
    curry.path.insert(0, self.tmpdir)
    M2 = curry.import_(name)
    self.assertEqual(
        os.path.realpath(cyrt.SharedCurryModule.find_sofilename(name))
      , os.path.realpath(sofile)
      )
    self.assertEqual(self.py(M2.total, 2), 8)
