import cytest # from ./lib; must be first
import flat2icurry_oracle as oracle
from curry.toolchain.flat2icurry import bindingopt as bo, flatcurry as fc
from curry.utility import maxrecursion
from curry import config, toolchain
from curry.toolchain import _frontend, _system
import contextlib, io, os, re, shutil, sys, tempfile, unittest

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
    archive, or from an import on this machine, whose route rewrote every
    FlatCurry file its run of the front end wrote before the translation
    (section 8 of the README), so the plain translation of the file on
    disk is the ICurry beside it.

    One writer outside the toolchain leaves a FlatCurry file in the text
    of the front end: the PAKCS oracle (tests/oracle, tests/oracle_type).
    Its ``:load M`` runs the front end, which compiles every module of the
    chain whose files are stale for it (an import whose interface is older
    than the interface of one of its own imports among them), and its
    ``:eval`` runs the front end once more, for the goal, with the targets
    ``--acy --flat``, which compiles every module without an ``.acy`` file
    again.  The binding optimization of PAKCS runs over the modules it
    compiles to Prolog, not over those files.  So the check accepts such a
    file when the pass over it in memory translates to the ICurry beside
    it (accept_unrewritten of flat2icurry_oracle.check_file), and reports
    how many pairs needed it.  A pair that differs either way is a product
    made before the routes rewrote the file, or a real difference; rewrite
    the module (sprite-make --rewrite-flat M) or the file alone (python -m
    curry.toolchain.flat2icurry.rewrite M.fcy).  TestUnrewrittenFile pins
    the acceptance on a pair of its own.
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
    results = oracle.check_pairs(
        pairs, self.overlay.library_dirs() + LIBRARY_DIRS + CORPUS_IMPORT_DIRS
      , accept_unrewritten=True
      )
    self.assertEqual(
        oracle.summarize(results), (len(pairs), 0, 0), oracle.report(results)
      )
    unrewritten = [r.fcyfile for r in results if r.unrewritten]
    if unrewritten:
      sys.stderr.write(
          '\n%d of %d FlatCurry files on disk are in the text of the front '
          'end beside an ICurry file of the rewritten program (a writer '
          'outside the toolchain, such as the PAKCS oracle, wrote them):\n  %s\n'
              % (len(unrewritten), len(pairs), '\n  '.join(unrewritten))
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


class TestUnrewrittenFile(cytest.TestCase):
  '''
  The on-disk check over a pair that a writer outside the toolchain leaves:
  a FlatCurry file in the text of the front end beside an ICurry file of
  the rewritten program.  The pair is made here, in a scratch directory,
  as the PAKCS oracle makes one (see test_products_on_disk): the route
  converts the module, then a plain run of the front end writes the
  FlatCurry file again without the rewrite.
  '''

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    if config.curry_frontend() is None:
      raise unittest.SkipTest('the Curry front end is not configured')

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, self.tmpdir, True)

  def test_unrewritten_file_beside_rewritten_icurry(self):
    curryfile = os.path.join(self.tmpdir, 'Guard.curry')
    with open(curryfile, 'w', encoding='utf-8') as ostream:
      ostream.write(
          'module Guard where\n'
          'f :: Int -> Int\n'
          'f x | x == 3 = x\n'
          'main :: Int\n'
          'main = f y where y free\n'
        )
    icy = toolchain.curry2icurry(curryfile, [], use_cache=False, quiet=True)
    fcy = _frontend.flatcurryfile(curryfile)
    with open(fcy, 'rb') as istream:
      rewritten = istream.read()
    self.assertIn(b'constrEq', rewritten)
    self.assertEqual(oracle.check_file(fcy, icyfile=icy).status, oracle.EQUAL)
    # A writer outside the toolchain: the front end alone, as PAKCS runs it.
    os.unlink(fcy)
    _system.pexec(
        _frontend.command(curryfile, [], quiet=True), cwd=self.tmpdir
      )
    with open(fcy, 'rb') as istream:
      unrewritten = istream.read()
    self.assertNotIn(b'constrEq', unrewritten)
    plain = oracle.check_file(fcy, icyfile=icy)
    self.assertEqual(plain.status, oracle.DIFFERENT)
    self.assertFalse(plain.unrewritten)
    accepted = oracle.check_file(fcy, icyfile=icy, accept_unrewritten=True)
    self.assertEqual(accepted.status, oracle.EQUAL, accepted.detail)
    self.assertTrue(accepted.unrewritten)
    self.assertIn('unrewritten', accepted.detail)
    # The check leaves the file as it is; check_pairs takes the keyword too.
    with open(fcy, 'rb') as istream:
      self.assertEqual(istream.read(), unrewritten)
    results = oracle.check_pairs([(fcy, icy)], accept_unrewritten=True)
    self.assertEqual(oracle.summarize(results), (1, 0, 0))
    # A corrupted oracle: the pass changes the program, but the optimized
    # program does not translate to this ICurry file, so the pair stays
    # DIFFERENT (the case of a file the pass leaves as it is follows).
    with open(icy, 'r', encoding='utf-8', newline='') as istream:
      text = istream.read()
    other = os.path.join(self.tmpdir, 'other.icy')
    with open(other, 'w', encoding='utf-8', newline='') as ostream:
      ostream.write(text.replace('constrEq', 'constrEQ'))
    corrupted = oracle.check_file(fcy, icyfile=other, accept_unrewritten=True)
    self.assertEqual(corrupted.status, oracle.DIFFERENT)
    self.assertFalse(corrupted.unrewritten)

  def test_pass_that_changes_nothing(self):
    '''
    A FlatCurry file the pass leaves as it is (no required equality) beside
    an ICurry file that differs: the acceptance does not apply, and the
    pair is DIFFERENT with ``unrewritten`` False.
    '''
    curryfile = os.path.join(self.tmpdir, 'Plain.curry')
    with open(curryfile, 'w', encoding='utf-8') as ostream:
      ostream.write(
          'module Plain where\n'
          'f :: Int -> Int\n'
          'f x = x + 1\n'
          'main :: Int\n'
          'main = f 3\n'
        )
    icy = toolchain.curry2icurry(curryfile, [], use_cache=False, quiet=True)
    fcy = _frontend.flatcurryfile(curryfile)
    prog = fc.load(fcy)
    self.assertIs(bo.optimize_bindings(prog), prog)
    self.assertEqual(oracle.check_file(fcy, icyfile=icy).status, oracle.EQUAL)
    with open(icy, 'r', encoding='utf-8', newline='') as istream:
      text = istream.read()
    self.assertIn('"Plain"', text)
    other = os.path.join(self.tmpdir, 'other.icy')
    with open(other, 'w', encoding='utf-8', newline='') as ostream:
      ostream.write(text.replace('"Plain"', '"Plane"'))
    for accept in False, True:
      result = oracle.check_file(fcy, icyfile=other, accept_unrewritten=accept)
      self.assertEqual(result.status, oracle.DIFFERENT)
      self.assertFalse(result.unrewritten)
