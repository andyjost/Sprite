'''
Tests for the cxx worker, safepoint adoption and publication.

The worker tests dispatch armed jobs immediately to isolate publication,
loader and table-lifetime regressions. unit_jit covers the actual hot
threshold trigger and synchronous eager compilation from text.
'''
import cytest # from ./lib; must be first
from cytest.logging import capture_log
from curry import common, config, inspect
from curry.backends.cxx import compiler, curryrtbindings as curryrt, tiered
from curry.objects.handle import getHandle
from curry.utility.binding import binding
import curry, gc, itertools, logging, os, shutil, subprocess, sys, tempfile
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
  return cytest.raw.interp()._evaluation_totals.steps


class TestPrivateDirectoryFork(cytest.TestCase):
  @cytest.posix_only('requires os.fork')
  def test_child_exit_keeps_parent_directory(self):
    script = """
import cytest
from curry.backends.cxx import tiered
import os, sys
parent = tiered._tmpdir()
tiered._state.private.append(parent)
pid = os.fork()
if pid == 0:
  assert tiered._state.tmpdir is None
  assert tiered._state.private == []
  child = tiered._tmpdir()
  assert child != parent
  sys.exit(0)
_, status = os.waitpid(pid, 0)
assert os.waitstatus_to_exitcode(status) == 0
assert os.path.isdir(parent)
assert tiered._state.private == [parent]
"""
    child = subprocess.run([sys.executable, '-c', script],
        capture_output=True, text=True, timeout=TIMEOUT)
    self.assertEqual(child.returncode, 0, child.stdout + child.stderr)


class TestLoadedDependencyView(cytest.TestCase):
  def test_adoption_refuses_wrong_dependency_stamp(self):
    code = r"""
import curry, logging, os, sys, tempfile
from curry.backends.cxx import tiered, curryrtbindings as curryrt
from cytest.logging import capture_log
curry.reset(interpret='all', jit='off')
module = curry.compile('answer :: Int\nanswer = 1\n', name='StampMismatch')
with tempfile.TemporaryDirectory() as root:
  obj = os.path.join(root, 'unused' + curry.config.module_object_suffix())
  stamp = obj + '.abi'
  with open(stamp, 'w') as stream:
    stream.write('abi\ninstallation\n{"imports": {"Prelude": "wrong"}}\n')
  tiered.curryrt.tiered_submit(curry._interpreter_._its, 'StampMismatch', [sys.executable, '-c', 'pass'],
      tiered._environment(curry._interpreter_), os.path.join(root, 'job.log'),
      obj, '', [], '', '', [], [stamp + '\n"Prelude": "expected"'])
  assert curryrt.tiered_wait(30)
  with capture_log('curry.backends.cxx.tiered') as log:
    results = tiered.poll(curry._interpreter_)
  assert len(results) == 1, results
  assert not results[0]['ok'], results
  assert 'fingerprints differ' in results[0]['error'], results
  assert curryrt.icurry_is_interpreted(module.answer.info)
  assert len(log.data[logging.INFO]) == 1, log.data
  assert not log.data[logging.WARNING], log.data
tiered.finish()
"""
    child = cytest.run_in_subprocess(code, timeout=120, address_space=3 << 30)
    self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_probe_view_storage(self):
    code = r"""
import curry, os, stat, tempfile
from curry.backends.cxx import tiered
from curry.objects.handle import getHandle
curry.reset(interpret='new', jit='off')
with tempfile.TemporaryDirectory() as root:
  source = os.path.join(root, 'StorageProbe.curry')
  with open(source, 'w') as stream:
    stream.write('module StorageProbe where\nanswer :: Int\nanswer = 1\n')
  module = curry.import_(source)
  copied, roots = tiered._private_copy(getHandle(module).icurry)
  files = [os.stat(os.path.join(directory, name))
      for directory, _, names in os.walk(roots[0]) for name in names]
  linked = [item for item in files if item.st_nlink > 1]
  prelude = getHandle(curry.modules['Prelude']).icurry._loaded_generation.source
  product = curry.toolchain.icurryfilename(prelude)
  try:
    os.link(product, os.path.join(root, 'link-probe'))
  except OSError as exc:
    print('Probe view link attempt: errno %d' % exc.errno, flush=True)
  else:
    print('Probe view link attempt: supported', flush=True)
  with tempfile.TemporaryDirectory(dir='.') as build_root:
    original = os.path.join(build_root, 'original')
    with open(original, 'wb') as stream:
      stream.write(b'link probe')
    try:
      os.link(original, os.path.join(build_root, 'linked'))
    except OSError as exc:
      print('Build file system link attempt: errno %d' % exc.errno, flush=True)
    else:
      print('Build file system link attempt: supported', flush=True)
  print('Probe view: %d files, %d logical bytes, %d linked files, %d copied bytes' %
      (len(files), sum(item.st_size for item in files), len(linked),
       sum(item.st_size for item in files if item.st_nlink == 1)), flush=True)
tiered.finish()
"""
    child = cytest.run_in_subprocess(code, timeout=120, address_space=3 << 30)
    self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
    print(child.stdout.strip())

  def test_source_symlink_compiles_and_saves(self):
    for mode in ('eager', 'hot'):
      with self.subTest(mode=mode), tempfile.TemporaryDirectory() as work:
        source = os.path.join(work, 'source')
        alias = os.path.join(work, 'alias')
        os.mkdir(source)
        os.mkdir(alias)
        real = os.path.join(source, 'FreshAlias.curry')
        link = os.path.join(alias, 'FreshAlias.curry')
        with open(real, 'w') as stream:
          stream.write('module FreshAlias where\nf :: Int -> Int\nf x = x + 1\n')
        try:
          os.symlink(real, link)
        except (OSError, NotImplementedError) as exc:
          self.skipTest('source-file symlinks unavailable: %s' % exc)
        with open(os.path.join(alias, 'AliasImporter.curry'), 'w') as stream:
          stream.write('module AliasImporter where\nimport FreshAlias\n'
                       'main :: Int\nmain = f 41\n')
        code = r"""
import curry, os, subprocess
from curry.backends.cxx import tiered, curryrtbindings as curryrt, image
from curry.objects.handle import getHandle
from curry.toolchain import _findcurry, _filenames
from curry.interpreter import Interpreter
root = %r
os.environ['SPRITE_CACHE_FILE'] = ''
os.environ['SPRITE_JIT_THRESHOLD'] = '1'
flags = dict(interpret='all', jit=%r, jit_backend='cxx')
curry.reset(**flags)
interp = curry._interpreter_
alias = os.path.join(root, 'alias', 'FreshAlias.curry')
real = os.path.join(root, 'source', 'FreshAlias.curry')
leaf = curry.import_(alias)
generation = _findcurry.loaded_generation('FreshAlias', interp)
assert generation.source == os.path.realpath(real)
assert not os.path.exists(_filenames.icurryfilename(real))
assert interp.eval(leaf.f(41)).one() == 42
assert tiered.wait(120, interp=interp)
assert not curryrt.icurry_is_interpreted(leaf.f.info)
# A second interpreter owns a separate record for the same real source.
other = Interpreter(flags=flags)
second = other.import_(real, is_sourcefile=True)
second_generation = _findcurry.loaded_generation('FreshAlias', other)
assert second_generation is not generation
assert second_generation.source == generation.source
assert other.eval(second.f(41)).one() == 42
assert tiered.wait(120, interp=other)
assert not curryrt.icurry_is_interpreted(leaf.f.info)
assert not curryrt.icurry_is_interpreted(second.f.info)
assert generation.source_spelling == alias
assert second_generation.source_spelling == real
assert generation.product_digest('.icy') == image.digest(_filenames.icurryfilename(alias))
module = interp.import_(os.path.join(root, 'alias', 'AliasImporter.curry'), is_sourcefile=True)
# Inspect the compile job's dependency view, then exercise actual compilation.
copy, roots = tiered._private_copy(getHandle(module).icurry)
view = _filenames.icurryfilename(os.path.join(roots[0], 'FreshAlias.curry'))
for suffix in ('.icy', '.fint', '.icurry', '.icy.imports', '.icy.source'):
  original = _filenames.icurryfilename(alias)[:-4] + suffix
  with open(view[:-4] + suffix, 'rb') as stream:
    with open(original, 'rb') as expected:
      assert stream.read() == expected.read(), suffix
assert interp.eval(module.main).one() == 42
assert tiered.wait(120, interp=interp)
assert not curryrt.icurry_is_interpreted(module.main.info)
program = os.path.join(root, 'saved.exe')
curry.save(module, program, main='main')
run = subprocess.run([program], capture_output=True, text=True, timeout=120)
assert run.returncode == 0, run.stdout + run.stderr
assert run.stdout == '42\n', run.stdout
assert _findcurry.loaded_generation('FreshAlias', interp) is generation
assert _findcurry.loaded_generation('FreshAlias', other) is second_generation
tiered.finish()
""" % (work, mode)
        child = cytest.run_in_subprocess(code, timeout=360, address_space=3 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_reordered_path_keeps_loaded_leaf(self):
    with tempfile.TemporaryDirectory() as work:
      for answer in (1, 2):
        directory = os.path.join(work, str(answer))
        os.mkdir(directory)
        source = os.path.join(directory, 'Leaf.curry')
        with open(source, 'w') as stream:
          stream.write('module Leaf where\nanswer :: Int\nanswer = %d\n' % answer)
        code = "import curry; curry.reset(interpret='off', jit='off'); curry.import_(%r)" % source
        child = cytest.run_in_subprocess(code, timeout=180, address_space=3 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
      probe = os.path.join(work, 'Probe.curry')
      with open(probe, 'w') as stream:
        stream.write('module Probe where\nimport Leaf\ngoal :: (Int,Int)\ngoal = (answer,answer)\n')
      for mode in ('eager', 'hot'):
        code = r"""
import curry, os
from curry.backends.cxx import tiered, curryrtbindings as curryrt
from curry.objects.handle import getHandle
root = %r
os.environ['SPRITE_JIT_THRESHOLD'] = '1'
curry.reset(interpret='new', jit=%r, jit_backend='cxx')
curry.path.insert(0, os.path.join(root, '1'))
leaf = curry.import_('Leaf')
assert curry.eval(leaf.answer).one() == 1
curry.path.insert(0, os.path.join(root, '2'))
probe = curry.import_(os.path.join(root, 'Probe.curry'))
assert curry.show(curry.eval(probe.goal).one()) == '(1,1)'
assert tiered.wait(120, interp=curry._interpreter_)
assert not curryrt.icurry_is_interpreted(probe.goal.info)
assert curry.show(curry.eval(probe.goal).one()) == '(1,1)'
assert curry.eval(leaf.answer).one() == 1
tiered.finish()
""" % (work, mode)
        child = cytest.run_in_subprocess(code, timeout=240, address_space=3 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)


class TieredTestCase(cytest.TestCase):
  '''A temporary source directory with one fresh module per import.'''
  counter = itertools.count()

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-tiered-test-')
    # Exercise worker/publication regressions without waiting for hot calls.
    # Actual threshold gating is covered in unit_jit.
    arm = curryrt.cxx_arm
    def dispatch(state, name, *args):
      # Expressions remain cold in these worker-only regression fixtures.
      return (arm if config.is_expression_modname(name) else curryrt.tiered_submit)(state, name, *args)
    patch = mock.patch.object(curryrt, 'cxx_arm', side_effect=dispatch)
    patch.start()
    self.addCleanup(patch.stop)
    self.switch('cxx')

  def switch(self, mode, **flags):
    '''
    Reloads the interpreter with the flag ``interpret`` set to ``mode``, and
    ``flags``, and puts the source directory on its path: the imports of a
    module are found through the path of the interpreter.  The caller drops
    its module objects first (see unit_cxx_interp.switch).
    '''
    gc.collect()
    flags.setdefault('jit', 'hot' if mode == 'cxx' else 'off')
    flags.setdefault('jit_backend', 'cxx')
    curry.reset(**dict(flags, backend='cxx', interpret='new' if mode == 'cxx' else mode))
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
        self.tmpdir, '.curry', config.intermediate_subdir(), name + config.module_object_suffix()
      )

  def edit_module(self, name, text):
    '''Writes a new text for the module ``name``.'''
    with open(os.path.join(self.tmpdir, name + '.curry'), 'w') as stream:
      stream.write(text % {'name': name})

  def value(self, *args):
    '''The first value of a goal, as a Curry node.'''
    return next(cytest.raw.values(cytest.raw.expr(*args, typed=True)))

  def py(self, *args):
    '''The first value of a goal, as a Python object.'''
    return cytest.raw.interp().topython(self.value(*args))

  def stamp(self, name):
    '''The ABI stamp of the object: written after a compile ends.'''
    return self.sofile(name) + '.abi'

  def wait(self):
    self.assertTrue(
        tiered.wait(COMPILE_SECONDS, cytest.raw.interp())
      , 'the background compile did not end in %s s' % COMPILE_SECONDS
      )


class TestRemovedDirectory(TieredTestCase):
  '''
  A search path entry that goes while its module compiles in the background
  (issue #173).  The child compiles a private copy and writes nothing under
  the directory, so its removal never finds a half-written product, and the
  products are published beside the source only at the swap, when the
  source is still there.
  '''
  def test_removed_directory_gets_no_products(self):
    work = tempfile.mkdtemp(prefix='sprite-tiered-removed-')
    curry.path.insert(0, work)
    name = 'CxxTieredRemoved%d' % next(self.counter)
    with open(os.path.join(work, name + '.curry'), 'w') as stream:
      stream.write(MODULE % {'name': name})
    M = curry.import_(name)
    self.assertTrue(tiered.pending(name))
    # The directory goes at once, as a TemporaryDirectory of a test does at
    # the end of its block: the compile is still running.
    shutil.rmtree(work)
    self.wait()
    self.assertFalse(os.path.exists(work))
    # The module runs on, interpreted or swapped to the private object.  The
    # untyped builder: the interface files went with the directory.
    goal = cytest.raw.expr(M.total, 3, typed=False)
    self.assertEqual(
        cytest.raw.interp().topython(next(cytest.raw.values(goal))), 20
      )

  def test_products_published_at_the_swap(self):
    '''A module whose source stays gets its object and stamp beside it.'''
    name = self.write_module()
    M = self.import_module(name)
    private = os.path.realpath(tiered._tmpdir()) + os.sep
    record = tiered._state.records[tiered._key(cytest.raw.interp(), name)]
    self.assertTrue(os.path.realpath(record.sofile).startswith(private), record.sofile)
    self.wait()
    self.assertTrue(os.path.isfile(self.sofile(name)))
    self.assertTrue(os.path.isfile(self.stamp(name)))
    self.assertEqual(self.py(M.total, 3), 20)

  def test_adoption_keeps_private_generation(self):
    name = self.write_module()
    M = self.import_module(name)
    private = tiered._state.records[tiered._key(cytest.raw.interp(), name)].sofile
    self.wait()
    self.assertTrue(os.path.isfile(self.sofile(name)))
    self.assertEqual(getHandle(M).sofilename, private,
        'adoption reopened the replaceable canonical pathname')
    self.assertEqual(self.py(M.total, 3), 20)

  @cytest.posix_only('POSIX flock regression')
  def test_busy_product_lock_keeps_private_object(self):
    import fcntl
    name = self.write_module()
    M = self.import_module(name)
    lockfile = os.path.splitext(self.sofile(name))[0] + '.lock'
    with open(lockfile, 'a+b') as lock:
      fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
      # A blocking native lock here holds the GIL and deadlocks the test.
      self.wait()
      self.assertFalse(os.path.exists(self.sofile(name)))
      self.assertFalse(os.path.exists(self.stamp(name)))
      self.assertFalse(curryrt.icurry_is_interpreted(M.total.info))
      self.assertEqual(self.py(M.total, 3), 20)

  def test_publication_with_windows_publication(self):
    from pathlib import Path
    with mock.patch.dict(os.environ, SPRITE_TEST_WINDOWS_PUBLICATION='1'):
      self.test_products_published_at_the_swap()
      copies = list(Path(self.tmpdir).rglob('*.tiered'))
      self.assertFalse(copies, 'publication must not make per-load copies')


class TestSwap(TieredTestCase):
  '''
  A fresh module is interpreted at once.  Its functions run compiled after
  the background compile, in the same process, with the same values and
  steps.
  '''
  @cytest.hardreset
  def test_swap(self):
    self.assertEqual(curry.flags['interpret'], 'new')
    M = self.fresh_module()
    name = M.__name__
    h = getHandle(M)
    # Interpreted at once, with the compile queued.
    self.assertIsNone(h.icurry.metadata.get('cxx.shlib'))
    for f in M.area, M.mk, M.same, M.total, M.loop:
      self.assertTrue(curryrt.icurry_is_interpreted(f.info), f.name)
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
      self.assertFalse(curryrt.icurry_is_interpreted(f.info), f.name)
    # The stats line counts the swapped functions.
    self.assertEqual(
        curry.stats()['swapped'] - swapped_stat
      , after['swapped_functions'] - before['swapped_functions']
      )
    # The object is on record and on disk.
    self.assertTrue(os.path.isfile(self.sofile(name)))
    self.assertIsNotNone(h.icurry.metadata.get('cxx.shlib'))
    self.assertNotEqual(
        os.path.realpath(h.sofilename), os.path.realpath(self.sofile(name))
      )
    # Values of the compiled tier: the same, in the same steps.
    v2 = self.value(M.mk, 3)
    self.assertEqual(str(v2), 'Rect 3 4')
    n0 = steps()
    self.assertEqual(self.py(M.total, 4), 40)
    self.assertEqual(steps() - n0, steps_interpreted)
    # One table per symbol: the compiled code binds to the tables the
    # interpreter made (the binding of the load), so a value of each tier
    # has the same constructor, isa holds, and the two compare equal.
    self.assertEqual(v2.info.address, v1.info.address)
    self.assertEqual(v2.info.address, M.Rect.info.address)
    self.assertTrue(inspect.isa(v2, M.Rect))
    self.assertTrue(inspect.isa(v2, curry.info(curry.modules[name]).types['Shape']))
    self.assertIs(self.py(M.same, v1, v2), True)
    self.assertIs(self.py(M.same, v2, self.value(M.mk, 3)), True)
    self.assertIs(self.py(M.same, v1, self.value(M.mk, 4)), False)
    # The bytecode stays with the table.
    self.assertIsNone(curryrt.icurry_bytecode(M.area.info))

  @cytest.hardreset
  def test_swap_within_an_evaluation(self):
    # The evaluation of choices yields three values from three
    # alternatives.  After the first value, the swap is applied while the
    # evaluation waits; the remaining alternatives run compiled, and the
    # evaluation ends with the same values.
    M = self.fresh_module()
    expected = sorted(str(v) for v in curry.eval((M.choices)(4)))
    self.assertEqual(expected, ['0', '20', '40'])
    N = self.fresh_module()
    values = curry.eval((N.choices)(4))
    first = next(values)
    self.assertTrue(curryrt.icurry_is_interpreted(N.choices.info))
    self.wait()
    self.assertFalse(curryrt.icurry_is_interpreted(N.choices.info))
    self.assertFalse(curryrt.icurry_is_interpreted(N.loop.info))
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
    self.assertFalse(curryrt.icurry_is_interpreted(M.loop.info))
    self.assertEqual(self.py(M.loop, 10), 0)

  @cytest.hardreset
  def test_llvm_flush_preserves_a_ready_cxx_swap(self):
    # A cxx result can arrive between the foreground poll and LLVM flush.
    # Its wakeup must survive that flush until the scheduler reaches it.
    from curry.backends.cxx import llvmjit
    M = self.fresh_module()
    goal = cytest.raw.expr(M.loop, 10, typed=True)
    before = tiered.status()['applied_in_evaluation']
    poll = tiered.poll
    first = True
    def delayed_poll(interp=None):
      nonlocal first
      if first:
        first = False
        return []
      return poll(interp)
    def flush_ready():
      self.assertTrue(curryrt.tiered_wait(COMPILE_SECONDS))
      curryrt.icurry_apply_posted()
    with mock.patch.object(tiered, 'poll', side_effect=delayed_poll):
      with mock.patch.object(llvmjit, 'flush', side_effect=flush_ready):
        self.assertEqual([str(v) for v in cytest.raw.values(goal)], ['0'])
    self.assertEqual(tiered.status()['applied_in_evaluation'], before + 1)
    self.assertFalse(curryrt.icurry_is_interpreted(M.loop.info))

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
    self.assertTrue(curryrt.icurry_is_interpreted(N.biggest.info))
    self.assertTrue(curryrt.icurry_is_interpreted(M.area.info))
    self.assertEqual(self.py(N.biggest, 4), 20)
    self.wait()
    self.assertFalse(curryrt.icurry_is_interpreted(N.biggest.info))
    self.assertFalse(curryrt.icurry_is_interpreted(M.area.info))
    self.assertEqual(self.py(N.biggest, 4), 20)
    v = self.value(N.build, 2)
    self.assertEqual(str(v), 'Rect 2 3')
    self.assertTrue(inspect.isa(v, M.Rect))
    self.assertIs(self.py(M.same, v, self.value(M.mk, 2)), True)

  @cytest.hardreset
  def test_compiled_tables_survive_a_private_reload(self):
    # Compiled tables belong to the process. A private reload gets fresh
    # tables and leaves the previous object's bound tables intact.
    name = self.write_module()
    M = self.import_module(name)
    old_info = M.area.info
    address = old_info.address
    self.wait()
    self.assertFalse(curryrt.icurry_is_interpreted(old_info))
    bindings = tiered.status()['bindings']
    M = None
    self.switch('cxx')
    # The object exists now, so a plain import loads it compiled.  Remove
    # it: the module is interpreted again, from the image beside the
    # generated file, and the compile starts from that file. The process
    # keeps the first incarnation's tables; no warning is logged.
    os.unlink(self.sofile(name))
    os.unlink(self.stamp(name))
    with capture_log('curry.backends.cxx.tiered') as log:
      M = self.import_module(name)
      self.assertNotEqual(M.area.info.address, address)
      self.assertFalse(curryrt.icurry_is_interpreted(old_info))
      self.assertTrue(curryrt.icurry_is_interpreted(M.area.info))
      self.assertEqual(self.py(M.area, self.value(M.mk, 3)), 12)
      self.wait()
    self.assertEqual(log.data[logging.WARNING], [])
    self.assertEqual(tiered.status()['bindings'], bindings)
    self.assertFalse(curryrt.icurry_is_interpreted(M.area.info))
    self.assertEqual(self.py(M.area, self.value(M.mk, 3)), 12)

  @cytest.hardreset
  def test_edited_module_swaps_to_its_new_code(self):
    # After an edit that keeps the shape of the module, a reload imports
    # the new source. A loaded canonical object keeps its file; the new
    # compile is adopted from its private generation.
    text = 'module %%(name)s where\nbump :: Int -> Int\nbump x = x + %d\n'
    name = self.write_module(text % 1)
    M = self.import_module(name)
    address = M.bump.info.address
    self.assertEqual(self.py(M.bump, 1), 2)
    self.wait()
    self.assertFalse(curryrt.icurry_is_interpreted(M.bump.info))
    self.assertEqual(self.py(M.bump, 1), 2)
    M = None
    self.edit_module(name, text % 2)
    self.switch('cxx')
    M = self.import_module(name)
    new_address = M.bump.info.address
    self.assertNotEqual(new_address, address)
    self.assertTrue(curryrt.icurry_is_interpreted(M.bump.info))
    self.assertEqual(self.py(M.bump, 1), 3)
    before = tiered.status()
    with capture_log('curry.backends.cxx.tiered') as log:
      self.wait()
    after = tiered.status()
    self.assertEqual(after['swapped_modules'], before['swapped_modules'] + 1)
    self.assertFalse(curryrt.icurry_is_interpreted(M.bump.info))
    self.assertEqual(self.py(M.bump, 1), 3)
    self.assertEqual(M.bump.info.address, new_address)

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
    self.assertFalse(curryrt.icurry_is_interpreted(D.h.info))
    self.assertFalse(curryrt.icurry_is_interpreted(B.g.info))
    self.assertTrue(os.path.isfile(self.stamp(dep)))
    D = B = None
    self.edit_module(base, base_text % 2)
    self.switch('cxx')
    D = self.import_module(dep)
    B = curry.import_(base)
    self.assertTrue(curryrt.icurry_is_interpreted(B.g.info))
    self.assertTrue(curryrt.icurry_is_interpreted(D.h.info))
    self.assertIsNone(getHandle(D).icurry.metadata.get('cxx.shlib'))
    self.assertEqual(self.py(B.g, 1), 3)
    self.assertEqual(self.py(D.h, 1), 3)
    self.wait()
    self.assertFalse(curryrt.icurry_is_interpreted(B.g.info))
    self.assertFalse(curryrt.icurry_is_interpreted(D.h.info))
    self.assertEqual(self.py(B.g, 1), 3)
    self.assertEqual(self.py(D.h, 1), 3)

  @cytest.hardreset
  def test_string_module_made_again_after_a_reset(self):
    # A module compiled from a string is interpreted and makes no library,
    # so a module of the same name after a reset is not refused (compare
    # unit_compile.testReusedModuleNameIsAnError under interpret:off): it
    # takes the tables of the first back and runs its own code.
    first = curry.compile('f :: Int\nf = 1', name='TieredDup')
    address = first.f.info.address
    self.assertEqual(self.py(first.f), 1)
    first = None
    curry.reset()
    second = curry.compile('f :: Int\nf = 2', name='TieredDup')
    self.assertEqual(second.f.info.address, address)
    self.assertEqual(self.py(second.f), 2)

  @cytest.hardreset
  def test_string_module_made_again_while_the_first_is_alive(self):
    # Issue #114: the first module object alive across the reset.  Its
    # tables stayed in the registry with their steps, and the second module
    # found them and ran the first code.  The reset hands the tables over
    # (Module::retire), so the second module takes them back, at the same
    # addresses, without the steps.
    first = curry.compile('f :: Int\nf = 1', name='TieredDupAlive')
    address = first.f.info.address
    self.assertEqual(self.py(first.f), 1)
    curry.reset()
    second = curry.compile('f :: Int\nf = 2', name='TieredDupAlive')
    with self.assertRaises(curry.StaleError):
      first.f
    self.assertEqual(second.f.info.address, address)
    self.assertEqual(self.py(second.f), 2)
    del first

  EDITED = (
      'module %%(name)s where\n\n'
      'data T = A | B Int deriving (Eq, Show)\n\n'
      'f :: T\nf = B %d\n\n'
      'g :: T -> Int\ng A = 0\ng (B n) = n\n\n'
      'main :: Int\nmain = g f\n'
    )

  @cytest.hardreset
  def test_edited_module_made_again_while_the_first_is_alive(self):
    # The import route of issue #114: the source edited between two imports
    # with a reset between them, the first module object alive.  The first
    # incarnation is swapped to compiled code before the edit; the second
    # gets private tables, runs the new code interpreted, and is swapped
    # to the new object in turn. The old compiled generation keeps its
    # tables, including the data type; no warning is logged.
    name = self.write_module(self.EDITED % 1)
    first = self.import_module(name)
    self.assertEqual(self.py(first.main), 1)
    self.wait()
    self.assertFalse(curryrt.icurry_is_interpreted(first.f.info))
    addresses = first.f.info.address, first.B.info.address
    self.edit_module(name, self.EDITED % 2)
    curry.reset()
    curry.path.insert(0, self.tmpdir)
    with capture_log('curry.backends.cxx.tiered') as log:
      second = self.import_module(name)
    self.assertEqual(log.data[logging.WARNING], [])
    with self.assertRaises(curry.StaleError):
      first.f
    self.assertNotEqual(second.f.info.address, addresses[0])
    self.assertNotEqual(second.B.info.address, addresses[1])
    self.assertTrue(curryrt.icurry_is_interpreted(second.f.info))
    self.assertEqual(self.py(second.main), 2)
    self.wait()
    self.assertFalse(curryrt.icurry_is_interpreted(second.f.info))
    self.assertEqual(self.py(second.main), 2)
    del first

  @cytest.hardreset
  def test_edited_module_made_again_after_a_reload(self):
    # The same across the hard reset of curry.reload, which unlinks the
    # modules of the interpreter it replaces, the first module object alive.

    name = self.write_module(self.EDITED % 1)
    first = self.import_module(name)
    self.assertEqual(self.py(first.main), 1)
    self.edit_module(name, self.EDITED % 2)
    self.switch('cxx')
    second = self.import_module(name)
    with self.assertRaises(curry.StaleError):
      first.f
    self.assertEqual(self.py(second.main), 2)
    del first

  @cytest.hardreset
  def test_edited_module_made_again_under_interpret_off(self):
    # The import route of issue #114 under interpret:off, the owner's
    # decision: the second incarnation runs the first code.  Its object
    # lands at the path of the object the process maps, and the loader
    # joins the registry entry of the loaded library without a refusal or
    # a warning (see the TODO entry of 2026-10-10).  The compile of the
    # first incarnation runs in the foreground here.
    name = self.write_module(self.EDITED % 1)
    self.switch('off')
    first = self.import_module(name)
    self.assertEqual(self.py(first.main), 1)
    self.edit_module(name, self.EDITED % 2)
    curry.reset()
    curry.path.insert(0, self.tmpdir)
    second = self.import_module(name)
    self.assertEqual(self.py(second.main), 2)
    del first


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
    self.assertTrue(curryrt.icurry_is_interpreted(M.area.info))
    self.assertFalse(os.path.exists(self.stamp(M.__name__)))
    warnings = log.data[logging.WARNING]
    self.assertEqual(len(warnings), 1)
    self.assertIn('stays interpreted', warnings[0])
    self.assertIn('no-such-flag-of-sprite', warnings[0])

  @cytest.hardreset
  def test_strings_and_expressions_stay_interpreted(self):
    before = tiered.status()
    self.switch('new', jit='off')
    S = curry.compile(
        'double :: Int -> Int\ndouble x = x + x\n'
      )
    self.assertTrue(curryrt.icurry_is_interpreted(S.double.info))
    e = curry.parse('double 21', imports=[S])
    self.assertEqual(next(curry.eval(e)), 42)
    self.assertTrue(tiered.wait(10))
    after = tiered.status()
    self.assertEqual(after['queued'], 0)
    self.assertEqual(after['swapped_modules'], before['swapped_modules'])
    self.assertEqual(after['failed_modules'], before['failed_modules'])
    self.assertTrue(curryrt.icurry_is_interpreted(S.double.info))

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
    self.switch('cxx')
    M = self.import_module(name)
    self.assertIsNotNone(getHandle(M).icurry.metadata.get('cxx.shlib'))
    self.assertFalse(curryrt.icurry_is_interpreted(M.area.info))
    self.assertEqual(self.py(M.total, 2), 8)
    prelude = curry.import_('Prelude')
    self.assertIsNotNone(getHandle(prelude).icurry.metadata.get('cxx.shlib'))
    self.assertFalse(curryrt.icurry_is_interpreted(prelude.map.info))

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
    self.assertTrue(curryrt.icurry_is_interpreted(M.main.info))
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
    self.switch('cxx', inline_budget=0)
    self.assertEqual(curry.flags['inline_budget'], 0)
    env = dict(
        item.split('=', 1)
          for item in tiered._environment(cytest.raw.interp())
      )
    self.assertIn(
        'inline_budget:0', env['SPRITE_INTERPRETER_FLAGS'].split(',')
      )
    M = self.fresh_module(BUDGET_MODULE)
    self.assertTrue(curryrt.icurry_is_interpreted(M.viaCall.info))
    n0 = steps()
    self.assertEqual(self.py(M.direct), 3)
    direct = steps() - n0
    n0 = steps()
    self.assertEqual(self.py(M.viaCall), 3)
    interpreted = steps() - n0
    self.assertEqual(interpreted, direct + 1)
    self.wait()
    self.assertFalse(curryrt.icurry_is_interpreted(M.viaCall.info))
    n0 = steps()
    self.assertEqual(self.py(M.viaCall), 3)
    self.assertEqual(steps() - n0, interpreted)
    # Under the default budget the call is inlined on both tiers.
    self.switch('cxx')
    env = dict(
        item.split('=', 1)
          for item in tiered._environment(cytest.raw.interp())
      )
    self.assertIn(
        'inline_budget:4', env['SPRITE_INTERPRETER_FLAGS'].split(',')
      )
    N = self.fresh_module(BUDGET_MODULE)
    n0 = steps()
    self.assertEqual(self.py(N.viaCall), 3)
    self.assertEqual(steps() - n0, direct)
    self.wait()
    self.assertFalse(curryrt.icurry_is_interpreted(N.viaCall.info))
    n0 = steps()
    self.assertEqual(self.py(N.viaCall), 3)
    self.assertEqual(steps() - n0, direct)

  def test_getimpl_after_the_swap(self):
    '''
    inspect.getimpl of a swapped function reads the compiled code from the
    generated file beside the object in the process that swapped it, as it
    does in a process that loads the object; before the swap it shows the
    bytecode.  After a wait without an interpreter it raised "its module
    has no compiled object": the poll recorded the object in the ICurry of
    the module through the interpreter alone (issue #115).
    '''
    M = self.fresh_module()
    name = M.__name__
    banner = '/****** %s.area ******/\n' % name
    code = inspect.getimpl(M.area)
    self.assertTrue(code.startswith(banner), code)
    self.assertIn('bytecode:', code)
    self.assertIsNone(getHandle(M).sofilename)
    # The wait of the issue names no interpreter.
    self.assertTrue(tiered.wait(COMPILE_SECONDS))
    self.assertFalse(curryrt.icurry_is_interpreted(M.area.info))
    self.assertNotEqual(
        os.path.realpath(getHandle(M).sofilename)
      , os.path.realpath(self.sofile(name))
      )
    code = inspect.getimpl(M.area)
    self.assertTrue(code.startswith(banner), code)
    self.assertNotIn('bytecode:', code)
    self.assertIn('RuntimeState * rts', code)
    self.assertEqual(code, M.area.getimpl())

  @cytest.hardreset
  def test_original_cpp_after_private_adoption(self):
    name = self.write_module(BUDGET_MODULE)
    env = dict(os.environ, CURRYPATH=self.tmpdir,
        SPRITE_INTERPRETER_FLAGS='backend:cxx,inline_budget:4')
    result = subprocess.run([config.installed_path('bin', 'sprite-make'), '--so', name],
        env=env, capture_output=True, text=True, timeout=120)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    original = os.path.splitext(self.sofile(name))[0] + '.cpp'
    code = """
import curry, os
from curry.backends.cxx import tiered
from curry.backends.cxx.toolchain import Cpp2So
from curry.objects.handle import getHandle
curry.reset(interpret='all', jit='eager', jit_backend='cxx', inline_budget=0)
curry.path.insert(0, %r)
module = curry.import_(%r)
tiered.wait(120)
tiered.poll(curry._interpreter_)
assert os.path.realpath(getHandle(module).sofilename) != os.path.realpath(%r)
assert Cpp2So(curry._interpreter_).format_version(%r) is not None
""" % (self.tmpdir, name, self.sofile(name), original)
    child = cytest.run_in_subprocess(code, timeout=240, address_space=3 << 30)
    self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  @cytest.hardreset
  def test_foreign_budget_compiles_a_private_copy(self):
    '''
    A process whose inline budget is not the environment's compiles a
    module in the background into a directory of its own: the swap gives
    it code of its budget, and nothing lands beside the source, where every
    later process took an object of another budget for current, because
    the ABI stamp does not record the budget (issue #116).  A process
    under the budget of the environment then finds no object, compiles the
    module beside the source, and runs the inlined code on both tiers.
    '''
    self.switch('cxx', inline_budget=0)
    self.assertTrue(tiered._foreign_flags(cytest.raw.interp()))
    name = self.write_module(BUDGET_MODULE)
    M = self.import_module(name)
    self.assertTrue(curryrt.icurry_is_interpreted(M.viaCall.info))
    n0 = steps()
    self.assertEqual(self.py(M.direct), 3)
    direct = steps() - n0
    n0 = steps()
    self.assertEqual(self.py(M.viaCall), 3)
    self.assertEqual(steps() - n0, direct + 1)
    self.wait()
    self.assertFalse(curryrt.icurry_is_interpreted(M.viaCall.info))
    n0 = steps()
    self.assertEqual(self.py(M.viaCall), 3)
    self.assertEqual(steps() - n0, direct + 1)
    # Nothing beside the source.  The object, its stamp and the generated
    # file lie in the directory of the process, and getimpl reads them.
    self.assertFalse(os.path.exists(self.sofile(name)))
    self.assertFalse(os.path.exists(self.stamp(name)))
    self.assertFalse(os.path.exists(self.sofile(name)[:-3] + '.cpp'))
    sofile = getHandle(M).sofilename
    private = os.path.realpath(tiered._tmpdir()) + os.sep
    self.assertTrue(os.path.realpath(sofile).startswith(private), sofile)
    self.assertTrue(os.path.isfile(sofile + '.abi'))
    self.assertIn(
        '/****** %s.viaCall ******/' % name, inspect.getimpl(M.viaCall)
      )
    # The same module under the budget of the environment.
    del M
    self.switch('cxx')
    self.assertFalse(tiered._foreign_flags(cytest.raw.interp()))
    N = self.import_module(name)
    self.assertTrue(curryrt.icurry_is_interpreted(N.viaCall.info))
    n0 = steps()
    self.assertEqual(self.py(N.viaCall), 3)
    self.assertEqual(steps() - n0, direct)
    self.wait()
    self.assertFalse(curryrt.icurry_is_interpreted(N.viaCall.info))
    self.assertTrue(os.path.isfile(self.sofile(name)))
    self.assertTrue(os.path.isfile(self.stamp(name)))
    self.assertNotEqual(
        os.path.realpath(getHandle(N).sofilename)
      , os.path.realpath(self.sofile(name))
      )
    n0 = steps()
    self.assertEqual(self.py(N.viaCall), 3)
    self.assertEqual(steps() - n0, direct)

  def test_private_copies_have_independent_views(self):
    '''
    Each child searches its own view, then the original root.
    '''
    import types
    root = tempfile.mkdtemp(dir=self.tmpdir)
    if os.name == 'posix':
      alias = root + '-alias'
      os.symlink(root, alias)
      root = alias
    source = os.path.join(root, 'PrivateOrder.curry')
    with open(source, 'w') as stream:
      stream.write('f :: Int\nf = 1\n')
    imodule = types.SimpleNamespace(filename=source, fullname='PrivateOrder')
    before = list(tiered._state.private)
    try:
      copy1, dirs1 = tiered._private_copy(imodule)
      copy2, dirs2 = tiered._private_copy(imodule)
      copy3, dirs3 = tiered._private_copy(imodule)
    finally:
      added = tiered._state.private[len(before):]
      del tiered._state.private[len(before):]
    dir1, dir2, dir3 = added
    self.assertEqual(os.path.dirname(copy1), dir1)
    self.assertEqual(os.path.dirname(copy3), dir3)
    self.assertTrue(os.path.isfile(copy3))
    self.assertEqual(dirs1, [dir1, root])
    self.assertEqual(dirs2, [dir2, root])
    self.assertEqual(dirs3, [dir3, root])

  def test_sprite_make_compiles(self):
    # An explicit compile writes the object under the flag.
    name = self.write_module()
    env = dict(os.environ)
    env['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx,interpret:new,jit:hot,jit_backend:cxx'
    env['CURRYPATH'] = self.tmpdir
    cmd = cytest.limit_prefix(ADDRESS_SPACE, TIMEOUT) + [
        config.installed_path('bin', 'sprite-make'), '--so', name
      ]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertTrue(os.path.isfile(self.sofile(name)))
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
    env['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx,interpret:%s,jit:hot,jit_backend:cxx' % ('new' if mode == 'cxx' else mode)
    env['CURRYPATH'] = currypath
    env.pop('SPRITE_GC_STRESS', None)
    env.update(extra)
    cmd = cytest.limit_prefix(ADDRESS_SPACE, TIMEOUT) + [
        config.installed_path('bin', 'sprite-exec'), '--stats', '-m', program
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
    self.assertEqual(self.run_child('Fib', 'cxx', self.tmpdir), expected)
    sofile = os.path.join(
        self.tmpdir, '.curry', config.intermediate_subdir(), 'Fib' + config.module_object_suffix()
      )
    # The program ends before its compile; the compile is cancelled, so no
    # finished object (one with its ABI stamp) is left behind.
    self.assertFalse(os.path.exists(sofile + '.abi'))
    # The run was interpreted from the image.
    self.assertTrue(os.path.exists(sofile[:-3] + '.img'))

  def test_failed_compile_is_logged(self):
    # A compile that fails during the evaluation of a program is reported
    # on the standard error of sprite-exec, once, and counted in the stats
    # line; the program ends with the values of the interpreter.  Tak1
    # runs long enough for the child to fail first.
    expected = self.run_child('Tak1', 'off', BENCHMARKS)
    shutil.copy(os.path.join(BENCHMARKS, 'Tak1.curry'), self.tmpdir)
    actual = self.run_child(
        'Tak1', 'cxx', self.tmpdir, CXXFLAGS='-fno-such-flag-of-sprite'
      )
    self.assertEqual(actual, expected)
    stderr = self.last_stderr
    self.assertIn('WARNING:', stderr)
    self.assertEqual(sum('WARNING:' in line and 'stays interpreted' in line
        for line in stderr.splitlines()), 1, stderr)
    self.assertIn('no-such-flag-of-sprite', stderr)
    stats = stderr.strip().splitlines()[-1]
    self.assertIn(' swapped=0 ', stats)
    self.assertIn(' failed_compiles=1', stats)


# The sequence of the API study's probe (P55) for a child process: the
# import of a module whose object is stale queues its compile, and
# curry.load of that object returns the module of the import.
CHILD_LOAD = "\nimport cytest, curry\ncurry.path.insert(0, %(tmpdir)r)\nM = curry.import_(%(name)r)\nM2 = curry._interpreter_.load(%(sofile)r)\nprint(M2 is M)\nprint(next(curry.eval((M.total)(4))))\nprint('exiting normally')\n"

# The save-then-load sequence of the Quickstart ("Saving Compiled Curry") for
# a child process: the import, curry.save, sprite-make --so in a shell, then
# curry.load of the object.
#
# The sequence of the review of issue #109 for a child process: the object
# of a module that ran interpreted, loaded after a reset.  The tables of
# the interpreted module are kept for the process and its binding is on
# record.  Adoption keeps the object with those tables, across subsequent
# resets.
RESET_LOAD = r'''
import gc
import cytest, curry
from curry.backends.cxx import tiered
curry.path.insert(0, %(tmpdir)r)
M = curry.import_(%(name)r)
tiered.cancel()
print(tiered.has_binding(%(name)r))
del M
gc.collect()
curry.reset()
curry.path.insert(0, %(tmpdir)r)
curry._interpreter_.load(%(sofile)r)
print('adopted')
M = curry.import_(%(name)r)
print(next(curry.eval((M.total)(4))))
print('exiting normally')
'''
QUICKSTART = r'''
import os, subprocess
import cytest, curry
os.chdir(%(tmpdir)r)
curry.path.insert(0, '.')
M = curry.import_(%(name)r)
curry._interpreter_.save(M, %(name)r + '.cpp', module_main=False)
# The import started a compile of the module in the background, which
# writes the products sprite-make --so writes.  The two compiles never
# write at once: the lock of the products (toolchain._productlock) makes
# the second wait, and it compiles nothing when the first wrote a current
# object.  So sprite-make runs here while the background compile may run,
# as a session at the keyboard may run it.
subprocess.run(
    [%(make)r, '--so', %(name)r + '.curry'], check=True
  , env=dict(os.environ, CURRYPATH='.'), capture_output=True, text=True
  )
try:
  M2 = curry._interpreter_.load(os.path.join('.curry', %(subdir)r, %(name)r + curry.config.module_object_suffix()))
except ValueError as exc:
  assert str(exc) == 'the products of module %%s changed since it was loaded; reload it' %% %(name)r, str(exc)
  M2 = M
print(M2 is M)
print(next(curry.eval((M.bump)(1))))
print('exiting normally')
'''


class TestLoadDuringCompile(TieredTestCase):
  '''
  curry.load of the object of a module while its background compile runs,
  and of the object of a module that stays interpreted (issue #109).  The
  object binds to the live tables of the interpreted module at its load,
  so a load that dropped the object (the import returned the module of the
  import, and nothing kept the library) left the tables pointing into
  unmapped memory: the process ended at the next use of the module, or at
  its exit in Module::clear.  The loader waits for the compile and loads
  the object the compile wrote, or adopts a foreground object through the
  same swap when no compile is pending.
  '''
  def compile_by_hand(self, name):
    '''
    Compiles a module with sprite-make, as the Quickstart does.  Returns
    the object.
    '''
    env = dict(os.environ)
    env['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx,interpret:new,jit:hot,jit_backend:cxx'
    env['CURRYPATH'] = self.tmpdir
    cmd = cytest.limit_prefix(ADDRESS_SPACE, TIMEOUT) + [
        config.installed_path('bin', 'sprite-make'), '--so', name
      ]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertTrue(os.path.isfile(self.sofile(name)))
    return self.sofile(name)

  @cytest.hardreset
  def test_mapped_name_decline_loads_edited_image(self):
    from curry.backends.cxx import image
    text = 'module %%(name)s where\nanswer :: Int\nanswer = %d\n'
    name = self.write_module(text % 1)
    self.switch('off')
    first = self.import_module(name)
    self.assertEqual(self.py(first.answer), 1)
    self.edit_module(name, text % 2)
    self.compile_by_hand(name)
    error = 'the object is mapped under this name in this process; use a new process'
    with mock.patch.object(curryrt, 'tiered_adopt',
                           return_value={'ok': False, 'error': error}) as adopt, \
         mock.patch.object(image, 'current', return_value=None), \
         capture_log('curry.backends.cxx.tiered') as log:
      for _ in range(2):
        self.switch('new')
        second = self.import_module(name)
        self.assertTrue(curryrt.icurry_is_interpreted(second.answer.info))
        self.assertEqual(self.py(second.answer), 2)
      self.assertEqual(adopt.call_count, 2)
      self.assertEqual(len(log.data[logging.WARNING]), 1)
      self.assertIn('was not adopted', log.data[logging.WARNING][0])
      self.assertIn(error, log.data[logging.WARNING][0])
      self.switch('off')
      with self.assertRaisesRegex(curry.LoadError, 'the object is mapped'):
        self.import_module(name)

  def test_mapped_name_poll_reports_adoption_decline_once(self):
    name = self.write_module()
    error = 'the object is mapped under this name in this process'
    result = dict(registry_id=cytest.raw.interp()._its.registry_id,
                  module=name, ok=False, error=error, output='', mapped=[])
    with mock.patch.object(curryrt, 'tiered_poll'), \
         mock.patch.object(curryrt, 'tiered_results', return_value=[result]), \
         capture_log('curry.backends.cxx.tiered') as log:
      tiered.poll()
      tiered.poll()
    self.assertEqual(len(log.data[logging.WARNING]), 1)
    self.assertIn('was not adopted', log.data[logging.WARNING][0])
    self.assertIn('not applied', str(log.data[logging.INFO]))
    self.assertNotIn('compile failed', str(log.data))

  def make_stale(self, name):
    '''Changes source content, so its compiled receipt is stale.'''
    source = os.path.join(self.tmpdir, name + '.curry')
    with open(source, 'a') as stream:
      stream.write('\n-- invalidate the compiled source receipt\n')

  def run_child(self, code):
    with binding(
        os.environ, 'SPRITE_INTERPRETER_FLAGS', 'backend:cxx,interpret:new,jit:hot,jit_backend:cxx'
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
    self.assertTrue(curryrt.icurry_is_interpreted(M.area.info))
    before = tiered.status()
    with mock.patch('curry.backends.cxx.loader.WAIT_NOTICE_SECONDS', COMPILE_SECONDS), \
         capture_log('curry.backends.cxx.loader', 'curry.backends.cxx.tiered') as log:
      M2 = curry._interpreter_.load(self.sofile(name))
    self.assertIs(M2, M)
    self.assertFalse(tiered.pending(name))
    after = tiered.status()
    self.assertEqual(after['swapped_modules'], before['swapped_modules'] + 1)
    self.assertEqual(after['failed_modules'], before['failed_modules'])
    self.assertFalse(curryrt.icurry_is_interpreted(M.area.info))
    self.assertNotEqual(
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
    self.assertFalse(curryrt.icurry_is_interpreted(M.area.info))
    self.assertIsNotNone(curryrt.SharedCurryModule.find_sofilename(name))
    M = None
    self.switch('cxx')
    self.make_stale(name)
    M = self.import_module(name)
    self.assertTrue(tiered.pending(name))
    self.assertTrue(curryrt.icurry_is_interpreted(M.area.info))
    with mock.patch('curry.backends.cxx.loader.WAIT_NOTICE_SECONDS', COMPILE_SECONDS), \
         capture_log('curry.backends.cxx.loader', 'curry.backends.cxx.tiered') as log:
      M2 = curry._interpreter_.load(self.sofile(name))
    self.assertIs(M2, M)
    self.assertFalse(tiered.pending(name))
    self.assertFalse(curryrt.icurry_is_interpreted(M.area.info))
    self.assertTrue(
        any('Waiting for the background compile of module %s' % name in line
            for line in log.data[logging.INFO])
      , log.data[logging.INFO]
      )
    self.assertEqual(log.data[logging.WARNING], [])
    self.assertEqual(self.py(M.total, 2), 8)

  def test_reset_then_load_adopts_the_object(self):
    name = self.write_module()
    self.compile_by_hand(name)
    self.make_stale(name)
    proc = self.run_child(RESET_LOAD % dict(
        tmpdir=self.tmpdir, name=name, sofile=self.sofile(name)
      ))
    self.assertEqual(
        proc.stdout.splitlines(), ['True', 'adopted', '40', 'exiting normally']
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
    # The foreground sprite-make runs while the background compile may run
    # (the lock of the products; the test of the lock itself is
    # TestProductLock of unit_make.py).
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
  def test_interpreted_module_adopts_its_object(self):
    # No background compiler: a foreground load must retain the object and
    # swap the live tables, just as a finished background compile does.
    with mock.patch.object(tiered, 'submit', return_value=False):
      M = self.fresh_module()
    name = M.__name__
    self.assertTrue(curryrt.icurry_is_interpreted(M.area.info))
    self.assertFalse(tiered.pending(name))
    self.assertTrue(tiered.has_binding(name))
    sofile = self.compile_by_hand(name)
    loaded = curry._interpreter_.load(sofile)
    self.assertIs(loaded, M)
    self.assertIsNotNone(curryrt.SharedCurryModule.find_sofilename(name))
    self.assertFalse(curryrt.icurry_is_interpreted(M.area.info))
    self.assertEqual(self.py(M.total, 2), 8)

  @cytest.hardreset
  def test_changed_shape_swaps_after_a_reset(self):
    # The first incarnation is swapped to compiled code; the source then
    # changes the arity of a function, so the second incarnation, after a
    # reset, gets private tables for every symbol. The
    # object of the second compile binds to the tables of the second
    # incarnation, whatever their addresses, so the module swaps with no
    # warning.  (The shim of the tiered mode of before named the old
    # addresses, and the module stayed interpreted with a warning.)
    text = (
        'module %%(name)s where\n\nf :: %s\nf %s = %s\n\n'
        'g :: Int\ng = 7\n\nmain :: Int\nmain = %s\n'
      )
    name = self.write_module(text % ('Int', '', '1', 'f + g'))
    first = self.import_module(name)
    self.assertEqual(self.py(first.main), 8)
    self.wait()
    self.assertFalse(curryrt.icurry_is_interpreted(first.f.info))
    f_address, g_address = first.f.info.address, first.g.info.address
    self.edit_module(name, text % ('Int -> Int', 'x', 'x + 1', 'f g'))
    first = None
    curry.reset()
    curry.path.insert(0, self.tmpdir)
    with capture_log('curry.backends.cxx.tiered') as log:
      second = self.import_module(name)
      self.assertTrue(curryrt.icurry_is_interpreted(second.f.info))
      self.assertNotEqual(second.f.info.address, f_address)
      self.assertNotEqual(second.g.info.address, g_address)
      self.assertEqual(self.py(second.main), 8)
      self.wait()
    self.assertEqual(log.data[logging.WARNING], [])
    self.assertFalse(curryrt.icurry_is_interpreted(second.f.info))
    self.assertFalse(curryrt.icurry_is_interpreted(second.g.info))
    self.assertEqual(self.py(second.main), 8)

  def test_import_after_reset_takes_the_object(self):
    # After a reset the kept tables have no registered library.  The import
    # plan adopts the current object through the same swap as a user load.
    with mock.patch.object(tiered, 'submit', return_value=False):
      M = self.fresh_module()
    name = M.__name__
    self.assertTrue(curryrt.icurry_is_interpreted(M.area.info))
    sofile = self.compile_by_hand(name)
    del M
    curry.reset()
    curry.path.insert(0, self.tmpdir)
    M2 = curry.import_(name)
    self.assertEqual(
        os.path.realpath(curryrt.SharedCurryModule.find_sofilename(name))
      , os.path.realpath(sofile)
      )
    self.assertEqual(self.py(M2.total, 2), 8)


# A module without a function and without a table: a type synonym alone
# (a data type derives its Data instance, which is a function).  Nothing
# to swap, so its load queues no compile (submit) and records no binding,
# while its importers name its object by SONAME.
TYPES_MODULE = '''
module %(name)s where

type Pair = (Int, Int)
'''

# A module that imports TYPES_MODULE.
USER_MODULE = '''
module %%(name)s where
import %(types)s

mk :: Int -> Pair
mk n = (n, n + 1)

second :: Pair -> Int
second p = case p of
  (_, b) -> b
'''

# A module that imports MODULE.
IMPORTER_MODULE = '''
module %%(name)s where
import %(first)s

biggest :: Int -> Int
biggest n = foldr max 0 (map area (shapes n))
'''


class TestImportObjects(TieredTestCase):
  '''
  The swap maps the objects of the imports of a module before its own ("The
  imports" in tiered.py and tiered.hpp).  An object names the objects of
  its imports by SONAME, which the dynamic linker satisfies with an object
  of that name the process has mapped; an importer whose import had no job
  (a module without a function to swap) or whose import compiled later
  stayed interpreted, with the message of the dynamic linker in its log.
  '''
  @cytest.hardreset
  def test_import_without_a_job(self):
    types = self.write_module(TYPES_MODULE)
    user = self.write_module(USER_MODULE % {'types': types})
    with capture_log('curry.backends.cxx.tiered') as log:
      U = self.import_module(user)
      T = curry.import_(types)
      needs_types = types in getHandle(U).icurry.imports
      # The import has neither a binding nor a job; the child of the
      # importer compiles its object.
      self.assertFalse(tiered.has_binding(types))
      self.assertFalse(tiered.pending(types))
      self.assertIsNone(getHandle(T).sofilename)
      self.assertTrue(tiered.pending(user))
      self.assertTrue(curryrt.icurry_is_interpreted(U.mk.info))
      before = tiered.status()
      self.assertEqual(self.py(U.second, self.value(U.mk, 4)), 5)
      self.wait()
    after = tiered.status()
    self.assertEqual(after['swapped_modules'], before['swapped_modules'] + 1)
    self.assertEqual(after['failed_modules'], before['failed_modules'])
    self.assertEqual(log.data[logging.WARNING], [])
    self.assertEqual(
        any('Mapped the object of %s' % types in line
            for line in log.data[logging.INFO])
      , needs_types, log.data[logging.INFO]
      )
    self.assertFalse(curryrt.icurry_is_interpreted(U.mk.info))
    self.assertFalse(curryrt.icurry_is_interpreted(U.second.info))
    # The import has its object on record now.
    self.assertEqual(getHandle(T).sofilename is not None, needs_types)
    self.assertEqual(self.py(U.second, self.value(U.mk, 4)), 5)
    self.assertEqual(self.py(U.second, self.value(U.mk, 7)), 8)

  @cytest.hardreset
  def test_import_mapped_before_a_failed_load(self):
    # The swap maps the object of the import before it loads the object of
    # the importer.  When that load fails (the private object is cut short
    # here after the child wrote it, before the swap publishes and opens
    # it), the importer stays interpreted and the
    # import runs compiled all the same: poll refreshes its record whatever
    # came of the importer.  Before, the record of the import was refreshed
    # only after a swap of the importer, and a later load of another
    # importer of the import refused it.
    types = self.write_module(TYPES_MODULE)
    user = self.write_module(USER_MODULE % {'types': types})
    with capture_log('curry.backends.cxx.tiered') as log:
      U = self.import_module(user)
      T = curry.import_(types)
      needs_types = types in getHandle(U).icurry.imports
      self.assertTrue(tiered.pending(user))
      self.assertIsNone(getHandle(T).sofilename)
      before = tiered.status()
      # The child ends; its result waits for the poll.
      self.assertTrue(
          curryrt.tiered_wait(COMPILE_SECONDS)
        , 'the background compile did not end in %s s' % COMPILE_SECONDS
        )
      private = tiered._state.records[tiered._key(cytest.raw.interp(), user)].sofile
      self.assertTrue(os.path.isfile(private))
      self.assertFalse(os.path.exists(self.sofile(user)))
      with open(private, 'wb') as stream:
        stream.write(b'not an object\n')
      tiered.poll(cytest.raw.interp())
    after = tiered.status()
    self.assertEqual(after['failed_modules'], before['failed_modules'] + 1)
    self.assertEqual(after['swapped_modules'], before['swapped_modules'])
    self.assertTrue(
        any('cannot load the object' in line
            for line in log.data[logging.WARNING])
      , log.data[logging.WARNING]
      )
    self.assertEqual(
        any('Mapped the object of %s' % types in line
            for line in log.data[logging.INFO])
      , needs_types, log.data[logging.INFO]
      )
    self.assertTrue(curryrt.icurry_is_interpreted(U.mk.info))
    self.assertEqual(getHandle(T).sofilename is not None, needs_types)
    self.assertEqual(self.py(U.second, self.value(U.mk, 4)), 5)

  @cytest.hardreset
  @cytest.linux_only(
      'the object of an import is a needed library of the object on ELF, '
      'which the dynamic linker refuses to load without it; on macOS the '
      'import is a weak library, and the swap proceeds'
    )
  def test_swap_without_the_imports_fails(self):
    # The control: a job without the objects of its imports fails as every
    # such swap did before they were mapped, with the message of the
    # dynamic linker, and the importer stays interpreted.
    types = self.write_module(TYPES_MODULE)
    user = self.write_module(USER_MODULE % {'types': types})
    with mock.patch.object(tiered, '_import_objects', return_value=[]):
      with capture_log('curry.backends.cxx.tiered') as log:
        U = self.import_module(user)
        needs_types = types in getHandle(U).icurry.imports
        before = tiered.status()
        self.wait()
    after = tiered.status()
    # Expanded synonyms no longer create an object dependency in 3.1.0.
    self.assertEqual(after['failed_modules'], before['failed_modules'] + needs_types)
    self.assertEqual(after['swapped_modules'], before['swapped_modules'] + (not needs_types))
    self.assertEqual(curryrt.icurry_is_interpreted(U.mk.info), needs_types)
    self.assertEqual(
        any('cannot open shared object file' in line
            for line in log.data[logging.WARNING])
      , needs_types, log.data[logging.WARNING]
      )
    self.assertEqual(self.py(U.second, self.value(U.mk, 4)), 5)

  @cytest.hardreset
  def test_import_compiled_later(self):
    # The job of the import runs after the job of its importer.  The child
    # of the importer compiles the import as a dependency, so both objects
    # are ready when the importer swaps: the swap maps the object of the
    # import first, and the job of the import then adopts the mapped
    # object.  The jobs are queued by hand in that order: the loads queue
    # nothing (tiered_submit is stubbed) and record the modules.
    first = self.write_module()
    second = self.write_module(IMPORTER_MODULE % {'first': first})
    with mock.patch.object(curryrt, 'tiered_submit'):
      N = self.import_module(second)
      M = curry.import_(first)
    tiered.cancel()
    self.assertFalse(tiered.pending(first))
    self.assertFalse(tiered.pending(second))
    self.assertTrue(curryrt.icurry_is_interpreted(N.biggest.info))
    self.assertTrue(curryrt.icurry_is_interpreted(M.area.info))
    interp = cytest.raw.interp()
    before = tiered.status()
    with capture_log('curry.backends.cxx.tiered') as log:
      self.assertTrue(tiered.submit(interp, N, curry.path))
      self.assertTrue(tiered.submit(interp, M, curry.path))
      self.wait()
    after = tiered.status()
    self.assertEqual(after['swapped_modules'], before['swapped_modules'] + 2)
    self.assertEqual(after['failed_modules'], before['failed_modules'])
    self.assertEqual(log.data[logging.WARNING], [])
    self.assertTrue(
        any('Mapped the object of %s' % first in line
            for line in log.data[logging.INFO])
      , log.data[logging.INFO]
      )
    self.assertFalse(curryrt.icurry_is_interpreted(N.biggest.info))
    self.assertFalse(curryrt.icurry_is_interpreted(M.area.info))
    self.assertIsNotNone(getHandle(M).sofilename)
    self.assertIsNotNone(getHandle(N).sofilename)
    self.assertEqual(self.py(N.biggest, 4), 20)
    self.assertEqual(self.py(M.total, 4), 40)
