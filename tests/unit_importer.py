import cytest # from ./lib; must be first
from curry import interpreter
from curry.exceptions import ModuleLookupError
import pathlib, tempfile

class TestImporter(cytest.TestCase):
  def test_module_and_namespace(self):
    # Both import orders must preserve the parent's symbols and its child.
    with tempfile.TemporaryDirectory() as work:
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
    with tempfile.TemporaryDirectory() as work:
      source = pathlib.Path(work) / 'Prelude.curry'
      source.write_text('module Prelude where\nuserSymbol = 1\n')
      for loaded in (False, True):
        interp = interpreter.Interpreter()
        if loaded:
          interp.import_('Prelude')
        interp.path.insert(0, work)
        with self.subTest(loaded=loaded):
          with self.assertRaisesRegex(ModuleLookupError,
              "^Curry module 'Prelude' conflicts with the installed library module[.]$"):
            interp.import_(str(source), is_sourcefile=True)
          with self.assertRaisesRegex(ModuleLookupError, 'conflicts with the installed library'):
            interp.import_('Prelude')

  def test_ordinary_library_namesake(self):
    with tempfile.TemporaryDirectory() as work:
      directory = pathlib.Path(work) / 'Data'
      directory.mkdir()
      source = directory / 'List.curry'
      source.write_text('module Data.List where\nuserValue :: Bool\nuserValue = True\n')
      interp = interpreter.Interpreter(flags={'interpret': 'off'})
      interp.path.insert(0, work)
      module = interp.import_('Data.List')
      self.assertEqual(module.__file__, str(source))
      self.assertEqual(list(interp.eval(module.userValue)), [True])
      for interpret in ('off', 'all'):
        interp = interpreter.Interpreter(flags={'interpret': interpret})
        interp.import_('Data.List')
        interp.path.insert(0, work)
        for name, isfile in (('Data.List', False), (str(source), True)):
          with self.subTest(interpret=interpret, isfile=isfile):
            with self.assertRaisesRegex(ModuleLookupError,
                "Curry module 'Data.List' conflicts with the installed library module[.]"):
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


