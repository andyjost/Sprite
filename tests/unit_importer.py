import cytest # from ./lib; must be first
from curry import interpreter
from curry.exceptions import ModuleLookupError
import pathlib, tempfile, sys

class TestImporter(cytest.TestCase):
  def test_directory_does_not_hide_module(self):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
      root = pathlib.Path(work)
      (root / 'early/Parent').mkdir(parents=True)
      (root / 'late').mkdir()
      (root / 'early/Parent/Child.curry').write_text(
          'module Parent.Child where\nchild :: Bool\nchild = True\n')
      (root / 'late/Parent.curry').write_text(
          'module Parent where\nanswer :: Bool\nanswer = True\n')
      (root / 'late/Consumer.curry').write_text(
          'module Consumer where\nimport Parent\n'
          'answer :: Bool\nanswer = Parent.answer\n')
      for child_first in (False, True):
        with self.subTest(child_first=child_first):
          interp = interpreter.Interpreter(flags={'interpret': 'all', 'jit': 'off'})
          interp.path[:0] = [str(root / 'early'), str(root / 'late')]
          if child_first:
            interp.import_('Parent.Child')
          consumer = interp.import_('Consumer')
          self.assertEqual(list(interp.eval(consumer.answer)), [True])
          parent = interp.import_('Parent')
          self.assertEqual(list(interp.eval(parent.answer)), [True])
          child = interp.import_('Parent.Child')
          self.assertIs(parent.Child, child)

  def test_directory_does_not_hide_library_module(self):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
      directory = pathlib.Path(work) / 'System/IO'
      directory.mkdir(parents=True)
      (directory / 'Child.curry').write_text(
          'module System.IO.Child where\nimport System.IO\n'
          'value :: IOMode\nvalue = ReadMode\n')
      interp = interpreter.Interpreter(flags={'interpret': 'all', 'jit': 'off'})
      interp.path.insert(0, work)
      child = interp.import_('System.IO.Child')
      self.assertEqual([str(value) for value in interp.eval(child.value)], ['ReadMode'])
      self.assertEqual(interp.import_('System.IO').__name__, 'System.IO')

  def test_hierarchical_import_of_last_name(self):
    for by_path in (False, True):
      for name in ('Leaf', 'Parent.Leaf', 'Parent.Middle.Leaf'):
        with self.subTest(by_path=by_path, name=name):
          with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
            root = pathlib.Path(work)
            source = root / 'src' / (name.replace('.', '/') + '.curry')
            source.parent.mkdir(parents=True)
            (root / 'deps').mkdir()
            dependency = 'Other' if name == 'Leaf' else 'Leaf'
            source.write_text(
                'module %s where\nimport %s\nvalue :: Bool\nvalue = %s.value\n'
                % (name, dependency, dependency))
            (root / 'deps' / (dependency + '.curry')).write_text(
                'module %s where\nvalue :: Bool\nvalue = True\n' % dependency)
            interp = interpreter.Interpreter(flags={'interpret': 'all', 'jit': 'off'})
            interp.path[:0] = [str(root / 'src'), str(root / 'deps')]
            module = interp.import_(str(source), is_sourcefile=True) if by_path else \
                interp.import_(name)
            self.assertEqual(module.__name__, name)
            self.assertEqual(list(interp.eval(module.value)), [True])

  def test_commented_headers_and_mismatched_place(self):
    headers = (
        '{-\nmodule Example where\n{- nested -}\n-}\nmodule Parent.Leaf where'
      , 'module {- comment -} Parent.Leaf where'
      , '{-# OPTIONS_FRONTEND -Wno-missing-signatures #-}\nmodule Parent.Leaf where'
      )
    for header, place in [(header, 'Parent') for header in headers] + [
        ('module Parent.Leaf where', 'Other')]:
      with self.subTest(header=header, place=place):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
          root = pathlib.Path(work)
          source = root / place / 'Leaf.curry'
          source.parent.mkdir()
          source.write_text(header + '\nimport Helper\nvalue :: Bool\nvalue = Helper.value\n')
          helper_root = root if place == 'Parent' else source.parent
          (helper_root / 'Helper.curry').write_text(
              'module Helper where\nvalue :: Bool\nvalue = True\n')
          interp = interpreter.Interpreter(flags={'interpret': 'all', 'jit': 'off'})
          module = interp.import_(str(source), is_sourcefile=True)
          self.assertEqual(module.__name__, 'Parent.Leaf')
          self.assertEqual(list(interp.eval(module.value)), [True])

  def test_hierarchy_root_precedes_sibling_directory(self):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
      root = pathlib.Path(work)
      (root / 'Parent').mkdir()
      (root / 'Parent/Leaf.curry').write_text(
          'module Parent.Leaf where\nimport Helper\n'
          'value :: Bool\nvalue = Helper.value\n')
      for directory, value in ((root, 'True'), (root / 'Parent', 'False')):
        (directory / 'Helper.curry').write_text(
            'module Helper where\nvalue :: Bool\nvalue = %s\n' % value)
      interp = interpreter.Interpreter(flags={'interpret': 'all', 'jit': 'off'})
      interp.path.insert(0, work)
      module = interp.import_('Parent.Leaf')
      self.assertEqual(list(interp.eval(module.value)), [True])

  def test_misplaced_filename_prefers_sibling_helper(self):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
      root = pathlib.Path(work)
      (root / 'Parent').mkdir()
      source = root / 'Parent/Other.curry'
      source.write_text(
          'module Parent.Leaf where\nimport Helper\n'
          'value :: Bool\nvalue = Helper.value\n')
      for directory, value in ((root, 'False'), (source.parent, 'True')):
        (directory / 'Helper.curry').write_text(
            'module Helper where\nvalue :: Bool\nvalue = %s\n' % value)
      interp = interpreter.Interpreter(flags={'interpret': 'all', 'jit': 'off'})
      interp.path.insert(0, work)
      module = interp.import_(str(source), is_sourcefile=True)
      self.assertEqual(module.__name__, 'Parent.Leaf')
      self.assertEqual(list(interp.eval(module.value)), [True])

  def test_module_and_namespace(self):
    # Both import orders must preserve the parent's symbols and its child.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
      root = pathlib.Path(work)
      (root / 'Parent').mkdir()
      (root / 'Parent.curry').write_text(
          'module Parent where\nimport Parent.Child\n'
          'answer :: Bool\nanswer = Parent.Child.answer\n')
      (root / 'Parent/Child.curry').write_text(
          'module Parent.Child where\ndata Marker = Marker\n'
          'answer :: Bool\nanswer = True\n')
      for first in ('Parent', 'Parent.Child'):
        with self.subTest(first=first):
          interp = interpreter.Interpreter(flags={'interpret': 'off'})
          interp.path.insert(0, work)
          interp.import_(first)
          parent = interp.import_('Parent')
          child = interp.import_('Parent.Child')
          self.assertIs(parent.Child, child)
          self.assertEqual(list(interp.eval(parent.answer)), [True])
          self.assertEqual(list(interp.eval(child.answer)), [True])
          self.assertEqual(interp.symbol('Parent.Child.answer').fullname,
                           'Parent.Child.answer')
          self.assertEqual(interp.type('Parent.Child.Marker').name, 'Marker')

  def test_library_namesake(self):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
      source = pathlib.Path(work) / 'Prelude.curry'
      source.write_text('module Prelude where\nuserSymbol = 1\n')
      for loaded in (False, True):
        interp = interpreter.Interpreter()
        if loaded:
          interp.import_('Prelude')
        interp.path.insert(0, work)
        with self.subTest(loaded=loaded):
          with self.assertRaisesRegex(ModuleLookupError,
              "Curry module 'Prelude'.*conflicts with the installed library module"):
            interp.import_(str(source), is_sourcefile=True)
          with self.assertRaisesRegex(ModuleLookupError, 'conflicts with the installed library'):
            interp.import_('Prelude')

  def test_ordinary_library_namesake(self):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=sys.platform == 'win32') as work:
      directory = pathlib.Path(work) / 'Data'
      directory.mkdir()
      source = directory / 'List.curry'
      source.write_text('module Data.List where\nuserValue :: Bool\nuserValue = True\n')
      for interpret in ('off', 'all'):
        for loaded in (False, True):
          interp = interpreter.Interpreter(flags={'interpret': interpret})
          if loaded:
            interp.import_('Data.List')
          interp.path.insert(0, work)
          for name, isfile in (('Data.List', False), (str(source), True)):
            with self.subTest(interpret=interpret, loaded=loaded, isfile=isfile):
              with self.assertRaisesRegex(ModuleLookupError,
                  "Curry module 'Data.List'.*conflicts with the installed library module"):
                interp.import_(name, is_sourcefile=isfile)

  def test_automodules(self):
    interp = interpreter.Interpreter()
    self.assertNotIn('Prelude', interp.modules)
    prelude = interp.prelude
    self.assertEqual(prelude.__name__, 'Prelude')
    self.assertIn('Prelude', interp.modules)
    #
    self.assertNotIn('Control', interp.modules)
    self.assertNotIn('Control.SetFunctions', interp.modules)
    setf = interp.setfunctions
    self.assertEqual(setf.__name__, 'Control.SetFunctions')
    self.assertIn('Control', interp.modules)
    self.assertIn('Control.SetFunctions', interp.modules)

  def test_import_data(self):
    interp = interpreter.Interpreter()
    for name in [
        'Char', 'Either', 'Function', 'Functor.Identity', 'List', 'Maybe'
      ]:
      modulename = 'Data.' + name
      cymodule = interp.import_(modulename)
      self.assertEqual(cymodule.__name__, modulename)


