'''
Modules: frozen acceptance of Appendix A of python-api-review2.md.

Each row maps a test to the review's lines and the flip lane of
python-api-implementation-plan.md. Section 12 amends metadata access.
  test_import_example: lines 5783-5784; lane 5.
  test_compile_setup_example: lines 5797; lane 5.
  test_compile_result_example: lines 5797-5799; lane 5.
  test_reload_example: lines 5817-5818; lane 5.
  test_reset_example: lines 5832-5833; lane 5.
  test_save_example: lines 5845; lane 5.
  test_load_example: lines 5856-5857; 6667-6677; lane 5.
  test_import_pathlike_is_a_file: lines 5774-5777; lane 5.
  test_import_explicit_search_path: lines 5776-5777; lane 5.
  test_import_dotted_name_loads_packages: lines 5777-5778; lane 5.
  test_import_hook_identity: lines 5780-5781; lane 5.
  test_loaded_source_is_not_read_and_warns_once: lines 5778-5780; lane 5.
  test_compile_header_registers_name: lines 5789-5791; lane 5.
  test_compile_generated_name_is_registered: lines 5789-5791; lane 5.
  test_compile_imports_modules: lines 5791-5792; lane 5.
  test_compile_imports_names: lines 5791-5792; lane 5.
  test_compile_loaded_name_is_rejected: lines 5792-5794; lane 5.
  test_compile_refusal_is_compile_error: lines 5794-5795; lane 1.
  test_reload_text_updates_in_place_and_stales_terms: lines 5804-5809; lane 5.
  test_reload_text_module_requires_text: lines 5804-5806; lane 5.
  test_reload_file_limit_names_ways_out: lines 5810-5815; lane 5.
  test_reset_keeps_path_and_purges_import_hook: lines 5825-5827; lane 5.
  test_reset_stales_term: lines 5826-5828; lane 5.
  test_reset_stales_variable: lines 5826-5828; lane 5.
  test_reset_stales_module: lines 5826-5828; lane 5.
  test_reset_rejects_unknown_flag: lines 5828-5830; lane 5.
  test_reset_rejects_invalid_flag_value: lines 5828-5830; lane 5.
  test_wait_returns_none: lines 5860-5865; lane 5.
  test_modules_omit_packages: lines 5868-5870; lane 5.
  test_path_mutation_changes_search: lines 5872-5875; lane 5.
  test_path_assignment_changes_search: lines 5872-5875; lane 5.
  test_flags_are_read_only: lines 5877-5879; lane 5.
  test_stats_are_numeric_counters: lines 5881-5882; lane 5.
  test_module_example: lines 6247-6248; lane 4a.
  test_module_is_python_module: lines 6233-6240; lane 4a.
  test_module_private_symbol_lookup: lines 6242-6244; lane 4a.
  test_module_missing_symbol_raises: lines 6243-6245; lane 1.
  test_info_is_the_dotted_slot: lines 6667-6677; lane 4a.
  test_metadata_names_remain_curry_symbols: lines 6667-6677; lane 4a.
  test_info_symbols_include_private_not_dictionaries: lines 6209; 6253-6258; 6667-6677; lane 4a.
  test_load_bad_format_is_load_error: lines 5852-5854; lane 5.
  test_load_other_backend_is_load_error: lines 5852-5854; lane 5.
  test_load_same_file_returns_registered_module: lines 5850-5852; lane 5.
  test_load_same_name_from_another_file_is_rejected: lines 5852-5854; lane 5.
  test_saved_main_prints_goal_answers: lines 5840-5843; lane 5.
  test_environment_flag_validator_matches_reset: lines 5828-5830; 5877-5879; lane 5.
  test_import_literate_file: lines 5774-5777; lane 5.
  test_path_order_selects_first_module: lines 5872-5875; lane 5.
  test_reload_reads_edited_source_in_place: lines 5804-5809; 5814-5815; lane 5.

Examples left out: none. Setup prompts have their own tests; result
tests repeat their setup so they can run independently.
The import example runs in the fixture directory. Save/load examples
keep Coin.so literally, including on Python. Child processes save objects
before this process loads them. Reload's identity example uses interpret=new,
as required for file modules by lines 5810-5815.
'''
import cytest # from ./lib; must be first
import curry
import unittest
import os
import contextlib
import importlib
import shutil
import subprocess
import sys
import tempfile
import types
import warnings
from collections.abc import Mapping
from pathlib import Path


@contextlib.contextmanager
def working_directory(path):
  previous = os.getcwd()
  try:
    os.chdir(path)
    yield
  finally:
    os.chdir(previous)

FLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'flows')


def setUpModule():
  curry.path.insert(0, FLOW_PATH)


class TestStubModules(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)
    self.addCleanup(importlib.reload, curry)

  @unittest.expectedFailure
  def test_import_example(self):
    Coin = curry.import_('Coin')
    with working_directory(FLOW_PATH):
      self.assertIs(curry.import_('./Coin.curry'), Coin)

  @unittest.expectedFailure
  def test_compile_setup_example(self):
    N = curry.compile('f :: Int -> Int\nf x = x + 1', name='N')
    self.assertIs(curry.modules['N'], N)

  @unittest.expectedFailure
  def test_compile_result_example(self):
    N = curry.compile('f :: Int -> Int\nf x = x + 1', name='N')
    self.assertEqual(list(curry.eval(N.f(1))), [2])

  @unittest.expectedFailure
  def test_reload_example(self):
    curry.reset(interpret='new')
    Coin = curry.import_('Coin')
    self.assertIs(curry.reload(Coin), Coin)

  @unittest.expectedFailure
  def test_reset_example(self):
    curry.import_('Coin')
    curry.reset(backend='py')
    self.assertEqual(sorted(curry.modules), ['Prelude'])

  @unittest.expectedFailure
  def test_save_example(self):
    Coin = curry.import_('Coin')
    with tempfile.TemporaryDirectory() as work, working_directory(work):
      self.assertIsNone(curry.save(Coin, 'Coin.so'))
      self.assertIsNone(curry.save(Coin, 'coin.exe', main=Coin.coin))
      self.assertGreater(os.path.getsize('Coin.so'), 0)
      self.assertGreater(os.path.getsize('coin.exe'), 0)

  @unittest.expectedFailure
  def test_load_example(self):
    with tempfile.TemporaryDirectory() as work:
      product = os.path.join(work, 'Coin.so')
      code = "import curry; curry.path.insert(0, %r); curry.save(curry.import_('Coin'), %r)" % (FLOW_PATH, product)
      subprocess.run([sys.executable, '-c', code], check=True, capture_output=True, text=True)
      M = curry.load(product)
      self.assertEqual(curry.info(M).name, 'Coin')

  @unittest.expectedFailure
  def test_import_pathlike_is_a_file(self):
    M = curry.import_(Path(FLOW_PATH) / 'Coin.curry')
    self.assertIs(M, curry.import_('Coin'))

  @unittest.expectedFailure
  def test_import_explicit_search_path(self):
    M = curry.import_('Coin', path=[Path(FLOW_PATH)])
    self.assertIs(M, curry.modules['Coin'])

  def test_import_dotted_name_loads_packages(self):
    M = curry.import_('Data.List')
    from curry.lib import Data
    self.assertIs(Data.List, M)

  def test_import_hook_identity(self):
    from curry.lib import Coin
    self.assertIs(Coin, curry.import_('Coin'))

  @unittest.expectedFailure
  def test_loaded_source_is_not_read_and_warns_once(self):
    with tempfile.TemporaryDirectory() as work:
      source = Path(work) / 'Coin.curry'
      shutil.copyfile(Path(FLOW_PATH) / 'Coin.curry', source)
      M = curry.import_(source)
      source.write_text('module Coin where\ncoin :: Int\ncoin = 9\n')
      with self.assertWarns(curry.CurryWarning):
        self.assertIs(curry.import_(source), M)
      with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter('always', curry.CurryWarning)
        self.assertIs(curry.import_(source), M)
      self.assertEqual(seen, [])
      self.assertEqual(list(curry.eval(M.coin)), [0, 1])

  def test_compile_header_registers_name(self):
    M = curry.compile('module StubHeader where\nf :: Int\nf = 1')
    self.assertIs(curry.modules['StubHeader'], M)
    self.assertIsNone(curry.info(M).file)

  def test_compile_generated_name_is_registered(self):
    M = curry.compile('f :: Int\nf = 1')
    self.assertIs(curry.modules[curry.info(M).name], M)

  @unittest.expectedFailure
  def test_compile_imports_modules(self):
    M = curry.compile('f :: Int\nf = Coin.inc 1', imports=[curry.import_('Coin')])
    self.assertEqual(curry.eval(M.f).one(), 2)

  @unittest.expectedFailure
  def test_compile_imports_names(self):
    M = curry.compile('f :: Int\nf = Coin.inc 1', imports=['Coin'])
    self.assertEqual(curry.eval(M.f).one(), 2)

  @unittest.expectedFailure
  def test_compile_loaded_name_is_rejected(self):
    M = curry.compile('f :: Int\nf = 1', name='Same')
    with self.assertRaises(curry.ModuleExistsError):
      curry.compile('f :: Int\nf = 2', name='Same')
    self.assertIs(curry.modules['Same'], M)

  def test_compile_refusal_is_compile_error(self):
    with self.assertRaises(curry.CompileError):
      curry.compile('f = )')

  @unittest.expectedFailure
  def test_reload_text_updates_in_place_and_stales_terms(self):
    M = curry.compile('f :: Int\nf = 1', name='StubReload')
    old = M.f
    self.assertIs(curry.reload(M, text='f :: Int\nf = 2'), M)
    self.assertEqual(curry.eval(M.f).one(), 2)
    with self.assertRaises(curry.StaleError):
      curry.eval(old).one()

  @unittest.expectedFailure
  def test_reload_text_module_requires_text(self):
    M = curry.compile('f :: Int\nf = 1')
    with self.assertRaises(curry.LoadError) as caught:
      curry.reload(M)
    self.assertIn('text', str(caught.exception))

  @unittest.expectedFailure
  def test_reload_file_limit_names_ways_out(self):
    Coin = curry.import_('Coin')
    if curry.flags['backend'] == 'cxx' and curry.flags['interpret'] in ('tiered', 'off'):
      with self.assertRaises(curry.LoadError) as caught:
        curry.reload(Coin)
      self.assertIn("curry.reset(interpret='new')", str(caught.exception))
      self.assertIn('process', str(caught.exception))
    else:
      self.assertIs(curry.reload(Coin), Coin)

  @unittest.expectedFailure
  def test_reset_keeps_path_and_purges_import_hook(self):
    from curry.lib import Coin
    path = list(curry.path)
    curry.reset()
    self.assertEqual(curry.path, path)
    self.assertNotIn('curry.lib.Coin', sys.modules)
    from curry.lib import Coin as fresh
    self.assertIsNot(fresh, Coin)

  @unittest.expectedFailure
  def test_reset_stales_term(self):
    M = curry.import_('Coin')
    old = M.inc(1)
    curry.reset()
    with self.assertRaises(curry.StaleError):
      curry.eval(old).one()

  @unittest.expectedFailure
  def test_reset_stales_variable(self):
    M = curry.import_('Coin')
    old = curry.free('x')
    curry.reset()
    with self.assertRaises(curry.StaleError):
      curry.term(old)

  @unittest.expectedFailure
  def test_reset_stales_module(self):
    M = curry.import_('Coin')
    old = M
    curry.reset()
    with self.assertRaises(curry.StaleError):
      old.coin

  @unittest.expectedFailure
  def test_reset_rejects_unknown_flag(self):
    with self.assertRaises(curry.FlagError):
      curry.reset(bogus=True)

  @unittest.expectedFailure
  def test_reset_rejects_invalid_flag_value(self):
    with self.assertRaises(curry.FlagError):
      curry.reset(backend='missing')

  @unittest.expectedFailure
  def test_wait_returns_none(self):
    M = curry.import_('Coin')
    self.assertIsNone(curry.wait(M))
    self.assertIsNone(curry.wait())

  @unittest.expectedFailure
  def test_modules_omit_packages(self):
    M = curry.import_('Data.List')
    self.assertIsInstance(curry.modules, Mapping)
    self.assertIs(curry.modules['Data.List'], M)
    self.assertNotIn('Data', curry.modules)

  def test_path_mutation_changes_search(self):
    with tempfile.TemporaryDirectory() as work:
      source = Path(work) / 'StubPath.curry'
      source.write_text('module StubPath where\nf :: Int\nf = 1\n')
      curry.path.insert(0, work)
      self.assertEqual(curry.info(curry.import_('StubPath')).file, str(source))

  @unittest.expectedFailure
  def test_path_assignment_changes_search(self):
    with tempfile.TemporaryDirectory() as work:
      source = Path(work) / 'StubPath.curry'
      source.write_text('module StubPath where\nf :: Int\nf = 1\n')
      curry.path = [work] + list(curry.path)
      self.assertEqual(curry.info(curry.import_('StubPath')).file, str(source))

  @unittest.expectedFailure
  def test_flags_are_read_only(self):
    self.assertIsInstance(curry.flags, Mapping)
    with self.assertRaises(TypeError):
      curry.flags['backend'] = curry.flags['backend']

  def test_stats_are_numeric_counters(self):
    counters = curry.stats()
    self.assertIsInstance(counters, dict)
    self.assertTrue(counters)
    self.assertTrue(all(isinstance(k, str) for k in counters))
    self.assertTrue(all(isinstance(v, (int, float)) for v in counters.values()))

  def test_module_example(self):
    P = curry.import_('Prelude')
    Coin = curry.import_('Coin')
    self.assertEqual(
        (str(P['not'](True)), Coin.inc == Coin.inc, Coin.inc is Coin.inc)
      , ('not True', True, False)
      )

  def test_module_is_python_module(self):
    M = curry.import_('Coin')
    self.assertIsInstance(M, curry.Module)
    self.assertIsInstance(M, types.ModuleType)
    self.assertIsInstance(M.inc, curry.Term)

  @unittest.expectedFailure
  def test_module_private_symbol_lookup(self):
    M = curry.compile('module StubPrivate (public) where\npublic :: Int\npublic = helper\nhelper :: Int\nhelper = 1')
    self.assertEqual(curry.eval(M['helper']).one(), 1)

  def test_module_missing_symbol_raises(self):
    M = curry.import_('Coin')
    with self.assertRaises(curry.SymbolLookupError):
      M.nosuch

  def test_info_is_the_dotted_slot(self):
    M = curry.import_('Geo')
    info = curry.info(M)
    self.assertIs(info, getattr(M, '.info'))
    self.assertEqual(info.name, 'Geo')
    self.assertTrue(os.path.samefile(info.file, Path(FLOW_PATH) / 'Geo.curry'))
    self.assertIn('Point', info.types)
    self.assertIn('origin', info.symbols)
    for name in ('name', 'file', 'types', 'symbols'):
      with self.assertRaises(curry.SymbolLookupError):
        getattr(M, name)

  @unittest.expectedFailure
  def test_metadata_names_remain_curry_symbols(self):
    M = curry.compile('module StubMetadata where\nname = 1 :: Int\nfile = 2 :: Int\ntypes = 3 :: Int\nsymbols = 4 :: Int')
    self.assertEqual(
        [curry.eval(getattr(M, n)).one() for n in ('name', 'file', 'types', 'symbols')]
      , [1, 2, 3, 4]
      )
    self.assertEqual(curry.info(M).name, 'StubMetadata')

  def test_info_symbols_include_private_not_dictionaries(self):
    M = curry.compile('module StubPrivate (public) where\npublic :: Int\npublic = helper\nhelper :: Int\nhelper = 1')
    info = curry.info(M)
    self.assertIsInstance(info.types, Mapping)
    self.assertIsInstance(info.symbols, Mapping)
    self.assertIn('helper', info.symbols)
    self.assertFalse(info.symbols['helper'].public)
    self.assertTrue(info.symbols['public'].public)
    self.assertFalse(any('_impl#' in n or '_inst#' in n for n in info.symbols))

  @unittest.expectedFailure
  def test_load_bad_format_is_load_error(self):
    with tempfile.TemporaryDirectory() as work:
      path = Path(work) / 'bad.data'
      path.write_text('not a compiled module')
      with self.assertRaises(curry.LoadError):
        curry.load(path)

  @unittest.expectedFailure
  def test_load_other_backend_is_load_error(self):
    with tempfile.TemporaryDirectory() as work:
      other = 'py' if curry.flags['backend'] == 'cxx' else 'cxx'
      ext = '.py' if other == 'py' else '.so'
      product = str(Path(work) / ('Coin' + ext))
      code = "import curry; curry.reset(backend=%r); curry.path.insert(0, %r); curry.save(curry.import_('Coin'), %r)" % (other, FLOW_PATH, product)
      subprocess.run([sys.executable, '-c', code], check=True, capture_output=True, text=True)
      with self.assertRaises(curry.LoadError):
        curry.load(product)

  @unittest.expectedFailure
  def test_load_same_file_returns_registered_module(self):
    with tempfile.TemporaryDirectory() as work:
      ext = '.so' if curry.flags['backend'] == 'cxx' else '.py'
      product = str(Path(work) / ('Coin' + ext))
      code = "import curry; curry.path.insert(0, %r); curry.save(curry.import_('Coin'), %r)" % (FLOW_PATH, product)
      subprocess.run([sys.executable, '-c', code], check=True, capture_output=True, text=True)
      M = curry.load(product)
      self.assertIs(curry.modules['Coin'], M)
      self.assertIs(curry.load(product), M)

  @unittest.expectedFailure
  def test_load_same_name_from_another_file_is_rejected(self):
    M = curry.import_('Coin')
    with tempfile.TemporaryDirectory() as work:
      ext = '.so' if curry.flags['backend'] == 'cxx' else '.py'
      product = str(Path(work) / ('Coin' + ext))
      self.assertIsNone(curry.save(M, product))
      with self.assertRaises(curry.LoadError):
        curry.load(product)

  @unittest.expectedFailure
  def test_saved_main_prints_goal_answers(self):
    Coin = curry.import_('Coin')
    with tempfile.TemporaryDirectory() as work:
      program = str(Path(work) / 'coin.exe')
      curry.save(Coin, program, main=Coin.coin)
      run = subprocess.run([program], check=True, capture_output=True, text=True)
      self.assertEqual(run.stdout, '0\n1\n')

  @unittest.expectedFailure
  def test_environment_flag_validator_matches_reset(self):
    env = dict(os.environ, SPRITE_INTERPRETER_FLAGS='bogus:1')
    code = "try:\n import curry\nexcept Exception as error:\n print(type(error).__name__)\nelse:\n raise AssertionError('unknown flag accepted')"
    run = subprocess.run([sys.executable, '-c', code], env=env, check=True, capture_output=True, text=True)
    self.assertEqual(run.stdout.strip(), 'FlagError')

  @unittest.expectedFailure
  def test_import_literate_file(self):
    with tempfile.TemporaryDirectory() as work:
      source = Path(work) / 'StubLiterate.lcurry'
      source.write_text('> module StubLiterate where\n> f :: Int\n> f = 1\n')
      M = curry.import_(source)
      self.assertEqual(curry.eval(M.f).one(), 1)

  @unittest.expectedFailure
  def test_path_order_selects_first_module(self):
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
      for work, number in ((first, 1), (second, 2)):
        (Path(work) / 'StubPathOrder.curry').write_text('module StubPathOrder where\nf :: Int\nf = %d\n' % number)
      curry.path[:0] = [first, second]
      self.assertEqual(curry.eval(curry.import_('StubPathOrder').f).one(), 1)

  @unittest.expectedFailure
  def test_reload_reads_edited_source_in_place(self):
    curry.reset(interpret='new')
    with tempfile.TemporaryDirectory() as work:
      source = Path(work) / 'Coin.curry'
      shutil.copyfile(Path(FLOW_PATH) / 'Coin.curry', source)
      M = curry.import_(source)
      old = M.inc(1)
      source.write_text(source.read_text().replace('inc x = x + 1', 'inc x = x + 2'))
      self.assertIs(curry.reload(M), M)
      self.assertEqual(curry.eval(M.inc(1)).one(), 3)
      with self.assertRaises(curry.StaleError):
        curry.eval(old).one()


if __name__ == '__main__':
  unittest.main()
