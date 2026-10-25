import cytest # from ./lib; must be first
from cytest.buildtools import cmake_executable
from curry import config, icurry
from curry.toolchain import _frontend
import curry, glob, hashlib, os, shutil, subprocess, sys, tempfile, unittest, zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENV = {
    'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')
  , 'HOME': os.environ.get('HOME', '/')
  , 'LC_ALL': 'C.UTF-8'
  , 'TMPDIR': os.environ.get('TMPDIR', tempfile.gettempdir())
  }
if 'PYTHON_GIL' in os.environ:
  ENV['PYTHON_GIL'] = os.environ['PYTHON_GIL']

# The modules whose ICurry products are committed beside their sources under
# curry/lib.  The hash pins the source each product was made from.  After a
# change to one of these sources, rebuild its products (see curry/README.md)
# and update the hash here.
PINNED_SHA256 = {
    'Prelude'              : '0e80d110de5e2d33f6d270df7549cd56b89c22a3c81d0596261d5c56c5d4b4e4'
  , 'Control.SetFunctions' : '4d324ade06db0712738e7817b20b978fe3e3a89caabfe7c5fa78585dadcb1970'
  , 'Data.Char'            : 'f4d64684dff42c64eaeb62e0fe32b2cd2bf56a548913a674bc448cf9519e25f7'
  , 'Data.Either'          : '48d4a26127999f6a67e56fa23dc67d3efedc302b9b4dee002ce9c3e22ea5cc57'
  , 'Data.Function'        : '1c73aa4fde467d8017dbaa7be047fad96a19c0d35ae1bc774c1f00eaaf6f5182'
  , 'Data.Functor.Identity': '795b03c98f33cef6d58f6ea129d10f947ded3b992550e4d9ed7e94e8267cc7d6'
  , 'Data.List'            : '5d5a135967e9bbc4932b439da6a4f3e687b96279ce4a4813e783a12cc437d34b'
  , 'Data.Maybe'           : '004f7c64f9d9b214afcae95c7ff4e4c013b8fd8adba3e6a94f9a8e9c4f80e322'
  }

# The vendored Prelude is the PAKCS Prelude with this prefix.  The define
# selects the KiCS2 branches of the externals, which Sprite implements.
PRELUDE_PREFIX = '{-# LANGUAGE CPP #-}\n#define __KICS2__ 1\n\n'

def sourcefile(modulename):
  '''The installed source of a system library module.'''
  parts = modulename.split('.')
  return os.path.join(config.system_curry_path(), *parts[:-1], parts[-1] + '.curry')

def productfile(modulename, suffix):
  '''The installed product of a system library module, e.g., its .icy file.'''
  parts = modulename.split('.')
  return os.path.join(
      config.system_curry_path(), *parts[:-1]
    , '.curry', config.intermediate_subdir(), parts[-1] + suffix
    )

def interfacefile(modulename, suffix='.fint'):
  '''The installed FlatCurry interface of a system library module.'''
  parts = modulename.split('.')
  return os.path.join(
      config.system_curry_path(), '.curry', config.frontend_subdir(), *parts[:-1]
    , parts[-1] + suffix
    )

def unit_currylib_pinned():
  '''The names of the modules with committed products.'''
  return set(PINNED_SHA256)

def sha256(filename):
  with open(filename, 'rb') as istream:
    return hashlib.sha256(istream.read()).hexdigest()

def snapshot(root):
  '''The files under ``root`` with their sizes and modification times.'''
  found = set()
  for dirpath, _, filenames in os.walk(root):
    for filename in filenames:
      path = os.path.join(dirpath, filename)
      st = os.stat(path)
      found.add((os.path.relpath(path, root), st.st_size, st.st_mtime_ns))
  return found

def chmod_tree(root, dirmode, filemode):
  for dirpath, dirnames, filenames in os.walk(root):
    os.chmod(dirpath, dirmode)
    for filename in filenames:
      os.chmod(os.path.join(dirpath, filename), filemode)

class TestCurryLib(cytest.TestCase):
  '''Tests for the Curry library installed from curry/lib.'''

  def library_goal(self, imports, declarations):
    module = curry.compile(imports + '\n' + declarations)
    return list(curry.eval(module['goal']))

  def test_compose(self):
    '''Composition preserves the Functor and Applicative operations.'''
    self.assertEqual(self.library_goal('import Data.Functor.Compose', '''
goal :: [[Int]]
goal = getCompose (fmap (+1) (Compose [[1,2],[3]]))
'''), [[[2, 3], [4]]])
    self.assertEqual(self.library_goal('import Data.Functor.Compose', '''
goal :: [[Int]]
goal = getCompose (Compose [[(+1),(*2)]] <*> Compose [[3,4]])
'''), [[[4, 5, 6, 8]]])

  def test_const(self):
    '''Const ignores mapped functions and retains its derived instances.'''
    self.assertEqual(self.library_goal('import Data.Functor.Const', '''
goal :: (Bool, Bool, Int)
goal = ( Const 3 == (Const 3 :: Const Int Bool)
       , Const 2 < (Const 3 :: Const Int Bool)
       , getConst (read (show (Const 5 :: Const Int Bool)) :: Const Int Bool))
'''), [(True, True, 5)])
    self.assertEqual(self.library_goal('import Data.Functor.Const', '''
goal :: Int
goal = getConst (fmap (+1) (Const 7 :: Const Int Int))
'''), [7])

  def test_monoid(self):
    '''The six wrappers combine values with their documented identities.'''
    self.assertEqual(self.library_goal('import Data.Monoid', '''
goal :: (Int, Int, Bool, Bool, Int, Int)
goal = ( getSum (mappend (Sum 2) (Sum 3))
       , getProduct (mappend (Product 2) (Product 3))
       , getAll (mappend (All True) (All False))
       , getAny (mappend (Any False) (Any True))
       , maybe 0 id (getFirst (mappend (First (Just 2)) (First (Just 3))))
       , maybe 0 id (getLast (mappend (Last (Just 2)) (Last (Just 3)))))
'''), [(5, 6, False, True, 2, 3)])
    self.assertEqual(self.library_goal('import Data.Monoid', '''
goal :: (Int, Int, Bool, Bool, Bool, Bool)
goal = ( getSum mempty, getProduct mempty, getAll mempty, getAny mempty
       , getFirst (mempty :: First Int) == Nothing
       , getLast (mempty :: Last Int) == Nothing)
'''), [(0, 1, True, False, True, True)])

  def test_syslibs_installed(self):
    '''Every system library module is installed as a source, and nothing else is.'''
    syslibs = config.syslibs()
    self.assertEqual(syslibs[0], 'Prelude')
    self.assertEqual(syslibs[1:], sorted(syslibs[1:]))
    for name in ['Prelude', 'Control.SetFunctions', 'Numeric', 'System.IO', 'Text.Show']:
      self.assertIn(name, syslibs)
    for name in syslibs:
      self.assertTrue(os.path.isfile(sourcefile(name)), name)
    root = config.system_curry_path()
    found = set()
    for dirpath, dirnames, filenames in os.walk(root):
      dirnames[:] = [d for d in dirnames if not d.startswith('.')]
      for filename in filenames:
        if filename.endswith('.curry'):
          relpath = os.path.relpath(os.path.join(dirpath, filename[:-6]), root)
          found.add('.'.join(relpath.split(os.sep)))
    self.assertEqual(found, set(syslibs))

  def test_module_names_script(self):
    '''The module list in the source tree agrees with the staged configuration.'''
    script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'curry', 'module_names.py'
      )
    if not os.path.exists(script):
      self.skipTest('the source tree is not available')
    output = subprocess.check_output([sys.executable, script], text=True)
    self.assertEqual(output.split(), config.syslibs())

  def test_notices(self):
    '''The license of the origin and the notice are installed with the library.'''
    license_ = os.path.join(config.system_curry_path(), 'LICENSE')
    notice = os.path.join(config.system_curry_path(), 'NOTICE')
    self.assertTrue(os.path.isfile(license_))
    with open(notice) as istream:
      text = istream.read()
    self.assertIn('PAKCS 3.10.0', text)
    self.assertIn('3.4.0', text)
    self.assertIn('__KICS2__', text)
    self.assertIn('Control/SetFunctions.curry', text)
    # The repository has no license file yet; the notice must not cite one.
    self.assertIn('is not covered by the\nPAKCS license', text)
    self.assertNotIn('Sprite license', text)

  def test_prelude_prefix(self):
    '''The Prelude is the PAKCS Prelude behind the three-line prefix.'''
    with open(sourcefile('Prelude')) as istream:
      text = istream.read()
    self.assertTrue(text.startswith(PRELUDE_PREFIX))
    rest = text[len(PRELUDE_PREFIX):]
    self.assertIn('The standard prelude', rest.split('module Prelude', 1)[0])
    self.assertIn('#ifdef __KICS2__', rest)
    self.assertIn('{-# LANGUAGE CPP #-}', rest)

  def test_pinned_sources(self):
    '''The sources of the pinned modules are the ones their products were made from.'''
    for name, digest in PINNED_SHA256.items():
      self.assertEqual(sha256(sourcefile(name)), digest, name)

  def test_pinned_products(self):
    '''The committed .icy and .json.z files of the pinned modules are installed.'''
    for name in PINNED_SHA256:
      self.assertTrue(os.path.isfile(productfile(name, '.icy')), name)
      self.assertTrue(os.path.isfile(productfile(name, '.json.z')), name)
    # The products of a small module parse, name the module, and agree.
    for name in ['Data.Function', 'Data.Either', 'Data.Maybe']:
      imodule = icurry.readcurry.load(productfile(name, '.icy'))
      self.assertEqual(imodule.fullname, name)
      with open(productfile(name, '.json.z'), 'rb') as istream:
        ijson = icurry.json.loads(zlib.decompress(istream.read()))
      self.assertEqual(ijson, imodule)

  def test_import_source_only_module(self):
    '''
    A module shipped as source only (no committed products) compiles on
    first use.  The products that the installation holds for it are set
    aside, so the import compiles the module, and they are put back
    afterwards: unit_prebuild.py expects the products of every module.
    '''
    self.assertNotIn('Numeric', unit_currylib_pinned())
    saved = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    # The products and the bytecode cache of the Python file.  The cache goes
    # with the file: a cache of another copy of the file is stale.
    patterns = [
        productfile('Numeric', '.*')
      , os.path.join(os.path.dirname(productfile('Numeric', '.py')), '__pycache__', 'Numeric.*')
      ]
    # The products in the order of the toolchain.  copy2 keeps their
    # modification times, which the staleness rule of the toolchain compares,
    # and each product is put back after the one it is made from.
    order = ['.icy', '.json.z', '.py', '.pyc', '.cpp', '.so', '.so.abi']
    def rank(path):
      return next((i for i, s in enumerate(order) if path.endswith(s)), len(order))
    def found():
      return sorted((f for pattern in patterns for f in glob.glob(pattern)), key=rank)
    products = found()
    def restore():
      for product in found():
        os.remove(product)
      for product in products:
        os.makedirs(os.path.dirname(product), exist_ok=True)
        shutil.copy2(os.path.join(saved, os.path.basename(product)), product)
      shutil.rmtree(saved, ignore_errors=True)
    self.addCleanup(restore)
    for product in products:
      shutil.copy2(product, saved)
      os.remove(product)
    self.assertFalse(os.path.exists(productfile('Numeric', '.icy')))
    Numeric = curry.import_('Numeric')
    self.assertEqual(next(curry.eval((Numeric.readHex)('ffz'))), [(255, 'z')])
    self.assertTrue(os.path.isfile(productfile('Numeric', '.icy')))
    # The import leaves the installed FlatCurry file of the module in place:
    # the front end reads it for every program, and a cache hit would not
    # make it again (the staleness rule of #164 forces the elaboration of a
    # module whose imports changed by removing that file, never for a module
    # of the shipped library).
    self.assertTrue(os.path.isfile(interfacefile('Numeric', '.fcy')))

  def test_interfaces_installed(self):
    '''
    The FlatCurry interfaces of every library module are installed, so the
    front end reads them and never writes them into the installation tree.
    '''
    if config.curry_frontend() is None:
      self.skipTest('the Curry front end is not configured')
    for name in config.syslibs():
      for suffix in ['.fcy', '.fint', '.icurry']:
        self.assertTrue(os.path.isfile(interfacefile(name, suffix)), name + suffix)
      # The interface is at least as new as the source it was made from.
      self.assertGreaterEqual(
          os.stat(interfacefile(name)).st_mtime, os.stat(sourcefile(name)).st_mtime, name
        )

  def test_readonly_library(self):
    '''
    The front end compiles a program against a read-only copy of the installed
    library without writing into it.
    '''
    if config.curry_frontend() is None:
      self.skipTest('the Curry front end is not configured')
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
      self.skipTest('file permissions do not bind the superuser')
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    copy = os.path.join(tmpdir, 'curry')
    def cleanup():
      chmod_tree(copy, 0o755, 0o644)
      shutil.rmtree(tmpdir, ignore_errors=True)
    self.addCleanup(cleanup)
    # The compiled forms (.py, .so, ...) under sprite-* are not needed.
    shutil.copytree(
        config.system_curry_path(), copy
      , ignore=shutil.ignore_patterns(config.intermediate_subdir())
      )
    chmod_tree(copy, 0o555, 0o444)
    before = snapshot(copy)
    program = os.path.join(tmpdir, 'UseLib.curry')
    with open(program, 'w') as ostream:
      ostream.write(
          'import Control.Monad\nimport Data.List\nimport Numeric\nimport System.IO\n'
          'main :: IO ()\nmain = when True (putStrLn (show (nub [1, 2, 1 :: Int])))\n'
        )
    fcyfile = _frontend.curry2flat(program, [copy], quiet=True)
    self.assertTrue(os.path.isfile(fcyfile))
    self.assertTrue(fcyfile.startswith(tmpdir))
    self.assertEqual(snapshot(copy), before)

  def test_install_interfaces(self):
    """CMake installs the interfaces and pinned products of its build image."""
    build = os.environ.get('SPRITE_TEST_BUILD_DIR', os.path.join(ROOT, 'object-root', 'cmake'))
    if not os.path.isfile(os.path.join(build, 'CMakeCache.txt')):
      self.skipTest('the source tree has no CMake build')
    cmake = cmake_executable(build)
    if cmake is None:
      self.skipTest('cmake is not available')
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as prefix:
      result = subprocess.run(
          [cmake, '--install', build, '--prefix', prefix], env=ENV
        , stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=600)
      self.assertEqual(result.returncode, 0, result.stdout)
      libdir = os.path.join(prefix, 'curry')
      flatdir = os.path.join(libdir, '.curry', config.frontend_subdir())
      for name in config.syslibs():
        parts = name.split('.')
        self.assertTrue(os.path.isfile(os.path.join(libdir, *parts) + '.curry'), name)
        for suffix in ['.fcy', '.fint', '.icurry']:
          self.assertTrue(os.path.isfile(os.path.join(flatdir, *parts) + suffix), name)
        sidecars = os.path.join(libdir, *parts[:-1], '.curry',
                                config.intermediate_subdir(), parts[-1])
        for suffix in ['.icy', '.fint', '.icurry', '.json.z']:
          self.assertTrue(os.path.isfile(sidecars + suffix), name + suffix)
      for name in config.supported_syslibs():
        parts = name.split('.')
        stamp = os.path.join(libdir, *parts[:-1], '.curry',
            config.intermediate_subdir(), parts[-1] + '.so.abi')
        with open(stamp) as stream:
          self.assertEqual(stream.read().splitlines()[1], os.path.realpath(prefix))
      result = subprocess.run(
          [cmake, '--install', build, '--prefix', prefix], env=ENV
        , stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=600)
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertNotIn('--flat', result.stdout)
