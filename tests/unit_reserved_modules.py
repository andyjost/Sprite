"""Module names follow the Curry path except for runtime implementations."""
import cytest # from ./lib; must be first
import curry
from curry import config
from curry.backends.cxx import curryrtbindings
from curry.objects import handle
from curry.toolchain import _curry2icurry, _filenames
import hashlib
import re
from pathlib import Path
import shutil
import tempfile


def products(source):
  directory = source.parent / '.curry'
  return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in directory.rglob('*') if p.is_file()}


def installed(name):
  return Path(config.installed_path('curry', 'lib', name.replace('.', '/') + '.curry'))


class TestReservedModules(cytest.TestCase):
  @cytest.posix_only('Windows cannot replace or restore a mapped DLL')
  def test_saved_dependency_object_changed(self):
    self._saved_dependency_object_changed(False)

  @cytest.posix_only('Windows cannot replace or restore a mapped DLL')
  def test_saved_adopted_dependency_object_changed(self):
    self._saved_dependency_object_changed(True)

  def test_saved_dependency_stamp_changed(self):
    # Windows replaces the unmapped ABI stamp instead of the loaded DLL.
    self._saved_dependency_object_changed(False, stamp=True)

  def test_saved_adopted_dependency_stamp_changed(self):
    # The adopted object's ABI stamp is also an unmapped link input.
    self._saved_dependency_object_changed(True, stamp=True)

  def _saved_dependency_object_changed(self, background, stamp=False):
    with tempfile.TemporaryDirectory() as work:
      root = Path(work)
      for number in (1, 2):
        directory = root / str(number)
        directory.mkdir()
        (directory / 'Leaf.curry').write_text(
            'module Leaf where\nf :: Int -> Int\nf x = x + %d\n' % number)
        (directory / 'Probe.curry').write_text(
            'module Probe where\nimport Leaf\ngoal :: Int\ngoal = f 1\n')
        if number == 2 or not background:
          code = "import curry; curry.reset(interpret='off', jit='off', inline_budget=0); curry.path.insert(0, %r); curry.import_('Probe')" % str(directory)
          child = cytest.run_in_subprocess(code, timeout=180, address_space=3 << 30)
          self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
      code = r"""
import curry, os, shutil, subprocess, sys
from pathlib import Path
from curry.backends.cxx import tiered, toolchain, curryrtbindings as curryrt
from curry.objects.handle import getHandle
from curry.toolchain import _findcurry
root = Path(%r)
curry.reset(interpret='new', jit='off', inline_budget=0)
curry.path.insert(0, str(root / '1'))
leaf = curry.import_('Leaf')
probe = curry.import_('Probe')
background = %r
if background:
    curry._interpreter_.flags['jit_backend'] = 'cxx'
    curry._interpreter_.flags['jit'] = 'hot'
    from unittest import mock
    with mock.patch.object(curryrt, 'cxx_arm', side_effect=curryrt.tiered_submit):
        assert tiered.submit(curry._interpreter_, leaf, curry.path)
    assert tiered.wait(120, interp=curry._interpreter_)
    curry._interpreter_.flags['jit'] = 'off'
    assert getHandle(leaf).sofilename
obj = Path(getHandle(leaf).sofilename)
stamp = %r
product = Path(str(obj) + '.abi') if stamp else obj
replacement = next((root / '2').rglob('Leaf' + obj.suffix))
original = product.read_bytes()
try:
    temporary = product.with_name(product.name + '.replacement')
    if stamp:
        temporary.write_bytes(original + b'\n')
    else:
        shutil.copyfile(replacement, temporary)
    os.replace(temporary, product)
    message = 'the products of module Leaf changed since it was loaded; reload it'
    step = toolchain.Cpp2So(curry._interpreter_)
    # Save and loaded-object lookup read the object directly. The stamp
    # subcase checks readers that consume the stamp as a link input.
    readers = [('stamp freshness', lambda: step.stamp_is_current(str(obj))),
               ('private copy', lambda: tiered._private_copy(getHandle(probe).icurry))]
    if stamp:
        readers.append(('stamp records', lambda: step._read_stamp_records(str(obj))))
    else:
        readers.extend([
            ('save', lambda: curry.save(probe, root / 'Probe.so')),
            ('object lookup', lambda: step._object_on_disk('Leaf', curry.path))])
    for name, read in readers:
        try:
            with _findcurry.resolving(curry._interpreter_):
                read()
        except ValueError as exc:
            assert str(exc) == message, str(exc)
        else:
            raise AssertionError(name + ': changed link input accepted')
    if not stamp:
        # A reset admits a complete replacement generation. The isolated
        # object copy in the first tree still has the old content receipt.
        curry.reset(interpret='new', jit='off', inline_budget=0)
        curry.path.insert(0, str(root / '2'))
        probe = curry.import_('Probe')
        curry.save(probe, root / 'Probe.so')
        run = "import curry; curry.reset(interpret='new', jit='off', inline_budget=0); curry.path.insert(0, %%r); module = curry.load(%%r); print(curry.eval(module.goal).one())" %% (str(root / '2'), str(root / 'Probe.so'))
        result = subprocess.run([sys.executable, '-c', run], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == '3', result.stdout
finally:
    try:
        temporary = product.with_name(product.name + '.restore')
        temporary.write_bytes(original)
        os.replace(temporary, product)
        if stamp:
            # Check before finish removes an adopted object's private files.
            assert step.stamp_is_current(str(obj))
            curry.save(probe, root / 'Probe.so')
    finally:
        tiered.finish()
""" % (work, background, stamp)
      child = cytest.run_in_subprocess(code, timeout=240, address_space=3 << 30)
      self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_loaded_product_readers(self):
    with tempfile.TemporaryDirectory() as work:
      code = r"""
import curry, os, subprocess, sys
from pathlib import Path
from curry.backends.cxx import toolchain, image, loader
from curry.toolchain import _findcurry, _productcache, plans
from curry.objects.handle import getHandle
root = Path(%r)
source = root / 'Leaf.curry'
source.write_text('module Leaf where\nf :: Int -> Int\nf x = x + 1\n')
child = subprocess.run([sys.executable, '-c',
    "import curry; curry.reset(interpret='off', jit='off'); curry.import_(%%r)" %% str(source)],
    capture_output=True, text=True, timeout=120)
assert child.returncode == 0, child.stdout + child.stderr
curry.reset(interpret='new', jit='off')
leaf = curry.import_(source)
generation = getHandle(leaf).icurry._loaded_generation
obj = Path(getHandle(leaf).sofilename)
cpp = obj.with_suffix('.cpp')
stamp = Path(str(obj) + '.abi')
step = toolchain.Cpp2So(curry._interpreter_)
message = 'the products of module Leaf changed since it was loaded; reload it'
plan = plans.makeplan(curry._interpreter_, plans.MAKE_ALL)
checks = [(cpp, [lambda: step._moduleName(str(cpp)),
                 lambda: step._importedModules(str(cpp)),
                 lambda: toolchain.format_version(str(cpp)),
                 lambda: toolchain.source_interfaces(str(cpp)),
                 lambda: toolchain.source_record(str(cpp)),
                 lambda: curry.inspect.getimpl(leaf.f)]),
          (stamp, [lambda: step._read_stamp_records(str(obj)),
                   lambda: step.read_stamp(str(obj)),
                   lambda: step.read_import_stamp(str(obj)),
                   lambda: _findcurry.currentfile(plan, str(source), curry.path, is_sourcefile=True),
                   lambda: _productcache.store('test', 'stamp', [str(stamp)], str(root / 'cache'))]),
          (Path(generation.image), [lambda: image.read(generation.image),
              lambda: image.ensure(curry._interpreter_, str(source))])]
# Windows replaces generated C++ for inspection and the ABI stamp for
# link inputs above; a mapped DLL cannot be replaced or restored.
if sys.platform != 'win32':
    checks.append((obj, [lambda: loader.needed_modules(str(obj)),
                        lambda: _findcurry.currentfile(plan, str(source), curry.path, is_sourcefile=True),
                        lambda: _productcache.store('test', 'key', [str(obj)], str(root / 'cache'))]))
for path, readers in checks:
    original = path.read_bytes()
    try:
        temporary = path.with_name(path.name + '.replacement')
        temporary.write_bytes(original + b'\n')
        os.replace(temporary, path)
        for read in readers:
            with _findcurry.resolving(curry._interpreter_):
                try:
                    read()
                except ValueError as exc:
                    assert str(exc) == message, str(exc)
                else:
                    raise AssertionError('changed product accepted: ' + str(path.suffix))
    finally:
        temporary = path.with_name(path.name + '.restore')
        temporary.write_bytes(original)
        os.replace(temporary, path)
# Cached objects may be hard links to the mapped file. Windows replaces
# only the cached ABI stamp; POSIX also retains the cached-object case.
with _findcurry.resolving(curry._interpreter_):
    for product in ((stamp,) if sys.platform == 'win32' else (obj, stamp)):
        cache = root / 'cache'
        key = 'restore' + product.suffix
        entry = Path(_productcache.store('test', key, [str(product)], str(cache)))
        cached = entry / product.name
        original = cached.read_bytes()
        before = product.read_bytes()
        try:
            temporary = cached.with_name(cached.name + '.replacement')
            temporary.write_bytes(original + b'\n')
            os.replace(temporary, cached)
            try:
                _productcache.restore('test', key, str(product.parent), [product.name], str(cache))
            except ValueError as exc:
                assert str(exc) == message, str(exc)
            else:
                raise AssertionError('changed cached product accepted')
            assert product.read_bytes() == before
        finally:
            temporary = cached.with_name(cached.name + '.restore')
            temporary.write_bytes(original)
            os.replace(temporary, cached)
""" % work
      child = cytest.run_in_subprocess(code, timeout=240, address_space=3 << 30)
      self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_loaded_in_place_edit(self):
    for mode in ('new', 'all'):
      for generalized in (False, True):
        with self.subTest(mode=mode, generalized=generalized), tempfile.TemporaryDirectory() as work:
          source = Path(work) / 'Data/Char.curry'
          source.parent.mkdir()
          original = installed('Data.Char').read_text()
          source.write_text(original)
          edited = original.replace("ord c - ord '0'", "ord c - ord '0' + 1")
          if generalized:
            edited = original.replace('digitToInt      :: Char -> Int',
                'digitToInt      :: Num a => Char -> a')
            edited = re.sub(r"=  (ord c - ord '[0Aa]'(?: \+ 10)?)", r'=  fromInt (\1)', edited)
          code = r"""
import curry, os, warnings
from pathlib import Path
from curry import cache
from curry.toolchain import _findcurry, _productcache
curry.reset(interpret=%r, jit='off')
curry.path.insert(0, %r)
source = Path(%r)
module = curry.import_(source)
probe = source.parent.parent / 'Probe.curry'
probe.write_text("module Probe where\nimport Data.Char\ngoal :: Int\ngoal = digitToInt '1'\n")
with _findcurry.resolving(curry._interpreter_):
    before = [f(str(probe), curry.path)['Data.Char'].digest
              for f in (cache.import_closure, _productcache.import_closure)]
source.write_text(%r)
os.utime(source, None)
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always')
    assert curry.import_(source) is module
assert any('changed after the import' in str(w.message) for w in caught)
with _findcurry.resolving(curry._interpreter_):
    after = [f(str(probe), curry.path)['Data.Char'].digest
             for f in (cache.import_closure, _productcache.import_closure)]
assert before == after, (before, after)
assert list(curry.eval(curry.import_(probe).goal)) == [1]
if %r == 'new':
    curry.reload(module)
else:
    curry.reset(interpret='all', jit='off')
nextprobe = probe.with_name('ProbeAfter.curry')
nextprobe.write_text(probe.read_text().replace('module Probe ', 'module ProbeAfter '))
assert list(curry.eval(curry.import_(nextprobe).goal)) == [%d]
""" % (mode, work, str(source), edited, mode, 1 if generalized else 2)
          child = cytest.run_in_subprocess(code, timeout=120, address_space=3 << 30)
          self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
          fresh = "import curry; curry.reset(interpret=%r, jit='off'); curry.path.insert(0, %r); assert list(curry.eval(curry.import_('Probe').goal)) == [%d]" % (mode, work, 1 if generalized else 2)
          child = cytest.run_in_subprocess(fresh, timeout=120, address_space=3 << 30)
          self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_source_free_object_keeps_generated_code(self):
    with tempfile.TemporaryDirectory() as work:
      code = r"""
import curry
import shutil
from pathlib import Path
from curry.backends.cxx import toolchain
source = Path(%r) / 'Frozen.curry'
source.write_text('module Frozen where\nf :: Int -> Int\nf x = x + 1\n')
module = curry.import_(source)
cpp = Path(curry.inspect.geticurryfile(module)).with_suffix('.cpp')
curry._interpreter_.save(module, str(cpp), module_main=False, interfaces=True)
obj = toolchain.Cpp2So(curry._interpreter_)(str(cpp), curry.path)
shutil.copyfile(cpp, source.with_suffix('.cpp'))
shutil.copyfile(obj, source.with_suffix('.so'))
""" % work
      child = cytest.run_in_subprocess(code, timeout=120, address_space=3 << 30)
      self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
      code = r"""
import curry
from pathlib import Path
from curry.objects.handle import getHandle
root = Path(%r)
module = curry.load(root / 'Frozen.so')
assert getHandle(module).icurry.filename is None
before = curry.inspect.getimpl(module.f)
cpp = root / 'Frozen.cpp'
original = cpp.read_bytes()
try:
    cpp.write_text('// replaced after the load\n')
    try:
        curry.inspect.getimpl(module.f)
    except ValueError as exc:
        assert str(exc) == 'the products of module Frozen changed since it was loaded; reload it', str(exc)
    else:
        raise AssertionError('changed generated code accepted')
    assert list(curry.eval(module.f(1))) == [2]
finally:
    cpp.write_bytes(original)
""" % work
      child = cytest.run_in_subprocess(code, timeout=120, address_space=3 << 30)
      self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_import_has_no_snapshot_files(self):
    self._import_and_finish(True)

  def test_loaded_module_survives_finish(self):
    self._import_and_finish(False)

  def _import_and_finish(self, check_files):
    with tempfile.TemporaryDirectory() as work:
      code = r"""
import curry, tempfile, subprocess, sys
from pathlib import Path
from curry.backends.cxx import tiered
from curry import __main__
curry.reset(interpret='all', jit='off')
root = Path(%r)
curry.path.insert(0, str(root))
(root / 'Leaf.curry').write_text('module Leaf where\nf :: Int -> Int\nf x = x + 1\n')
(root / 'Probe.curry').write_text('module Probe where\nimport Leaf\ngoal = f 1\n')
child = subprocess.run([sys.executable, '-c',
    "import curry; curry.reset(interpret='all', jit='off'); curry.path.insert(0, %%r); curry.import_('Data.List'); curry.import_('Probe')" %% str(root)],
    capture_output=True, text=True, timeout=90)
assert child.returncode == 0, child.stdout + child.stderr
from unittest import mock
with mock.patch.object(tempfile, 'mkdtemp', wraps=tempfile.mkdtemp) as created:
    leaf = curry.import_('Leaf')
    curry.import_('Data.List')
    probe = curry.import_('Probe')
if %r:
    assert tiered._state.tmpdir is None, tiered._state.tmpdir
    assert created.call_count == 0, created.mock_calls
assert list(curry.eval(probe.goal)) == [2]
tiered.finish()
(root / 'Other.curry').write_text('module Other where\nmain = putStrLn "ok"\n')
__main__.main('sprite', ['--stats', str(root / 'Other.curry')])
curry._interpreter_.sigtable.clear()
assert leaf.f.signature == 'Int -> Int'
(root / 'Fresh.curry').write_text('module Fresh where\nimport Leaf\ngoal = f 2\n')
assert list(curry.eval(curry.import_('Fresh').goal)) == [3]
""" % (work, check_files)
      child = cytest.run_in_subprocess(code, timeout=180, address_space=3 << 30)
      self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_changed_icurry_refused(self):
    with tempfile.TemporaryDirectory() as work:
      code = r"""
import curry, subprocess, sys
from pathlib import Path
from curry.backends.cxx import tiered
from curry.objects.handle import getHandle
from curry.interpreter.loadsave import compilable_icurry
curry.reset(interpret='all', jit='off')
root = Path(%r)
curry.path.insert(0, str(root))
source = root / 'Leaf.curry'
source.write_text('module Leaf where\nf :: Int -> Int\nf x = x + 1\n')
leaf = curry.import_('Leaf')
(root / 'Probe.curry').write_text('module Probe where\nimport Leaf\ngoal = f 1\n')
probe = curry.import_('Probe')
source.write_text('module Leaf where\nf :: Int -> Int\nf x = x + 2\n')
child = subprocess.run([sys.executable, '-c',
    "import curry; curry.reset(interpret='all', jit='off'); curry.path.insert(0, %%r); curry.import_('Leaf')" %% str(root)],
    capture_output=True, text=True, timeout=90)
assert child.returncode == 0, child.stdout + child.stderr
message = 'the products of module Leaf changed since it was loaded; reload it'
for read in (lambda: curry.inspect.geticurryfile(leaf),
             lambda: curry.inspect.geticurry(leaf),
             lambda: compilable_icurry(curry._interpreter_, leaf, getHandle(leaf).icurry)):
    try:
        read()
    except ValueError as exc:
        assert str(exc) == message, str(exc)
    else:
        raise AssertionError('changed ICurry accepted')
import logging
messages = []
class Capture(logging.Handler):
    def emit(self, record):
        messages.append(record.getMessage())
logger = logging.getLogger('curry.backends.cxx.tiered')
handler = Capture()
logger.addHandler(handler)
logger.setLevel(logging.INFO)
try:
    curry._interpreter_.flags['jit_backend'] = 'cxx'
    curry._interpreter_.flags['jit'] = 'hot'
    assert not tiered.submit(curry._interpreter_, probe, None)
    curry._interpreter_.flags['jit'] = 'off'
finally:
    logger.removeHandler(handler)
assert sum(message in line for line in messages) == 1, messages
assert list(curry.eval(probe.goal)) == [2]
""" % work
      child = cytest.run_in_subprocess(code, timeout=180, address_space=3 << 30)
      self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_source_free_import_fingerprint(self):
    with tempfile.TemporaryDirectory() as work:
      root = Path(work)
      for answer in (1, 2):
        directory = root / str(answer)
        directory.mkdir()
        code = r"""
import curry
from pathlib import Path
curry.reset(interpret='all', jit='off')
root = Path(%r)
source = root / 'Leaf.curry'
source.write_text('module Leaf where\nanswer :: Int\nanswer = %%d\n' %% %d)
leaf = curry.import_(source)
curry.save(leaf, root / 'Leaf.so')
""" % (str(directory), answer)
        child = cytest.run_in_subprocess(code, timeout=180, address_space=3 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
      (root / 'Probe.curry').write_text(
          'module Probe where\nimport Leaf\ngoal :: (Int,Int)\ngoal = (answer,answer)\n')
      for mode in ('new', 'all'):
        for answer in (1, 2):
          code = r"""
import curry
from pathlib import Path
curry.reset(interpret='new', jit='off')
root = Path(%r)
curry.load(root / str(%d) / 'Leaf.so')
curry._interpreter_.flags['interpret'] = %r
curry.path.insert(0, str(root))
assert curry.show(curry.eval(curry.import_('Probe').goal).one()) == %r
""" % (work, answer, mode, '(%d,%d)' % (answer, answer))
          child = cytest.run_in_subprocess(code, timeout=180, address_space=3 << 30)
          self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_loaded_optimizer_generation(self):
    self._loaded_optimizer_or_signature(False)

  def test_loaded_lazy_signature_generation(self):
    self._loaded_optimizer_or_signature(True)

  def _loaded_optimizer_or_signature(self, typed):
    for mode in ('new', 'all'):
      with self.subTest(mode=mode, typed=typed), tempfile.TemporaryDirectory() as work:
        source = Path(work) / 'Leaf.curry'
        old = ('f :: Int -> Int\nf x = x\n' if typed else
               'answer :: Int\nanswer = 1\n')
        new = ('f :: Bool -> Bool\nf x = x\n' if typed else
               'answer :: Int\nanswer = 2\n')
        source.write_text('module Leaf where\n' + old)
        code = r"""
import curry, subprocess, sys
from pathlib import Path
curry.reset(interpret=%r, jit='off')
curry.path.insert(0, %r)
source = Path(%r)
leaf = curry.import_('Leaf')
from curry.objects.handle import getHandle
import json
for name in ('Prelude', 'Leaf'):
    raw = getHandle(curry.modules[name]).icurry
    generation = raw._loaded_generation
    seen = set()
    def size(value):
        if id(value) in seen:
            return 0
        seen.add(id(value))
        total = sys.getsizeof(value)
        if isinstance(value, dict):
            return total + sum(size(k) + size(v) for k, v in value.items())
        if isinstance(value, (tuple, list)):
            return total + sum(size(v) for v in value)
        return total
    # Import generations are shared references, not recursively owned copies.
    seen.update(id(dep) for _, dep in generation.imports if dep is not None)
    memory = size(generation) + size(vars(generation.source_info))
    print('generation bytes', name, memory,
          'interfaces', sum(len(generation.texts.get(suffix, b'')) for suffix in ('.fint', '.icurry')))
source.write_text('module Leaf where\n' + %r)
child = subprocess.run([sys.executable, '-c',
    "import curry; curry.reset(interpret='all', jit='off'); curry.path.insert(0, %%r); curry.import_('Leaf')" %% str(source.parent)],
    capture_output=True, text=True, timeout=90)
assert child.returncode == 0, child.stdout + child.stderr
if %r:
    assert str(curry.typeof(leaf.f)) == 'Int -> Int', curry.typeof(leaf.f)
    assert list(curry.eval(leaf.f(1))) == [1]
else:
    probe = source.with_name('Probe.curry')
    probe.write_text('module Probe where\nimport Leaf\ngoal :: (Int,Int)\ngoal = (answer,answer)\n')
    assert curry.show(curry.eval(curry.import_(probe).goal).one()) == '(1,1)'
if %r == 'new':
    curry.reload(leaf)
else:
    curry.reset(interpret='all', jit='off')
leaf = curry.import_('Leaf')
if %r:
    assert str(curry.typeof(leaf.f)) == 'Bool -> Bool', curry.typeof(leaf.f)
    assert list(curry.eval(leaf.f(True))) == [True]
else:
    probe = source.with_name('After.curry')
    probe.write_text('module After where\nimport Leaf\ngoal :: (Int,Int)\ngoal = (answer,answer)\n')
    assert curry.show(curry.eval(curry.import_(probe).goal).one()) == '(2,2)'
""" % (mode, work, str(source), new, typed, mode, typed)
        child = cytest.run_in_subprocess(code, timeout=240, address_space=3 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        print(child.stdout.strip())

  def test_reserved(self):
    names = curryrtbindings.builtin_module_names()
    print('Reserved module names: ' + ', '.join(names))
    self.assertEqual(names, sorted(set(names)))
    self.assertIn('Prelude', names)
    self.assertNotIn('System.IO.Unsafe', names)
    self.assertNotIn('System.Directory', names)
    original = list(curry.path)
    with tempfile.TemporaryDirectory() as work:
      for name in names:
        root = Path(work) / name.replace('.', '_')
        source = root / (name.replace('.', '/') + '.curry')
        source.parent.mkdir(parents=True, exist_ok=True)
        for copy in (True, False):
          if copy:
            shutil.copyfile(installed(name), source)
          else:
            source.write_text('module %s where\nuserValue = True\n' % name)
          for loaded in (False, True):
            curry.path[:] = original
            curry.reset()
            if loaded:
              curry.import_(name)
            curry.path.insert(0, str(root))
            for target in (name, source):
              with self.subTest(name=name, copy=copy, loaded=loaded, target=str(target)):
                with self.assertRaisesRegex(ImportError, 'runtime implements') as caught:
                  curry.import_(target)
                self.assertIn(repr(str(source))[1:-1], str(caught.exception))
                self.assertIn(repr(str(installed(name)))[1:-1], str(caught.exception))
    curry.path[:] = original

  def test_plain_library(self):
    original = list(curry.path)
    with tempfile.TemporaryDirectory() as work:
      for name in ('Data.List', 'Test.Prop', 'Numeric'):
        curry.path[:] = original
        curry.reset()
        source = Path(work) / (name.replace('.', '/') + '.curry')
        source.parent.mkdir(parents=True, exist_ok=True)
        text = installed(name).read_text()
        # Expose the added definition in each library's explicit export list.
        text = re.sub(r'(module\s+' + re.escape(name) + r'\s*\()',
                      r'\1userValue, ', text, count=1)
        source.write_text(text + '\nuserValue :: Bool\nuserValue = True\n')
        before = products(installed(name))
        curry.path.insert(0, work)
        module = curry.import_(name)
        self.assertEqual(Path(module.__file__), source)
        self.assertEqual(list(curry.eval(module.userValue)), [True])
        self.assertFalse(_curry2icurry.in_system_library(str(source)))
        self.assertTrue(Path(_filenames.icurryfilename(str(source))).exists())
        self.assertEqual(products(installed(name)), before)
    curry.path[:] = original

  def test_importer_of_replacement(self):
    for mode in ('new', 'all', 'off'):
      with self.subTest(interpret=mode), tempfile.TemporaryDirectory() as work:
        source = Path(work) / 'Data/Char.curry'
        source.parent.mkdir()
        text = installed('Data.Char').read_text()
        # Change the implementation while retaining all exported declarations.
        text = text.replace('ord c - ord \'0\'', "ord c - ord '0' + 1")
        source.write_text(text)
        before = products(installed('Numeric'))
        code = '''
import curry
import logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('curry').setLevel(logging.INFO)
from curry.backends.cxx import image
from curry.objects import handle
curry.reset(interpret=%r, jit='off')
curry.path.insert(0, %r)
module = curry.import_('Numeric')
print(curry.show(curry.eval(module.readNat(curry.term('1'))).one()))
source = handle.getHandle(module).icurry.filename
path = image._path(curry._interpreter_, source)
assert not __import__('os').path.realpath(path).startswith(__import__('os').path.realpath(curry.config.installed_path('curry', 'lib')) + __import__('os').sep), path
assert __import__('os').path.isfile(path)
print('private image')
''' % (mode, work)
        child = cytest.run_in_subprocess(code, timeout=120, address_space=3 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        self.assertIn('[(2,"")]', child.stdout)
        self.assertIn('private image', child.stdout)
        print('interpret %s: %s' % (mode, child.stdout.strip().replace('\n', '; ')))
        if mode == 'new':
          self.assertIn("module Numeric: interpreted (stale object (an import's interface))", child.stderr)
        self.assertEqual(products(installed('Numeric')), before)

  def test_importer_of_generalized_interface(self):
    for mode in ('new', 'all'):
      with self.subTest(interpret=mode), tempfile.TemporaryDirectory() as work:
        source = Path(work) / 'Data/Char.curry'
        source.parent.mkdir()
        text = installed('Data.Char').read_text()
        text = text.replace('digitToInt      :: Char -> Int',
                            'digitToInt      :: Num a => Char -> a')
        text = re.sub(r"=  (ord c - ord '[0Aa]'(?: \+ 10)?)", r'=  fromInt (\1)', text)
        source.write_text(text)
        before = products(installed('Numeric'))
        code = r"""
import curry, os
from curry.objects.handle import getHandle
from curry.toolchain import _filenames, _interfaces
curry.reset(interpret=%r, jit='off')
curry.path.insert(0, %r)
module = curry.import_('Numeric')
source = getHandle(module).icurry.filename
assert not os.path.realpath(source).startswith(os.path.realpath(curry.config.installed_path('curry', 'lib')) + os.sep), source
assert _interfaces.is_current(_filenames.icurryfilename(source), curry.path)
assert curry.show(curry.eval(module.readNat(curry.term('1'))).one()) == '[(1,"")]'
print('Numeric translated privately and evaluated')
""" % (mode, work)
        child = cytest.run_in_subprocess(code, timeout=120, address_space=3 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        self.assertIn('translated privately and evaluated', child.stdout)
        self.assertEqual(products(installed('Numeric')), before)

  def test_loaded_dependency_translation(self):
    for generalized in (False, True):
      with tempfile.TemporaryDirectory() as work:
        source = Path(work) / 'Data/Char.curry'
        source.parent.mkdir()
        text = installed('Data.Char').read_text()
        if generalized:
          text = text.replace('digitToInt      :: Char -> Int',
                              'digitToInt      :: Num a => Char -> a')
          text = re.sub(r"=  (ord c - ord '[0Aa]'(?: \+ 10)?)",
                        r'=  fromInt (\1)', text)
        else:
          text = text.replace("ord c - ord '0'", "ord c - ord '0' + 1")
        source.write_text(text)
        library = Path(config.installed_path('curry', 'lib'))
        def snapshot():
          return {str(path.relative_to(library)):
                  hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in library.rglob('*') if path.is_file()}
        before = snapshot()
        child = cytest.run_in_subprocess(
            "import curry; curry.path.insert(0, %r); curry.import_('Data.Char')"
            % work, timeout=120, address_space=3 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        for mode in ('new', 'all'):
          for copy_first in (False, True):
            with self.subTest(generalized=generalized, mode=mode,
                              copy_first=copy_first):
              code = r"""
import curry, os, logging
from curry.objects.handle import getHandle
from curry.backends.cxx import image
from curry import cache
from curry.toolchain import _findcurry, _filenames, _interfaces, _productcache
logging.basicConfig(level=logging.WARNING)
curry.reset(interpret=%r, jit='off')
root = %r
copy_first = %r
if copy_first:
  curry.path.insert(0, root)
char = curry.import_('Data.Char')
if copy_first:
  curry.path.remove(root)
else:
  curry.path.insert(0, root)
assert curry.import_(os.path.join(root, 'Data', 'Char.curry')) is char
module = curry.import_('Numeric')
with _findcurry.resolving(curry._interpreter_):
  filename = getHandle(module).icurry.filename
  assert _interfaces.is_current(_filenames.icurryfilename(filename), curry.path)
  loaded = os.path.realpath(getHandle(char).icurry.filename)
  for closure in (cache.import_closure, _productcache.import_closure):
    assert os.path.realpath(closure(filename, curry.path)['Data.Char'].path) == loaded
assert curry.show(curry.eval(module.readNat(curry.term('1'))).one()) == %r
path = image._path(curry._interpreter_, getHandle(module).icurry.filename)
private = not os.path.realpath(path).startswith(
    os.path.realpath(curry.config.installed_path('curry', 'lib')) + os.sep)
assert private == copy_first, path
print('loaded: ' + ('private' if private else 'installed'))
if root not in curry.path:
  curry.path.insert(0, root)
curry.reset(interpret=%r, jit='off')
module = curry.import_('Numeric')
assert curry.show(curry.eval(module.readNat(curry.term('1'))).one()) == %r
path = image._path(curry._interpreter_, getHandle(module).icurry.filename)
assert not os.path.realpath(path).startswith(
    os.path.realpath(curry.config.installed_path('curry', 'lib')) + os.sep), path
print('reset: private')
""" % (mode, work, copy_first,
       '[(2,"")]' if copy_first and not generalized else '[(1,"")]',
       mode, '[(1,"")]' if generalized else '[(2,"")]')
              child = cytest.run_in_subprocess(code, timeout=120,
                                               address_space=3 << 30)
              self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
              self.assertIn('reset: private', child.stdout)
              if not copy_first:
                self.assertIn('loaded already', child.stderr)
        self.assertEqual(snapshot(), before)

  def test_reserved_importer_snapshot(self):
    for mode in ('new', 'all', 'off'):
      with self.subTest(mode=mode), tempfile.TemporaryDirectory() as work:
        source = Path(work) / 'Data/List.curry'
        source.parent.mkdir()
        text = installed('Data.List').read_text()
        text = text.replace(') where', ', roundEight) where', 1)
        source.write_text(text + '\nroundEight :: Bool\nroundEight = True\n')
        before = products(installed('Control.SetFunctions'))
        code = """
import curry
curry.reset(interpret=%r, jit='off')
curry.path.insert(0, %r)
s = curry.import_('Control.SetFunctions')
assert list(curry.eval(s.values2list(s.set0(curry.term(True))))) == [[True]]
from pathlib import Path
import shutil
outside = Path(curry.path[0]) / 'Control/SetFunctions.curry'
outside.parent.mkdir(exist_ok=True)
shutil.copyfile(curry.config.installed_path('curry', 'lib', 'Control/SetFunctions.curry'), outside)
try:
  curry.import_(outside)
except ImportError as error:
  assert 'runtime implements' in str(error)
else:
  raise AssertionError('user copy accepted')
""" % (mode, work)
        child = cytest.run_in_subprocess(code, timeout=120, address_space=3 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        self.assertEqual(products(installed('Control.SetFunctions')), before)

  def test_snapshot_trust_after_reset_and_replacement(self):
    with tempfile.TemporaryDirectory() as work:
      source = Path(work) / 'Data/List.curry'
      source.parent.mkdir()
      source.write_text(installed('Data.List').read_text().replace(
          ') where', ', roundNine) where', 1) +
          '\nroundNine :: Bool\nroundNine = True\n')
      code = r"""
import curry, os, subprocess, sys
from pathlib import Path
from curry.toolchain import _findcurry, _filenames
curry.reset(interpret='new', jit='off')
curry.path.insert(0, %r)
module = curry.import_('Control.SetFunctions')
from curry.objects.terms import ModuleInfo
source = Path(ModuleInfo(module).file)
assert not _findcurry._installed_library_file(str(source))
curry.reset(interpret='new', jit='off')
module = curry.import_(source)
assert list(curry.eval(module.values2list(module.set0(curry.term(True))))) == [[True]]
child = subprocess.run([sys.executable, '-c',
    "import curry; curry.reset(jit='off'); m = curry.import_(" + repr(str(source)) +
    "); assert list(curry.eval(m.values2list(m.set0(curry.term(True))))) == [[True]]"],
    capture_output=True, text=True, timeout=120)
# Replace the source at the exact trusted pathname, rather than editing it
# through a new path. All product guards must revoke its exemption too.
original = source.read_bytes()
try:
  replacement = source.with_suffix('.new')
  replacement.write_text('module Control.SetFunctions where\nuserValue = True\n')
  os.replace(replacement, source)
  curry.reset(interpret='new', jit='off')
  for target in (str(source), _filenames.icurryfilename(str(source)),
                 _filenames.replacesuffix(str(source), '.cpp'),
                 _filenames.replacesuffix(str(source), '.img'),
                 _filenames.replacesuffix(str(source), curry.config.module_object_suffix())):
    try:
      _findcurry.reject_library_shadow('Control.SetFunctions', target, curry._interpreter_)
    except ImportError as error:
      assert 'runtime implements' in str(error), error
    else:
      raise AssertionError('modified snapshot accepted: ' + target)
  try:
    curry.import_(source)
  except ImportError as error:
    assert 'runtime implements' in str(error), error
  else:
    raise AssertionError('replaced snapshot imported')
finally:
  replacement = source.with_suffix('.restore')
  replacement.write_bytes(original)
  os.replace(replacement, source)
assert child.returncode == 0, child.stdout + child.stderr
""" % work
      child = cytest.run_in_subprocess(code, timeout=240, address_space=3 << 30)
      self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_saved_reserved_snapshot(self):
    with tempfile.TemporaryDirectory() as work:
      source = Path(work) / 'Data/List.curry'
      source.parent.mkdir()
      source.write_text(installed('Data.List').read_text().replace(
          ') where', ', roundNine) where', 1) +
          '\nroundNine :: Bool\nroundNine = True\n')
      code = r'''
import ast, base64, curry, os, subprocess, sys, tempfile
from pathlib import Path
curry.reset(interpret='new', jit='off')
curry.path.insert(0, %r)
s = curry.import_('Control.SetFunctions')
module = curry.compile('main = values2list (set0 True)', imports=[s])
expected = curry.show(curry.eval(module.main).one())
program = Path(%r) / 'saved'
curry.save(module, program, main='main')
env = dict(os.environ, CURRYPATH='', SPRITE_CPM_PATH='0')
with tempfile.TemporaryDirectory() as elsewhere:
  result = subprocess.run(([str(program)] if sys.platform == 'win32' else [sys.executable, str(program)]), cwd=elsewhere,
      env=env, capture_output=True, text=True, timeout=120)
  assert result.returncode == 0, result.stdout + result.stderr
  assert result.stdout.strip() == expected, (result.stdout, expected)
  # Extract the very same bundled reserved object for the public-load check.
  data = program.read_bytes()
  if data.startswith(b'MZ'):
    data = data[data.index(b'import base64, os, tempfile'):].split(b'\0', 1)[0]
  tree = ast.parse(data.decode('utf-8'))
  payload = next(node.iter for node in ast.walk(tree) if isinstance(node, ast.For))
  for filename, data in ast.literal_eval(payload):
    if filename == 'Control.SetFunctions' + curry.config.module_object_suffix():
      outside = Path(elsewhere) / filename
      outside.write_bytes(base64.b64decode(data))
      result = subprocess.run([sys.executable, '-c',
          'import curry; curry.load(' + repr(str(outside)) + ')'],
          cwd=elsewhere, env=env, capture_output=True, text=True, timeout=120)
      assert result.returncode != 0, result.stdout
      assert 'runtime implements' in result.stderr, result.stderr
      break
  else:
    raise AssertionError('reserved snapshot missing from saved payload')
''' % (work, work)
      child = cytest.run_in_subprocess(code, timeout=240, address_space=3 << 30)
      self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_renamed_library_objects(self):
    for name in ('System.IO', 'Data.Char'):
      with self.subTest(name=name), tempfile.TemporaryDirectory() as work:
        product = Path(_filenames.replacesuffix(
            _filenames.icurryfilename(str(installed(name))), config.module_object_suffix()))
        copy = Path(work) / ('Other' + config.module_object_suffix())
        shutil.copyfile(product, copy)
        code = r"""
import curry
curry.reset(interpret='new', jit='off')
name, copy = %r, %r
if name == 'System.IO':
  try:
    curry.load(copy)
  except curry.exceptions.LoadError as error:
    assert 'runtime implements' in str(error), error
    assert 'System.IO' in str(error), error
  else:
    raise AssertionError('outside reserved object accepted')
else:
  module = curry.load(copy)
  assert module.__name__ == name, module.__name__
  assert curry.eval(module.digitToInt(curry.parse("'1'"))).one() == 1
""" % (name, str(copy))
        child = cytest.run_in_subprocess(code, timeout=120, address_space=3 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_saved_transitively_stale_library(self):
    for direct_only in (False, True):
      with self.subTest(direct_import_receipt=direct_only), tempfile.TemporaryDirectory() as work:
        source = Path(work) / 'Data/Maybe.curry'
        source.parent.mkdir()
        source.write_text(installed('Data.Maybe').read_text().replace(
            'listToMaybe (a : _) = Just a', 'listToMaybe (a : _) = Nothing'))
        main = Path(work) / 'Probe.curry'
        main.write_text('module Probe where\nimport System.Console.GetOpt\n'
            'main :: ([Bool],[String],[String])\n'
            'main = getOpt Permute [Option [] ["yes"] (NoArg True) ""] ["--yes"]\n')
        code = r"""
import contextlib, curry, os, shutil, subprocess, sys
from pathlib import Path
from curry.objects.handle import getHandle
curry.reset(interpret='new', jit='off')
curry.path.insert(0, %r)
module = curry.import_('Probe')
for name in ('Data.List', 'System.Console.GetOpt'):
  assert getHandle(curry.import_(name)).sofilename is None, name
expected = curry.show(curry.eval(module.main).one())
assert expected.startswith('([],'), expected
program = Path(%r) / 'saved'
# Model an old direct-import-only receipt in memory. Freshness must compare
# it with this session's loaded private Data.List image, so the installed
# object is already rejected before the missing-object guard runs.
from curry.backends.cxx.toolchain import Cpp2So
from curry.toolchain import _filenames
from unittest import mock
source = getHandle(curry.import_('System.Console.GetOpt')).icurry.filename
product = _filenames.replacesuffix(_filenames.icurryfilename(source), curry.config.module_object_suffix())
read_records = Cpp2So._read_stamp_records
def direct_records(cls, filename):
  digest, path, imports, record = read_records(filename)
  if filename == product:
    imports = {name: value for name, value in imports.items() if name != 'Data.Maybe'}
  return digest, path, imports, record
direct_only = DIRECT_ONLY
with (mock.patch.object(Cpp2So, '_read_stamp_records', classmethod(direct_records))
      if direct_only else contextlib.nullcontext()):
  step = Cpp2So(curry._interpreter_)
  if direct_only:
    assert step._object_on_disk('System.Console.GetOpt', curry.path) is None
  assert step.import_lacks_an_object(product)
  curry.save(module, program, main='main')
# The executable must carry its session without the original source tree.
shutil.rmtree(program.parent / 'Data')
shutil.rmtree(program.parent / '.curry')
(program.parent / 'Probe.curry').unlink()
env = dict(os.environ, CURRYPATH='', SPRITE_CPM_PATH='0')
result = subprocess.run(([str(program)] if sys.platform == 'win32' else [sys.executable, str(program)]), env=env,
    capture_output=True, text=True, timeout=120)
assert result.returncode == 0, result.stdout + result.stderr
assert result.stdout.strip() == expected, (result.stdout, expected)
""" % (work, work)
        child = cytest.run_in_subprocess(code.replace('DIRECT_ONLY', repr(direct_only)),
            timeout=180, address_space=3 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_saved_library_replacement(self):
    child = cytest.run_in_subprocess(r'''
import curry
from pathlib import Path
import subprocess, sys, tempfile
with tempfile.TemporaryDirectory() as work:
  source = Path(work) / 'Test/Prop.curry'
  source.parent.mkdir()
  source.write_text('module Test.Prop where\nimport Test.Prop.Child\n'
                    'userValue :: Bool\nuserValue = Test.Prop.Child.value\n')
  child = source.parent / 'Prop/Child.curry'
  child.parent.mkdir()
  child.write_text('module Test.Prop.Child where\nvalue :: Bool\nvalue = True\n')
  curry.path.insert(0, work)
  module = curry.import_('Test.Prop')
  program = Path(work) / 'saved'
  curry.save(module, program, main='userValue')
  result = subprocess.run(([str(program)] if sys.platform == 'win32' else [sys.executable, str(program)]), capture_output=True, text=True)
  assert result.returncode == 0, result.stderr
  assert result.stdout.strip() == 'True', result.stdout
''', timeout=120, address_space=3 << 30)
    self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_loaded_name(self):
    curry.reset()
    module = curry.import_('Data.Char')
    with tempfile.TemporaryDirectory() as work:
      source = Path(work) / 'Data/Char.curry'
      source.parent.mkdir()
      shutil.copyfile(installed('Data.Char'), source)
      curry.path.insert(0, work)
      self.assertIs(curry.import_('Data.Char'), module)
      with self.assertLogs('curry', level='WARNING') as logs:
        self.assertIs(curry.import_(source), module)
      self.assertIn('Data.Char', '\n'.join(logs.output))
