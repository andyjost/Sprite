'''Tests for the prebuilt Curry library and its compiled objects.'''
import cytest # from ./lib; must be first
from cytest.logging import capture_log
from curry import config
from curry.toolchain import plans, makecurry
from curry.tools import make
from curry.utility.binding import binding
from unittest import mock
import curry, importlib.machinery, importlib.util, itertools, json, logging
import os, re, runpy, shutil, subprocess, sys, tempfile, unittest, zlib
from pathlib import Path

SUBDIR = os.path.join('.curry', config.intermediate_subdir())

# The source tree, which holds the Makefile of the Curry library.
SOURCE_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
  )

def installed_file(name, suffix):
  '''The file of system module ``name`` with ``suffix`` in the installation.'''
  parts = name.split('.')
  return os.path.join(
      config.system_curry_path(), *parts[:-1], SUBDIR, parts[-1] + suffix
    )

class TestStagedLibrary(cytest.TestCase):
  '''The products that make stage leaves in the installation.'''

  def test_intermediates_are_staged(self):
    '''
    Every system module has its ICurry and JSON.  The library has no
    generated Python products.
    '''
    for name in config.syslibs():
      self.assertTrue(os.path.isfile(installed_file(name, '.icy')), name)
      self.assertTrue(os.path.isfile(installed_file(name, '.json.z')), name)
    supported = config.supported_syslibs()
    self.assertEqual(supported[0], 'Prelude')
    self.assertFalse(set(supported) & set(config.unsupported_syslibs()))
    for name in supported:
      self.assertFalse(os.path.exists(installed_file(name, '.py')), name)

  @unittest.skipIf(config.cxx_tool() is None, 'no C++ compiler is installed')
  def test_cxx_objects_are_staged(self):
    '''
    Every system module has its object with the current ABI stamp, and the
    precompiled header of the default flavor exists.
    '''
    from curry.backends.cxx import toolchain as cxx_toolchain
    # The stamp is the digest of the headers and of the installed flavor.
    digest = cxx_toolchain.object_digest()
    for name in config.supported_syslibs():
      sofile = installed_file(name, '.so')
      self.assertTrue(os.path.isfile(sofile), sofile)
      self.assertTrue(os.path.isfile(installed_file(name, '.cpp')), name)
      self.assertEqual(cxx_toolchain.Cpp2So.read_stamp(sofile), digest, sofile)
      self.assertTrue(cxx_toolchain.Cpp2So(cytest.raw.interp()).stamp_is_current(sofile), sofile)
    # The member name follows the compiler flags.  make stage does not pass
    # CXXFLAGS on, so a test run with CXXFLAGS set would look for another
    # member.
    # No header where the platform compiles without one (config.cxx_pch_root).
    if config.cxx_pch_root() is not None and not os.environ.get('CXXFLAGS') \
        and not curry.flags['debug']:
      cpp2so = cxx_toolchain.Cpp2So(cytest.raw.interp())
      pch = cxx_toolchain.PrecompiledHeader(
          config.installed_path('include'), config.cxx_tool()
        , cpp2so._cxxflags()
        )
      self.assertTrue(os.path.isfile(pch.filename), pch.filename)
      self.assertTrue(pch.is_current())

  def test_first_import_compiles_nothing(self):
    '''
    A new process imports every supported system module on the current
    backend without a compiler command and without compiling a generated
    Python file.
    '''
    if config.cxx_tool() is None:
      self.skipTest('no C++ compiler is installed')
    code = '\n'.join([
        'import cytest, curry, json, os'
      , 'from curry import config'
      , 'from curry.toolchain import _system'
      , 'import importlib.machinery as machinery'
      , 'commands, compiled = [], []'
      , 'pexec = _system.pexec'
      , 'def counting_pexec(cmd, *args, **kwds):'
      , '  commands.append(cmd)'
      , '  return pexec(cmd, *args, **kwds)'
      , '_system.pexec = counting_pexec'
      , 'source_to_code = machinery.SourceFileLoader.source_to_code'
      , 'def counting_source_to_code(self, data, path, *args, **kwds):'
      , '  if os.sep + ".curry" + os.sep in path:'
      , '    compiled.append(path)'
      , '  return source_to_code(self, data, path, *args, **kwds)'
      , 'machinery.SourceFileLoader.source_to_code = counting_source_to_code'
      , 'for name in config.supported_syslibs():'
      , '  curry.import_(name)'
      , 'print(json.dumps([commands, compiled, sorted(curry.modules)]))'
      ])
    proc = cytest.run_in_subprocess(code, timeout=300)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    commands, compiled, modules = json.loads(
        proc.stdout.strip().splitlines()[-1]
      )
    self.assertEqual(commands, [])
    self.assertEqual(compiled, [])
    for name in config.supported_syslibs():
      self.assertIn(name, modules)

  def test_prebuild_uses_its_own_environment(self):
    """
    The Python prebuild step clears ambient runtime settings.  Its PYTHONPATH
    names the package of the stage first and keeps the caller's path after
    it: in the isolated build of pip (the sdist) that path names the site of
    the build environment, where the console script of the front end, a
    build requirement, finds its module.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location('build_package',
        os.path.join(SOURCE_ROOT, 'scripts', 'build-package.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ambient = {
        'SPRITE_HOME': '/other', 'CURRYPATH': '/other',
        'SPRITE_INTERPRETER_FLAGS': 'backend:cxx,interpret:all', 'CXXFLAGS': '-bad',
        'SPRITE_PRODUCT_CACHE': '/products'}
    for pythonpath, expected in [
        (None, '/stage/python'), ('', '/stage/python'),
        ('/build-env/site', '/stage/python' + os.pathsep + '/build-env/site')]:
      with self.subTest(pythonpath=pythonpath):
        with mock.patch.dict(os.environ, ambient):
          if pythonpath is None:
            os.environ.pop('PYTHONPATH', None)
          else:
            os.environ['PYTHONPATH'] = pythonpath
          env = module.build_environment('/stage')
        self.assertEqual(env['SPRITE_HOME'], '/stage')
        self.assertEqual(env['PYTHONPATH'], expected)
        self.assertEqual(env['SPRITE_PRODUCT_CACHE'], '/products')
        for name in ['CURRYPATH', 'CXXFLAGS', 'SPRITE_INTERPRETER_FLAGS']:
          self.assertNotIn(name, env)

  @unittest.skipIf(config.cxx_tool() is None, 'no C++ compiler is installed')
  def test_stage_rebuilds_dependents_of_changed_interface(self):
    '''The actual prebuild step keeps B's source but replaces its old object.'''
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      source, prefix = root / 'source', root / 'prefix'
      shutil.copytree(config.prefix(), prefix, symlinks=True)
      (source / 'src').mkdir(parents=True)
      for name in ('python', 'curryrt', 'export'):
        (source / 'src' / name).symlink_to(Path(SOURCE_ROOT) / 'src' / name,
            target_is_directory=True)
      lib = source / 'curry/lib'
      lib.mkdir(parents=True)
      for name in ('Prelude.curry', 'Prelude.icy', 'LICENSE', 'NOTICE'):
        shutil.copy2(Path(SOURCE_ROOT) / 'curry/lib' / name, lib / name)
      (lib / 'A.curry').write_text(
          'module A where\nf :: Int\nf = 1\noldExport :: Int\noldExport = 0\n')
      (lib / 'B.curry').write_text('module B where\nimport A\nmain :: Int\nmain = f\n')
      (prefix / 'sysconfig/currylib_module_names').write_text('Prelude A B\n')
      (prefix / 'sysconfig/currylib_unsupported_modules').write_text('')
      command = ['timeout', '180', sys.executable,
          str(Path(SOURCE_ROOT) / 'scripts/build-package.py'),
          '--source', str(source), '--prefix', str(prefix), '--jobs', '1',
          '--frontend', config.curry_frontend(), '--cxx', config.cxx_tool()]
      def stage():
        result = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      stage()
      products = [prefix / 'curry' / SUBDIR / ('B' + suffix)
          for suffix in ('.icy', '.cpp', '.so', '.so.abi')]
      self.assertTrue(all(p.is_file() for p in products))
      # Establish an unchanged pinned B, as in an incremental library stage.
      shutil.copy2(products[0], lib / 'B.icy')
      stage()
      before = [p.stat().st_mtime_ns for p in products]
      text = (lib / 'B.curry').read_bytes()
      (lib / 'A.curry').write_text(
          'module A where\nadded :: Int\nadded = 0\nf :: Int\nf = 2\n')
      stage()
      self.assertEqual((lib / 'B.curry').read_bytes(), text)
      self.assertTrue(all(p.stat().st_mtime_ns != old
          for p, old in zip(products, before)))
      # An unchanged pinned input must not overwrite B's valid retranslation.
      current = [p.stat().st_mtime_ns for p in products]
      stage()
      self.assertEqual([p.stat().st_mtime_ns for p in products], current)


class JsonModuleTestCase(cytest.TestCase):
  '''A temporary source directory of hand-written ICurry-JSON modules.'''
  # The C++ runtime keeps one entry per module name, so every module built in
  # this process gets a new name.
  counter = itertools.count()

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-prebuild-')
    self.srcdir = os.path.join(self.tmpdir, 'src')
    self.subdir = os.path.join(self.srcdir, SUBDIR)
    os.makedirs(self.subdir)
    self.plan = plans.makeplan(
        cytest.raw.interp(), plans.MAKE_ALL | plans.ZIP_JSON
      )

  def tearDown(self):
    super().tearDown()
    os.chmod(self.subdir, 0o700)
    shutil.rmtree(self.tmpdir, ignore_errors=True)

  def write_json(self, value, package=None):
    '''
    Writes the JSON of a module whose goal returns ``value``, inside
    ``package`` if one is named.  Returns the full name of the module.
    '''
    name = 'PrebuildTest%d' % next(self.counter)
    if package is not None:
      name = package + '.' + name
    path = self.cached_file(name, '.json.z')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = cytest.json_module(name, value)
    with open(path, 'wb') as stream:
      stream.write(zlib.compress(text.encode('utf-8')))
    return name

  def cached_file(self, name, suffix):
    '''The file of the module ``name`` with the given suffix in the cache.'''
    parts = name.split('.')
    return os.path.join(self.srcdir, *parts[:-1], SUBDIR, parts[-1] + suffix)

  def build(self, value):
    '''
    Builds the target file of a module whose goal returns ``value`` without
    loading the module.  Returns the module name.
    '''
    name = self.write_json(value)
    suffix = cytest.raw.interp().backend.object_file_extension
    target = makecurry(self.plan, name, [self.srcdir])
    self.assertEqual(target, self.cached_file(name, suffix))
    return name

  def import_module(self, name):
    return curry.import_(name, path=[self.srcdir] + curry.path)

  def check_value(self, module, value):
    self.assertEqual(
        list(curry.eval(module.goal)), [value]
      )

class TestPackagedModule(JsonModuleTestCase):
  @cytest.with_flags(interpret='off')
  def test_packaged_products_ignore_extraction_order(self):
    """pip's extraction times do not force an unchanged library to compile."""
    from curry.toolchain import _curry2icurry, _findcurry, _interfaces
    # The plan is made here, under the flag the test sets: the plan of setUp
    # ends at the JSON under interpret:all (toolchain.extend_plan_skeleton).
    self.plan = plans.makeplan(
        cytest.raw.interp(), plans.MAKE_ALL | plans.ZIP_JSON
      )
    name = self.build(6)
    target = self.cached_file(name, cytest.raw.interp().backend.object_file_extension)
    source = os.path.join(self.srcdir, name + '.curry')
    with open(source, 'w') as stream:
      stream.write('main :: Int\nmain = 6\n')
    icy = self.cached_file(name, '.icy')
    for suffix in ['.icy', '.fint', '.icurry']:
      with open(self.cached_file(name, suffix), 'w') as stream:
        stream.write('')
    with open(icy, 'w') as stream:
      stream.write('(IProg "%s" [] [] [])' % name)
    _interfaces.write(icy, [self.srcdir])
    with open(icy + '.source', 'w') as stream:
      stream.write(_curry2icurry.source_digest(source))
    future = os.stat(target).st_mtime + 120
    os.utime(source, (future, future))
    def current():
      return _findcurry.currentfile(self.plan, source, [self.srcdir], is_sourcefile=True)
    with mock.patch.object(config, 'system_curry_path', return_value=self.srcdir):
      self.assertEqual(current(), target)
      with open(source, 'a') as stream:
        stream.write('-- changed\n')
      # The edited source is the newest file by its time, strictly: the
      # kernel stamps files with a coarse clock, so an edit a moment after
      # the products were written can share their time, and a tie goes to
      # the product (filesys.newest).
      os.utime(source, (future + 1, future + 1))
      self.assertEqual(current(), source)

  @cytest.with_flags(interpret='off')
  def test_module_in_a_package(self):
    '''
    The step that writes the target source imports the package of the module
    before the module itself.  An import by name does this through the name
    prefixes; the import of the ICurry object did not, so sprite-make --so
    Data.Maybe failed with KeyError.  The step runs with the flag
    ``interpret`` off: under its default (tiered) the C++ backend ends the
    plan at the JSON.
    '''
    plan = plans.makeplan(
        cytest.raw.interp(), plans.MAKE_ALL | plans.ZIP_JSON
      )
    package = 'PrebuildPkg%d' % next(self.counter)
    name = self.write_json(6, package=package)
    suffix = cytest.raw.interp().backend.object_file_extension
    target = makecurry(plan, name, [self.srcdir])
    self.assertEqual(target, self.cached_file(name, suffix))
    self.assertNotIn(package, curry.modules)
    self.assertNotIn(name, curry.modules)
    self.check_value(self.import_module(name), 6)
