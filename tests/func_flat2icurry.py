import cytest # from ./lib; must be first
import flat2icurry_oracle as oracle
import contextlib, io, os, re, shutil, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, 'data')

# Where the FlatCurry interfaces of the library modules may be found on disk.
LIBRARY_DIRS = [os.path.join(ROOT, 'curry', 'lib')]
# The import directories of the corpora under tests/data/curry: a module
# of the kiel corpus imports from kiel/lib (CURRYPATH of func_kiel.py), so
# its FlatCurry resolves against that directory as well.
CORPUS_IMPORT_DIRS = [os.path.join(DATA, 'curry', 'kiel', 'lib')]

# The route through the front end looks through a type annotation at the root
# of a rule, which icurry 3.1.0 does not (see curry.toolchain._frontend).  The
# .icy it writes for these probe modules differs from the oracle: TypedRoot
# (the bindings under the annotation) and Externals (`failed :: Int` becomes
# IExempt).  Both are checked against the archive in unit_flat2icurry.py.
ROUTE_DIFFERS = {'TypedRoot', 'Externals'}

class TestWholeCorpus(cytest.TestCase):
  '''
  Runs the FlatCurry-to-ICurry port over the whole oracle: every file of the
  overlay archive, the library included, and every product that other test
  runs left on disk.  The fast version, a fixed sample of 60 files, is in
  unit_flat2icurry.py.
  '''

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    if oracle.overlay_archive() is None:
      raise unittest.SkipTest('the overlay archive is not in the repository')
    cls.tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    cls.overlay = oracle.Overlay.extract(cls.tmpdir)

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.tmpdir, ignore_errors=True)
    super().tearDownClass()

  def check_pairs(self, pairs, importdirs, accept_build_route=False):
    results = oracle.check_pairs(
        pairs, importdirs, accept_build_route=accept_build_route
      )
    self.assertEqual(oracle.summarize(results), (len(pairs), 0, 0), oracle.report(results))

  def test_library(self):
    '''The committed .icy files of the library.'''
    pairs = self.overlay.library_pairs()
    self.assertGreaterEqual(len(pairs), 8)
    self.check_pairs(pairs, self.overlay.library_dirs())

  def test_test_programs(self):
    '''
    Every test program of the archive.  No .icy of the archive is left out.
    A hierarchical module has two FlatCurry files (its own directory and the
    root it was imported from) and one .icy.
    '''
    pairs = self.overlay.test_pairs()
    self.assertGreater(len(pairs), 0)
    self.assertEqual(sorted(set(icy for _, icy in pairs)), self.overlay.test_icys())
    self.check_pairs(pairs, self.overlay.library_dirs())

  def test_products_on_disk(self):
    '''
    The products under tests/data on this machine.  They come from the
    archive, or from an import on this machine, which translates with the
    settings of the build route (the binding optimization among them); a
    product of the build route is equal when the port reproduces it with
    those settings.
    '''
    pairs = []
    for dirpath, _, files in os.walk(DATA):
      for fn in files:
        if not fn.endswith('.fcy') or fn[:-len('.fcy')] in ROUTE_DIFFERS:
          continue
        fcy = os.path.join(dirpath, fn)
        location = oracle.f2i.product_path(fcy)
        if location is None or location[1] != self.overlay.subdir:
          continue
        icy = oracle.expected_icy(fcy)
        if icy:
          pairs.append((fcy, icy))
    if not pairs:
      self.skipTest('no front-end products under tests/data')
    self.check_pairs(
        sorted(pairs)
      , self.overlay.library_dirs() + LIBRARY_DIRS + CORPUS_IMPORT_DIRS
      , accept_build_route=True
      )

  def test_cli_overlay(self):
    '''The --overlay option of the harness checks the same files.'''
    expected = len(self.overlay.library_pairs()) + len(self.overlay.test_pairs())
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
      status = oracle.main(['-q', '--overlay'])
    self.assertEqual(status, 0, stdout.getvalue())
    last = stdout.getvalue().strip().splitlines()[-1]
    self.assertEqual(last, 'equal %d / different 0 / failed 0' % expected)
