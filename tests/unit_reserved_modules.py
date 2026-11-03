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
