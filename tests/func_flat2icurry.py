import cytest # from ./lib; must be first
import flat2icurry_oracle as oracle
from curry.toolchain.flat2icurry import bindingopt as bo, flatcurry as fc
from curry.utility import maxrecursion
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

  def check_pairs(self, pairs, importdirs):
    results = oracle.check_pairs(pairs, importdirs)
    self.assertEqual(oracle.summarize(results), (len(pairs), 0, 0), oracle.report(results))

  def on_disk_fcys(self):
    '''Every FlatCurry file of the front end under tests/data, sorted.'''
    fcys = []
    for dirpath, _, files in os.walk(DATA):
      for fn in files:
        if fn.endswith('.fcy'):
          fcy = os.path.join(dirpath, fn)
          location = oracle.f2i.product_path(fcy)
          if location is not None and location[1] == self.overlay.subdir:
            fcys.append(fcy)
    return sorted(fcys)

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
    archive, or from an import on this machine, whose route rewrote the
    FlatCurry file before the translation (section 8 of the README), so
    the plain translation of the file on disk is the ICurry beside it.  A
    pair made before the routes rewrote the file differs; rewrite the file
    (python -m curry.toolchain.flat2icurry.rewrite) or run sprite-make
    --rewrite-flat on the module.
    '''
    pairs = []
    for fcy in self.on_disk_fcys():
      if os.path.basename(fcy)[:-len('.fcy')] in ROUTE_DIFFERS:
        continue
      icy = oracle.expected_icy(fcy)
      if icy:
        pairs.append((fcy, icy))
    if not pairs:
      self.skipTest('no front-end products under tests/data')
    self.check_pairs(
        pairs, self.overlay.library_dirs() + LIBRARY_DIRS + CORPUS_IMPORT_DIRS
      )

  def test_writer_round_trip(self):
    '''
    The FlatCurry writer reproduces the front end's text byte for byte:
    every .fcy of the archive, the library included, and every one under
    tests/data that the front end wrote.  A file PAKCS rewrote (its
    preprocessing writes the showTerm format) is not the front end's text
    and is left out; there is none in the archive.
    '''
    archive = self.overlay.fcys()
    self.assertGreater(len(archive), 1200)
    checked = skipped = 0
    for fcy in archive + self.on_disk_fcys():
      with open(fcy, 'r', encoding='utf-8', newline='') as istream:
        text = istream.read()
      if not text.startswith('Prog '):
        self.assertFalse(fcy.startswith(self.overlay.directory), fcy)
        skipped += 1
        continue
      shown = fc.show(fc.read(text))
      if shown != text:
        self.fail('%s\n%s' % (fcy, oracle.first_difference(text, shown)))
      checked += 1
    self.assertGreaterEqual(checked, len(archive))

  def test_rewrite_is_idempotent(self):
    '''
    The binding optimization over an optimized program replaces nothing and
    gives the program back, and the optimized program survives the writer
    and the reader: the second run of a route over a rewritten file changes
    nothing.  Every .fcy of the archive, some of which the pass changes.
    '''
    changed = []
    for fcy in self.overlay.fcys():
      prog = fc.load(fcy)
      once, n = bo.transform_prog(prog)
      twice, m = bo.transform_prog(once)
      self.assertEqual(m, 0, fcy)
      # A deep term (a long string literal) compares below the default
      # recursion limit.
      with maxrecursion():
        self.assertTrue(twice == once, fcy)
        if n:
          changed.append(os.path.basename(fcy))
          self.assertTrue(fc.read(fc.show(once)) == once, fcy)
          self.assertIsNot(bo.optimize_bindings(prog), prog)
        else:
          self.assertIs(bo.optimize_bindings(prog), prog)
    self.assertTrue(changed, 'no module of the archive has a required equality')

  def test_cli_overlay(self):
    '''The --overlay option of the harness checks the same files.'''
    expected = len(self.overlay.library_pairs()) + len(self.overlay.test_pairs())
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
      status = oracle.main(['-q', '--overlay'])
    self.assertEqual(status, 0, stdout.getvalue())
    last = stdout.getvalue().strip().splitlines()[-1]
    self.assertEqual(last, 'equal %d / different 0 / failed 0' % expected)
