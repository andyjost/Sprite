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
  return Path(config.installed_path('curry', name.replace('.', '/') + '.curry'))


class TestReservedModules(cytest.TestCase):
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
assert not __import__('os').path.realpath(path).startswith(__import__('os').path.realpath(curry.config.installed_path('curry')) + __import__('os').sep), path
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
assert not os.path.realpath(source).startswith(os.path.realpath(curry.config.installed_path('curry')) + os.sep), source
assert _interfaces.is_current(_filenames.icurryfilename(source), curry.path)
assert curry.show(curry.eval(module.readNat(curry.term('1'))).one()) == '[(1,"")]'
print('Numeric translated privately and evaluated')
""" % (mode, work)
        child = cytest.run_in_subprocess(code, timeout=120, address_space=3 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        self.assertIn('translated privately and evaluated', child.stdout)
        self.assertEqual(products(installed('Numeric')), before)

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
shutil.copyfile(curry.config.installed_path('curry', 'Control/SetFunctions.curry'), outside)
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
# A direct-import-only receipt can match the installed Data.List image
# even though this session uses its private image. Model that receipt in
# memory: the current pinned object's extra summary also names Data.Maybe.
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
    assert step._object_on_disk('System.Console.GetOpt', curry.path) == product
  assert step.import_lacks_an_object(product)
  curry.save(module, program, main='main')
# The executable must carry its session without the original source tree.
shutil.rmtree(program.parent / 'Data')
shutil.rmtree(program.parent / '.curry')
(program.parent / 'Probe.curry').unlink()
env = dict(os.environ, CURRYPATH='', SPRITE_CPM_PATH='0')
result = subprocess.run([sys.executable, str(program)], env=env,
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
  result = subprocess.run([sys.executable, str(program)], capture_output=True, text=True)
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
