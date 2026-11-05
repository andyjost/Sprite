import cytest # from ./lib; must be first
from cytest.buildtools import cmake_executable
from curry import config, icurry
from curry.toolchain import _curry2icurry, _frontend
import curry, glob, hashlib, os, shutil, subprocess, sys, tempfile, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENV = {
    'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')
  , 'HOME': os.environ.get('HOME', '/')
  , 'LC_ALL': 'C.UTF-8'
  , 'TMPDIR': os.environ.get('TMPDIR', tempfile.gettempdir())
  }
if 'PYTHON_GIL' in os.environ:
  ENV['PYTHON_GIL'] = os.environ['PYTHON_GIL']

# Historical source checks for the original subset of library pins.
# Every module now has products and a source receipt under curry/lib.
# After a change to one of these sources, rebuild its products (see curry/README.md)
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

  def test_missing_installed_translation(self):
    from pathlib import Path
    from curry.toolchain import _filenames
    from unit_reserved_modules import installed, products
    import re
    for mode in ('new', 'all', 'off'):
      for readonly in (False, True):
        if readonly and os.name == 'nt':
          continue
        with self.subTest(mode=mode, readonly=readonly), tempfile.TemporaryDirectory() as work:
          if not readonly:
            source = Path(work) / 'Data/Char.curry'
            source.parent.mkdir()
            text = installed('Data.Char').read_text().replace(
                'digitToInt      :: Char -> Int', 'digitToInt      :: Num a => Char -> a')
            text = re.sub(r"=  (ord c - ord '[0Aa]'(?: \+ 10)?)", r'=  fromInt (\1)', text)
            source.write_text(text)
          icy = Path(_filenames.icurryfilename(str(installed('Numeric'))))
          saved = {p: p.read_bytes() for p in (icy, Path(str(icy) + '.imports'))}
          permissions = icy.parent.stat().st_mode
          try:
            for p in saved:
              p.unlink()
            before = products(installed('Numeric'))
            if readonly:
              icy.parent.chmod(permissions & ~0o222)
            code = """
import curry, os
from curry.objects.handle import getHandle
curry.reset(interpret=%r, jit='off')
curry.path.insert(0, %r)
m = curry.import_('Numeric')
assert not os.path.realpath(getHandle(m).icurry.filename).startswith(os.path.realpath(curry.config.installed_path('curry')) + os.sep)
assert curry.show(curry.eval(m.readNat(curry.term('1'))).one()) == '[(1,"")]'
""" % (mode, work)
            child = cytest.run_in_subprocess(code, timeout=120, address_space=3 << 30)
            self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
            self.assertEqual(products(installed('Numeric')), before)
          finally:
            icy.parent.chmod(permissions)
            for p, data in saved.items():
              p.write_bytes(data)

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
    self.assertEqual(config.supported_syslibs(), syslibs)
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
    '''The pinned ICurry and its derived module image are installed.'''
    for name in config.syslibs():
      if config.frontend_version() == '3.1.0':
        source = os.path.join(ROOT, 'curry', 'lib', *name.split('.')) + '.curry'
        pinned = os.path.join(os.path.dirname(source), '.curry',
            'sprite-pakcs-3.10.0', os.path.basename(source)[:-6] + '.icy')
        with open(pinned, 'rb') as expected, open(productfile(name, '.icy'), 'rb') as actual:
          self.assertEqual(expected.read(), actual.read(), name)
      self.assertTrue(os.path.isfile(productfile(name, '.icy')), name)
      if name not in config.unsupported_syslibs():
        self.assertTrue(os.path.isfile(productfile(name, '.img')), name)
    # The products of a small module parse, name the module, and agree.
    for name in ['Data.Function', 'Data.Either', 'Data.Maybe']:
      imodule = icurry.readcurry.load(productfile(name, '.icy'))
      self.assertEqual(imodule.fullname, name)
      from curry.backends.cxx import image
      self.assertEqual(image.read(productfile(name, '.img'))['source'],
          image.digest(productfile(name, '.icy')))

  def test_rebuild_library_module(self):
    '''
    A library module compiles from source when its installed products are set
    aside, so the import compiles the module, and they are put back
    afterwards: unit_prebuild.py expects the products of every module.
    '''
    if config.curry_frontend() is None:
      self.skipTest('rebuilding a library module requires the front end')
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
    order = ['.icy', '.img', '.py', '.pyc', '.cpp', '.so', '.so.abi']
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
    self.assertFalse(os.path.exists(productfile('Numeric', '.icy')))
    from curry.objects.handle import getHandle
    from curry.toolchain import _filenames
    rebuiltfile = _filenames.icurryfilename(getHandle(Numeric).icurry.filename)
    self.assertFalse(os.path.realpath(rebuiltfile).startswith(
        os.path.realpath(config.installed_path('curry')) + os.sep))
    with open(rebuiltfile, 'rb') as rebuilt:
      with open(os.path.join(saved, 'Numeric.icy'), 'rb') as staged:
        self.assertEqual(rebuilt.read(), staged.read())
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
      # Windows ships the versioned interfaces beside ICurry; FlatCurry
      # bodies are build inputs, not installed products there.
      suffixes = ['.fint', '.icurry'] if os.name == 'nt' else ['.fcy', '.fint', '.icurry']
      for suffix in suffixes:
        path = (productfile(name, suffix) if os.name == 'nt' else
                interfacefile(name, suffix))
        self.assertTrue(os.path.isfile(path), name + suffix)
      if os.name == 'nt':
        # Staged copies need not preserve the build-input timestamp order.
        self.assertTrue(_curry2icurry.source_matches(
            sourcefile(name), productfile(name, '.icy')), name)
      else:
        # The interface is at least as new as the source it was made from.
        self.assertGreaterEqual(
            os.stat(interfacefile(name)).st_mtime,
            os.stat(sourcefile(name)).st_mtime, name)


  @cytest.posix_only('requires POSIX directory permission bits')
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

  def test_builtin_missing_prerequisite_rewrite(self):
    self._explicit_make_replaced_import_is_private(
        '--rewrite-flat', transitive=True, missing_frontend=True)

  def test_builtin_missing_prerequisite_import(self):
    self._explicit_make_replaced_import_is_private(
        '--import', transitive=True, missing_frontend=True)

  def test_user_rewrite_replaced_import_is_private(self):
    self._explicit_make_replaced_import_is_private(
        '--rewrite-flat', transitive=True, user=True)

  def test_user_import_replaced_import_is_private(self):
    self._explicit_make_replaced_import_is_private(
        '--import', transitive=True, user=True)

  def test_interface_view_reuse_and_invalidation(self):
    from pathlib import Path
    from unittest.mock import patch
    from curry.toolchain import _interfaceview
    from contextlib import contextmanager
    import time
    outdir = os.path.join('.curry', config.frontend_subdir())
    _interfaceview._views.clear()
    copy = shutil.copy2
    with tempfile.TemporaryDirectory() as work:
      for number in (1, 2):
        program = Path(work) / ('View%d.curry' % number)
        program.write_text('module View%d where\ngoal = True\n' % number)
        elapsed = []
        original_view = _interfaceview.interface_view
        @contextmanager
        def measured(outdir):
          started = time.monotonic()
          with original_view(outdir) as library:
            elapsed.append(time.monotonic() - started)
            yield library
        with patch.object(_interfaceview, 'interface_view', measured), \
             patch.object(_interfaceview.shutil, 'copy2', wraps=copy) as copies:
          _frontend.curry2flat(str(program), [], quiet=True)
        print('Interface view translation %d: %d copies, %.6f s' %
              (number, copies.call_count, elapsed[0]))
        if number == 1:
          self.assertGreater(copies.call_count, 0)
        else:
          self.assertEqual(copies.call_count, 0)
      fake = Path(work) / 'library/.curry' / config.intermediate_subdir()
      fake.mkdir(parents=True)
      product = fake / 'Probe.fint'
      product.write_text('first')
      installed_path = config.installed_path
      def installed(*parts):
        return str(Path(work) / 'library') if parts == ('curry',) else installed_path(*parts)
      with patch.object(config, 'syslibs', return_value=['Probe']), \
           patch.object(config, 'installed_path', installed):
        with _interfaceview.interface_view(outdir) as first:
          before = product.stat()
          self.assertEqual((Path(first) / 'Probe.fint').stat().st_mtime_ns,
                           before.st_mtime_ns)
          product.write_text('other')
          os.utime(product, ns=(before.st_atime_ns, before.st_mtime_ns))
          with _interfaceview.interface_view(outdir) as second:
            self.assertNotEqual(first, second)
            self.assertEqual((Path(second) / 'Probe.fint').read_text(), 'other')
          os.utime(product, ns=(before.st_atime_ns, before.st_mtime_ns + 1000000))
          with _interfaceview.interface_view(outdir) as third:
            self.assertNotEqual(second, third)

  def test_loaded_private_import_closure_destination(self):
    from pathlib import Path
    from curry.toolchain import _filenames
    for mode in ('new', 'all'):
      with self.subTest(mode=mode), tempfile.TemporaryDirectory() as work:
        root = Path(work)
        maybe = root / 'Data/Maybe.curry'
        maybe.parent.mkdir()
        maybe.write_text(Path(sourcefile('Data.Maybe')).read_text().replace(
            'listToMaybe (a : _) = Just a', 'listToMaybe (a : _) = Nothing'))
        target = Path(_filenames.icurryfilename(sourcefile('System.Console.GetOpt')))
        removed = [target, Path(str(target) + '.imports')]
        library = Path(config.installed_path('curry'))
        before = {p: p.read_bytes() for p in library.rglob('*') if p.is_file()}
        try:
          for p in removed:
            p.unlink(missing_ok=True)
          expected = {p: p.read_bytes() for p in library.rglob('*') if p.is_file()}
          code = r"""
import curry, os
from curry.backends.cxx import image
from curry.objects.handle import getHandle
curry.reset(interpret=%r, jit='off')
curry.path.insert(0, %r)
lists = curry.import_('Data.List')
raw = getHandle(lists).icurry
generation = raw._loaded_generation
assert generation.source.startswith(curry.config.installed_path('curry')), generation.source
assert not generation.image.startswith(curry.config.installed_path('curry')), generation.image
module = curry.import_('System.Console.GetOpt')
raw = getHandle(module).icurry
assert not raw.filename.startswith(curry.config.installed_path('curry')), raw.filename
assert not raw._loaded_generation.image.startswith(curry.config.installed_path('curry'))
curry.reset(interpret=%r, jit='off')
curry.path.remove(%r)
module = curry.import_('Data.Maybe')
assert curry.show(curry.eval(module.listToMaybe(curry.term([1]))).one()) == 'Just 1'
""" % (mode, work, mode, work)
          child = cytest.run_in_subprocess(code, timeout=180, address_space=3 << 30)
          self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
          self.assertEqual({p: p.read_bytes() for p in library.rglob('*') if p.is_file()}, expected)
        finally:
          # Restore the complete installation even if a writer regresses.
          for p in library.rglob('*'):
            if p.is_file() and p not in before:
              p.unlink()
          for p, data in before.items():
            if not p.exists() or p.read_bytes() != data:
              p.write_bytes(data)

  def test_later_explicit_list_replacement(self):
    from pathlib import Path
    from curry.backends.cxx import tiered
    for reset in (False, True):
      with self.subTest(reset=reset), tempfile.TemporaryDirectory() as work:
        root = Path(work)
        maybe = root / 'first/Data/Maybe.curry'
        maybe.parent.mkdir(parents=True)
        maybe.write_text(Path(sourcefile('Data.Maybe')).read_text().replace(
            'listToMaybe (a : _) = Just a', 'listToMaybe (a : _) = Nothing'))
        first = root / 'user/First.curry'
        first.parent.mkdir()
        first.write_text('module First where\nimport System.Console.GetOpt\ngoal = True\n')
        _frontend.curry2flat(str(first), [str(root / 'first')], quiet=True)
        self.assertTrue(list(Path(tiered._state.tmpdir).rglob('List.curry')))
        if reset:
          curry.reset()
        replacement = root / 'second/Data/List.curry'
        replacement.parent.mkdir(parents=True)
        text = Path(sourcefile('Data.List')).read_text()
        # Add the export to the existing explicit export list.
        start = text.index('module Data.List')
        export = text.index('(', start)
        text = text[:export + 1] + 'sentinel, ' + text[export + 1:]
        replacement.write_text(text + '\nsentinel :: Int\nsentinel = 42\n')
        second = root / 'other/Second.curry'
        second.parent.mkdir()
        second.write_text('module Second where\nimport Data.List (sentinel)\ngoal = sentinel\n')
        result = _frontend.curry2flat(str(second), [str(root / 'second')], quiet=True)
        self.assertTrue(Path(result).is_file())

  def test_external_user_import_is_private(self):
    if config.icurry_tool() is None:
      self.skipTest('external icurry is not configured')
    self._explicit_make_replaced_import_is_private(
        '--external', transitive=True, user=True)

  def test_user_frontend_command(self):
    from unittest.mock import patch
    from curry.toolchain import _system
    import time
    with tempfile.TemporaryDirectory() as work:
      program = os.path.join(work, 'Probe.curry')
      with open(program, 'w') as stream:
        stream.write('module Probe where\nimport System.Console.GetOpt\ngoal = True\n')
      ordinary = _frontend.command(program, [], quiet=True)
      execute = _system.pexec
      commands = []
      def checked(cmd, **kwargs):
        commands.append(cmd)
        return execute(cmd, **kwargs)
      started = time.monotonic()
      with patch.object(_system, 'pexec', checked):
        result = _frontend.curry2flat(program, [], quiet=True)
      print('Warm user translation: %.6f s' % (time.monotonic() - started))
      self.assertTrue(os.path.isfile(result))
      self.assertEqual(len(commands), 1)
      actual = commands[0]
      def without_paths(cmd):
        result = []
        skip = False
        for item in cmd:
          if skip:
            skip = False
          elif item in ('-i', '-P'):
            skip = True
          else:
            result.append(item)
        return result
      self.assertEqual(without_paths(actual)[:-1], without_paths(ordinary)[:-1])
      self.assertEqual(actual[-1], program[:-6])
      self.assertIn('-P', actual)
      paths = [actual[i + 1] for i, item in enumerate(actual[:-1]) if item == '-i']
      self.assertNotIn(config.system_curry_path(), paths)
      self.assertEqual(os.path.realpath(paths[0]), os.path.realpath(work))
      self.assertEqual(paths[-1], actual[actual.index('-P') + 1])

  def test_missing_object_replaced_import_is_private(self):
    self._explicit_make_replaced_import_is_private(
        '--image', generalized=False, missing_object=True)

  def test_transitive_explicit_image_is_private(self):
    self._explicit_make_replaced_import_is_private(
        '--image', transitive=True, direct_icy=True)

  def test_transitive_rewrite_is_private(self):
    self._explicit_make_replaced_import_is_private(
        '--rewrite-flat', transitive=True)

  def test_transitive_import_stale_translation_is_private(self):
    self._explicit_make_replaced_import_is_private(
        '--import', transitive=True)

  def test_installed_icy_spellings(self):
    for spelling in ('relative', 'symlink'):
      for replaced in (False, True):
        with self.subTest(spelling=spelling, replaced=replaced):
          self._explicit_make_replaced_import_is_private(
              '--image', generalized=False, direct_icy=True,
              spelling=spelling, replaced=replaced)

  def test_explicit_icy_image_replaced_import_is_private(self):
    self._explicit_make_replaced_import_is_private(
        '--image', generalized=False, direct_icy=True)

  def test_explicit_image_replaced_import_is_private(self):
    self._explicit_make_replaced_import_is_private('--image', generalized=False)

  def test_explicit_rewrite_replaced_import_is_private(self):
    self._explicit_make_replaced_import_is_private('--rewrite-flat')

  def test_explicit_make_replaced_import_is_private(self):
    self._explicit_make_replaced_import_is_private('--icy')

  def _explicit_make_replaced_import_is_private(self, route, generalized=True,
                                                     direct_icy=False,
                                                     missing_object=False,
                                                     transitive=False,
                                                     spelling='absolute',
                                                     replaced=True, user=False,
                                                     missing_frontend=False):
    # This file runs exclusively: restore every installed byte and mode even
    # when an unfixed builder writes replacement-dependent products there.
    from pathlib import Path
    root = Path(config.installed_path('curry'))
    with tempfile.TemporaryDirectory() as work:
      backup = Path(work) / 'backup'
      shutil.copytree(root, backup)
      module = 'System.Console.GetOpt' if transitive else 'Numeric'
      dependency = 'Data.Maybe' if transitive else 'Data.Char'
      source = Path(work) / ('replacement/' + dependency.replace('.', '/') + '.curry')
      source.parent.mkdir(parents=True)
      text = Path(sourcefile('Data.Char')).read_text()
      text = text.replace('digitToInt      :: Char -> Int',
                          'digitToInt      :: Num a => Char -> a')
      import re
      text = re.sub(r"=  (ord c - ord '[0Aa]'(?: \+ 10)?)", r'=  fromInt (\1)', text)
      if not generalized:
        text = Path(sourcefile('Data.Char')).read_text()
        text = re.sub(r"=  (ord c - ord '[0Aa]'(?: \+ 10)?)", r'=  (\1) + 1', text)
      self.assertNotEqual(text, Path(sourcefile('Data.Char')).read_text())
      if transitive:
        text = Path(sourcefile(dependency)).read_text().replace(
            'listToMaybe (a : _) = Just a', 'listToMaybe (a : _) = Nothing')
      source.write_text(text)
      def restore():
        for entry in [root] + list(root.rglob('*')):
          entry.chmod(entry.stat().st_mode | 0o700)
        for entry in sorted(root.rglob('*'), reverse=True):
          if not (backup / entry.relative_to(root)).exists():
            if entry.is_dir():
              entry.rmdir()
            else:
              entry.unlink()
        for saved in backup.rglob('*'):
          destination = root / saved.relative_to(backup)
          if saved.is_dir():
            destination.mkdir(exist_ok=True)
          else:
            if not destination.exists() or destination.read_bytes() != saved.read_bytes():
              shutil.copyfile(saved, destination)
            shutil.copystat(saved, destination)
        for saved in sorted(backup.rglob('*'), reverse=True):
          if saved.is_dir():
            shutil.copystat(saved, root / saved.relative_to(backup))
        shutil.copystat(backup, root)

      for readonly in (False, True):
        with self.subTest(readonly=readonly):
          try:
            if route == '--import' and not user and not missing_frontend:
              for suffix in ('.icy', '.icy.source'):
                Path(productfile('Data.List', suffix)).unlink()
            if missing_frontend:
              if route == '--import':
                for suffix in ('.icy', '.icy.source'):
                  path = Path(productfile(module, suffix))
                  if path.exists():
                    path.unlink()
              for suffix in ('.fint', '.fcy'):
                paths = [Path(interfacefile('Data.List', suffix)),
                         root / 'Data/.curry' / config.frontend_subdir() /
                         ('List' + suffix)]
                for path in paths:
                  if path.exists():
                    path.unlink()
              self.assertTrue(Path(productfile('Data.List', '.fint')).is_file())
              self.assertTrue(Path(productfile('Data.List', '.icy')).is_file())
            if missing_object:
              Path(productfile(module, config.module_object_suffix())).unlink()
            expected_files = snapshot(str(root))
            expected_bytes = {p.relative_to(root): p.read_bytes()
                              for p in root.rglob('*') if p.is_file()}
            if readonly:
              for entry in [root] + list(root.rglob('*')):
                entry.chmod(entry.stat().st_mode & ~0o222)
            argument = productfile(module, '.icy') if direct_icy else module
            directory = str(source.parent.parent) if replaced else ''
            if transitive:
              directory = str(Path(work) / 'replacement')
            if user:
              userdir = Path(work) / ('user-readonly' if readonly else 'user-writable')
              userdir.mkdir()
              probe = userdir / 'Probe.curry'
              probe.write_text('module Probe where\nimport System.Console.GetOpt\ngoal = True\n')
              argument = str(probe)
            code = r"""
import os
os.environ['SPRITE_CACHE_FILE'] = ''
os.environ['SPRITE_DEBUG'] = '1'
os.environ['CURRYPATH'] = %r
missing_frontend = %r
if missing_frontend:
  os.environ['SPRITE_CURRY2ICURRY'] = 'frontend'
import curry
from pathlib import Path
from curry.tools import make
from curry.backends.cxx import tiered, image
from curry.objects.handle import getHandle
from curry.toolchain import _frontend
from curry.toolchain import flat2icurry
original_translate = flat2icurry.translate_file
read_list = []
frontend_paths = {}
from contextlib import contextmanager
from curry.toolchain import _interfaceview
original_view = _interfaceview.interface_view
live_views = set()
@contextmanager
def checked_view(outdir):
  with original_view(outdir) as library:
    live_views.add(library)
    try:
      yield library
    finally:
      live_views.remove(library)
if missing_frontend:
  _interfaceview.interface_view = checked_view
def checked_translate(fcyfile, finder, *args, **kwargs):
  if missing_frontend and fcyfile.endswith(os.path.join('System', 'Console', 'GetOpt.fcy')):
    path = finder.filename('Data.List')
    paths, library = frontend_paths[fcyfile]
    assert finder.searchdirs == paths, (finder.searchdirs, paths)
    assert library in live_views, 'interface view closed before translation'
    assert tiered._state.tmpdir and path.startswith(tiered._state.tmpdir + os.sep), path
    assert Path(path).name == 'List.fint', path
    assert Path(path).with_suffix('.fcy').is_file(), path
    assert path in [_frontend.interfacefile(str(p), '.fint')
                    for p in Path(tiered._state.tmpdir).rglob('List.curry')], path
    read_list.append(path)
  return original_translate(fcyfile, finder, *args, **kwargs)
flat2icurry.translate_file = checked_translate
original_protected_translation = _frontend.protected_translation
translation_routes = []
command_routes = []
@contextmanager
def checked_protected_translation(file_in, currypath, quiet=False, rewrite=True, external=False):
  translation_routes.append(external)
  try:
    with original_protected_translation(file_in, currypath, quiet, rewrite, external) as context:
      yield context
  finally:
    translation_routes.pop()
_frontend.protected_translation = checked_protected_translation
original_command = _frontend.command
def checked_command(*args, **kwargs):
  cmd = original_command(*args, **kwargs)
  if '-P' in cmd:
    library = cmd[cmd.index('-P') + 1]
    paths = [cmd[i + 1] for i, value in enumerate(cmd[:-1]) if value == '-i']
    frontend_paths[_frontend.flatcurryfile(args[0])] = paths, library
    views = {entry[1] for entry in _interfaceview._views.values()}
    loaded_views = [path for path in paths if path in views and path != library]
    external = translation_routes[-1]
    command_routes.append(external)
    assert all(any(p.is_file() for p in Path(path).rglob('*.curry')) == external
               for path in loaded_views)
    if loaded_views:
      assert paths[0] in loaded_views, paths
    from curry.toolchain import _findcurry
    authorized = _findcurry._loader_inputs.get() or {}
    assert all(any(os.path.realpath(p) in authorized for p in Path(path).rglob('*.curry'))
               or path in loaded_views for path in paths
               if path != library and tiered._state.tmpdir
               and path.startswith(tiered._state.tmpdir + os.sep)), paths
    assert not any(path.startswith(curry.config.installed_path('curry')) for path in paths)
    assert any(path.is_file() for path in Path(library).rglob('*.curry')) == external
    assert list(Path(library).rglob('*.fint'))
  return cmd
_frontend.command = checked_command
curry.reset(interpret='all' if %r == '--import' else
            ('off' if %r else 'new'), jit='off')
argument = %r
absolute = argument
spelling = %r
if spelling == 'relative':
  os.chdir(os.path.dirname(argument))
  argument = os.path.basename(argument)
elif spelling == 'symlink':
  link = Path(%r) / 'Numeric.icy'
  if link.is_symlink():
    link.unlink()
  link.symlink_to(argument)
  argument = str(link)
if spelling != 'absolute':
  expected_path, expected_header = image.ensure(curry._interpreter_, absolute, curry.path)
if %r:
  module = curry.import_('Numeric')
  handle = getHandle(module)
  assert handle.sofilename and not handle.sofilename.startswith(curry.config.installed_path('curry'))
  assert Path(handle.sofilename).with_suffix('.cpp').is_file()
  answer = curry.show(curry.eval(curry.parse('readNat "1"', imports=[module])).one())
  assert answer == '[(2,"")]', answer
else:
  route = %r
  if route == '--import':
    if %r:
      curry.path.insert(0, str(Path(argument).parent))
      curry.import_('Probe')
    else:
      curry.import_('System.Console.GetOpt')
  else:
    make.main('sprite-make', (['--icy', '--curry2icurry', 'icurry', argument]
        if route == '--external' else [route, argument]))
  if spelling != 'absolute':
    actual_path, actual_header = image.ensure(curry._interpreter_, argument, curry.path)
    assert actual_path == expected_path, (actual_path, expected_path)
    assert actual_header == expected_header
if %r:
  assert Path(_frontend.flatcurryfile(argument)).is_file(), 'user FlatCurry missing'
  if route == '--import':
    from curry.toolchain import _filenames
    assert Path(_filenames.icurryfilename(argument)).is_file(), 'user ICurry missing'
if %r:
  assert tiered._state.tmpdir is not None, 'no private generation'
  products = list(Path(tiered._state.tmpdir).rglob(%r))
  assert products, 'private product missing'
if %r:
  if route == '--rewrite-flat':
    assert list(Path(tiered._state.tmpdir).rglob('List.fcy')), 'private dependency missing'
  elif route == '--import':
    assert list(Path(tiered._state.tmpdir).rglob('List.icy')), 'private translation missing'
  module = curry.import_('System.Console.GetOpt')
  path = image._path(curry._interpreter_, getHandle(module).icurry.filename)
  assert not path.startswith(curry.config.installed_path('curry')), path
if missing_frontend:
  assert read_list, 'GetOpt did not read its private List interface'
assert any(command_routes) == %r, command_routes
""" % (directory, missing_frontend, route, missing_object, argument, spelling, work,
           missing_object, route, user, user, replaced,
           module.split('.')[-1] + ('.img' if route == '--image' else
               '.fcy' if route == '--rewrite-flat' else '.icy'),
           transitive, route == '--external')
            child = cytest.run_in_subprocess(code, timeout=120, address_space=3 << 30)
            self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
            self.assertEqual(snapshot(str(root)), expected_files)
            self.assertEqual({p.relative_to(root): p.read_bytes()
                              for p in root.rglob('*') if p.is_file()}, expected_bytes)
          finally:
            restore()

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
        suffixes = ['.fint', '.icurry']
        if config.curry_frontend():
          suffixes.append('.fcy')
        for suffix in suffixes:
          self.assertTrue(os.path.isfile(os.path.join(flatdir, *parts) + suffix), name)
        sidecars = os.path.join(libdir, *parts[:-1], '.curry',
                                config.intermediate_subdir(), parts[-1])
        for suffix in ['.icy', '.fint', '.icurry']:
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
