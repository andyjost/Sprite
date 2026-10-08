'''
Tests of the product cache (curry.toolchain._productcache): the compiled
products of a module, kept outside its tree under a key made from what they
depend on, and placed beside the source instead of a compile.

The cache of these tests lives in a scratch directory under tests/.cache,
and so do the modules: the cache leaves out a module in the temporary
directory of the system (_productcache.excluded), where the other test
files compile theirs.  The tests of the generic parts (the key, the store,
the lookup, the restore, the race of two writers) run on both backends with
stand-in files.  The tests of the compile steps belong to the C++ backend.
'''
import cytest # from ./lib; must be first
from cytest.logging import capture_log
from curry import config
from curry.toolchain import _productcache, plans, makecurry, _findcurry, _system
from curry.tools import make
from curry.utility.binding import binding
from unittest import mock
import contextlib, curry, gc, importlib, io, itertools, json, logging, os
import shutil, stat, tempfile, time, unittest, zlib

TESTDIR = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.path.join(TESTDIR, '.cache')

class ProductCacheTestCase(cytest.TestCase):
  '''A scratch cache root and a source directory, both under tests/.cache.'''
  counter = itertools.count()

  def setUp(self):
    super().setUp()
    os.makedirs(SCRATCH, exist_ok=True)
    self.base = tempfile.mkdtemp(dir=SCRATCH, prefix='product-cache-')
    self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
    self.root = os.path.join(self.base, 'cache')
    self.srcdir = os.path.join(self.base, 'src')
    self.subdir = os.path.join(
        self.srcdir, '.curry', config.intermediate_subdir()
      )
    os.makedirs(self.subdir)
    patcher = mock.patch.dict(os.environ, {'SPRITE_PRODUCT_CACHE': self.root})
    patcher.start()
    self.addCleanup(patcher.stop)
    _productcache.reset_counts()

  def new_name(self):
    return 'ProductCacheTest%d' % next(self.counter)

  def write_source(self, name, text):
    '''Writes a Curry source into the source directory.  Returns its path.'''
    path = os.path.join(self.srcdir, name + '.curry')
    with open(path, 'w') as stream:
      stream.write(text)
    return path

  def write_json(self, value, name=None):
    '''Writes the JSON of a module whose goal returns ``value``.  Returns its name.'''
    if name is None:
      name = self.new_name()
    with open(self.cached_file(name, '.json.z'), 'wb') as stream:
      stream.write(zlib.compress(cytest.json_module(name, value).encode('utf-8')))
    return name

  def cached_file(self, name, suffix):
    return os.path.join(self.subdir, name + suffix)

  def write_products(
      self, name, so=b'object', cpp='// FORMAT: 12\n// IMPORTS: Prelude\n'
    , abi='digest\n/install\n'
    ):
    '''Stand-in products of a module beside its JSON.  Returns their paths.'''
    files = []
    for suffix, content in [('.cpp', cpp), ('.so', so), ('.so.abi', abi)]:
      path = self.cached_file(name, suffix)
      mode = 'wb' if isinstance(content, bytes) else 'w'
      with open(path, mode) as stream:
        stream.write(content)
      files.append(path)
    return files

  def entries(self, digest):
    '''The keys stored under ``digest``.'''
    directory = os.path.join(self.root, digest)
    if not os.path.isdir(directory):
      return []
    return sorted(
        name for name in os.listdir(directory) if not name.startswith('.')
      )

  def temporary_names(self):
    '''The temporary files and directories left in the cache.'''
    found = []
    for dirpath, dirnames, filenames in os.walk(self.root):
      found += [
          os.path.join(dirpath, name) for name in dirnames + filenames
              if name.startswith('.') or name.endswith('.tmp')
        ]
    return found


class TestConfiguration(ProductCacheTestCase):
  '''SPRITE_PRODUCT_CACHE names the root; the empty string turns the cache off.'''

  def test_root(self):
    self.assertEqual(_productcache.root(), self.root)
    self.assertTrue(_productcache.enabled())
    with mock.patch.dict(os.environ, {'SPRITE_PRODUCT_CACHE': ''}):
      self.assertIsNone(_productcache.root())
      self.assertFalse(_productcache.enabled())
      self.assertIsNone(config.product_cache_dir())
    with mock.patch.dict(os.environ, {'SPRITE_PRODUCT_CACHE': '  '}):
      self.assertFalse(_productcache.enabled())
    with mock.patch.dict(os.environ, {'SPRITE_PRODUCT_CACHE': 'relative/dir'}):
      self.assertEqual(_productcache.root(), os.path.abspath('relative/dir'))
    # Unset: off, as before the cache existed (issue #100).
    env = dict(os.environ)
    del env['SPRITE_PRODUCT_CACHE']
    with mock.patch.dict(os.environ, env, clear=True):
      self.assertIsNone(_productcache.root())
      self.assertFalse(_productcache.enabled())
      self.assertIsNone(config.product_cache_dir())

  def test_excluded(self):
    '''A module in the temporary directory of the system stays out.'''
    tmpdir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    self.assertTrue(_productcache.excluded(os.path.join(tmpdir, 'A.curry')))
    self.assertTrue(
        _productcache.excluded(os.path.join(tempfile.gettempdir(), 'A.curry'))
      )
    self.assertFalse(_productcache.excluded(os.path.join(self.srcdir, 'A.curry')))
    # The directory of a module compiled from a string.
    from curry.toolchain import _str2module
    with mock.patch.object(_str2module, 'is_temporary', lambda filename: True):
      self.assertTrue(_productcache.excluded(os.path.join(self.srcdir, 'A.curry')))


class TestKey(ProductCacheTestCase):
  '''The key follows the source chain and the facts, not the directory.'''

  def test_chain_digest(self):
    a = self.write_source('A', 'import B\nmain = B.x\n')
    self.write_source('B', 'x = 1\n')
    digest = _productcache.chain_digest(a, [self.srcdir])
    self.assertRegex(digest, r'^[0-9a-f]{64}$')
    self.assertEqual(_productcache.chain_digest(a, [self.srcdir]), digest)
    # The closure: B by name, the Prelude of the installation.
    closure = _productcache.import_closure(a, [self.srcdir])
    self.assertEqual(sorted(closure), ['B', 'Prelude'])
    self.assertEqual(closure['B'].path, os.path.join(self.srcdir, 'B.curry'))
    # A change to an import changes the digest; so does a change to the
    # module.  The directory does not.
    self.write_source('B', 'x = 2\n')
    changed = _productcache.chain_digest(a, [self.srcdir])
    self.assertNotEqual(changed, digest)
    self.write_source('A', 'import B\nmain = B.x + 1\n')
    self.assertNotEqual(_productcache.chain_digest(a, [self.srcdir]), changed)
    other = os.path.join(self.base, 'other')
    shutil.copytree(self.srcdir, other)
    self.assertEqual(
        _productcache.chain_digest(os.path.join(other, 'A.curry'), [other])
      , _productcache.chain_digest(a, [self.srcdir])
      )
    # An import the path does not hold is left out, as the ICurry cache
    # leaves it out.
    self.write_source('A', 'import Nowhere\nmain = 1\n')
    self.assertEqual(
        sorted(_productcache.import_closure(a, [self.srcdir])), ['Prelude']
      )

  def test_texts_in_the_chain(self):
    '''
    The ICurry file and the JSON of a module are in its chain with the
    source: a new JSON from the same source (another ICurry reader, a
    pinned ICurry file replaced) changes the key, and so does the ICurry
    file.  The source text alone does not decide.
    '''
    a = self.write_source('A', 'main = 1\n')
    self.assertEqual(
        [label for label, _ in _productcache._module_texts(a)], ['curry']
      )
    source_only = _productcache.chain_digest(a, [self.srcdir])
    with open(self.cached_file('A', '.icy'), 'w') as stream:
      stream.write('-- ICurry 1\n')
    with_icy = _productcache.chain_digest(a, [self.srcdir])
    self.assertNotEqual(with_icy, source_only)
    self.write_json(1, name='A')
    self.assertEqual(
        [label for label, _ in _productcache._module_texts(a)]
      , ['curry', 'icy', 'json']
      )
    with_json = _productcache.chain_digest(a, [self.srcdir])
    self.assertNotEqual(with_json, with_icy)
    # The source unchanged, the JSON changed: another chain.
    self.write_json(2, name='A')
    self.assertNotEqual(_productcache.chain_digest(a, [self.srcdir]), with_json)
    self.assertEqual(cytest.readfile(a), 'main = 1\n')
    # The same files again give the same chain.
    self.write_json(1, name='A')
    self.assertEqual(_productcache.chain_digest(a, [self.srcdir]), with_json)
    self.assertEqual(_productcache.KEY_FORMAT, 3)

  def test_module_without_a_source(self):
    '''
    The text of a module without a source is its ICurry file, else its
    JSON; its imports come from the JSON.  A module without any text has no
    key.
    '''
    name = self.write_json(1)
    curryfile = os.path.join(self.srcdir, name + '.curry')
    self.assertFalse(os.path.exists(curryfile))
    self.assertEqual(
        sorted(_productcache.import_closure(curryfile, [])), ['Prelude']
      )
    from_json = _productcache.chain_digest(curryfile, [])
    self.assertRegex(from_json, r'^[0-9a-f]{64}$')
    with open(self.cached_file(name, '.icy'), 'w') as stream:
      stream.write('-- ICurry\n')
    from_icy = _productcache.chain_digest(curryfile, [])
    self.assertNotEqual(from_icy, from_json)
    self.write_source(name, 'goal = 1\n')
    self.assertNotEqual(_productcache.chain_digest(curryfile, []), from_icy)
    nothing = os.path.join(self.srcdir, 'Nothing.curry')
    self.assertIsNone(_productcache.chain_digest(nothing, []))
    self.assertIsNone(_productcache.product_key(nothing, []))

  def test_product_key(self):
    a = self.write_source('A', 'main = 1\n')
    key = _productcache.product_key(a, [self.srcdir], ['format 12', 'x'])
    self.assertRegex(key, r'^[0-9a-f]{64}$')
    self.assertEqual(
        key, _productcache.product_key(a, [self.srcdir], ['format 12', 'x'])
      )
    self.assertNotEqual(
        key, _productcache.product_key(a, [self.srcdir], ['format 13', 'x'])
      )
    self.assertNotEqual(
        key, _productcache.product_key(a, [self.srcdir], ['x', 'format 12'])
      )
    self.assertNotEqual(key, _productcache.product_key(a, [self.srcdir], []))
    # Two modules of one text under two names: two keys, since the
    # generated code and the symbols of the object carry the name (the
    # math corpus of the tests has such pairs).
    b = self.write_source('B', 'main = 1\n')
    self.assertEqual(
        _productcache.chain_digest(a, [self.srcdir])
      , _productcache.chain_digest(b, [self.srcdir])
      )
    self.assertNotEqual(
        key, _productcache.product_key(b, [self.srcdir], ['format 12', 'x'])
      )
    self.write_source('A', 'main = 2\n')
    self.assertNotEqual(
        key, _productcache.product_key(a, [self.srcdir], ['format 12', 'x'])
      )


class TestStore(ProductCacheTestCase):
  '''The store, the lookup and the restore, with stand-in products.'''
  DIGEST = '0123456789abcdef'
  KEY = 'f' * 64

  def test_store_lookup_restore(self):
    name = self.write_json(1)
    files = self.write_products(name, so=b'the object')
    names = [os.path.basename(path) for path in files]
    self.assertIsNone(_productcache.lookup(self.DIGEST, self.KEY, names))
    entry = _productcache.store(self.DIGEST, self.KEY, files)
    self.assertEqual(entry, _productcache.entry_dir(self.DIGEST, self.KEY))
    self.assertEqual(entry, os.path.join(self.root, self.DIGEST, self.KEY))
    self.assertEqual(sorted(os.listdir(entry)), sorted(names))
    self.assertEqual(self.temporary_names(), [])
    self.assertEqual(_productcache.counts, {'restored': 0, 'stored': 1})
    found = _productcache.lookup(self.DIGEST, self.KEY, names)
    self.assertEqual(found, {name: os.path.join(entry, name) for name in names})
    # A lookup needs every name.
    self.assertIsNone(
        _productcache.lookup(self.DIGEST, self.KEY, names + ['more'])
      )
    self.assertIsNone(_productcache.lookup('fedcba9876543210', self.KEY, names))
    self.assertIsNone(_productcache.lookup(self.DIGEST, 'e' * 64, names))
    # The object in the entry is a hard link of the one beside the source
    # (one file system); the generated file is a copy.
    self.assertEqual(os.stat(os.path.join(entry, name + '.so')).st_nlink, 2)
    self.assertTrue(os.path.samefile(files[1], os.path.join(entry, name + '.so')))
    self.assertFalse(
        os.path.samefile(files[0], os.path.join(entry, name + '.cpp'))
      )
    # The restore into another product directory: the files, in the order
    # of the toolchain, newer than the JSON there, the object a hard link.
    other = os.path.join(
        self.base, 'other', '.curry', config.intermediate_subdir()
      )
    os.makedirs(other)
    jsonfile = os.path.join(other, name + '.json.z')
    shutil.copy(self.cached_file(name, '.json.z'), jsonfile)
    later = time.time_ns() + 3 * 10 ** 9
    os.utime(jsonfile, ns=(later, later))
    placed = _productcache.restore(self.DIGEST, self.KEY, other, names[:2])
    self.assertEqual(placed, {n: os.path.join(other, n) for n in names[:2]})
    self.assertEqual(_productcache.counts, {'restored': 1, 'stored': 1})
    self.assertEqual(cytest.readfile(placed[name + '.so'], 'rb'), b'the object')
    self.assertEqual(
        cytest.readfile(placed[name + '.cpp']).splitlines()[0], '// FORMAT: 12'
      )
    times = [
        os.stat(path).st_mtime_ns
        for path in [jsonfile, placed[name + '.cpp'], placed[name + '.so']]
      ]
    self.assertEqual(times, sorted(times))
    self.assertEqual(len(set(times)), 3)
    self.assertTrue(
        os.path.samefile(placed[name + '.so'], os.path.join(entry, name + '.so'))
      )
    self.assertFalse(os.path.exists(os.path.join(other, name + '.so.abi')))
    self.assertEqual(self.temporary_names(), [])
    # A miss restores nothing.
    self.assertIsNone(
        _productcache.restore(self.DIGEST, 'e' * 64, other, names[:2])
      )
    self.assertEqual(_productcache.counts['restored'], 1)

  def test_restore_replaces_without_writing_into_the_old_file(self):
    '''
    An old object beside the source may be a hard link into the cache; a
    restore replaces the name, and the old inode keeps its content.
    '''
    name = self.write_json(2)
    files = self.write_products(name, so=b'new object')
    names = [os.path.basename(path) for path in files[:2]]
    _productcache.store(self.DIGEST, self.KEY, files)
    other = os.path.join(
        self.base, 'other', '.curry', config.intermediate_subdir()
      )
    os.makedirs(other)
    old = os.path.join(other, name + '.so')
    with open(old, 'wb') as stream:
      stream.write(b'old object')
    os.link(old, os.path.join(self.base, 'old-link'))
    _productcache.restore(self.DIGEST, self.KEY, other, names)
    self.assertEqual(cytest.readfile(old, 'rb'), b'new object')
    self.assertEqual(
        cytest.readfile(os.path.join(self.base, 'old-link'), 'rb'), b'old object'
      )

  def test_copy_across_file_systems(self):
    '''Without one file system the files are copied, with their mode.'''
    name = self.write_json(3)
    files = self.write_products(name, so=b'object')
    os.chmod(files[1], 0o755)
    with mock.patch.object(_productcache, '_same_device', lambda a, b: False):
      entry = _productcache.store(self.DIGEST, self.KEY, files)
    stored = os.path.join(entry, name + '.so')
    self.assertEqual(os.stat(stored).st_nlink, 1)
    self.assertEqual(cytest.readfile(stored, 'rb'), b'object')
    self.assertTrue(os.stat(stored).st_mode & stat.S_IXUSR)
    other = os.path.join(self.base, 'other')
    os.makedirs(other)
    with mock.patch.object(_productcache, '_same_device', lambda a, b: False):
      placed = _productcache.restore(self.DIGEST, self.KEY, other, [name + '.so'])
    self.assertEqual(os.stat(placed[name + '.so']).st_nlink, 1)
    self.assertTrue(os.stat(placed[name + '.so']).st_mode & stat.S_IXUSR)

  def test_link_refused_is_a_copy(self):
    '''A file system that refuses the hard link gets a copy, and the entry is whole.'''
    name = self.write_json(7)
    files = self.write_products(name, so=b'object')
    def refuse(src, dst, *args, **kwds):
      raise PermissionError('no links here')
    with mock.patch.object(os, 'link', refuse):
      entry = _productcache.store(self.DIGEST, self.KEY, files)
      other = os.path.join(self.base, 'other')
      os.makedirs(other)
      placed = _productcache.restore(self.DIGEST, self.KEY, other, [name + '.so'])
    stored = os.path.join(entry, name + '.so')
    self.assertEqual(os.stat(stored).st_nlink, 1)
    self.assertEqual(os.stat(placed[name + '.so']).st_nlink, 1)
    self.assertEqual(cytest.readfile(placed[name + '.so'], 'rb'), b'object')
    self.assertEqual(self.temporary_names(), [])
    self.assertEqual(_productcache.counts, {'restored': 1, 'stored': 1})

  def test_store_replaces_an_entry(self):
    '''A second store of a key replaces the entry; no temporary name remains.'''
    name = self.write_json(4)
    files = self.write_products(name, so=b'first')
    entry = _productcache.store(self.DIGEST, self.KEY, files)
    self.write_products(name, so=b'second')
    self.assertEqual(_productcache.store(self.DIGEST, self.KEY, files), entry)
    self.assertEqual(
        cytest.readfile(os.path.join(entry, name + '.so'), 'rb'), b'second'
      )
    self.assertEqual(self.entries(self.DIGEST), [self.KEY])
    self.assertEqual(self.temporary_names(), [])
    self.assertEqual(_productcache.counts['stored'], 2)

  def test_concurrent_store(self):
    '''
    Two processes store one key at once.  Each writes into a temporary
    directory beside the entry and renames it into place; the one that
    finds the entry there removes its own files, and the entry is whole.
    Here the other writer is simulated between the write and the rename.
    '''
    name = self.write_json(5)
    files = self.write_products(name, so=b'mine')
    entry = _productcache.entry_dir(self.DIGEST, self.KEY)
    real_rename = os.rename
    def other_writer_first(src, dst):
      if dst == entry and not os.path.isdir(entry):
        os.makedirs(entry)
        for path in files:
          shutil.copy(path, entry)
        with open(os.path.join(entry, name + '.so'), 'wb') as stream:
          stream.write(b'theirs')
      return real_rename(src, dst)
    with mock.patch.object(os, 'rename', other_writer_first):
      self.assertEqual(_productcache.store(self.DIGEST, self.KEY, files), entry)
    self.assertEqual(
        cytest.readfile(os.path.join(entry, name + '.so'), 'rb'), b'theirs'
      )
    self.assertEqual(
        sorted(os.listdir(entry)), sorted(os.path.basename(f) for f in files)
      )
    self.assertEqual(self.entries(self.DIGEST), [self.KEY])
    self.assertEqual(self.temporary_names(), [])
    # A rename that fails for another reason is an error.
    def broken(src, dst):
      raise PermissionError('no')
    with mock.patch.object(os, 'rename', broken):
      with self.assertRaises(PermissionError):
        _productcache.store(self.DIGEST, 'e' * 64, files)
    self.assertEqual(self.temporary_names(), [])
    self.assertEqual(self.entries(self.DIGEST), [self.KEY])

  def test_prune(self):
    '''
    The digest directories not kept go, with the old leftovers of an
    interrupted store under a kept one; a fresh leftover (a store under
    way) and the kept entries stay.  Nothing without a root.
    '''
    name = self.write_json(7)
    files = self.write_products(name)
    other = 'fedcba9876543210'
    _productcache.store(self.DIGEST, self.KEY, files)
    _productcache.store(other, self.KEY, files)
    kept = os.path.join(self.root, self.DIGEST)
    old = os.path.join(kept, '.%s-abcd.tmp' % self.KEY[:8])
    fresh = os.path.join(kept, '.%s-efgh.old' % self.KEY[:8])
    os.makedirs(old)
    os.makedirs(fresh)
    past = time.time() - 7200
    os.utime(old, (past, past))
    with open(os.path.join(self.root, 'a-file'), 'w'):
      pass
    self.assertEqual(_productcache.prune({self.DIGEST}), (1, 1))
    self.assertEqual(
        sorted(os.listdir(self.root)), sorted([self.DIGEST, 'a-file'])
      )
    self.assertEqual(sorted(os.listdir(kept)), sorted([self.KEY, os.path.basename(fresh)]))
    self.assertEqual(_productcache.prune({self.DIGEST}), (0, 0))
    self.assertEqual(_productcache.prune({self.DIGEST}, max_age=0), (0, 1))
    self.assertEqual(sorted(os.listdir(kept)), [self.KEY])
    self.assertEqual(_productcache.prune({other}, os.path.join(self.base, 'none')), (0, 0))
    with mock.patch.dict(os.environ, {'SPRITE_PRODUCT_CACHE': ''}):
      self.assertEqual(_productcache.prune({other}), (0, 0))
    # Nothing to keep (a runtime without a digest): nothing goes.
    self.assertEqual(_productcache.prune(set()), (0, 0))
    self.assertEqual(_productcache.prune({None}), (0, 0))
    self.assertEqual(sorted(os.listdir(self.root)), sorted([self.DIGEST, 'a-file']))
    self.assertEqual(_productcache.prune({other}), (1, 0))
    self.assertEqual(os.listdir(self.root), ['a-file'])

  def test_unwritable_root(self):
    '''A store into a root that cannot be written raises OSError.'''
    parent = os.path.join(self.base, 'nowhere')
    os.makedirs(parent)
    os.chmod(parent, 0o555)
    self.addCleanup(os.chmod, parent, 0o755)
    if os.access(parent, os.W_OK):
      self.skipTest('the directory stays writable (root)')
    name = self.write_json(6)
    files = self.write_products(name)
    with mock.patch.dict(
        os.environ, {'SPRITE_PRODUCT_CACHE': os.path.join(parent, 'cache')}
      ):
      with self.assertRaises(OSError):
        _productcache.store(self.DIGEST, self.KEY, files)


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'the compile steps belong to the C++ backend'
  )
class TestCompile(ProductCacheTestCase):
  '''
  The compile step stores its products, and the plan places them instead of
  a generation and a compile.  The modules come from hand-written
  ICurry-JSON, so no Curry front end runs.
  '''
  def setUp(self):
    super().setUp()
    if config.cxx_tool() is None:
      self.skipTest('no C++ compiler is installed')
    # The flag ``interpret`` off, as unit_cxx_toolchain.py has it: the plan
    # of an import then compiles (a test of the tiered default reloads).
    curry.reload({'interpret': 'off'})
    curry.import_('Prelude')
    from curry.backends.cxx import toolchain
    self.toolchain = toolchain
    self.plan = plans.makeplan(
        curry.getInterpreter(), plans.MAKE_ALL | plans.ZIP_JSON
      )
    self.cpp2so = toolchain.Cpp2So(curry.getInterpreter())

  def tearDown(self):
    super().tearDown()
    importlib.reload(curry)
    gc.collect()

  def prerequisite(self, name):
    return _findcurry.currentfile(self.plan, name, [self.srcdir])

  def remove_products(self, name):
    for suffix in ['.cpp', '.so', '.so.abi']:
      os.unlink(self.cached_file(name, suffix))

  def no_compiler(self):
    return mock.patch.object(
        _system, 'pexec', side_effect=AssertionError('a compiler ran')
      )

  def entry(self, name):
    key = self.cpp2so.product_key(
        self.cached_file(name, '.json.z'), [self.srcdir]
      )
    return _productcache.entry_dir(self.cpp2so.digest(), key)

  def test_compile_stores(self):
    '''A compile stores the generated file, the object and its stamp.'''
    name = self.write_json(1)
    sofile = makecurry(self.plan, name, [self.srcdir])
    self.assertEqual(sofile, self.cached_file(name, '.so'))
    entry = self.entry(name)
    self.assertEqual(
        sorted(os.listdir(entry)), [name + '.cpp', name + '.so', name + '.so.abi']
      )
    self.assertTrue(os.path.samefile(sofile, os.path.join(entry, name + '.so')))
    self.assertEqual(
        cytest.readfile(os.path.join(entry, name + '.so.abi'))
      , '%s\n%s\n' % (self.cpp2so.digest(), self.toolchain.installation_path())
      )
    self.assertEqual(_productcache.counts, {'restored': 0, 'stored': 1})
    # The facts of the key name the format, the generator, the optimizer,
    # the budget and the route.  No fact names a tree: the installation and
    # the source directory left the key when the objects stopped naming
    # them (format 13), so a second tree is served (test_hit_in_another_tree).
    facts = self.cpp2so.product_facts(os.path.join(self.srcdir, name + '.curry'))
    heads = [fact.split()[0] for fact in facts]
    self.assertEqual(
        heads
      , ['format', 'generator', 'optimizers', 'inline_budget', 'subdir', 'frontend']
      )
    for fact in facts:
      self.assertNotIn(self.toolchain.installation_path(), fact)
      self.assertNotIn(config.prefix(), fact)
      self.assertNotIn(self.srcdir, fact)
      self.assertNotIn(os.path.realpath(self.srcdir), fact)
      self.assertNotIn(os.sep, fact.split(' ', 1)[1])
    self.assertIn('inline_budget %d' % curry.flags['inline_budget'], facts)
    self.assertIn('format %d' % self.toolchain.compiler.FORMAT_VERSION, facts)
    self.assertRegex(self.toolchain.generator_digest(), r'^[0-9a-f]{16}$')
    files = dict(self.toolchain.generator_files())
    self.assertIn(os.path.join('backends', 'cxx', 'compiler.py'), files)
    self.assertIn(os.path.join('interpreter', 'optimize.py'), files)
    self.assertTrue(
        any(f.startswith(os.path.join('icurry', 'analysis')) for f in files)
      )
    # The readers of the ICurry on the way to the emitter: a change to them
    # changes the JSON or its reading, and the key must see it.
    self.assertIn(os.path.join('icurry', 'json.py'), files)
    self.assertIn(os.path.join('icurry', 'types', 'imodule.py'), files)
    self.assertIn(os.path.join('toolchain', '_icurry2json.py'), files)
    self.assertIn(os.path.join('toolchain', '_loadcurry.py'), files)
    for relpath, path in files.items():
      self.assertTrue(os.path.isfile(path), relpath)

  def test_second_make_restores(self):
    '''
    The products removed, a second make places them from the cache: no
    generation, no compile.  The stamp names this installation, the object
    is the newest file of the module, and the module runs from it.  The
    restore counts on the compile clock.
    '''
    name = self.write_json(2)
    sofile = makecurry(self.plan, name, [self.srcdir])
    self.remove_products(name)
    self.assertEqual(self.prerequisite(name), self.cached_file(name, '.json.z'))
    before = curry.stats()['compile']
    with self.no_compiler(), capture_log('curry.backends.cxx.toolchain') as log:
      self.assertEqual(makecurry(self.plan, name, [self.srcdir]), sofile)
    log.checkMessages(self, info='Restored %r from the product cache' % sofile)
    self.assertGreater(curry.stats()['compile'], before)
    self.assertEqual(_productcache.counts, {'restored': 1, 'stored': 1})
    self.assertTrue(os.path.isfile(self.cached_file(name, '.cpp')))
    self.assertEqual(
        self.cpp2so.read_stamp_lines(sofile)
      , (self.cpp2so.digest(), self.toolchain.installation_path())
      )
    self.assertFalse(self.cpp2so.is_stale(sofile))
    self.assertEqual(self.prerequisite(name), sofile)
    self.assertEqual(os.stat(sofile).st_nlink, 2)
    module = curry.import_(name, currypath=[self.srcdir] + curry.path)
    self.assertEqual(list(curry.eval(module.goal, converter='topython')), [2])

  def test_stale_object_is_replaced(self):
    '''
    An object with the stamp of another runtime beside the source goes;
    the cached one takes its place.
    '''
    name = self.write_json(3)
    sofile = makecurry(self.plan, name, [self.srcdir])
    with open(self.cpp2so.stampfile(sofile), 'w') as stream:
      stream.write('0123456789abcdef\n/elsewhere\n')
    self.assertTrue(self.cpp2so.is_stale(sofile))
    self.assertEqual(self.prerequisite(name), self.cached_file(name, '.cpp'))
    with self.no_compiler():
      self.assertEqual(makecurry(self.plan, name, [self.srcdir]), sofile)
    self.assertFalse(self.cpp2so.is_stale(sofile))
    self.assertEqual(_productcache.counts['restored'], 1)

  def test_miss_on_a_changed_source(self):
    '''A change to the text of the module is a miss: a compile, and a second entry.'''
    name = self.write_json(4)
    makecurry(self.plan, name, [self.srcdir])
    first = self.entry(name)
    self.remove_products(name)
    self.write_json(5, name=name)
    with capture_log('curry.backends.cxx.toolchain') as log:
      sofile = makecurry(self.plan, name, [self.srcdir])
    log.checkMessages(self, info='Compiling %r' % sofile)
    self.assertNotEqual(self.entry(name), first)
    self.assertTrue(os.path.isdir(first))
    self.assertTrue(os.path.isdir(self.entry(name)))
    self.assertEqual(_productcache.counts, {'restored': 0, 'stored': 2})

  def test_miss_on_a_changed_json(self):
    '''
    The source unchanged and the JSON changed (a new ICurry reader, a
    pinned ICurry file replaced): a miss, since the JSON is the input of
    the code generator and part of the chain.  Before the JSON joined the
    chain the old object was served, and the goal gave the old value.
    '''
    name = self.new_name()
    source = self.write_source(name, 'goal :: Int\ngoal = 1\n')
    past = time.time() - 100
    os.utime(source, (past, past))
    self.write_json(1, name=name)
    sofile = makecurry(self.plan, name, [self.srcdir])
    first = self.entry(name)
    self.assertEqual(_productcache.counts, {'restored': 0, 'stored': 1})
    self.remove_products(name)
    self.write_json(2, name=name)
    self.assertEqual(cytest.readfile(source), 'goal :: Int\ngoal = 1\n')
    self.assertEqual(self.prerequisite(name), self.cached_file(name, '.json.z'))
    with capture_log('curry.backends.cxx.toolchain') as log:
      self.assertEqual(makecurry(self.plan, name, [self.srcdir]), sofile)
    log.checkMessages(self, info='Compiling %r' % sofile)
    self.assertNotEqual(self.entry(name), first)
    self.assertEqual(_productcache.counts, {'restored': 0, 'stored': 2})
    module = curry.import_(name, currypath=[self.srcdir] + curry.path)
    self.assertEqual(list(curry.eval(module.goal, converter='topython')), [2])

  def test_interpret_new_does_not_restore(self):
    '''
    Under interpret:new a module without a current object is interpreted
    and never compiled (section 4 of README); the cache places nothing for
    it, so the mode keeps its meaning with a warm cache.
    '''
    name = self.write_json(15)
    sofile = makecurry(self.plan, name, [self.srcdir])
    self.remove_products(name)
    curry.reload({'interpret': 'new'})
    from curry.objects.handle import getHandle
    with self.no_compiler():
      module = curry.import_(name, currypath=[self.srcdir] + curry.path)
      self.assertEqual(list(curry.eval(module.goal, converter='topython')), [15])
    self.assertIsNone(getHandle(module).icurry.metadata.get('cxx.shlib'))
    self.assertFalse(os.path.exists(sofile))
    self.assertEqual(_productcache.counts, {'restored': 0, 'stored': 1})

  def test_hit_in_another_tree(self):
    '''
    The same text in another directory is a hit: the key names no tree,
    and the products name no path (the objects name their imports by
    SONAME and the record names the source relative to the object).  Two
    copies of a project that share one cache directory, as two worktrees
    do: the first compiles, the second compiles nothing, and the module
    runs in the second from the restored object, which names the source of
    the second.
    '''
    name = self.write_json(14)
    first = makecurry(self.plan, name, [self.srcdir])
    other = os.path.join(self.base, 'other')
    shutil.copytree(self.srcdir, other)
    for suffix in ['.cpp', '.so', '.so.abi']:
      os.unlink(os.path.join(other, '.curry', config.intermediate_subdir(), name + suffix))
    curryfile = os.path.join(other, name + '.curry')
    self.assertEqual(
        _productcache.chain_digest(curryfile, [other])
      , _productcache.chain_digest(os.path.join(self.srcdir, name + '.curry'), [self.srcdir])
      )
    self.assertEqual(
        self.cpp2so.product_facts(curryfile)
      , self.cpp2so.product_facts(os.path.join(self.srcdir, name + '.curry'))
      )
    self.assertEqual(
        self.cpp2so.product_key(curryfile, [other])
      , self.cpp2so.product_key(os.path.join(self.srcdir, name + '.curry'), [self.srcdir])
      )
    with self.no_compiler(), capture_log('curry.backends.cxx.toolchain') as log:
      sofile = makecurry(self.plan, name, [other])
    log.checkMessages(self, info='Restored %r from the product cache' % sofile)
    self.assertEqual(
        sofile, os.path.join(other, '.curry', config.intermediate_subdir(), name + '.so')
      )
    self.assertNotEqual(sofile, first)
    # Both trees link the object of the entry (one file system here).
    self.assertTrue(os.path.samefile(sofile, first))
    self.assertEqual(os.stat(sofile).st_nlink, 3)
    self.assertEqual(_productcache.counts, {'restored': 1, 'stored': 1})
    self.assertEqual(len(self.entries(self.cpp2so.digest())), 1)
    self.assertEqual(
        self.cpp2so.read_stamp_lines(sofile)
      , (self.cpp2so.digest(), self.toolchain.installation_path())
      )
    # The module runs in the second tree, in a child (the runtime of this
    # process keeps one library per module name), with no compiler.
    code = '\n'.join([
        'import curry, json'
      , 'from curry.objects.handle import getHandle'
      , 'from curry.toolchain import _system'
      , 'commands = []'
      , 'pexec = _system.pexec'
      , 'def counting_pexec(cmd, *args, **kwds):'
      , '  commands.append(cmd)'
      , '  return pexec(cmd, *args, **kwds)'
      , '_system.pexec = counting_pexec'
      , 'module = curry.import_(%r, currypath=%r)' % (name, [other] + curry.path)
      , 'value = list(curry.eval(module.goal, converter="topython"))'
      , 'print(json.dumps([commands, value, module.__file__, getHandle(module).sofilename]))'
      ])
    with mock.patch.dict(
        os.environ, {'SPRITE_INTERPRETER_FLAGS': 'backend:cxx,interpret:off'}
      ):
      proc = cytest.run_in_subprocess(code, timeout=300)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    commands, value, source, loaded = json.loads(proc.stdout.strip().splitlines()[-1])
    self.assertEqual(commands, [])
    self.assertEqual(value, [14])
    self.assertEqual(source, curryfile)
    self.assertEqual(loaded, sofile)

  def test_miss_on_another_digest(self):
    '''An entry of another runtime is not seen: the digest heads the key.'''
    name = self.write_json(6)
    makecurry(self.plan, name, [self.srcdir])
    self.remove_products(name)
    other = 'fedcba9876543210'
    with mock.patch.object(
        self.toolchain, 'object_digest', lambda *args, **kwds: other
      ):
      self.assertEqual(self.cpp2so.digest(), other)
      with capture_log('curry.backends.cxx.toolchain') as log:
        sofile = makecurry(self.plan, name, [self.srcdir])
      log.checkMessages(self, info='Compiling %r' % sofile)
      self.assertEqual(self.cpp2so.read_stamp(sofile), other)
    self.assertEqual(
        sorted(os.listdir(self.root)), sorted([self.cpp2so.digest(), other])
      )
    self.assertEqual(_productcache.counts, {'restored': 0, 'stored': 2})

  def test_cache_off(self):
    '''The empty string: nothing is stored and nothing is looked up.'''
    name = self.write_json(7)
    with mock.patch.dict(os.environ, {'SPRITE_PRODUCT_CACHE': ''}):
      sofile = makecurry(self.plan, name, [self.srcdir])
      self.assertFalse(os.path.exists(self.root))
      self.remove_products(name)
      with capture_log('curry.backends.cxx.toolchain') as log:
        self.assertEqual(makecurry(self.plan, name, [self.srcdir]), sofile)
      log.checkMessages(self, info='Compiling %r' % sofile)
    self.assertEqual(_productcache.counts, {'restored': 0, 'stored': 0})

  def test_forced_recompile_skips_the_restore(self):
    '''SPRITE_FORCE_RECOMPILE_CXX compiles, and the compile refreshes the entry.'''
    name = self.write_json(8)
    sofile = makecurry(self.plan, name, [self.srcdir])
    with mock.patch.dict(os.environ, {'SPRITE_FORCE_RECOMPILE_CXX': '1'}):
      with capture_log('curry.backends.cxx.toolchain') as log:
        self.assertEqual(makecurry(self.plan, name, [self.srcdir]), sofile)
    log.checkMessages(self, info='Compiling %r' % sofile)
    self.assertEqual(_productcache.counts, {'restored': 0, 'stored': 2})
    self.assertTrue(
        os.path.samefile(sofile, os.path.join(self.entry(name), name + '.so'))
      )

  def test_excluded_module_is_not_cached(self):
    '''A module in the temporary directory of the system is compiled and not stored.'''
    tmpdir = tempfile.mkdtemp(prefix='product-cache-')
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    subdir = os.path.join(tmpdir, '.curry', config.intermediate_subdir())
    os.makedirs(subdir)
    name = self.new_name()
    with open(os.path.join(subdir, name + '.json.z'), 'wb') as stream:
      stream.write(zlib.compress(cytest.json_module(name, 9).encode('utf-8')))
    makecurry(self.plan, name, [tmpdir])
    self.assertFalse(os.path.exists(self.root))
    self.assertEqual(_productcache.counts, {'restored': 0, 'stored': 0})

  def test_unwritable_cache_is_a_warning(self):
    '''A cache that cannot be written is logged once; the compile ends well.'''
    name = self.write_json(10)
    with mock.patch.object(
        _productcache, 'store', side_effect=PermissionError('no')
      ):
      self.toolchain.Cpp2So._warned.discard('store')
      with capture_log('curry.backends.cxx.toolchain') as log:
        sofile = makecurry(self.plan, name, [self.srcdir])
        self.remove_products(name)
        makecurry(self.plan, name, [self.srcdir])
    messages = [
        message for message in log.data[logging.WARNING]
                if 'cannot store' in message
      ]
    self.assertEqual(len(messages), 1, messages)
    self.assertIn('SPRITE_PRODUCT_CACHE', messages[0])
    self.assertTrue(os.path.isfile(sofile))

  def test_first_import_under_tiered_loads_the_cached_object(self):
    '''
    Under the tiered default an import of a module without an object
    interprets it.  With the products in the cache the import places them
    first and loads the module from its object, and no compiler runs.
    '''
    name = self.write_json(11)
    sofile = makecurry(self.plan, name, [self.srcdir])
    self.remove_products(name)
    curry.reload({'interpret': 'tiered'})
    from curry.objects.handle import getHandle
    with self.no_compiler():
      module = curry.import_(name, currypath=[self.srcdir] + curry.path)
      self.assertEqual(list(curry.eval(module.goal, converter='topython')), [11])
    self.assertIsNotNone(getHandle(module).icurry.metadata.get('cxx.shlib'))
    self.assertTrue(os.path.isfile(sofile))
    self.assertEqual(_productcache.counts['restored'], 1)

  def test_sprite_make_reports(self):
    '''
    sprite-make prints one line with the counts at the end of a run that
    stored or restored a product, not under -q; under --jobs the counts of
    the children are summed into one line.
    '''
    first = self.write_json(12)
    second = self.write_json(13)
    def run(*args):
      out = io.StringIO()
      with binding(os.environ, 'CURRYPATH', self.srcdir):
        config.currypath(reset=True)
        try:
          with contextlib.redirect_stdout(out):
            make.main('sprite-make', list(args))
        finally:
          config.currypath(reset=True)
      return out.getvalue()
    text = run('--so', '-z', first)
    self.assertEqual(text, 'sprite-make: product cache: 0 restored, 1 stored\n')
    # Current: nothing to say.
    self.assertEqual(run('--so', '-z', first), '')
    self.remove_products(first)
    self.assertEqual(run('--so', '-z', '-q', first), '')
    self.assertEqual(_productcache.counts['restored'], 1)
    self.remove_products(first)
    self.assertEqual(
        run('--so', '-z', first)
      , 'sprite-make: product cache: 1 restored, 0 stored\n'
      )
    # The parallel run: the children print the line for the parent, which
    # sums them and prints one line.
    self.remove_products(first)
    text = run('--so', '-z', '--jobs', '2', first, second)
    self.assertEqual(text, 'sprite-make: product cache: 1 restored, 1 stored\n')
    self.assertRegex(
        make.cache_line('sprite-make', {'restored': 3, 'stored': 4})
      , make.CACHE_LINE
      )
    m = make.CACHE_LINE.match('sprite-make: product cache: 3 restored, 4 stored')
    self.assertEqual((m.group('restored'), m.group('stored')), ('3', '4'))
