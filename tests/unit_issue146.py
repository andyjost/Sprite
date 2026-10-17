'''
Issue #146: a module named in the imports of curry.compile that is not loaded
is imported on demand, as curry.import_ would import it, and a module that
cannot be found raises ModuleLookupError with the message of curry.import_,
never a bare KeyError.

These tests are the acceptance tests of a task; they are frozen.  A change to
this file is a finding, not a fix.
'''
import cytest # from ./lib; must be first
import curry, unittest
from curry.exceptions import ModuleLookupError

class TestIssue146(unittest.TestCase):
  def test_unknown_import_raises_module_lookup_error(self):
    with self.assertRaises(ModuleLookupError) as cm:
      curry.parse('1', imports=['Nosuch'])
    self.assertIn('Nosuch', str(cm.exception))

  def test_unknown_import_is_never_a_bare_key_error(self):
    try:
      curry.parse('1', imports=['Nosuch'])
    except ModuleLookupError:
      pass
    except KeyError: # pragma: no cover
      self.fail('a bare KeyError escaped from curry.compile')

  def test_loaded_module_by_name(self):
    goal = curry.parse('length [1,2,3]', imports=['Prelude'])
    self.assertEqual(list(curry.eval(goal)), [3])

  def test_loaded_module_by_object(self):
    P = curry.import_('Prelude')
    goal = curry.parse('length [1,2,3]', imports=[P])
    self.assertEqual(list(curry.eval(goal)), [3])

  def test_library_module_imported_on_demand(self):
    # Data.List is a module of the installed library; it need not be loaded
    # before the call: a name in imports is imported as curry.import_ imports
    # it.
    goal = curry.parse('nub [1,1,2]', imports=['Data.List'])
    self.assertEqual(list(curry.eval(goal)), [[1, 2]])
    self.assertIn('Data.List', curry.modules)

  def test_module_mode_unknown_import(self):
    with self.assertRaises(ModuleLookupError) as cm:
      curry.compile('x :: Int\nx = 1\n', mode='module', imports=['Nosuch'])
    self.assertIn('Nosuch', str(cm.exception))
