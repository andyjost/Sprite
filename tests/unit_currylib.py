import cytest # from ./lib; must be first
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

# The modules whose ICurry products are committed beside their sources under
# curry/lib.  The hash pins the source each product was made from.  After a
# change to one of these sources, rebuild its products (see curry/README.md)
# and update the hash here.
PINNED_SHA256 = {
    'Prelude'              : '748bf87cf8a5c197d8b6c84a20cdc12c4c4cef6ef9280287351bc8d15e180d00'
  , 'Control.SetFunctions' : '675fcba933c71e68b0bc6ec3fc374b44e1b1a97fdcf18a2d86b93a2c9a6fd353'
  , 'Data.Char'            : '11259bdd56bb7760ac3078e0ae00e1d32f28fdf3b68fc2b4cee3cdc76f8c0214'
  , 'Data.Either'          : 'e1905d37f366c9bdb4de75e3d558bc0d090ade88b714a21109fd8ba32c0cf051'
  , 'Data.Function'        : 'cb6a890a3d0f0524585c8437a2ed257af88331250c24d8b9efadba7da66003ee'
  , 'Data.Functor.Identity': '795b03c98f33cef6d58f6ea129d10f947ded3b992550e4d9ed7e94e8267cc7d6'
  , 'Data.List'            : '937fdccb70b253bdbc05e655523efbd1b6e63f833882a347965c73a80ea3bdcf'
  , 'Data.Maybe'           : 'dc5c300183d8c2bd2ec488e2ab8b1c997918f481c5e70c62e241b6978bc8cec1'
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
    self.assertIn('PAKCS 3.4.1', text)
    self.assertIn('3.1.0', text)
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
    self.assertTrue(rest.startswith('-' * 80 + '\n--- The standard prelude'))
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

  @cytest.with_flags(defaultconverter='topython')
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
    self.assertEqual(next(curry.eval([Numeric.readHex, 'ffz'])), [(255, 'z')])
    self.assertTrue(os.path.isfile(productfile('Numeric', '.icy')))

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
    '''
    make install writes the library interfaces with the front end, and make
    uninstall removes them.
    '''
    if config.curry_frontend() is None:
      self.skipTest('the Curry front end is not configured')
    makefile = os.path.join(ROOT, 'curry', 'Makefile')
    if not os.path.isfile(makefile) or not os.path.isfile(os.path.join(ROOT, 'Make.config')):
      self.skipTest('the source tree is not available')
    def make(*args):
      return subprocess.run(
          ['make', '-C', os.path.dirname(makefile)] + list(args), env=ENV
        , stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=600
        )
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as prefix:
      result = make('install', 'PREFIX=' + prefix)
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertEqual(result.stdout.count('--flat'), 1, result.stdout)
      libdir = os.path.join(prefix, 'curry')
      flatdir = os.path.join(libdir, '.curry', config.frontend_subdir())
      for name in config.syslibs():
        parts = name.split('.')
        self.assertTrue(os.path.isfile(os.path.join(libdir, *parts) + '.curry'), name)
        for suffix in ['.fcy', '.fint', '.icurry']:
          self.assertTrue(os.path.isfile(os.path.join(flatdir, *parts) + suffix), name)
      self.assertTrue(os.path.isfile(os.path.join(
          libdir, 'Data', '.curry', config.intermediate_subdir(), 'Maybe.icy'
        )))
      # A second install runs the front end again only when a source changed.
      result = make('install', 'PREFIX=' + prefix)
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertNotIn('--flat', result.stdout)
      result = make('uninstall', 'PREFIX=' + prefix)
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertFalse(os.path.exists(libdir), os.listdir(prefix))
