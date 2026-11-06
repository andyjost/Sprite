'''Issue #168: module namespaces and library replacements.'''
import cytest # from ./lib; must be first
from curry import config
from curry.toolchain import _filenames
import os, pathlib, tempfile, unittest, zlib
import curry


class TestIssue168(cytest.TestCase):
  def test_prefix_module(self):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=os.name == 'nt') as work:
      root = pathlib.Path(work)
      (root / 'A').mkdir()
      parentfile = root / 'A.curry'
      childfile = root / 'A/B.curry'
      parentfile.write_text(
          'module A where\nimport A.B\n'
          'answer :: Bool\nanswer = A.B.answer\n')
      childfile.write_text(
          'module A.B where\nanswer :: Bool\nanswer = True\n')
      curry.path.insert(0, work)
      for interpret in ('off', 'new'):
        for first in ('A', 'A.B', parentfile, childfile):
          with self.subTest(interpret=interpret, first=str(first)):
            curry.reset(interpret=interpret)
            curry.import_(first)
            parent = curry.import_('A')
            child = curry.import_('A.B')
            self.assertIs(parent.B, child)
            self.assertEqual(pathlib.Path(parent.__file__), parentfile)
            self.assertEqual(pathlib.Path(child.__file__), childfile)
            self.assertEqual(list(curry.eval(parent.answer)), [True])
            self.assertEqual(list(curry.eval(child.answer)), [True])
            self.assertTrue(pathlib.Path(_filenames.icurryfilename(
                str(childfile))).is_file())
            self.assertEqual(pathlib.Path(_filenames.icurryfilename(
                str(childfile))).parent.parent, root / 'A/.curry')

  def test_library_namesakes(self):
    for name in ('Prelude', 'Data.List'):
      for mode in ('off', 'new'):
        for loaded in (False, True):
          with self.subTest(name=name, interpret=mode, loaded=loaded):
            code = r'''
import curry
from curry import config
from curry.toolchain import _filenames
from pathlib import Path
import os, tempfile
curry.reset(interpret=%r, jit='off')
name = %r
with tempfile.TemporaryDirectory(ignore_cleanup_errors=os.name == 'nt') as work:
  source = Path(work) / (name.replace('.', '/') + '.curry')
  source.parent.mkdir(parents=True, exist_ok=True)
  source.write_text('module %%s where\nuserValue :: Bool\nuserValue = True\n' %% name)
  installed = Path(config.installed_path('curry', 'lib', name.replace('.', '/') + '.curry'))
  library = curry.import_(name) if %r else None
  curry.path.insert(0, work)
  for target in (name, source):
    if name == 'Prelude':
      try:
        curry.import_(target)
      except ImportError as exc:
        assert 'runtime implements' in str(exc)
        assert repr(str(source))[1:-1] in str(exc)
        assert repr(str(installed))[1:-1] in str(exc)
      else:
        raise AssertionError('reserved module accepted')
    else:
      module = curry.import_(target)
      if library is not None:
        assert module is library
      else:
        assert list(curry.eval(module.userValue)) == [True]
        assert Path(_filenames.icurryfilename(str(source))).exists()
''' % (mode, name, loaded)
            child = cytest.run_in_subprocess(code, timeout=60, address_space=2 << 30)
            self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_loaded_library_with_product_only_namesake(self):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=os.name == 'nt') as work:
      curry.reset(interpret='new')
      library = curry.import_('Data.List')
      source = pathlib.Path(work) / 'Data/List.curry'
      product = pathlib.Path(_filenames.replacesuffix(str(source), '.img'))
      product.parent.mkdir(parents=True)
      product.write_bytes(zlib.compress(b'{}'))
      curry.path.insert(0, work)
      self.assertIs(curry.import_('Data.List'), library)


if __name__ == '__main__':
  unittest.main()
