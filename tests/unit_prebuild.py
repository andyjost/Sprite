'''
Tests for the prebuilt Curry library and the bytecode cache of generated
Python modules.

make stage compiles the installed Curry library for both backends (the
prebuild step of curry/Makefile): every module Sprite can compile
(config.supported_syslibs).  The Python backend finds a generated
module and its bytecode cache; the C++ backend finds the shared object, its
ABI stamp, and the precompiled header.  So the first import after a stage
compiles nothing.  The other modules get their ICurry and JSON only.  The toolchain writes the bytecode cache when it writes a
Python file, and the loader of the Python backend reads the cache through
importlib and writes a missing or stale one, with or without -B.  A generated
Python file carries a format stamp; a cached file of another stamp, or of
none, is written again from the JSON file.  The modules of the cache and
stamp tests come from hand-written ICurry-JSON, so no Curry front end runs.
'''
import cytest # from ./lib; must be first
from cytest.logging import capture_log
from curry import config
from curry.backends.py import compiler as py_compiler
from curry.backends.py import toolchain as py_toolchain
from curry.toolchain import plans, makecurry
from curry.tools import make
from curry.utility.binding import binding
from unittest import mock
import curry, importlib.machinery, importlib.util, itertools, json, logging
import os, re, shutil, subprocess, sys, tempfile, unittest, zlib

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

  def test_python_files_are_staged(self):
    '''
    Every supported system module has its Python file and a current bytecode
    cache; every system module has its ICurry and JSON.
    '''
    for name in config.syslibs():
      self.assertTrue(os.path.isfile(installed_file(name, '.icy')), name)
      self.assertTrue(os.path.isfile(installed_file(name, '.json.z')), name)
    supported = config.supported_syslibs()
    self.assertEqual(supported[0], 'Prelude')
    self.assertFalse(set(supported) & set(config.unsupported_syslibs()))
    for name in supported:
      pyfile = installed_file(name, '.py')
      self.assertTrue(os.path.isfile(pyfile), pyfile)
      cache = py_toolchain.bytecode_file(pyfile)
      self.assertTrue(os.path.isfile(cache), cache)
      self.assertTrue(py_toolchain.bytecode_is_current(pyfile), pyfile)

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
    # The member name follows the compiler flags.  make stage does not pass
    # CXXFLAGS on, so a test run with CXXFLAGS set would look for another
    # member.
    if not os.environ.get('CXXFLAGS') and not curry.flags['debug']:
      cpp2so = cxx_toolchain.Cpp2So(curry.getInterpreter())
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
    if curry.flags['backend'] == 'cxx' and config.cxx_tool() is None:
      self.skipTest('no C++ compiler is installed')
    code = '\n'.join([
        'import curry, json, os'
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

  def test_prebuild_recipe_pins_the_installation(self):
    '''
    The prebuild recipe of the library Makefile runs sprite-make with
    SPRITE_HOME set to the installation it builds, and without the run-time
    variables of the shell.  sprite-invoke keeps an exported SPRITE_HOME, so
    a stage run with the variable set would otherwise compile the library of
    another installation.  The environment of the recipe is read through the
    print rule of the root Make.include, which needs the configured source
    tree.
    '''
    make_program = shutil.which('make')
    if make_program is None \
        or not os.path.isfile(os.path.join(SOURCE_ROOT, 'Make.config')):
      self.skipTest('no make, or the source tree is not configured')
    prefix = '/nonexistent/prefix'
    proc = subprocess.run(
        [ make_program, '-s', '-C', os.path.join(SOURCE_ROOT, 'curry')
        , 'print-PREBUILD_ENV', 'PREFIX=' + prefix
        ]
      , capture_output=True, text=True, timeout=120
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    match = re.search(
        r'PREBUILD_ENV is a \w+ variable set to \[(.*)\]', proc.stdout
      )
    self.assertIsNotNone(match, proc.stdout)
    words = match.group(1).split()
    self.assertEqual(words[0], 'env')
    self.assertIn('SPRITE_HOME=' + prefix, words)
    unset = [words[i + 1] for i, word in enumerate(words) if word == '-u']
    for name in [ 'CURRYPATH', 'CFLAGS', 'CXXFLAGS', 'SPRITE_INTERPRETER_FLAGS'
                , 'SPRITE_CXX_PCH_ROOT', 'SPRITE_FORCE_RECOMPILE_CXX'
                ]:
      self.assertIn(name, unset)

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
        curry.getInterpreter(), plans.MAKE_ALL | plans.ZIP_JSON
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
    suffix = curry.getInterpreter().backend.object_file_extension
    target = makecurry(self.plan, name, [self.srcdir])
    self.assertEqual(target, self.cached_file(name, suffix))
    return name

  def import_module(self, name):
    return curry.import_(name, currypath=[self.srcdir] + curry.path)

  def check_value(self, module, value):
    self.assertEqual(
        list(curry.eval(module.goal, converter='topython')), [value]
      )

class TestPackagedModule(JsonModuleTestCase):
  @cytest.with_flags(interpret='off')
  def test_module_in_a_package(self):
    '''
    The step that writes the target source imports the package of the module
    before the module itself.  An import by name does this through the name
    prefixes; the import of the ICurry object did not, so sprite-make --py
    Data.Maybe failed with KeyError.  The step runs with the flag
    ``interpret`` off: under its default (tiered) the C++ backend ends the
    plan at the JSON.
    '''
    plan = plans.makeplan(
        curry.getInterpreter(), plans.MAKE_ALL | plans.ZIP_JSON
      )
    package = 'PrebuildPkg%d' % next(self.counter)
    name = self.write_json(6, package=package)
    suffix = curry.getInterpreter().backend.object_file_extension
    target = makecurry(plan, name, [self.srcdir])
    self.assertEqual(target, self.cached_file(name, suffix))
    self.assertIn(package, curry.modules)
    self.assertNotIn(name, curry.modules)
    self.check_value(self.import_module(name), 6)

@unittest.skipIf(
    curry.flags['backend'] != 'py'
  , 'the bytecode cache belongs to the Python backend'
  )
class TestBytecodeCache(JsonModuleTestCase):
  def test_toolchain_writes_the_cache(self):
    '''
    The step that writes a Python file writes its bytecode cache too, whether
    or not the process runs with -B.
    '''
    with mock.patch.object(sys, 'dont_write_bytecode', True):
      name = self.build(1)
    pyfile = self.cached_file(name, '.py')
    cache = py_toolchain.bytecode_file(pyfile)
    self.assertEqual(cache, importlib.util.cache_from_source(pyfile))
    self.assertEqual(
        os.path.dirname(cache), os.path.join(self.subdir, '__pycache__')
      )
    self.assertTrue(os.path.isfile(cache))
    self.assertTrue(py_toolchain.bytecode_is_current(pyfile))
    self.check_value(self.import_module(name), 1)

  def test_loader_reads_the_cache(self):
    '''
    The loader reads a current cache instead of the source.  After the
    source changes, it compiles the source once and writes the cache again,
    although the process runs with -B.  A missing cache is written the same
    way.
    '''
    name = self.build(2)
    pyfile = self.cached_file(name, '.py')
    cache = py_toolchain.bytecode_file(pyfile)
    compiled = []
    source_to_code = importlib.machinery.SourceFileLoader.source_to_code
    def recording(loader, data, path, *args, **kwds):
      if path == pyfile:
        compiled.append(path)
      return source_to_code(loader, data, path, *args, **kwds)
    with mock.patch.object(
        importlib.machinery.SourceFileLoader, 'source_to_code', recording
      ), mock.patch.object(sys, 'dont_write_bytecode', True):
      self.check_value(curry.load(pyfile), 2)
      self.assertEqual(compiled, [])
      # The source changes, so its cache is stale.
      stamp = os.stat(pyfile).st_mtime + 5
      os.utime(pyfile, (stamp, stamp))
      self.assertFalse(py_toolchain.bytecode_is_current(pyfile))
      curry.load(pyfile)
      self.assertEqual(compiled, [pyfile])
      self.assertTrue(py_toolchain.bytecode_is_current(pyfile))
      curry.load(pyfile)
      self.assertEqual(compiled, [pyfile])
      # The cache is missing: the file came from an installation that wrote
      # none.
      os.unlink(cache)
      self.check_value(curry.load(pyfile), 2)
      self.assertEqual(compiled, [pyfile] * 2)
      self.assertTrue(py_toolchain.bytecode_is_current(pyfile))
      curry.load(pyfile)
      self.assertEqual(compiled, [pyfile] * 2)

  def test_file_without_a_cache_is_compiled_once(self):
    '''
    A generated file without a cache, such as a test module from the overlay
    archive, is compiled by the first process that loads it, which writes
    the cache under -B; the next process compiles nothing.
    '''
    name = self.build(6)
    pyfile = self.cached_file(name, '.py')
    os.unlink(py_toolchain.bytecode_file(pyfile))
    code = '\n'.join([
        'import curry, json, sys'
      , 'import importlib.machinery as machinery'
      , 'compiled = []'
      , 'source_to_code = machinery.SourceFileLoader.source_to_code'
      , 'def counting(self, data, path, *args, **kwds):'
      , '  if path == %r:' % pyfile
      , '    compiled.append(path)'
      , '  return source_to_code(self, data, path, *args, **kwds)'
      , 'machinery.SourceFileLoader.source_to_code = counting'
      , 'module = curry.import_(%r, currypath=[%r] + curry.path)'
            % (name, self.srcdir)
      , 'values = list(curry.eval(module.goal, converter="topython"))'
      , 'print(json.dumps([len(compiled), values, sys.dont_write_bytecode]))'
      ])
    for expected in [1, 0]:
      proc = cytest.run_in_subprocess(code, timeout=120)
      self.assertEqual(proc.returncode, 0, proc.stderr)
      result = json.loads(proc.stdout.strip().splitlines()[-1])
      self.assertEqual(result, [expected, [6], True])
      self.assertTrue(py_toolchain.bytecode_is_current(pyfile))

  def test_ensure_bytecode(self):
    '''
    ensure_bytecode writes a missing or stale cache and keeps a current one.
    A cache whose header does not name the file as it is now is stale.
    '''
    name = self.build(3)
    pyfile = self.cached_file(name, '.py')
    cache = py_toolchain.bytecode_file(pyfile)
    os.unlink(cache)
    self.assertFalse(py_toolchain.bytecode_is_current(pyfile))
    py_toolchain.ensure_bytecode(pyfile)
    self.assertTrue(py_toolchain.bytecode_is_current(pyfile))
    written = os.stat(cache).st_mtime_ns
    py_toolchain.ensure_bytecode(pyfile)
    self.assertEqual(os.stat(cache).st_mtime_ns, written)
    # The size field of the header is overwritten.
    with open(cache, 'r+b') as stream:
      stream.seek(12)
      stream.write(b'\0\0\0\0')
    self.assertFalse(py_toolchain.bytecode_is_current(pyfile))
    py_toolchain.ensure_bytecode(pyfile)
    self.assertTrue(py_toolchain.bytecode_is_current(pyfile))
    # A file that does not exist has no cache, and nothing is written.
    missing = self.cached_file('Nothing', '.py')
    self.assertFalse(py_toolchain.bytecode_is_current(missing))
    py_toolchain.ensure_bytecode(missing)
    self.assertFalse(os.path.exists(py_toolchain.bytecode_file(missing)))

  @unittest.skipIf(
      hasattr(os, 'geteuid') and os.geteuid() == 0
    , 'a read-only directory does not stop the superuser'
    )
  def test_unwritable_cache_is_skipped(self):
    '''
    A cache that cannot be written gives one warning; the loader compiles
    the source and the file still loads.
    '''
    name = self.build(4)
    pyfile = self.cached_file(name, '.py')
    cache = py_toolchain.bytecode_file(pyfile)
    os.unlink(cache)
    os.rmdir(os.path.dirname(cache))
    os.chmod(self.subdir, 0o500)
    try:
      with capture_log('curry.backends.py.toolchain') as log:
        self.check_value(self.import_module(name), 4)
    finally:
      os.chmod(self.subdir, 0o700)
    log.checkMessages(self, warning='cannot write the bytecode cache')
    self.assertEqual(len(log.data[logging.WARNING]), 1)
    self.assertFalse(os.path.exists(cache))

  def test_sprite_make_py_writes_a_missing_cache(self):
    '''
    sprite-make --py writes the bytecode cache of a Python file that is
    current already, as an installation from before the cache was written
    holds.  No step of the plan runs, and the file keeps its time stamp.  A
    current cache is kept.
    '''
    name = self.build(7)
    pyfile = self.cached_file(name, '.py')
    cache = py_toolchain.bytecode_file(pyfile)
    os.unlink(cache)
    stamp = os.stat(pyfile).st_mtime_ns
    def sprite_make_py():
      # sprite-make reads CURRYPATH through config.currypath, which caches.
      with binding(os.environ, 'CURRYPATH', self.srcdir):
        config.currypath(reset=True)
        with mock.patch.object(
            py_toolchain.Json2Py, '__call__'
          , side_effect=AssertionError('a step of the plan ran')
          ):
          make.main('sprite-make', ['--py', '-z', name])
      config.currypath(reset=True)
    sprite_make_py()
    self.assertEqual(os.stat(pyfile).st_mtime_ns, stamp)
    self.assertTrue(py_toolchain.bytecode_is_current(pyfile))
    written = os.stat(cache).st_mtime_ns
    sprite_make_py()
    self.assertEqual(os.stat(cache).st_mtime_ns, written)
    self.check_value(curry.load(pyfile), 7)

  def test_tidy_removes_the_cache(self):
    '''A Python file that --tidy removes takes its cache along.'''
    name = self.write_json(5)
    output = os.path.join(self.tmpdir, 'out.py')
    pyfile = self.cached_file(name, '.py')
    result = makecurry(self.plan, name, [self.srcdir], tidy=True, output=output)
    self.assertEqual(result, pyfile)
    self.assertTrue(os.path.isfile(output))
    self.assertFalse(os.path.exists(pyfile))
    self.assertFalse(os.path.exists(py_toolchain.bytecode_file(pyfile)))

@unittest.skipIf(
    curry.flags['backend'] != 'py'
  , 'the Python toolchain belongs to the Python backend'
  )
class TestFormatStamp(JsonModuleTestCase):
  '''
  The emitter stamps every generated Python file with its format.  A cached
  file of another stamp, or of none, is written again from the JSON file: the
  emitter writes other code now.  A file with the current stamp is loaded as
  it is.  The C++ backend has the same rule (unit_cxx_toolchain).
  '''
  STALE = "raise RuntimeError('this file is stale')\n"
  CURRENT = "raise RuntimeError('this file is current')\n"

  def write_py(self, name, lines):
    '''Writes a cached .py file for ``name``, newer than its JSON file.'''
    path = self.cached_file(name, '.py')
    with open(path, 'w') as stream:
      stream.write(''.join(lines))
    return path

  def stamp(self, version):
    return '# FORMAT: %d\n' % version

  def test_stamp_is_written(self):
    name = self.build(1)
    path = self.cached_file(name, '.py')
    with open(path) as stream:
      head = [next(stream) for _ in range(3)]
    # The stamp heads the file, before the first import.
    self.assertIn(self.stamp(py_compiler.FORMAT_VERSION), head)
    self.assertTrue(any(line.startswith('import') for line in head))
    self.assertEqual(
        py_toolchain.format_version(path), py_compiler.FORMAT_VERSION
      )
    self.assertFalse(py_toolchain.source_is_stale(path))
    json2py = py_toolchain.Json2Py(curry.getInterpreter())
    self.assertFalse(json2py.is_stale(path))
    self.assertFalse(json2py.is_stale(self.cached_file(name, '.json.z')))
    self.assertFalse(self.plan.is_stale(path))
    self.check_value(self.import_module(name), 1)

  def test_other_stamp_is_regenerated(self):
    '''A file of another format is written again from the JSON file.'''
    name = self.write_json(2)
    path = self.write_py(
        name, [self.stamp(py_compiler.FORMAT_VERSION + 1), self.STALE]
      )
    self.assertTrue(py_toolchain.source_is_stale(path))
    self.assertTrue(self.plan.is_stale(path))
    self.check_value(self.import_module(name), 2)
    text = cytest.readfile(path)
    self.assertIn(self.stamp(py_compiler.FORMAT_VERSION), text)
    self.assertNotIn('this file is stale', text)
    self.assertTrue(py_toolchain.bytecode_is_current(path))

  def test_missing_stamp_is_regenerated(self):
    '''A file from before the stamp has format 1, and is written again.'''
    name = self.write_json(3)
    path = self.write_py(name, [self.STALE])
    self.assertEqual(py_toolchain.format_version(path), 1)
    self.assertTrue(self.plan.is_stale(path))
    self.check_value(self.import_module(name), 3)
    self.assertNotIn('this file is stale', cytest.readfile(path))

  def test_current_stamp_is_loaded(self):
    '''A file with the current stamp is the prerequisite, as before.'''
    name = self.write_json(4)
    self.write_py(name, [self.stamp(py_compiler.FORMAT_VERSION), self.CURRENT])
    with self.assertRaisesRegex(RuntimeError, 'this file is current'):
      self.import_module(name)
