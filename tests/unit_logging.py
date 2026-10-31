'''Logging is configured in each process that imports the installed package.'''
import cytest # from ./lib; must be first
import curry, os, shutil, subprocess, tempfile
from unittest import mock


class TestLogging(cytest.TestCase):
  def setUp(self):
    super().setUp()
    self.base = tempfile.mkdtemp(dir=os.path.join(os.path.dirname(__file__), '.cache'))
    self.addCleanup(shutil.rmtree, self.base)
    self.log = os.path.join(self.base, 'sprite.log')

  def child(self, code, **env):
    environment = dict(os.environ)
    for name in ('SPRITE_LOG_FILE', 'SPRITE_LOG_LEVEL'):
      environment.pop(name, None)
    environment.update(env)
    with mock.patch.dict(os.environ, environment, clear=True):
      return cytest.run_in_subprocess(code, 120, address_space=6 << 30)

  def decisions(self, text):
    self.assertIn('process: backend=cxx', text)
    self.assertIn('interpret=', text)
    self.assertIn('jit=', text)
    self.assertIn('rotation=', text)
    self.assertIn('installation=', text)
    self.assertIn('module Prelude: compiled object loaded (', text)
    self.assertIn('module LoggingText: interpreted (no object)', text)

  code = "import curry; curry.compile('main = 42', name='LoggingText')"

  def test_file_and_append(self):
    for _ in range(2):
      proc = self.child(self.code, SPRITE_LOG_LEVEL='info', SPRITE_LOG_FILE=self.log)
      self.assertEqual(proc.returncode, 0, proc.stderr)
    with open(self.log) as stream:
      text = stream.read()
    self.decisions(text)
    self.assertEqual(text.count('process: backend='), 2)
    self.assertRegex(text, r'INFO \d+ curry[\w.]*: ')
    self.assertEqual(proc.stderr, '')

  def test_stderr(self):
    proc = self.child(self.code, SPRITE_LOG_LEVEL='INFO')
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.decisions(proc.stderr)

  def test_default_is_quiet(self):
    proc = self.child(self.code)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stderr, '')

  def test_default_warning_is_not_duplicated(self):
    proc = self.child("""
import curry
from curry.backends.cxx import tiered
tiered._warn_once('logging-default-test', 'logging default warning marker')
""")
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stderr.count('logging default warning marker'), 1)
    self.assertIn('CurryWarning', proc.stderr)

  def test_invalid_level(self):
    proc = self.child('import curry', SPRITE_LOG_LEVEL='invalid')
    self.assertNotEqual(proc.returncode, 0)
    self.assertIn("SPRITE_LOG_LEVEL should be one of 'DEBUG', 'INFO', 'WARNING', 'ERROR' or 'CRITICAL', not 'INVALID'", proc.stderr)

  def test_reload_keeps_one_handler_and_root_untouched(self):
    proc = self.child("""
import logging
root = logging.getLogger()
before = (list(root.handlers), root.level)
import curry, importlib
importlib.reload(curry.config)
assert (root.handlers, root.level) == before
assert len(logging.getLogger('curry').handlers) == 1
logging.getLogger('curry').info('logging reload marker')
""", SPRITE_LOG_LEVEL='INFO', SPRITE_LOG_FILE=self.log)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    with open(self.log) as stream:
      text = stream.read()
    self.assertEqual(text.count('logging reload marker'), 1)
    self.assertEqual(text.count('process: backend='), 1)

  def test_warning_keeps_warning_path_and_logs_once(self):
    proc = self.child("""
import curry, warnings
from curry.backends.cxx import tiered
with warnings.catch_warnings(record=True) as notices:
  warnings.simplefilter('always', curry.CurryWarning)
  for _ in range(2):
    tiered._warn_once('logging-test', 'logging warning marker')
assert len(notices) == 1
assert issubclass(notices[0].category, curry.CurryWarning)
""", SPRITE_LOG_FILE=self.log)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    with open(self.log) as stream:
      text = stream.read()
    self.assertEqual(text.count('logging warning marker'), 1)
    self.assertIn('WARNING', text)
    self.assertNotIn('process:', text)

  def test_off_does_not_report_a_pending_compile_as_interpreted(self):
    proc = self.child("""
import curry
curry.reset(interpret='off')
curry.compile('main = 42', name='LoggingPending')
""", SPRITE_LOG_LEVEL='INFO', SPRITE_LOG_FILE=self.log)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    with open(self.log) as stream:
      text = stream.read()
    self.assertNotIn('module LoggingPending: interpreted', text)

  def test_background_child_and_swap_share_file(self):
    source = os.path.join(self.base, 'LoggingBackground.curry')
    with open(source, 'w') as stream:
      stream.write('module LoggingBackground where\nmain = 42\n')
    proc = self.child("""
import curry
from curry.backends.cxx import tiered
curry.reset(interpret='tiered')
curry.path.insert(0, %r)
module = curry.import_('LoggingBackground')
assert tiered.wait(timeout=90)
assert list(curry.eval(module.main)) == [42]
""" % self.base, SPRITE_LOG_LEVEL='INFO', SPRITE_LOG_FILE=self.log)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    with open(self.log) as stream:
      text = stream.read()
    self.assertRegex(text, r'module LoggingBackground: background compile started \(pid \d+\)')
    self.assertRegex(text, r'module LoggingBackground: background compile finished in [\d.]+ s, swapped')

  def test_product_cache(self):
    source = os.path.join(self.base, 'LoggingProduct.curry')
    with open(source, 'w') as stream:
      stream.write('module LoggingProduct where\nmain = 42\n')
    environment = dict(os.environ, SPRITE_LOG_LEVEL='INFO', SPRITE_LOG_FILE=self.log,
        SPRITE_PRODUCT_CACHE=os.path.join(self.base, 'products'))
    command = cytest.limit_prefix(6 << 30, 120) + [curry.config.sprite_make(), '--so', source]
    for attempt in range(2):
      if attempt:
        products = os.path.join(self.base, '.curry', curry.config.intermediate_subdir())
        for suffix in ('.so', '.so.abi', '.cpp'):
          os.unlink(os.path.join(products, 'LoggingProduct' + suffix))
      proc = subprocess.run(command, capture_output=True, text=True, env=environment)
      self.assertEqual(proc.returncode, 0, proc.stderr)
      with open(self.log) as stream:
        text = stream.read()
      self.assertIn('module LoggingProduct: product cache ' + ('hit (' if attempt else 'miss'), text)
    self.assertIn('module LoggingProduct: product cache stored', text)
