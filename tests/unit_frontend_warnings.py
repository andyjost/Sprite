'''
Tests of the warnings of the Curry front end (issue #96).

The front end warns on overlapping rules, under which ``build 0 = ...;
build n = ...`` compiles to a choice with an infinite alternative.  A run of
the front end reports that warning once per module through the log of
curry.toolchain._frontend at the WARNING level, with the text of the front
end; the other warnings (non-exhaustive patterns, missing signatures) stay
quiet.  The environment variable SPRITE_FRONTEND_WARNINGS set to 0 silences
the warnings for a process; the test library sets it, so the tests here
set it to 1 for themselves.  The module compiles once from source and once
from its products or from the ICurry cache: the warning appears once.
'''
import cytest # from ./lib; must be first
from cytest.logging import capture_log
from curry import cache, config, toolchain
from curry.toolchain import _frontend
import curry, logging, os, shutil, subprocess, sys, tempfile, unittest
from unittest import mock

# The rules of build overlap, so the front end warns; the guard keeps the
# second alternative of build 0 finite (it fails), so main has one value.
OVERLAP = '''
module %s where

build :: Int -> [Int]
build 0 = []
build n | n > 0 = n : build (n - 1)

partial :: Maybe Int -> Int
partial (Just x) = x

main :: [Int]
main = build 3
'''

MESSAGE = 'potentially non-deterministic due to overlapping rules'
OTHER = 'non-exhaustive'

def warnings_of(log):
  '''The WARNING records of a capture.'''
  return log.data.get(logging.WARNING, [])

class TestFrontendWarnings(cytest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    if config.curry_frontend() is None:
      raise unittest.SkipTest('the Curry front end is not configured')

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, self.tmpdir, True)
    patcher = mock.patch.dict(os.environ, {_frontend.WARNINGS_VARIABLE: '1'})
    patcher.start()
    self.addCleanup(patcher.stop)

  def write(self, name):
    path = os.path.join(self.tmpdir, name + '.curry')
    with open(path, 'w', encoding='utf-8') as ostream:
      ostream.write(OVERLAP % name)
    return path

  def with_cache(self, filename):
    '''Routes the ICurry cache to a file of this test.'''
    patcher = mock.patch.dict(os.environ, {'SPRITE_CACHE_FILE': filename})
    patcher.start()
    self.addCleanup(patcher.stop)
    cache.reset()
    self.addCleanup(cache.reset)

  def test_warnings_by_file(self):
    '''The text of the front end is split into warnings and grouped by file.'''
    text = (
        '\nB.curry:6:1-7:7 Warning:\n    Function `g\' is potentially '
        'non-deterministic due to overlapping rules\n   | \n 6 | g 0 = 0\n'
        '   | ^^^^^^^...\n\n/x/C.curry:2:1-2:5 Warning:\n    one\n\n'
        'B.curry:9:1-9:14 Warning:\n    two\n'
      )
    groups = _frontend.warnings_by_file(text)
    self.assertEqual([key for key, _ in groups], ['B.curry', '/x/C.curry'])
    self.assertEqual(groups[0][1].count('Warning:'), 2)
    self.assertTrue(groups[0][1].startswith('B.curry:6:1-7:7 Warning:'))
    self.assertEqual(groups[1][1], '/x/C.curry:2:1-2:5 Warning:\n    one')
    self.assertEqual(_frontend.warnings_by_file(''), [])
    self.assertEqual(_frontend.warnings_by_file('\n\n'), [])
    self.assertEqual(
        _frontend.warnings_by_file('something else\n'), [(None, 'something else')]
      )
    with capture_log('curry.toolchain._frontend') as log:
      _frontend.report_warnings(text, '/m')
    records = warnings_of(log)
    self.assertEqual(len(records), 2)
    self.assertTrue(
        records[0].startswith('the Curry front end warns on module B (/m/B.curry):\n')
      )
    self.assertIn('overlapping rules', records[0])
    self.assertTrue(
        records[1].startswith('the Curry front end warns on module C (/x/C.curry):\n')
      )
    with capture_log('curry.toolchain._frontend') as log:
      _frontend.report_warnings('', '/m')
    self.assertEqual(warnings_of(log), [])

  def test_import_warns_once(self):
    '''
    curry.import_ reports the warning on overlapping rules once, with the
    module name, and nothing on the non-exhaustive function.  The second
    import, from the products, and the third, from the ICurry cache, report
    nothing: the front end does not run.
    '''
    self.with_cache(os.path.join(self.tmpdir, 'cache.db'))
    self.write('OverlapImport')
    with capture_log('curry.toolchain._frontend') as log:
      M = curry.import_('OverlapImport', currypath=[self.tmpdir])
    self.assertEqual(list(curry.eval(M.main, converter='topython')), [[3, 2, 1]])
    records = warnings_of(log)
    self.assertEqual(len(records), 1, records)
    self.assertIn('module OverlapImport (', records[0])
    self.assertEqual(records[0].count(MESSAGE), 1)
    self.assertIn('`build\'', records[0])
    self.assertNotIn(OTHER, records[0])
    # From the products.
    curry.reload()
    with capture_log('curry.toolchain._frontend') as log:
      curry.import_('OverlapImport', currypath=[self.tmpdir])
    self.assertEqual(warnings_of(log), [])
    # From the cache: the products are gone, the entry is not.
    curry.reload()
    shutil.rmtree(os.path.join(self.tmpdir, '.curry'))
    with capture_log('curry.toolchain._frontend') as log:
      curry.import_('OverlapImport', currypath=[self.tmpdir])
    self.assertEqual(warnings_of(log), [])
    self.assertFalse(
        os.path.exists(_frontend.flatcurryfile(os.path.join(self.tmpdir, 'OverlapImport.curry')))
      )

  def test_compile_warns_once(self):
    '''curry.compile reports the warning once; a quiet process reports nothing.'''
    # A private cache: the runner shares one cache file between the processes
    # of the two backends, and a hit on the text compiled by the other process
    # runs no front end and warns no more.
    self.with_cache(os.path.join(self.tmpdir, 'cache.db'))
    with capture_log('curry.toolchain._frontend') as log:
      M = curry.compile(OVERLAP % 'OverlapText', modulename='OverlapText')
    records = warnings_of(log)
    self.assertEqual(len(records), 1, records)
    self.assertIn('module OverlapText (', records[0])
    self.assertIn(MESSAGE, records[0])
    self.assertNotIn(OTHER, records[0])
    self.assertEqual(list(curry.eval(M.main, converter='topython')), [[3, 2, 1]])
    with mock.patch.dict(os.environ, {_frontend.WARNINGS_VARIABLE: '0'}):
      with capture_log('curry.toolchain._frontend') as log:
        curry.compile(OVERLAP % 'OverlapQuiet', modulename='OverlapQuiet')
    self.assertEqual(warnings_of(log), [])

  def test_sprite_make_warns_once(self):
    '''
    sprite-make prints the warning once, on its standard error, when the
    front end runs; a second run finds the module current and prints
    nothing; -q and SPRITE_FRONTEND_WARNINGS=0 print nothing.
    '''
    makeprg = os.path.join(os.environ['SPRITE_HOME'], 'bin', 'sprite-make')
    curryfile = self.write('OverlapMake')
    def make(*args, **env):
      environment = dict(os.environ, SPRITE_CACHE_FILE='')
      environment.update(env)
      return subprocess.run(
          [makeprg] + list(args), env=environment, stdout=subprocess.PIPE
        , stderr=subprocess.PIPE, text=True, timeout=300, cwd=self.tmpdir
        )
    proc = make('--icy', curryfile)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stderr.count(MESSAGE), 1, proc.stderr)
    self.assertIn('[WARNING] the Curry front end warns on module OverlapMake (', proc.stderr)
    self.assertNotIn(OTHER, proc.stderr)
    proc = make('--icy', curryfile)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stderr, '')
    products = os.path.join(self.tmpdir, '.curry')
    shutil.rmtree(products)
    proc = make('--icy', '-q', curryfile)
    self.assertEqual((proc.returncode, proc.stderr), (0, ''))
    shutil.rmtree(products)
    proc = make('--icy', curryfile, SPRITE_FRONTEND_WARNINGS='0')
    self.assertEqual((proc.returncode, proc.stderr), (0, ''))

  def test_suite_is_quiet(self):
    '''The test library turns the warnings off for every test file.'''
    with mock.patch.dict(os.environ, {_frontend.WARNINGS_VARIABLE: '0'}):
      self.assertFalse(_frontend.frontend_warnings())
      self.write('OverlapOff')
      with capture_log('curry.toolchain._frontend') as log:
        toolchain.curry2icurry(
            os.path.join(self.tmpdir, 'OverlapOff.curry'), [], use_cache=False
          )
    self.assertEqual(warnings_of(log), [])
    # cytest sets the variable to 0 before the first import of curry when
    # the environment leaves it unset or empty, and keeps a value.
    code = (
        'import cytest, os\n'
        'print(os.environ.get(%r))\n' % _frontend.WARNINGS_VARIABLE
      )
    for value, expected in (None, '0'), ('', '0'), ('1', '1'), ('off', 'off'):
      env = {k: v for k, v in os.environ.items() if k != _frontend.WARNINGS_VARIABLE}
      if value is not None:
        env[_frontend.WARNINGS_VARIABLE] = value
      proc = subprocess.run(
          [sys.executable, '-B', '-c', code], env=env, capture_output=True
        , text=True, timeout=120
        )
      self.assertEqual(proc.returncode, 0, proc.stderr)
      self.assertEqual(proc.stdout.strip(), expected, repr(value))
    with mock.patch.dict(os.environ):
      del os.environ[_frontend.WARNINGS_VARIABLE]
      self.assertTrue(_frontend.frontend_warnings())

if __name__ == '__main__':
  unittest.main()
