import cytest # from ./lib; must be first
from cytest.logging import capture_log
from import_blocker import with_import_blocked
import curry
from curry import cache, config, toolchain
from curry.toolchain import _curry2icurry, _filenames, _frontend, _system
from curry.utility.binding import binding
from unittest import mock
import contextlib, importlib, json, os, re, shutil, sqlite3, tempfile

SUBDIR = os.path.join('.curry', config.intermediate_subdir())

# A module with every kind of name the front end derives from the module
# name: qualified names, instance and superclass functions, a default method,
# local functions, and lambdas.  (An external function would need a runtime
# implementation to load; the rename test covers that name by hand.)  The
# type synonym reaches the Curry interface only.
MODULE_TEXT = '''
import Data.Maybe
type Pair = (Int, Int)
data T = A Int | B String
instance Show T where
  show (A n) = "A" ++ show n
  show (B s) = s
class Sized a where
  size :: a -> Int
  dflt :: a -> Int
  dflt _ = 0
class Show a => Pretty a where
  pretty :: a -> String
instance Sized T where
  size (A n) = n
  size (B s) = length s
instance Pretty T where
  pretty = show
f :: Int -> Int
f x = g x + h
  where g y = y * 2
        h = 1
mapf :: [Int] -> [Int]
mapf xs = map (\\y -> f y + 1) xs
main :: IO ()
main = putStrLn (show (A 1)) >> print (fromMaybe 0 (Just (size (B "ab"))))
'''

@contextlib.contextmanager
def cache_file(enabled=True):
  '''
  Binds SPRITE_CACHE_FILE to a new file in a temporary directory, or to the
  empty string, and resets the cache module.  The test starts with an empty
  cache and leaves no state behind.
  '''
  with tempfile.TemporaryDirectory() as tmpdir:
    value = os.path.join(tmpdir, 'cache.db') if enabled else ''
    with binding(os.environ, 'SPRITE_CACHE_FILE', value):
      cache.reset()
      try:
        yield value
      finally:
        cache.reset()

def frontend_tools():
  '''The programs of the routes from Curry to ICurry that are configured.'''
  return [t for t in (config.curry_frontend(), config.icurry_tool()) if t]

@contextlib.contextmanager
def frontend_calls():
  '''Collects the commands that run the Curry front end or icurry.'''
  calls = []
  pexec = _system.pexec
  tools = frontend_tools()
  def counting_pexec(cmd, *args, **kwds):
    if cmd[0] in tools:
      calls.append(cmd)
    return pexec(cmd, *args, **kwds)
  with mock.patch.object(_system, 'pexec', counting_pexec):
    yield calls

def icurry_text(module):
  '''The ICurry text of a module compiled from a string.'''
  filename = _filenames.icurryfilename(module.__file__)
  with open(filename, encoding='utf-8') as stream:
    return stream.read()

def interface_texts(module):
  '''
  The texts of the interface files beside the ICurry file of a module, by
  suffix.
  '''
  found = files(_filenames.icurryfilename(module.__file__))
  found.pop('.icy')
  return found

def files(icyfile):
  '''
  The texts of the ICurry file and of the interface files beside it, by
  suffix.  A missing file is left out.
  '''
  found = {}
  for suffix in ('.icy',) + cache.INTERFACE_SUFFIXES:
    filename = icyfile[:-len('.icy')] + suffix
    if os.path.exists(filename):
      found[suffix] = cytest.readfile(filename)
  return found

def write(path, text):
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, 'w', encoding='utf-8') as stream:
    stream.write(text)
  return path

def rows(cachefile):
  '''The (key, name, text, fint, icurry) rows of the ICurry cache.'''
  db = sqlite3.connect(cachefile)
  try:
    return db.execute(
        'SELECT key, name, text, fint, icurry FROM [%s] ORDER BY created'
            % cache.Curry2ICurryCache.TABLE
      ).fetchall()
  finally:
    db.close()


class TestRename(cytest.TestCase):
  '''The module name in an ICurry text.'''

  def test_rename_module(self):
    old, new = 'sprite__expression_1', 'sprite__interactive_42'
    # Every context the front end writes, and look-alikes that must stay: a
    # module whose name extends the old one, the Prelude, and the characters
    # of a string literal.
    template = (
        '(IProg "%(m)s" ["Prelude","Data.Maybe","%(o)s"] '
        '[(IDataType ("%(m)s","T",0) [(("%(m)s","A",0),1)])] '
        '[(IFunction ("%(m)s","_inst#Prelude.Show#%(m)s.T",0) 1 Public [0] '
        '(IFuncBody (IBlock [] [] (IReturn (ICCall ("Prelude",":",1) '
        '[(ILit (IChar \'s\')),(ICCall ("%(o)s","x",0) [])]))))),'
        '(IFunction ("%(m)s","_super#%(m)s.Pretty#Prelude.Show",1) 0 Public [] '
        '(IExternal "%(m)s.prim")),'
        '(IFunction ("%(m)s","_impl#show#Prelude.Show#%(m)s.T_CASE0",2) 1 '
        'Private [0] (IFuncBody (IBlock [] [] (IReturn (IFCall '
        '("%(m)s","f.g.2",3) [(IVar 1)])))))])\n'
      )
    other = old + '2'
    text = template % {'m': old, 'o': other}
    expected = template % {'m': new, 'o': other}
    self.assertEqual(cache.icurry_modulename(text), old)
    renamed = cache.rename_module(text, old, new)
    self.assertEqual(renamed, expected)
    self.assertEqual(cache.icurry_modulename(renamed), new)
    self.assertEqual(renamed.count(new), text.count(old) - text.count(other))
    self.assertEqual(renamed.count(other), text.count(other))
    # Renaming back gives the original text.
    self.assertEqual(cache.rename_module(renamed, new, old), text)
    self.assertIsNone(cache.icurry_modulename('not icurry'))

  def test_rename_interfaces(self):
    '''
    The same rule renames a FlatCurry interface, where the name follows a
    quote or a hash sign, and a Curry interface, which names its module in
    the header only.  A module whose name extends the old one stays.
    '''
    old, new = 'sprite__interactive_3', 'sprite__expression_9'
    other = old + '2'
    fint = (
        'Prog "%(m)s" ["Prelude","%(o)s"] [Type ("%(m)s","T") Public [] '
        '[Cons ("%(m)s","A") 1 Public [TCons ("Prelude","Int") []]],'
        'Type ("%(m)s","_Dict#Sized") Public [(0,KStar)] []] '
        '[Func ("%(m)s","_inst#Prelude.Show#%(m)s.T") 1 Public (FuncType '
        '(TCons ("Prelude","()") []) (TCons ("Prelude","_Dict#Show") '
        '[TCons ("%(m)s","T") []])) (Rule [] (Var 0)),'
        'Func ("%(m)s","_super#%(m)s.Pretty#Prelude.Show") 1 Public '
        '(TCons ("%(o)s","U") []) (Rule [] (Var 0))] []\n'
      )
    icurry = (
        'interface %(m)s where {\n'
        'import Prelude;\n'
        'import %(o)s;\n'
        'type Pair = (Prelude.Int, Prelude.Int);\n'
        'data T = A Prelude.Int;\n'
        'f 1 :: %(o)s.U -> Prelude.Int;\n'
        'instance Prelude.Show T {\n  show 1\n};\n'
        'hiding data Prelude.Int\n}'
      )
    for template in [fint, icurry]:
      text = template % {'m': old, 'o': other}
      expected = template % {'m': new, 'o': other}
      renamed = cache.rename_module(text, old, new)
      self.assertEqual(renamed, expected)
      self.assertEqual(cache.rename_module(renamed, new, old), text)
    # The header alone names the module of a Curry interface: the word
    # "interface" elsewhere is not a header.
    text = 'import %s;\n-- interface %s where\n' % (old, old)
    self.assertEqual(cache.rename_module(text, old, new), text)

  def test_anonymous_names(self):
    for name in ['sprite__interactive_0', 'sprite__expression_12']:
      self.assertTrue(config.is_anonymous_modname(name))
    for name in ['Prelude', 'Data.Maybe', 'hello', 'Or', 'sprite_expression_1']:
      self.assertFalse(config.is_anonymous_modname(name))


class TestKey(cytest.TestCase):
  '''The key of the ICurry cache follows the content of the sources.'''

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(prefix='cache-key-')
    self.addCleanup(shutil.rmtree, self.tmpdir)
    cache.reset()
    self.addCleanup(cache.reset)

  def key(self, relpath, text, currypath=(), options=(), tool=None):
    path = write(os.path.join(self.tmpdir, relpath), text)
    return cache.icurry_cache_key(path, currypath, options, tool)

  def test_route_is_part_of_the_key(self):
    '''
    The key names the route from Curry to ICurry and carries the digest of
    its program; for the front end the digest covers the flags and the
    sources of the built-in translation too.  So an entry written by one
    route is never served to the other.
    '''
    text = 'f :: Int\nf = 1\n'
    programs = {
        'frontend': config.curry_frontend(), 'icurry': config.icurry_tool()
      }
    digests = {}
    for tool in config.CURRY2ICURRY_TOOLS:
      digests[tool] = cache.frontend_digest(tool)
      self.assertEqual(len(digests[tool]), 64 if programs[tool] else 0, tool)
      # Memoized per route.
      self.assertEqual(cache.frontend_digest(tool), digests[tool])
    keys = {
        tool: self.key('route/M.curry', text, tool=tool)
            for tool in config.CURRY2ICURRY_TOOLS
      }
    self.assertNotEqual(keys['frontend'], keys['icurry'])
    # The default is the configured route.
    self.assertEqual(
        self.key('route/M.curry', text), keys[config.curry2icurry_tool()]
      )
    if programs['frontend'] is None:
      self.skipTest('the Curry front end is not configured')
    # New flags make a new digest, and so does a change to the translation.
    cache.reset()
    with mock.patch.object(config, 'frontend_flags', return_value='--other'):
      self.assertNotEqual(cache.frontend_digest('frontend'), digests['frontend'])
    cache.reset()
    with mock.patch.object(cache, 'PORT_DIR', self.tmpdir):
      self.assertNotEqual(cache.frontend_digest('frontend'), digests['frontend'])
    cache.reset()
    self.assertEqual(cache.frontend_digest('frontend'), digests['frontend'])

  def test_anonymous_name_is_not_part_of_the_key(self):
    text = 'f :: Int\nf = 1\n'
    key = self.key('one/sprite__interactive_0.curry', text)
    self.assertEqual(len(key), 64)
    self.assertEqual(key, self.key('two/sprite__expression_7.curry', text))
    # A changed text misses.
    self.assertNotEqual(
        key, self.key('three/sprite__interactive_0.curry', text + '\n')
      )

  def test_named_module_keeps_its_name(self):
    text = 'f :: Int\nf = 1\n'
    key = self.key('one/M.curry', text)
    # Another directory, the same key.
    self.assertEqual(key, self.key('two/M.curry', text))
    self.assertNotEqual(key, self.key('three/N.curry', text))
    self.assertNotEqual(
        key, self.key('four/M.curry', text, options=('--optvardecls',))
      )

  def test_imports_are_part_of_the_key(self):
    lib = os.path.join(self.tmpdir, 'lib')
    write(os.path.join(lib, 'A.curry'), 'a :: Int\na = 1\n')
    write(os.path.join(lib, 'B.curry'), 'import A\nb :: Int\nb = a\n')
    main = 'import B\nimport Nowhere\nmain :: Int\nmain = b\n'
    mainfile = os.path.join(self.tmpdir, 'app', 'Main.curry')
    key1 = self.key('app/Main.curry', main, currypath=[lib])
    # The closure holds the imports found in the path, two levels deep; the
    # Prelude and a module that is nowhere are left out.
    closure = cache.import_closure(mainfile, [lib])
    self.assertEqual(sorted(closure), ['A', 'B'])
    # A change two imports away changes the key.
    write(os.path.join(lib, 'A.curry'), 'a :: Int\na = 2\n')
    key2 = self.key('app/Main.curry', main, currypath=[lib])
    self.assertNotEqual(key1, key2)
    # The same tree in another place gives the same key.
    other = os.path.join(self.tmpdir, 'elsewhere')
    for name in ['lib', 'app']:
      shutil.copytree(
          os.path.join(self.tmpdir, name), os.path.join(other, name)
        )
    key3 = cache.icurry_cache_key(
        os.path.join(other, 'app', 'Main.curry'), [os.path.join(other, 'lib')]
      )
    self.assertEqual(key2, key3)
    # The Prelude is an implicit import.
    write(os.path.join(lib, 'Prelude.curry'), '-- a Prelude\n')
    key4 = self.key('app/Main.curry', main, currypath=[lib])
    self.assertNotEqual(key2, key4)
    self.assertIn('Prelude', cache.import_closure(mainfile, [lib]))
    # A module beside the file is found without a path entry.
    write(
        os.path.join(self.tmpdir, 'app', 'Nowhere.curry'), 'n :: Int\nn = 0\n'
      )
    key5 = self.key('app/Main.curry', main, currypath=[lib])
    self.assertNotEqual(key4, key5)

  def test_dynamic_import_is_part_of_the_key(self):
    '''
    curry.compile prepends "import sprite__interactive_N" for a module given
    through its imports argument and puts the directory of that module first
    in the path.  The source of that module is part of the key: the same
    expression text against another module of the same name must miss.  The
    name of an anonymous module begins with a lowercase letter.
    '''
    dyn = os.path.join(self.tmpdir, 'dyn')
    module = os.path.join(dyn, 'sprite__interactive_0.curry')
    write(module, 'f :: Int -> Int\nf x = x + 1\n')
    text = (
        'import sprite__interactive_0\n'
        'compiled_expression :: String\n'
        'compiled_expression = show (f 3)\n'
      )
    key1 = self.key('one/sprite__expression_1.curry', text, currypath=[dyn])
    closure = cache.import_closure(
        os.path.join(self.tmpdir, 'one', 'sprite__expression_1.curry'), [dyn]
      )
    self.assertEqual(sorted(closure), ['sprite__interactive_0'])
    write(module, 'f :: Int -> [Int]\nf x = [x, x]\n')
    key2 = self.key('two/sprite__expression_1.curry', text, currypath=[dyn])
    self.assertNotEqual(key1, key2)

  def test_import_scan(self):
    info = cache.SourceInfo('M.curry', (
        'module M where\n'
        'import qualified Data.Maybe as D\n'
        'import Data.List (nub)\n'
        'import Data.Maybe\n'
        "import Control.SetFunctions\n"
        '-- import Nope\n'
        'import sprite__interactive_0\n'
        'import hello\n'
        'important :: Int\n'
        'important = 1\n'
      ).encode('utf-8'))
    # The scan is lenient: an import in a comment counts.  Duplicates drop.
    # A module name may begin with a lowercase letter.
    self.assertEqual(
        info.imports
      , [ 'Data.Maybe', 'Data.List', 'Control.SetFunctions', 'Nope'
        , 'sprite__interactive_0', 'hello'
        ]
      )
    self.assertEqual(len(info.digest), 64)


class TestSlot(cytest.TestCase):
  '''
  The cache slot without the front end.  A hand-written ICurry text stands for
  the front end's output.
  '''

  def setUp(self):
    self.stack = contextlib.ExitStack()
    self.addCleanup(self.stack.close)
    self.cachefile = self.stack.enter_context(cache_file())
    self.tmpdir = self.stack.enter_context(tempfile.TemporaryDirectory())

  def slot(self, name, text='f :: Int\nf = 1\n', subdir='src', **kwds):
    file_in = write(os.path.join(self.tmpdir, subdir, name + '.curry'), text)
    file_out = os.path.join(self.tmpdir, subdir, SUBDIR, name + '.icy')
    return cache.Curry2ICurryCache.Slot(file_in, file_out, **kwds)

  @staticmethod
  def products(name, version=''):
    '''
    The texts that stand for the output of the front end: the ICurry and the
    two interface files, by suffix.
    '''
    return {
        '.icy': '(IProg "%s" ["Prelude"] [] [])%s\n' % (name, version)
      , '.fint': 'Prog "%s" ["Prelude"] [] [] []%s\n' % (name, version)
      , '.icurry': 'interface %s where {\nimport Prelude%s\n}' % (name, version)
      }

  @staticmethod
  def convert(slot, products):
    '''Writes the products beside the output file of a slot and updates it.'''
    for suffix, content in products.items():
      write(slot.file_out[:-len('.icy')] + suffix, content)
    slot.update()

  def test_miss_update_hit(self):
    stats = dict(cache.Curry2ICurryCache.stats)
    slot = self.slot('M')
    self.assertFalse(slot)
    self.assertFalse(os.path.exists(slot.file_out))
    products = self.products('M')
    self.convert(slot, products)
    self.assertEqual(
        [row[1:] for row in rows(self.cachefile)]
      , [('M', products['.icy'], products['.fint'], products['.icurry'])]
      )
    # The same text in another directory is a hit: the three files are
    # written beside each other.
    again = self.slot('M', subdir='other')
    self.assertTrue(again)
    self.assertEqual(files(again.file_out), products)
    self.assertEqual(
        cache.Curry2ICurryCache.stats
      , {'hit': stats['hit'] + 1, 'miss': stats['miss'] + 1}
      )
    # Another text is a miss.
    self.assertFalse(self.slot('M', text='f :: Int\nf = 2\n'))

  def test_hit_after_a_miss_on_a_reverted_text(self):
    '''
    Two versions of a source miss in turn; the first version, restored, hits.
    The files beside the ICurry are then the ones of the first version, while
    the front end's own copy, written at the second miss, still holds the
    second.  So a reader of the types must use the copies beside the ICurry.
    '''
    frontend_copy = os.path.join(
        self.tmpdir, 'src', '.curry', config.frontend_subdir(), 'M.fint'
      )
    v1, v2 = self.products('M', ' -- v1'), self.products('M', ' -- v2')
    slot = self.slot('M', text='f = 1\n')
    self.assertFalse(slot)
    self.convert(slot, v1)
    write(frontend_copy, v1['.fint'])
    slot = self.slot('M', text='f = 2\n')
    self.assertFalse(slot)
    self.convert(slot, v2)
    write(frontend_copy, v2['.fint'])
    self.assertEqual(files(slot.file_out), v2)
    slot = self.slot('M', text='f = 1\n')
    self.assertTrue(slot)
    self.assertEqual(files(slot.file_out), v1)
    self.assertEqual(cytest.readfile(frontend_copy), v2['.fint'])
    self.assertEqual(len(rows(self.cachefile)), 2)

  def test_missing_interface_is_null(self):
    '''
    An interface file that is missing or empty after a conversion is stored
    as NULL.  A hit then writes an empty file in its place, over a stale copy
    of another version, so a reader finds no type rather than a wrong one.
    '''
    slot = self.slot('M')
    products = self.products('M')
    self.convert(slot, {'.icy': products['.icy'], '.icurry': ''})
    self.assertEqual(
        [row[1:] for row in rows(self.cachefile)]
      , [('M', products['.icy'], None, None)]
      )
    stale = os.path.join(self.tmpdir, 'other', SUBDIR, 'M.fint')
    write(
        stale
      , 'Prog "M" ["Prelude"] [] [Func ("M","f") 0 Public (TVar 0) '
        '(Rule [] (Var 0))] []\n'
      )
    again = self.slot('M', subdir='other')
    self.assertTrue(again)
    self.assertEqual(
        files(again.file_out)
      , {'.icy': products['.icy'], '.fint': '', '.icurry': ''}
      )
    # The empty files count as present: the ICurry is not made again.
    self.assertFalse(_curry2icurry.icurry_is_stale(again.file_out))

  def test_old_format_rows_stay(self):
    '''The rows of an earlier key format stay in their own table, unread.'''
    slot = self.slot('M')
    old_table = 'curry2icurry_%d' % (cache.KEY_FORMAT - 1)
    db = sqlite3.connect(self.cachefile)
    with db:
      db.execute(
          'CREATE TABLE [%s](key TEXT PRIMARY KEY, name TEXT NOT NULL'
          ', text TEXT NOT NULL, error TEXT, created REAL)' % old_table
        )
      db.execute(
          'INSERT INTO [%s](key, name, text, created) VALUES(?, ?, ?, 0)'
              % old_table
        , (slot.key, 'M', '(IProg "M" ["Prelude"] [] [])\n')
        )
    db.close()
    self.assertFalse(self.slot('M'))
    self.convert(self.slot('M'), self.products('M'))
    self.assertTrue(self.slot('M'))
    db = sqlite3.connect(self.cachefile)
    try:
      self.assertEqual(
          db.execute('SELECT name FROM [%s]' % old_table).fetchall(), [('M',)]
        )
    finally:
      db.close()

  def test_anonymous_entry_is_renamed(self):
    text = (
        '(IProg "%(m)s" ["Prelude"] [] [(IFunction ("%(m)s","f",0) 0 Public []'
        ' (IFuncBody (IBlock [] [] (IReturn (ILit (IInt 1))))))])\n'
      )
    fint = (
        'Prog "%(m)s" ["Prelude"] [] [Func ("%(m)s","f") 0 Public '
        '(TCons ("Prelude","Int") []) (Rule [] (Var 0))] []\n'
      )
    icurry = 'interface %(m)s where {\nimport Prelude;\nf 0 :: Prelude.Int\n}'
    products = lambda name: {
        '.icy': text % {'m': name}, '.fint': fint % {'m': name}
      , '.icurry': icurry % {'m': name}
      }
    slot = self.slot('sprite__interactive_3')
    self.assertFalse(slot)
    self.convert(slot, products('sprite__interactive_3'))
    other = self.slot('sprite__expression_9')
    self.assertTrue(other)
    # The three files carry the new name.
    self.assertEqual(files(other.file_out), products('sprite__expression_9'))
    # The stored row keeps the first name.
    self.assertEqual(rows(self.cachefile)[0][1], 'sprite__interactive_3')

  def test_entry_of_another_module_is_ignored(self):
    def insert(key, name, text):
      db = sqlite3.connect(self.cachefile)
      with db:
        db.execute(
            'INSERT OR REPLACE INTO [%s](key, name, text, created) '
            'VALUES(?, ?, ?, 0)' % cache.Curry2ICurryCache.TABLE
          , (key, name, text)
          )
      db.close()
    # A named module under the key of another name.
    slot = self.slot('M')
    insert(slot.key, 'N', '(IProg "N" ["Prelude"] [] [])\n')
    with capture_log('curry.cache') as log:
      self.assertFalse(self.slot('M'))
    log.checkMessages(self, warning='ignoring a cache entry of module')
    # A named module under the key of an anonymous one.
    slot = self.slot('sprite__interactive_0')
    insert(slot.key, 'M', '(IProg "M" ["Prelude"] [] [])\n')
    with capture_log('curry.cache') as log:
      self.assertFalse(self.slot('sprite__interactive_0'))
    log.checkMessages(self, warning='ignoring a cache entry of module')
    # A packaged module matches on its last component.
    slot = self.slot('Maybe')
    insert(slot.key, 'Data.Maybe', '(IProg "Data.Maybe" ["Prelude"] [] [])\n')
    self.assertTrue(self.slot('Maybe'))
    # A text without a module name is not stored.
    slot = self.slot('Q')
    write(slot.file_out, 'garbage\n')
    with capture_log('curry.cache') as log:
      slot.update()
    log.checkMessages(self, warning='no module name found')
    self.assertFalse(self.slot('Q'))

  def test_program_error(self):
    '''A positioned error of the front end is stored; another failure is not.'''
    def failure(stderr):
      err = curry.CompileError('while running icurry:\n' + stderr)
      err.stderr = stderr
      err.returncode = 1
      return err
    program_error = (
        "\nsprite__interactive_3.curry:2:3 Error:\n    `x' is undefined\n"
        "   | \n 2 | f=x\n   |   ^\nERROR: user error: Illegal source program\n"
      )
    # The front end reports a span for a name of more than one character.
    span_error = (
        "\nS.curry:2:8-2:10 Error:\n    `foo' is undefined\n"
        "   | \n 2 | main = foo\n   |        ^^^\n"
        "ERROR: user error: Illegal source program\n"
      )
    # A missing module has a position, but the module may appear later in
    # the path without a change to any source file.
    missing_module = (
        "\nP.curry:1:8-1:11 Error:\n    Interface for module Nope not found\n"
        "   | \n 1 | import Nope\n   |        ^^^^\n"
        "ERROR: user error: Illegal source program\n"
      )
    self.assertTrue(cache.is_program_error(program_error))
    self.assertTrue(cache.is_program_error(span_error))
    self.assertFalse(cache.is_program_error(missing_module))
    self.assertFalse(cache.is_program_error('ERROR: File nope.fcy not found\n'))
    self.assertFalse(cache.is_program_error(None))
    slot = self.slot('sprite__interactive_3', text='f=x\n')
    self.assertFalse(slot)
    self.assertIsNone(slot.error)
    slot.update_error(failure(program_error))
    # The same text under another anonymous name replays the error with the
    # new name; the file is not written.
    again = self.slot('sprite__interactive_31', text='f=x\n')
    self.assertFalse(again)
    self.assertEqual(
        again.error
      , program_error.replace('sprite__interactive_3', 'sprite__interactive_31')
      )
    self.assertFalse(os.path.exists(again.file_out))
    # An error with a span is stored as well.
    slot = self.slot('S', text='main = foo\n')
    slot.update_error(failure(span_error))
    self.assertEqual(self.slot('S', text='main = foo\n').error, span_error)
    # A missing module is not stored.
    slot = self.slot('P', text='import Nope\n')
    slot.update_error(failure(missing_module))
    self.assertIsNone(self.slot('P', text='import Nope\n').error)
    # A failure of the environment is not stored.
    slot = self.slot('M', text='f=y\n')
    slot.update_error(failure('ERROR: File nope.fcy not found\n'))
    self.assertFalse(self.slot('M', text='f=y\n'))
    slot = self.slot('N', text='f=y\n')
    slot.update_error(curry.CompileError('no stderr attribute'))
    self.assertFalse(self.slot('N', text='f=y\n'))
    self.assertEqual(
        [row[1] for row in rows(self.cachefile)], ['sprite__interactive_3', 'S']
      )

  def test_force_update(self):
    slot = self.slot('M')
    write(slot.file_out, '(IProg "M" ["Prelude"] [] [])\n')
    slot.update()
    self.assertTrue(self.slot('M'))
    with binding(os.environ, 'SPRITE_CACHE_UPDATE', '*/M.curry'):
      cache.reset()
      with capture_log('curry.cache') as log:
        slot = self.slot('M')
      self.assertFalse(slot)
      log.checkMessages(self, info='forced to update')
      write(slot.file_out, '(IProg "M" [] [] [])\n')
      slot.update()
      # Another file does not match the pattern.
      self.assertFalse(self.slot('N'))
    cache.reset()
    slot = self.slot('M')
    self.assertTrue(slot)
    self.assertEqual(cytest.readfile(slot.file_out), '(IProg "M" [] [] [])\n')
    with binding(os.environ, 'SPRITE_CACHE_UPDATE', '/M\\.curry$/'):
      cache.reset()
      self.assertFalse(self.slot('M'))
      self.assertFalse(self.slot('N'))

  def test_enabled_by_the_environment(self):
    self.assertTrue(cache.enabled())
    self.assertTrue(cache.icurry_cache_enabled())
    self.assertEqual(cache.filename(), self.cachefile)
    self.assertTrue(_curry2icurry.Curry2ICurryConverter().use_cache)
    self.assertFalse(
        _curry2icurry.Curry2ICurryConverter(use_cache=False).use_cache
      )

  def test_disabled_by_the_empty_string(self):
    with cache_file(enabled=False):
      self.assertFalse(cache.enabled())
      self.assertFalse(cache.icurry_cache_enabled())
      self.assertIsNone(cache.filename())
      self.assertFalse(_curry2icurry.Curry2ICurryConverter().use_cache)
      slot = self.slot('M')
      self.assertFalse(slot)
      self.assertIsNone(slot.db)
      slot.update() # no file to read, no error

  def test_unset_variable_follows_the_installation(self):
    '''
    Without SPRITE_CACHE_FILE, Make.config decides, and nothing is created.
    '''
    from curry.utility.binding import del_
    with tempfile.TemporaryDirectory() as home:
      with binding(os.environ, 'HOME', home):
        with binding(os.environ, 'SPRITE_CACHE_FILE', del_):
          cache.reset()
          try:
            default = config.default_sprite_cache_file()
            if default:
              self.assertEqual(
                  cache.filename()
                , os.path.abspath(default.format(**os.environ))
                )
              self.assertTrue(cache.filename().startswith(home + os.sep))
            self.assertEqual(
                cache.icurry_cache_enabled()
              , bool(config.enable_icurry_cache()) and bool(default)
              )
            # Asking does not create the directory.
            self.assertEqual(os.listdir(home), [])
          finally:
            cache.reset()

  def test_unusable_cache_file_is_a_warning(self):
    blocker = write(os.path.join(self.tmpdir, 'blocker'), '')
    unusable = os.path.join(blocker, 'cache.db')
    with binding(os.environ, 'SPRITE_CACHE_FILE', unusable):
      cache.reset()
      with capture_log('curry.cache') as log:
        slot = self.slot('M')
      self.assertFalse(slot)
      self.assertIsNone(slot.db)
      log.checkMessages(self, warning='cannot open the cache file')
      cache.reset()

  def test_nosqlite3(self):
    '''Checks the warning issued when sqlite3 is not available.'''
    @with_import_blocked('sqlite3')
    def check():
      with capture_log('curry.cache') as log:
        importlib.reload(cache)
      log.checkMessages(self, warning='Cannot import sqlite3.  Caching is disabled')
      self.assertFalse(cache.icurry_cache_enabled())
      return True
    try:
      self.assertTrue(check())
    finally:
      importlib.reload(cache)


class TestCompile(cytest.TestCase):
  '''The cache under curry.compile and the toolchain, with the front end.'''

  @cytest.with_flags(defaultconverter='topython')
  def test_anonymous_module(self):
    '''
    The second compile of a text is a hit.  Its ICurry carries the new module
    name and is what the front end writes for that name.
    '''
    with cache_file() as cachefile:
      with frontend_calls() as calls:
        first = curry.compile(MODULE_TEXT)
        self.assertEqual(len(calls), 1)
        text1 = icurry_text(first)
        interfaces1 = interface_texts(first)
        second = curry.compile(MODULE_TEXT)
        self.assertEqual(len(calls), 1)
        text2 = icurry_text(second)
        interfaces2 = interface_texts(second)
      self.assertNotEqual(first.__name__, second.__name__)
      self.assertEqual(cache.icurry_modulename(text2), second.__name__)
      self.assertNotIn(first.__name__, text2)
      self.assertEqual(
          text2, cache.rename_module(text1, first.__name__, second.__name__)
        )
      # The interface files travel with the ICurry.  On the miss they are
      # copies of the front end's files; on the hit they come from the cache,
      # renamed, and the front end wrote nothing for the second module.
      self.assertEqual(sorted(interfaces1), sorted(cache.INTERFACE_SUFFIXES))
      for suffix in cache.INTERFACE_SUFFIXES:
        self.assertEqual(
            interfaces1[suffix]
          , cytest.readfile(_frontend.interfacefile(first.__file__, suffix))
          )
        self.assertEqual(
            interfaces2[suffix]
          , cache.rename_module(
                interfaces1[suffix], first.__name__, second.__name__
              )
          )
        self.assertFalse(
            os.path.exists(_frontend.interfacefile(second.__file__, suffix))
          )
      self.assertTrue(
          interfaces2['.fint'].startswith('Prog "%s" ' % second.__name__)
        )
      self.assertTrue(
          interfaces2['.icurry'].startswith(
              'interface %s where {' % second.__name__
            )
        )
      # The type synonym of the module is in the Curry interface of the hit.
      self.assertIn(
          'type Pair = (Prelude.Int, Prelude.Int);', interfaces2['.icurry']
        )
      self.assertEqual(len(rows(cachefile)), 1)
      # The module from the cache runs.
      self.assertEqual(next(curry.eval([second.f, 3])), 7)
      self.assertEqual(next(curry.eval([second.mapf, [1, 2]])), [4, 6])
      # A changed text misses.
      with frontend_calls() as calls:
        curry.compile(MODULE_TEXT + 'extra :: Int\nextra = 1\n')
        self.assertEqual(len(calls), 1)
      self.assertEqual(len(rows(cachefile)), 2)
    # Without the cache the front end writes, for a third name, the text the
    # rename gives, and the interface files are copied beside the ICurry.
    with cache_file(enabled=False):
      with frontend_calls() as calls:
        fourth = curry.compile(MODULE_TEXT)
        self.assertEqual(len(calls), 1)
      self.assertEqual(
          icurry_text(fourth)
        , cache.rename_module(text1, first.__name__, fourth.__name__)
        )
      self.assertEqual(
          interface_texts(fourth)
        , { suffix: cache.rename_module(content, first.__name__, fourth.__name__)
            for suffix, content in interfaces1.items()
          }
        )

  def test_second_process_compiles_nothing(self):
    '''
    A new process finds the module and the expression of this one in the
    cache, under its own module names, and the type of the expression in the
    interface beside its ICurry: no front end runs.
    '''
    with cache_file():
      with frontend_calls() as calls:
        module = curry.compile(MODULE_TEXT)
        curry.compile('1 + 2', 'expr', exprtype='Int')
        self.assertEqual(len(calls), 2)
      code = '\n'.join([
          'import curry, json, re'
        , 'from curry import cache, config'
        , 'from curry.toolchain import _filenames, _system'
        , 'pexec = _system.pexec'
        , 'tools = [config.curry_frontend(), config.icurry_tool()]'
        , 'def checking_pexec(cmd, *args, **kwds):'
        , '  if cmd[0] in tools:'
        , '    raise AssertionError("the front end ran: %r" % (cmd,))'
        , '  return pexec(cmd, *args, **kwds)'
        , '_system.pexec = checking_pexec'
        , 'module = curry.compile(%r)' % MODULE_TEXT
        , 'expr = curry.compile("1 + 2", "expr", exprtype="Int")'
        , 'values = [curry.topython(next(curry.eval([module.f, 3])))'
        , '         , curry.topython(next(curry.eval(expr)))]'
        , 'stats = cache.Curry2ICurryCache.stats'
        , 'exprmodule = curry.getInterpreter()._expression_modules[-1]'
        , 'icy = _filenames.icurryfilename(exprmodule.__file__)'
        , 'fint = open(cache.interface_filename(icy, ".fint")).read()'
        , 'pattern = r\'Func \\("%s","compiled_expression"\\) 0 Public \\((.*?)\\) \\(Rule\''
        , 'entry = re.search(pattern % exprmodule.__name__, fint)'
        , 'icurry = open(cache.interface_filename(icy, ".icurry")).read()'
        , 'print(json.dumps([values, stats, module.__name__, entry.group(1)'
          ', icurry.splitlines()[0]]))'
        ])
      proc = cytest.run_in_subprocess(code, timeout=300)
      self.assertEqual(proc.returncode, 0, proc.stderr)
      values, stats, name, exprtype, header = json.loads(
          proc.stdout.strip().splitlines()[-1]
        )
      self.assertEqual(values, [7, 3])
      self.assertEqual(stats, {'hit': 2, 'miss': 0})
      self.assertNotEqual(name, module.__name__)
      self.assertEqual(exprtype, 'TCons ("Prelude","Int") []')
      self.assertRegex(header, r'^interface sprite__expression_\d+ where \{$')

  def test_route_without_interfaces_stores_null(self):
    '''
    A route that leaves no interface file gets an empty file beside the
    ICurry and a NULL in the cache, with a warning.  The hit writes empty
    files as well.  The pinned front end writes both files on both routes
    (see unit_curry2icurry.py); this covers the fallback.
    '''
    if config.curry2icurry_tool() != 'frontend':
      self.skipTest('the configured route is not the front end')
    frontend_curry2icurry = _frontend.curry2icurry
    def forgetful(file_in, file_out, currypath, quiet=False):
      frontend_curry2icurry(file_in, file_out, currypath, quiet)
      os.unlink(_frontend.interfacefile(file_in, '.fint'))
    text = 'f :: Int\nf = 1\n'
    with cache_file() as cachefile:
      with mock.patch.object(_frontend, 'curry2icurry', forgetful):
        with capture_log('curry.toolchain._curry2icurry') as log:
          first = curry.compile(text)
      log.checkMessages(self, warning='left no %s.fint' % first.__name__)
      interfaces = interface_texts(first)
      self.assertEqual(interfaces['.fint'], '')
      self.assertTrue(interfaces['.icurry'].startswith('interface '))
      self.assertEqual(
          [row[3:] for row in rows(cachefile)], [(None, interfaces['.icurry'])]
        )
      with frontend_calls() as calls:
        second = curry.compile(text)
      self.assertEqual(calls, [])
      self.assertEqual(interface_texts(second)['.fint'], '')
      self.assertEqual(
          interface_texts(second)['.icurry']
        , cache.rename_module(
              interfaces['.icurry'], first.__name__, second.__name__
            )
        )

  def test_expression_follows_its_dynamic_import(self):
    '''
    Two processes compile the same expression text against a module of the
    same anonymous name (the counter starts at zero in every process) but of
    another type.  The second must miss: the key holds the source of the
    dynamic import.  A third process with the texts of the second hits.
    '''
    def child(module_text):
      code = '\n'.join([
          'import curry, json'
        , 'from curry import cache'
        , 'module = curry.compile(%r)' % module_text
        , 'expr = curry.compile('
          '"show (f 3)", "expr", imports=module, exprtype="String")'
        , 'value = curry.topython(next(curry.eval(expr)))'
        , 'stats = cache.Curry2ICurryCache.stats'
        , 'print(json.dumps([module.__name__, value, stats]))'
        ])
      proc = cytest.run_in_subprocess(code, timeout=300)
      self.assertEqual(proc.returncode, 0, proc.stderr)
      return json.loads(proc.stdout.strip().splitlines()[-1])
    with cache_file():
      first = child('f :: Int -> Int\nf x = x + 1\n')
      second = child('f :: Int -> [Int]\nf x = [x, x]\n')
      third = child('f :: Int -> [Int]\nf x = [x, x]\n')
    misses = {'hit': 0, 'miss': 2}
    self.assertEqual(first, ['sprite__interactive_0', '4', misses])
    self.assertEqual(second, ['sprite__interactive_0', '[3,3]', misses])
    self.assertEqual(
        third, ['sprite__interactive_0', '[3,3]', {'hit': 2, 'miss': 0}]
      )

  def test_program_error_is_cached(self):
    '''
    The second compile of a program the front end rejects runs no front end.
    '''
    with cache_file() as cachefile:
      messages = []
      for expected_calls in [1, 0]:
        with frontend_calls() as calls:
          with self.assertRaisesRegex(
              curry.CompileError, '.x. is undefined'
            ) as cm:
            curry.compile('f=x')
          self.assertEqual(len(calls), expected_calls)
        messages.append(str(cm.exception))
      names = [
          re.search(r'(sprite__interactive_\d+)\.curry:', m).group(1)
              for m in messages
        ]
      self.assertNotEqual(names[0], names[1])
      for message, name in zip(messages, names):
        # The command of the route names the module (its file for icurry, its
        # name for the front end), and the error names its position.
        self.assertIn(name, message.splitlines()[0])
        self.assertIn('%s.curry:2:3 Error:' % name, message)
      self.assertNotIn(names[0], messages[1])
      self.assertEqual([row[2] for row in rows(cachefile)], [''])

  def test_named_module(self):
    '''
    A source file compiled through the toolchain hits from another directory.
    '''
    with cache_file():
      with tempfile.TemporaryDirectory() as tmpdir:
        texts = []
        with frontend_calls() as calls:
          for i, sub in enumerate(['one', 'two']):
            curryfile = os.path.join(tmpdir, sub, 'hello.curry')
            os.makedirs(os.path.dirname(curryfile))
            shutil.copy(
                os.path.join('data', 'curry', 'hello.curry'), curryfile
              )
            icyfile = toolchain.curry2icurry(
                curryfile, currypath=[], quiet=True
              )
            self.assertEqual(len(calls), 1)
            texts.append(cytest.readfile(icyfile))
        self.assertEqual(texts[0], texts[1])
        self.assertEqual(cache.icurry_modulename(texts[1]), 'hello')
