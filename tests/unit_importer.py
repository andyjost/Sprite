import cytest # from ./lib; must be first
from curry import interpreter

class TestImporter(cytest.TestCase):
  def test_automodules(self):
    interp = interpreter.Interpreter()
    self.assertNotIn('Prelude', interp.modules)
    prelude = interp.prelude
    self.assertEqual(prelude.__name__, 'Prelude')
    self.assertIn('Prelude', interp.modules)
    #
    self.assertNotIn('Integer', interp.modules)
    integer = interp.integer
    self.assertEqual(integer.__name__, 'Integer')
    self.assertIn('Integer', interp.modules)
    #
    self.assertNotIn('Control', interp.modules)
    self.assertNotIn('Control.SetFunctions', interp.modules)
    setf = interp.setfunctions
    self.assertEqual(setf.__name__, 'SetFunctions')
    self.assertIn('Control', interp.modules)
    self.assertIn('Control.SetFunctions', interp.modules)

  def test_import_data(self):
    interp = interpreter.Interpreter()
    for name in [
        'Char', 'Either', 'Function', 'Functor.Identity', 'List', 'Maybe'
      ]:
      cymodule = interp.import_('Data.' + name)
      self.assertEqual(cymodule.__name__, name.split('.')[-1])


