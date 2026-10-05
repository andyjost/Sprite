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
from curry.backends.cxx import cyrtbindings as cyrt, tiered
from curry.objects.handle import getHandle
from curry.utility.binding import binding
import curry, gc, itertools, logging, os, shutil, subprocess, tempfile
import unittest

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

  def switch(self, mode):
    '''
    Reloads the interpreter with the flag ``interpret`` set to ``mode`` and
    puts the source directory on its path: the imports of a module are
    found through the path of the interpreter.  The caller drops its module
    objects first (see unit_cxx_interp.switch).
    '''
    gc.collect()
    curry.reload({'backend': 'cxx', 'interpret': mode})
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

  @unittest.expectedFailure
  @cytest.hardreset
  def test_nondet_io_argument_error(self):
    # An interpreted module that applies readFile of the compiled Prelude
    # to a nondeterministic name must raise the nondeterminism error, as
    # compiled code and a program interpreted whole (interpret:all) do.
    # Today it raises ValueError('bad Curry string'): a gap of the ICurry
    # interpreter in the mixed mode (see the dated TODO entry).  The compile
    # is cancelled, so the module stays interpreted.
    M = self.fresh_module(
        'module %(name)s where\nmain :: IO String\n'
        'main = readFile ("a.txt" ? "b.txt")\n'
      )
    tiered.cancel()
    self.assertTrue(cyrt.icurry_is_interpreted(M.main.info))
    with self.assertRaises(curry.EvaluationError) as cm:
      list(curry.eval(M.main))
    self.assertIn('non-determinism', str(cm.exception))

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
