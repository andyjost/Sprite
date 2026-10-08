'''
Tests for the staleness of a pair made before the binding rewrite (issue
#101): an ICurry file translated from the FlatCurry of the front end before
the binding optimization rewrote the file.  Such a pair is current by the
file times (a tree made before the rewrite, the products of the overlay
archive, a copy of either), and its program binds no variable through ==
in a guard, where PAKCS binds one.  The rule of the toolchain
(curry.toolchain._curry2icurry.translated_before_rewrite) counts the ICurry
file as stale, and the route makes it again at the first import.  The key
of the ICurry cache names the version of the route
(curry.toolchain._frontend.ROUTE_VERSION), so an entry of a route without
the rewrite is never served.  A hit of the cache writes the ICurry file and
runs the pass over the FlatCurry file of the front end as well
(curry.toolchain._curry2icurry.rewrite_on_hit), so the pair agrees as after
a translation.  sprite-make reports the pairs it made again and the pairs
the cache served, and the prepare pass of the test runner reads the line
(unit_runner.py).
'''
import cytest # from ./lib; must be first
from curry import cache, config, toolchain
from curry.toolchain import _curry2icurry, _frontend, _system, plans
from curry.utility import filesys
import curry, os, shutil, sqlite3, subprocess, tempfile, time, unittest
from unittest import mock

SUBDIR = os.path.join('.curry', config.intermediate_subdir())

def guard(name):
  '''A module that binds a free variable through == in a guard.'''
  return (
      'module %s where\n'
      'f :: Int -> Int\n'
      'f x | x == 3 = x\n'
      'main :: Int\n'
      'main = f y where y free\n' % name
    )

def ifeq(name):
  '''A module with an equality outside a required position.'''
  return (
      'module %s where\n'
      'f :: Int -> Int\n'
      'f x = if x == 3 then 1 else 0\n'
      'main :: Int\n'
      'main = f 3\n' % name
    )

def plain(name):
  '''A module without an equality.'''
  return (
      'module %s where\n'
      'f :: Int -> Int\n'
      'f x = x + 1\n'
      'main :: Int\n'
      'main = f 3\n' % name
    )

def readbytes(filename):
  with open(filename, 'rb') as istream:
    return istream.read()

def mtimes(*filenames):
  return [os.stat(filename).st_mtime_ns for filename in filenames]

def icurry_plan():
  return plans.makeplan(None, plans.MAKE_ICURRY | plans.MAKE_JSON)

class PreRewriteCase(cytest.TestCase):
  '''The scratch directory, the cache off, and the pair of the old route.'''

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    if config.curry_frontend() is None:
      raise unittest.SkipTest('the Curry front end is not configured')

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, self.tmpdir, True)
    # Without the ICurry cache: a hit writes the ICurry of the cache, not
    # the translation of the pair on disk.  A test of the cache names a
    # file of its own (with_cache).
    self.set_cache_file('')
    _curry2icurry.reset_counts()
    self.addCleanup(_curry2icurry.reset_counts)

  def set_cache_file(self, filename):
    patcher = mock.patch.dict(os.environ, {'SPRITE_CACHE_FILE': filename})
    patcher.start()
    self.addCleanup(patcher.stop)
    cache.reset()
    self.addCleanup(cache.reset)

  def write(self, name, text):
    path = os.path.join(self.tmpdir, name + '.curry')
    with open(path, 'w', encoding='utf-8') as ostream:
      ostream.write(text)
    return path

  def pre_rewrite_pair(self, curryfile):
    '''
    The products of a module as the route made them before the rewrite
    existed: the FlatCurry file of the front end, its plain translation,
    and the copies of the interfaces beside the ICurry file.  Both files
    are newer than the source, so the pair is current by the times.  A
    file of the front end from an earlier contact is removed first, so the
    front end writes its text again.
    '''
    old = _frontend.flatcurryfile(curryfile)
    if os.path.exists(old):
      os.unlink(old)
    fcy = _frontend.curry2flat(curryfile, [self.tmpdir], quiet=True, rewrite=False)
    icy = toolchain.icurryfilename(curryfile)
    os.makedirs(os.path.dirname(icy), exist_ok=True)
    _frontend.flat2icy(fcy, icy, _frontend.searchdirs(curryfile, [self.tmpdir]))
    converter = _curry2icurry.Curry2ICurryConverter(curry2icurry='frontend')
    converter.place_interfaces(curryfile, icy)
    self.assertNotIn(b'constrEq', readbytes(fcy))
    self.assertNotIn(b'constrEq', readbytes(icy))
    self.assertTrue(filesys.newer(icy, curryfile))
    self.assertTrue(filesys.newer(fcy, curryfile))
    return fcy, icy

  def convert(self, curryfile, **kwds):
    kwds.setdefault('curry2icurry', 'frontend')
    kwds.setdefault('quiet', True)
    return toolchain.curry2icurry(curryfile, [self.tmpdir], **kwds)

  def current(self, curryfile):
    return toolchain.currentfile(
        icurry_plan(), curryfile, [self.tmpdir], is_sourcefile=True
      )

  def no_front_end(self):
    '''
    Fails the test when the front end runs from here on.  Another command
    through _system.pexec runs as usual: under interpret:off the C++
    backend compiles the module with the C++ compiler through it.
    '''
    frontend = config.curry_frontend()
    real = _system.pexec
    def pexec(cmd, *args, **kwds):
      if cmd[0] == frontend:
        raise AssertionError('the front end ran: %s' % ' '.join(cmd))
      return real(cmd, *args, **kwds)
    patcher = mock.patch.object(_system, 'pexec', pexec)
    patcher.start()
    self.addCleanup(patcher.stop)

  def evaluate(self, name):
    module = curry.import_(name, currypath=[self.tmpdir])
    return list(curry.eval(module.main, converter='topython'))


class TestStaleness(PreRewriteCase):
  '''The rule on the pairs a tree may hold.'''

  def test_pre_rewrite_pair_is_stale(self):
    '''
    The pair of the old route is stale: the plan starts at the source, the
    import runs the step again (the front end leaves the current file, the
    pass rewrites it, the translation follows), the program binds its
    variable, and a second import touches nothing.
    '''
    curryfile = self.write('GuardA', guard('GuardA'))
    fcy, icy = self.pre_rewrite_pair(curryfile)
    self.assertTrue(_curry2icurry.translated_before_rewrite(curryfile, icy))
    self.assertTrue(_curry2icurry.icurry_is_stale(icy))
    self.assertIn(os.path.abspath(icy), _curry2icurry.stale_pairs)
    self.assertEqual(self.current(curryfile), curryfile)
    self.assertEqual(_curry2icurry.pairs_refreshed(), 0)
    before = mtimes(fcy, icy)
    self.assertEqual(self.evaluate('GuardA'), [3])
    self.assertEqual(readbytes(fcy).count(b'constrEq'), 1)
    self.assertEqual(readbytes(icy).count(b'constrEq'), 1)
    after = mtimes(fcy, icy)
    self.assertGreater(after[0], before[0])
    self.assertGreater(after[1], before[1])
    self.assertFalse(_curry2icurry.translated_before_rewrite(curryfile, icy))
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))
    self.assertEqual(_curry2icurry.pairs_refreshed(), 1)
    # The pair is current now: a make through the plan runs no front end
    # and changes no time.
    self.no_front_end()
    self.assertNotEqual(self.current(curryfile), curryfile)
    made = toolchain.makecurry(icurry_plan(), curryfile, [self.tmpdir], is_sourcefile=True)
    self.assertTrue(made.endswith('.json'), made)
    self.assertEqual(mtimes(fcy, icy), after)
    self.assertEqual(_curry2icurry.pairs_refreshed(), 1)

  def test_current_pair_is_not_touched(self):
    '''
    Three current pairs, one per tier of the check: a file the pass
    rewrote (constrEq in the text), a file with an equality outside a
    required position (the pass over the text counts zero), and a file
    without an equality name.  None is stale; an import runs no front end
    and changes no time.
    '''
    cases = [
        ('GuardB', guard('GuardB'), 3), ('IfEq', ifeq('IfEq'), 1)
      , ('Plain', plain('Plain'), 4)
      ]
    files = {}
    for name, text, _ in cases:
      curryfile = self.write(name, text)
      icy = self.convert(curryfile)
      fcy = _frontend.flatcurryfile(curryfile)
      interfaces = [
          cache.interface_filename(icy, suffix) for suffix in cache.INTERFACE_SUFFIXES
        ]
      files[name] = (curryfile, icy, [fcy, icy] + interfaces)
    self.assertIn(b'constrEq', readbytes(files['GuardB'][2][0]))
    ifeq_text = readbytes(files['IfEq'][2][0])
    self.assertNotIn(b'constrEq', ifeq_text)
    self.assertIsNotNone(_curry2icurry.EQUALITY_NAME.search(ifeq_text))
    self.assertIsNone(_curry2icurry.EQUALITY_NAME.search(readbytes(files['Plain'][2][0])))
    self.no_front_end()
    for name, _, value in cases:
      curryfile, icy, products = files[name]
      self.assertFalse(_curry2icurry.translated_before_rewrite(curryfile, icy), name)
      self.assertFalse(_curry2icurry.icurry_is_stale(icy), name)
      self.assertEqual(self.current(curryfile), icy, name)
      before = mtimes(*products)
      self.assertEqual(self.evaluate(name), [value])
      self.assertEqual(mtimes(*products), before, name)
    self.assertEqual(_curry2icurry.stale_pairs, set())
    self.assertEqual(_curry2icurry.pairs_refreshed(), 0)

  def test_unrewritten_file_beside_rewritten_icurry(self):
    '''
    A writer outside the toolchain (the PAKCS oracle of the tests) writes
    the FlatCurry file again in the text of the front end, newer than the
    ICurry file of the rewritten program.  The product is right, so the
    pair is current: the route is not run again and again for it.
    '''
    curryfile = self.write('GuardC', guard('GuardC'))
    icy = self.convert(curryfile)
    fcy = _frontend.flatcurryfile(curryfile)
    os.unlink(fcy)
    _system.pexec(
        _frontend.command(curryfile, [self.tmpdir], quiet=True), cwd=self.tmpdir
      )
    self.assertNotIn(b'constrEq', readbytes(fcy))
    self.assertIn(b'constrEq', readbytes(icy))
    self.assertTrue(filesys.newer(fcy, icy))
    self.assertFalse(_curry2icurry.translated_before_rewrite(curryfile, icy))
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))
    self.no_front_end()
    self.assertEqual(self.current(curryfile), icy)

  def test_file_of_another_version_of_the_source(self):
    '''
    A FlatCurry file older than the source belongs to another version of
    the source (a hit in the ICurry cache writes no FlatCurry) and is not
    judged; the ICurry file stands by the times.
    '''
    curryfile = self.write('GuardD', guard('GuardD'))
    fcy, icy = self.pre_rewrite_pair(curryfile)
    self.assertTrue(_curry2icurry.icurry_is_stale(icy))
    stamp = os.stat(fcy).st_mtime_ns
    os.utime(curryfile, ns=(stamp + 1000000, stamp + 1000000))
    os.utime(icy, ns=(stamp + 2000000, stamp + 2000000))
    self.assertFalse(_curry2icurry.translated_before_rewrite(curryfile, icy))
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))
    self.assertEqual(self.current(curryfile), icy)
    # The source as new as the file is judged (the strict order of newer).
    os.utime(curryfile, ns=(stamp, stamp))
    self.assertTrue(_curry2icurry.icurry_is_stale(icy))

  def test_files_not_judged(self):
    '''
    Without the FlatCurry file of the front end, without a source, or with
    a FlatCurry text the pass cannot read, the ICurry file is not judged;
    a file that is not an ICurry file is not asked about.
    '''
    curryfile = self.write('GuardE', guard('GuardE'))
    fcy, icy = self.pre_rewrite_pair(curryfile)
    text = readbytes(fcy)
    os.unlink(fcy)
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))
    with open(fcy, 'wb') as ostream:
      ostream.write(text[:len(text) // 2])
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))
    with open(fcy, 'wb') as ostream:
      ostream.write(text)
    self.assertTrue(_curry2icurry.icurry_is_stale(icy))
    self.assertFalse(_curry2icurry.icurry_is_stale(curryfile))
    self.assertFalse(_curry2icurry.icurry_is_stale(icy[:-4] + '.json'))
    os.unlink(curryfile)
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))

  def test_system_library_is_left_out(self):
    '''
    The ICurry of a module of the Curry library of the installation is
    committed; the rule does not judge it, hierarchical modules included.
    '''
    root = config.system_curry_path()
    for name in config.syslibs():
      parts = name.split('.')
      curryfile = os.path.join(root, *parts) + '.curry'
      icy = os.path.join(root, *parts[:-1], SUBDIR, parts[-1] + '.icy')
      self.assertTrue(_curry2icurry.in_system_library(curryfile), name)
      self.assertFalse(_curry2icurry.translated_before_rewrite(curryfile, icy), name)
      self.assertFalse(_curry2icurry.icurry_is_stale(icy), name)
    self.assertFalse(_curry2icurry.in_system_library(os.path.join(self.tmpdir, 'X.curry')))

  def test_parse_once_per_process(self):
    '''
    The count of the pass over a FlatCurry file is kept for the process by
    the size and time of the file: a second check of the same file does
    not parse again, a file written again (another time) is parsed again,
    and the memo does not hide a change.
    '''
    curryfile = self.write('IfEqM', ifeq('IfEqM'))
    icy = self.convert(curryfile)
    fcy = _frontend.flatcurryfile(curryfile)
    with mock.patch.object(
        _curry2icurry.bindingopt, 'transform_prog'
      , wraps=_curry2icurry.bindingopt.transform_prog
      ) as parse:
      self.assertFalse(_curry2icurry.icurry_is_stale(icy))
      self.assertFalse(_curry2icurry.icurry_is_stale(icy))
      self.assertEqual(parse.call_count, 1)
      # The same text with a new time is parsed again.
      stamp = os.stat(fcy).st_mtime_ns + 1000000
      os.utime(fcy, ns=(stamp, stamp))
      self.assertFalse(_curry2icurry.icurry_is_stale(icy))
      self.assertEqual(parse.call_count, 2)
      # A pre-rewrite text in its place is judged by its own parse.
      text = readbytes(fcy)
      guardfile = self.write('GuardQ', guard('GuardQ'))
      guardfcy, _ = self.pre_rewrite_pair(guardfile)
      with open(fcy, 'wb') as ostream:
        ostream.write(readbytes(guardfcy).replace(b'GuardQ', b'IfEqM'))
      self.assertNotIn(b'constrEq', readbytes(icy))
      self.assertTrue(_curry2icurry.translated_before_rewrite(curryfile, icy))
      self.assertEqual(parse.call_count, 3)
      with open(fcy, 'wb') as ostream:
        ostream.write(text)
      self.assertFalse(_curry2icurry.icurry_is_stale(icy))

  def test_large_file_is_not_judged(self):
    '''
    A FlatCurry file larger than PARSE_LIMIT is not parsed: the pair is
    not judged, and one warning per process names sprite-make
    --rewrite-flat.  The limit holds the cost of the check on an import;
    the parse costs about 0.3 ms per KB.
    '''
    curryfile = self.write('GuardL', guard('GuardL'))
    fcy, icy = self.pre_rewrite_pair(curryfile)
    self.assertTrue(_curry2icurry.icurry_is_stale(icy))
    size = os.path.getsize(fcy)
    with mock.patch.object(_curry2icurry, 'PARSE_LIMIT', size - 1):
      with mock.patch.object(
          _curry2icurry.bindingopt, 'transform_prog'
        , wraps=_curry2icurry.bindingopt.transform_prog
        ) as parse:
        with self.assertLogs(_curry2icurry.logger, 'WARNING') as logs:
          self.assertFalse(_curry2icurry.translated_before_rewrite(curryfile, icy))
          self.assertFalse(_curry2icurry.translated_before_rewrite(curryfile, icy))
        self.assertEqual(parse.call_count, 0)
      self.assertEqual(len(logs.output), 1)
      self.assertIn('sprite-make --rewrite-flat', logs.output[0])
      self.assertIn(fcy, logs.output[0])
      self.no_front_end()
      self.assertEqual(self.current(curryfile), icy)
    with mock.patch.object(_curry2icurry, 'PARSE_LIMIT', size):
      self.assertTrue(_curry2icurry.translated_before_rewrite(curryfile, icy))

  @unittest.skipIf(
      hasattr(os, 'geteuid') and os.geteuid() == 0, 'root writes a read-only file'
    )
  def test_read_only_pair_is_not_judged(self):
    '''
    A pre-rewrite pair whose FlatCurry file cannot be written again (a
    read-only file, or a read-only directory) is not judged: the import
    uses the pair as before the rule, and one warning per process names
    sprite-make --rewrite-flat.  A stale verdict would fail the import
    when the pass writes the file.
    '''
    curryfile = self.write('GuardR', guard('GuardR'))
    fcy, icy = self.pre_rewrite_pair(curryfile)
    directory = os.path.dirname(fcy)
    self.assertTrue(_curry2icurry.icurry_is_stale(icy))
    def restore():
      os.chmod(directory, 0o755)
      os.chmod(fcy, 0o644)
    self.addCleanup(restore)
    for path, mode in [(fcy, 0o444), (directory, 0o555)]:
      os.chmod(path, mode)
      try:
        with self.assertLogs(_curry2icurry.logger, 'WARNING') as logs:
          self.assertFalse(_curry2icurry.translated_before_rewrite(curryfile, icy))
          self.assertFalse(_curry2icurry.icurry_is_stale(icy))
        self.assertEqual(len(logs.output), 1, logs.output)
        self.assertIn('sprite-make --rewrite-flat', logs.output[0])
        self.assertIn(icy, logs.output[0])
      finally:
        os.chmod(path, 0o755 if path == directory else 0o644)
      _curry2icurry.reset_counts()
    os.chmod(fcy, 0o444)
    os.chmod(directory, 0o555)
    self.no_front_end()
    before = mtimes(fcy, icy)
    with self.assertLogs(_curry2icurry.logger, 'WARNING'):
      self.assertEqual(self.current(curryfile), icy)
      curry.import_('GuardR', currypath=[self.tmpdir])
    self.assertEqual(mtimes(fcy, icy), before)
    self.assertNotIn(b'constrEq', readbytes(icy))
    restore()
    self.assertTrue(_curry2icurry.icurry_is_stale(icy))

  def test_cost(self):
    '''
    The cost of the check: on the Prelude (the library is left out after
    a path comparison), on a file the pass rewrote (a read and a scan),
    and on a file with an equality outside a required position (the pass
    over the text, once per process; the memo answers after).  The best
    of five batches, so a loaded machine does not fail the test; the
    bounds are wide for the same reason.  Measured on the development
    machine: 0.05 ms, 0.1 ms, 1 ms for the parse and 0.1 ms after it.
    '''
    def best_ms(fn, n=20):
      best = None
      for _ in range(5):
        start = time.perf_counter()
        for _ in range(n):
          fn()
        elapsed = (time.perf_counter() - start) / n * 1000
        best = elapsed if best is None else min(best, elapsed)
      return best
    prelude = os.path.join(config.system_curry_path(), SUBDIR, 'Prelude.icy')
    self.assertTrue(os.path.isfile(prelude))
    cost = best_ms(lambda: _curry2icurry.icurry_is_stale(prelude))
    self.assertLess(cost, 2.0, 'the check on the Prelude costs %.3f ms' % cost)
    rewritten = self.convert(self.write('GuardF', guard('GuardF')))
    cost = best_ms(lambda: _curry2icurry.icurry_is_stale(rewritten))
    self.assertLess(cost, 5.0, 'the check on a rewritten file costs %.3f ms' % cost)
    parsed = self.convert(self.write('IfEqF', ifeq('IfEqF')))
    start = time.perf_counter()
    self.assertFalse(_curry2icurry.icurry_is_stale(parsed))
    cost = (time.perf_counter() - start) * 1000
    self.assertLess(cost, 25.0, 'the check with a parse costs %.3f ms' % cost)
    cost = best_ms(lambda: _curry2icurry.icurry_is_stale(parsed))
    self.assertLess(cost, 5.0, 'the check after the parse costs %.3f ms' % cost)


class TestCacheKey(PreRewriteCase):
  '''The version of the route in the key of the ICurry cache.'''

  def slot(self, curryfile, icy):
    return cache.Curry2ICurryCache.Slot(
        curryfile, icy, [self.tmpdir], (), tool='frontend'
      )

  def test_route_version_is_part_of_the_key(self):
    '''
    A bump of ROUTE_VERSION changes the key and leaves the digest of the
    route alone: the version is in the key of the ICurry cache alone, the
    product cache digests the ICurry text itself.
    '''
    self.assertEqual(_frontend.ROUTE_VERSION, 1)
    self.assertEqual(cache.route_version(), 1)
    curryfile = self.write('GuardK', guard('GuardK'))
    key = lambda: cache.icurry_cache_key(curryfile, [self.tmpdir], (), 'frontend')
    digest = cache.frontend_digest('frontend')
    now = key()
    with mock.patch.object(_frontend, 'ROUTE_VERSION', 0):
      self.assertEqual(cache.route_version(), 0)
      self.assertNotEqual(key(), now)
      self.assertEqual(cache.frontend_digest('frontend'), digest)
    self.assertEqual(key(), now)

  def test_pre_rewrite_entry_misses_and_the_new_entry_hits(self):
    '''
    An entry of the route before the rewrite (version 0, the ICurry of the
    pair as the route of that time stored it) is not found under the key
    of the route with the rewrite: the conversion misses, makes the pair
    again, and stores the new entry, which a later miss of the file is
    served from.  The old row stays in the table, unread.
    '''
    cachefile = os.path.join(self.tmpdir, 'cache', 'icurry.db')
    self.set_cache_file(cachefile)
    curryfile = self.write('GuardH', guard('GuardH'))
    fcy, icy = self.pre_rewrite_pair(curryfile)
    with mock.patch.object(_frontend, 'ROUTE_VERSION', 0):
      slot = self.slot(curryfile, icy)
      self.assertFalse(slot)
      slot.update()
      self.assertTrue(self.slot(curryfile, icy))
      self.assertNotIn(b'constrEq', readbytes(icy))
    stats = dict(cache.Curry2ICurryCache.stats)
    self.assertFalse(self.slot(curryfile, icy))
    self.assertEqual(cache.Curry2ICurryCache.stats['miss'], stats['miss'] + 1)
    self.assertTrue(_curry2icurry.icurry_is_stale(icy))
    self.assertEqual(self.convert(curryfile, use_cache=True), icy)
    self.assertEqual(readbytes(fcy).count(b'constrEq'), 1)
    self.assertEqual(readbytes(icy).count(b'constrEq'), 1)
    self.assertEqual(_curry2icurry.pairs_refreshed(), 1)
    os.unlink(icy)
    self.no_front_end()
    self.assertTrue(self.slot(curryfile, icy))
    self.assertEqual(readbytes(icy).count(b'constrEq'), 1)
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))
    cache.reset()
    db = sqlite3.connect(cachefile)
    try:
      rows = db.execute(
          'SELECT name, instr(text, ?) > 0 FROM [%s] ORDER BY created'
              % cache.Curry2ICurryCache.TABLE
        , ('constrEq',)
        ).fetchall()
    finally:
      db.close()
    self.assertEqual(rows, [('GuardH', 0), ('GuardH', 1)])


  def test_served_pair_is_counted_apart(self):
    '''
    The ICurry cache holds the entry of a module (a run of the route
    stored it), and the pair on disk is made pre-rewrite again (make
    overlay extracts the archive over the tree).  The next contact flags
    the pair, the cache writes the ICurry of the rewritten program, and
    the route rewrites the FlatCurry file as well (TestCacheHit): the pair
    agrees, and it is counted as served, not as translated again.
    '''
    cachefile = os.path.join(self.tmpdir, 'cache', 'icurry.db')
    self.set_cache_file(cachefile)
    curryfile = self.write('GuardS', guard('GuardS'))
    icy = self.convert(curryfile, use_cache=True)
    self.assertIn(b'constrEq', readbytes(icy))
    fcy, icy = self.pre_rewrite_pair(curryfile)
    _curry2icurry.reset_counts()
    self.assertTrue(_curry2icurry.icurry_is_stale(icy))
    self.no_front_end()
    self.assertEqual(self.convert(curryfile, use_cache=True), icy)
    self.assertIn(b'constrEq', readbytes(icy))
    self.assertIn(b'constrEq', readbytes(fcy))
    self.assertEqual(_curry2icurry.pairs_refreshed(), 0)
    self.assertEqual(_curry2icurry.pairs_served(), 1)
    # The pair agrees and is current now.
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))


class TestSpriteMake(PreRewriteCase):
  '''The line of sprite-make about the pairs it made again.'''

  def test_sprite_make_reports(self):
    '''
    sprite-make makes a pre-rewrite pair again and prints the count; a
    second run, and a run under -q, print nothing; under --jobs the counts
    of the children are summed into one line.
    '''
    makeprg = os.path.join(os.environ['SPRITE_HOME'], 'bin', 'sprite-make')
    env = dict(os.environ, SPRITE_CACHE_FILE='', CURRYPATH=self.tmpdir)
    def run(*args):
      return subprocess.run(
          [makeprg] + list(args), env=env, cwd=self.tmpdir, stdout=subprocess.PIPE
        , stderr=subprocess.PIPE, text=True, timeout=300
        )
    modules = {}
    for name in 'GuardM', 'GuardN', 'GuardO', 'GuardP':
      curryfile = self.write(name, guard(name))
      modules[name] = (curryfile,) + self.pre_rewrite_pair(curryfile)
    proc = run('--icy', modules['GuardM'][0])
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, 'sprite-make: pre-rewrite pairs: 1 translated again\n')
    self.assertIn(b'constrEq', readbytes(modules['GuardM'][1]))
    self.assertIn(b'constrEq', readbytes(modules['GuardM'][2]))
    proc = run('--icy', modules['GuardM'][0])
    self.assertEqual((proc.returncode, proc.stdout), (0, ''))
    proc = run('--icy', '-q', modules['GuardN'][0])
    self.assertEqual((proc.returncode, proc.stdout), (0, ''))
    self.assertIn(b'constrEq', readbytes(modules['GuardN'][2]))
    proc = run('--icy', '--jobs', '2', modules['GuardO'][0], modules['GuardP'][0])
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, 'sprite-make: pre-rewrite pairs: 2 translated again\n')
    for name in 'GuardO', 'GuardP':
      self.assertIn(b'constrEq', readbytes(modules[name][2]))
    usage = subprocess.check_output([makeprg, '--man', '--no-header'], env=dict(env, PAGER='cat')).decode('utf-8')
    self.assertIn('pre-rewrite pairs', usage)
    self.assertRegex(usage, r'from the\s+ICurry cache')
    # With the ICurry cache: the first run stores the entry; the pair made
    # pre-rewrite again is served from it, the line says so, and the hit
    # rewrites the FlatCurry file as well.
    cached = dict(env, SPRITE_CACHE_FILE=os.path.join(self.tmpdir, 'icurry.db'))
    def run_cached(*args):
      return subprocess.run(
          [makeprg] + list(args), env=cached, cwd=self.tmpdir, stdout=subprocess.PIPE
        , stderr=subprocess.PIPE, text=True, timeout=300
        )
    curryfile = self.write('GuardT', guard('GuardT'))
    fcy, icy = self.pre_rewrite_pair(curryfile)
    proc = run_cached('--icy', curryfile)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, 'sprite-make: pre-rewrite pairs: 1 translated again\n')
    self.pre_rewrite_pair(curryfile)
    proc = run_cached('--icy', curryfile)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(
        proc.stdout
      , 'sprite-make: pre-rewrite pairs: 0 translated again, 1 from the ICurry cache\n'
      )
    self.assertIn(b'constrEq', readbytes(icy))
    self.assertIn(b'constrEq', readbytes(fcy))


class TestCacheHit(PreRewriteCase):
  '''
  The route on a hit of the ICurry cache: the cache writes the ICurry file,
  and the route runs the binding optimization over the FlatCurry file of
  the front end beside the source (_curry2icurry.rewrite_on_hit), so the
  pair never disagrees because of the cache.
  '''

  def hit(self, curryfile, icy):
    '''Converts through the cache with the front end mocked away.'''
    self.no_front_end()
    stats = dict(cache.Curry2ICurryCache.stats)
    self.assertEqual(self.convert(curryfile, use_cache=True), icy)
    self.assertEqual(cache.Curry2ICurryCache.stats['hit'], stats['hit'] + 1)

  def test_hit_rewrites_a_file_that_needs_it(self):
    '''
    A hit on a module whose FlatCurry file holds a required equality
    leaves both files with constrEq: the text of the file is the text a
    translation writes, byte for byte.
    '''
    self.set_cache_file(os.path.join(self.tmpdir, 'cache', 'icurry.db'))
    curryfile = self.write('HitA', guard('HitA'))
    icy = self.convert(curryfile, use_cache=True)
    fcy = _frontend.flatcurryfile(curryfile)
    rewritten = readbytes(fcy)
    self.assertEqual(rewritten.count(b'constrEq'), 1)
    self.pre_rewrite_pair(curryfile)
    _curry2icurry.reset_counts()
    self.hit(curryfile, icy)
    self.assertEqual(readbytes(fcy), rewritten)
    self.assertEqual(readbytes(icy).count(b'constrEq'), 1)
    self.assertTrue(filesys.newer(fcy, curryfile))
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))
    self.assertEqual(self.evaluate('HitA'), [3])
    # The function alone: a second run replaces nothing.
    self.assertEqual(_curry2icurry.rewrite_on_hit(curryfile), 0)
    self.assertEqual(readbytes(fcy), rewritten)

  def test_hit_touches_no_file_without_a_required_equality(self):
    '''
    A hit on a module whose FlatCurry file needs no rewrite leaves the
    file alone: its bytes and its time stay.  A file without an equality
    name is not parsed; a file with one outside a required position is
    parsed and left.
    '''
    self.set_cache_file(os.path.join(self.tmpdir, 'cache', 'icurry.db'))
    cases = [('HitIfEq', ifeq('HitIfEq'), 1), ('HitPlain', plain('HitPlain'), 0)]
    files = {}
    for name, text, _ in cases:
      curryfile = self.write(name, text)
      icy = self.convert(curryfile, use_cache=True)
      fcy = _frontend.flatcurryfile(curryfile)
      files[name] = (curryfile, icy, fcy, (readbytes(fcy), mtimes(fcy)))
    for name, _, parses in cases:
      with self.subTest(name=name):
        curryfile, icy, fcy, before = files[name]
        os.unlink(icy)
        with mock.patch.object(
            _curry2icurry.bindingopt, 'transform_prog'
          , wraps=_curry2icurry.bindingopt.transform_prog
          ) as parse:
          self.hit(curryfile, icy)
        self.assertEqual(parse.call_count, parses)
        self.assertEqual((readbytes(fcy), mtimes(fcy)), before)
        self.assertTrue(os.path.isfile(icy))
        self.assertEqual(_curry2icurry.rewrite_on_hit(curryfile), 0)
        self.assertEqual((readbytes(fcy), mtimes(fcy)), before)

  def test_hit_leaves_a_file_of_another_version(self):
    '''
    A FlatCurry file older than the source belongs to another version of
    the source.  A hit leaves it as it is: a rewrite would make it current
    by the times for the front end.  A missing file is nothing to rewrite.
    '''
    self.set_cache_file(os.path.join(self.tmpdir, 'cache', 'icurry.db'))
    curryfile = self.write('HitV', guard('HitV'))
    icy = self.convert(curryfile, use_cache=True)
    fcy, icy = self.pre_rewrite_pair(curryfile)
    stamp = os.stat(fcy).st_mtime_ns + 1000000
    os.utime(curryfile, ns=(stamp, stamp))
    before = (readbytes(fcy), mtimes(fcy))
    self.assertNotIn(b'constrEq', before[0])
    self.assertIsNone(_curry2icurry.rewrite_on_hit(curryfile))
    self.hit(curryfile, icy)
    self.assertIn(b'constrEq', readbytes(icy))
    self.assertEqual((readbytes(fcy), mtimes(fcy)), before)
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))
    os.unlink(fcy)
    self.assertIsNone(_curry2icurry.rewrite_on_hit(curryfile))

  @unittest.skipIf(
      hasattr(os, 'geteuid') and os.geteuid() == 0, 'root writes a read-only directory'
    )
  def test_hit_with_a_read_only_directory_warns(self):
    '''
    A FlatCurry file the pass cannot write again (its directory is
    read-only) is left as it is, with one warning per process that names
    sprite-make --rewrite-flat; the hit stands and the program runs.
    '''
    self.set_cache_file(os.path.join(self.tmpdir, 'cache', 'icurry.db'))
    curryfile = self.write('HitR', guard('HitR'))
    icy = self.convert(curryfile, use_cache=True)
    fcy, icy = self.pre_rewrite_pair(curryfile)
    directory = os.path.dirname(fcy)
    os.chmod(directory, 0o555)
    self.addCleanup(os.chmod, directory, 0o755)
    before = (readbytes(fcy), mtimes(fcy))
    with self.assertLogs(_curry2icurry.logger, 'WARNING') as logs:
      self.hit(curryfile, icy)
      self.assertIsNone(_curry2icurry.rewrite_on_hit(curryfile))
    self.assertEqual(len(logs.output), 1, logs.output)
    self.assertIn('sprite-make --rewrite-flat', logs.output[0])
    self.assertIn(fcy, logs.output[0])
    self.assertIn(b'constrEq', readbytes(icy))
    self.assertEqual((readbytes(fcy), mtimes(fcy)), before)
    self.assertEqual(self.evaluate('HitR'), [3])

if __name__ == '__main__':
  unittest.main()
