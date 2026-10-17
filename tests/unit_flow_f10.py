'''
F10: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.3; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_import_by_name_and_file: alt.py 13-14; output 1; lane 5.
  test_compile_text: alt.py 15-16; output 2; lane 5.
  test_parse_in_module_scope: alt.py 17; output 3; lane 4.
  test_duplicate_module_name: alt.py 18; output 4; lane 5.
  test_cached_import_after_edit: alt.py 19-22; output 5-7; lane 5.
  test_reload_file_and_old_term: alt.py 23-24; output 8-9 (py: 8-9); lane 5.
  test_wait_for_compile: alt.py appendix 5860-5866; output decision (c); lane 5.
  test_reset_and_import_hook: alt.py 25-30; output 10-13; lane 5.
  test_save_and_load: alt.py 31-34; output 14-16 (py: 14-16); lane 5.
  test_missing_module: alt.py 35; output 17; lane 1.

Left out: Omit the timestamp, path and exact byte counts in outputs 6 and 14. They are
process details, not values of the API. No timing-dependent background-compile
observation is asserted. The fixture Peano is byte-identical to the existing root
fixture and is not copied.

Departures and rules: Decisions (c)-(d), Appendix A 5802-5819 and 5860-5866: wait names
compile completion and reload refusal depends on interpret, not timing. The save/load
approximation in the facade README is replaced by Appendix A 5848-5857: a name loaded
from another file raises LoadError on both backends. This departs from py output 15;
listed as an open point. An edited source must warn through CurryWarning (Appendix A
6574-6577).

Lanes refer to the Python API implementation plan. Tests import curry,
the package. Missing proposed names are only used inside test methods.
'''
import cytest # from ./lib; must be first
import curry
import unittest
import os
import shutil
import tempfile

FLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'flows')


def setUpModule():
  curry.path.insert(0, FLOW_PATH)


class TestFlowF10(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)
    work = tempfile.TemporaryDirectory()
    self.addCleanup(work.cleanup)
    self.work = work.name
    self.source = os.path.join(self.work, 'Peano.curry')
    shutil.copyfile(os.path.join(FLOW_PATH, '..', 'Peano.curry'), self.source)
    curry.path.insert(0, self.work)

  def edit_source(self):
    with open(self.source, encoding='utf-8') as stream:
      text = stream.read()
    with open(self.source, 'w', encoding='utf-8') as stream:
      stream.write(text.replace('main = add (S O) (S O)', 'main = S O'))

  @unittest.expectedFailure
  def test_import_by_name_and_file(self):
    M = curry.import_('Peano')
    self.assertIs(curry.import_(self.source), M)

  @unittest.expectedFailure
  def test_compile_text(self):
    N = curry.compile('f :: Int\nf = 1', name='Same')
    self.assertEqual(curry.eval(N.f).one(), 1)
    self.assertIs(curry.modules['Same'], N)

  def test_parse_in_module_scope(self):
    M = curry.import_('Peano')
    self.assertEqual(str(curry.eval(curry.parse('add (S O) O', imports=[M])).one()), 'S O')

  @unittest.expectedFailure
  def test_duplicate_module_name(self):
    N = curry.compile('f :: Int\nf = 1', name='Same')
    with self.assertRaises(curry.ModuleExistsError):
      curry.compile('f :: Int\nf = 2', name='Same')
    self.assertIs(curry.modules['Same'], N)

  @unittest.expectedFailure
  def test_cached_import_after_edit(self):
    M = curry.import_('Peano')
    self.assertEqual(str(curry.eval(M.main).one()), 'S (S O)')
    self.edit_source()
    with self.assertWarns(curry.CurryWarning):
      self.assertIs(curry.import_('Peano'), M)
    self.assertEqual(str(curry.eval(M.main).one()), 'S (S O)')

  @unittest.expectedFailure
  def test_reload_file_and_old_term(self):
    M = curry.import_('Peano'); old = M.main
    self.edit_source()
    if curry.flags['backend'] == 'cxx' and curry.flags['interpret'] in ('tiered', 'off'):
      with self.assertRaises(curry.LoadError):
        curry.reload(M)
      self.assertEqual(str(curry.eval(old).one()), 'S (S O)')
    else:
      self.assertIs(curry.reload(M), M)
      self.assertEqual(str(curry.eval(M.main).one()), 'S O')
      with self.assertRaises(curry.StaleError):
        curry.eval(old).one()

  @unittest.expectedFailure
  def test_wait_for_compile(self):
    M = curry.import_('Peano')
    self.assertIsNone(curry.wait(M))
    self.assertIsNone(curry.wait(module=None))
    self.assertEqual(str(curry.eval(M.main).one()), 'S (S O)')

  @unittest.expectedFailure
  def test_reset_and_import_hook(self):
    M = curry.import_('Peano'); self.edit_source()
    saved_path = list(curry.path)
    curry.reset()
    self.assertEqual(curry.path, saved_path)
    self.assertEqual(sorted(curry.modules), ['Prelude'])
    with self.assertRaises(curry.StaleError):
      curry.eval(M.main).one()
    from curry.lib import Peano as M3
    self.assertIsNot(M3, M)
    self.assertEqual(str(curry.eval(M3.main).one()), 'S O')
    self.assertIs(curry.import_('Peano'), M3)

  @unittest.expectedFailure
  def test_save_and_load(self):
    self.edit_source()
    M = curry.import_('Peano')
    ext = '.so' if curry.flags['backend'] == 'cxx' else '.py'
    product = os.path.join(self.work, 'Peano' + ext)
    self.assertIsNone(curry.save(M, product))
    self.assertGreater(os.path.getsize(product), 0)
    with self.assertRaises(curry.LoadError):
      curry.load(product)
    self.assertIs(curry.modules['Peano'], M)
    self.assertEqual(str(curry.eval(M.main).one()), 'S O')

  @unittest.expectedFailure
  def test_missing_module(self):
    with self.assertRaises(curry.ModuleLookupError) as caught:
      curry.import_('Nosuch')
    self.assertIsInstance(caught.exception, ImportError)
    self.assertIsInstance(caught.exception, curry.CurryError)
    self.assertIn('curry.path', str(caught.exception))


if __name__ == '__main__':
  unittest.main()
