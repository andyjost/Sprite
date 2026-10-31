'''Issue #168: a module can share a namespace, but not a library name.'''
import cytest # from ./lib; must be first
from curry import config
from curry.toolchain import _filenames
import pathlib, tempfile, unittest, zlib
import curry


class TestIssue168(cytest.TestCase):
  def test_prefix_module(self):
    with tempfile.TemporaryDirectory() as work:
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
    original_path = list(curry.path)
    with tempfile.TemporaryDirectory() as work:
      for name in ('Prelude', 'Data.List'):
        root = pathlib.Path(work) / name.replace('.', '_')
        source = root / (name.replace('.', '/') + '.curry')
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('module %s where\nuserValue :: Bool\n'
                          'userValue = True\n' % name)
        installed = pathlib.Path(config.installed_path(
            'curry', name.replace('.', '/') + '.curry'))
        for interpret in ('off', 'new'):
          for loaded in (False, True):
            with self.subTest(name=name, interpret=interpret, loaded=loaded):
              curry.path[:] = original_path
              curry.reset(interpret=interpret)
              library = curry.import_(name) if loaded else None
              curry.path.insert(0, str(root))
              for target in (name, source):
                with self.subTest(target=str(target)):
                  with self.assertRaises(ImportError) as caught:
                    curry.import_(target)
                  message = str(caught.exception)
                  self.assertIn(name, message)
                  self.assertIn(str(source), message)
                  self.assertIn(str(installed), message)
              curry.path[:] = original_path
              restored = curry.import_(name)
              if loaded:
                self.assertIs(restored, library)
              self.assertEqual(pathlib.Path(restored.__file__), installed)

  def test_loaded_library_with_product_only_namesake(self):
    with tempfile.TemporaryDirectory() as work:
      curry.reset(interpret='new')
      curry.import_('Data.List')
      source = pathlib.Path(work) / 'Data/List.curry'
      product = pathlib.Path(_filenames.jsonfilenames(str(source))[1])
      product.parent.mkdir(parents=True)
      product.write_bytes(zlib.compress(b'{}'))
      curry.path.insert(0, work)
      with self.assertRaises(ImportError) as caught:
        curry.import_('Data.List')
      self.assertIn(str(source), str(caught.exception))
      self.assertIn(config.installed_path('curry', 'Data/List.curry'),
                    str(caught.exception))


if __name__ == '__main__':
  unittest.main()
