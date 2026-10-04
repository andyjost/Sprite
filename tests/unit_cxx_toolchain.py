'''
Tests for the build steps of the C++ backend.

The compile of a generated module spends most of its time on the runtime
header, so the toolchain precompiles that header once (see
curry.backends.cxx.toolchain.PrecompiledHeader).  These tests put the header
under a temporary root through SPRITE_CXX_PCH_ROOT, so they touch nothing in
the installation.  The modules come from hand-written ICurry-JSON, so no
Curry front end runs.

The generated C++ carries a format stamp.  A cached file with another stamp,
or none, is written again from the JSON file instead of being compiled
against a runtime it was not written for.

Each compiled object carries an ABI stamp beside it: the digest of the
installed runtime headers it was compiled against and of the flags of its
flavor.  An object whose stamp differs is compiled again; the age of the
runtime library does not count.

Generated code comes in two flavors.  The release flavor has no assertions,
no stack protector, and no procedure linkage table.  The debug flavor keeps
the assertions.  A module follows the flavor of the installed runtime unless
the interpreter flag ``debug`` is set.
'''
import cytest # from ./lib; must be first
from cytest.logging import capture_log
from curry import config, exceptions
from curry.backends.cxx import compiler, toolchain
from curry.toolchain import plans, _findcurry, makecurry
from curry.utility.binding import binding, del_
from unittest import mock
import curry, itertools, json, logging, os, shutil, subprocess, tempfile, time
import types, unittest, zlib

# A module with one goal that returns an integer.
MODULE_JSON = (
    '{"__class__":"IProg","name":"%(name)s","imports":["Prelude"],"types":[]'
    ',"functions":[{"__class__":"IFunction","name":"%(name)s.goal","arity":0'
    ',"vis":{"__class__":"Public"},"needed":[],"body":{"__class__":"IFuncBody"'
    ',"block":{"__class__":"IBlock","vardecls":[],"assigns":[],"stmt":'
    '{"__class__":"IReturn","expr":{"__class__":"ILit","lit":{"__class__":'
    '"IInt","value":%(value)d}}}}}}],"aliases":[]}'
  )

class ToolchainTestCase(cytest.TestCase):
  '''A temporary source directory of hand-written ICurry-JSON modules.'''
  # The C++ runtime keeps one entry per module name, so every module compiled
  # in this process gets a new name.
  counter = itertools.count()

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-toolchain-')
    self.srcdir = os.path.join(self.tmpdir, 'src')
    self.subdir = os.path.join(
        self.srcdir, '.curry', config.intermediate_subdir()
      )
    os.makedirs(self.subdir)

  def tearDown(self):
    super().tearDown()
    shutil.rmtree(self.tmpdir, ignore_errors=True)

  def write_json(self, value):
    '''Writes the JSON of a module whose goal returns ``value``.  Returns its name.'''
    name = 'ToolchainTest%d' % next(self.counter)
    text = MODULE_JSON % {'name': name, 'value': value}
    with open(self.cached_file(name, '.json.z'), 'wb') as stream:
      stream.write(zlib.compress(text.encode('utf-8')))
    return name

  def cached_file(self, name, suffix):
    '''The file of the module ``name`` with the given suffix in the cache.'''
    return os.path.join(self.subdir, name + suffix)

  def import_module(self, name):
    return curry.import_(name, currypath=[self.srcdir] + curry.path)

  def check_value(self, module, value):
    self.assertEqual(
        list(curry.eval(module.goal, converter='topython')), [value]
      )

  def compile_module(self, value):
    '''Compiles a module whose goal returns ``value`` and checks the value.'''
    module = self.import_module(self.write_json(value))
    self.check_value(module, value)
    return module

@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'the toolchain belongs to the C++ backend'
  )
class TestPrecompiledHeader(ToolchainTestCase):
  def setUp(self):
    super().setUp()
    self.root = os.path.join(self.tmpdir, 'pch')
    os.mkdir(self.root)
    self.env = binding(os.environ, 'SPRITE_CXX_PCH_ROOT', self.root)
    self.env.__enter__()

  def tearDown(self):
    self.env.__exit__(None, None, None)
    os.chmod(self.root, 0o700)
    super().tearDown()

  @property
  def gch_dir(self):
    return os.path.join(self.root, 'cyrt', 'cyrt.hpp.gch')

  def members(self):
    '''The names of the precompiled headers under the temporary root.'''
    if os.path.isdir(self.gch_dir):
      return sorted(os.listdir(self.gch_dir))
    return []

  def compile_command(self, module):
    '''The g++ command for ``module``, as the toolchain would run it.'''
    cpp = self.cached_file(module.__name__, '.cpp')
    self.assertTrue(os.path.exists(cpp))
    out = os.path.join(self.tmpdir, 'probe.so')
    cpp2so = toolchain.Cpp2So(curry.getInterpreter())
    return list(cpp2so._compileCommand(cpp, out))

  def test_builds_once_and_reuses(self):
    '''The first compile builds the header.  Later compiles reuse it.'''
    self.compile_module(1)
    members = self.members()
    self.assertEqual(len(members), 1)
    self.assertTrue(members[0].startswith('O3-'), members[0])
    self.assertTrue(members[0].endswith('.gch'), members[0])
    path = os.path.join(self.gch_dir, members[0])
    self.assertGreater(os.path.getsize(path), 1 << 20)
    stamp = os.path.getmtime(path)
    self.compile_module(2)
    self.assertEqual(self.members(), members)
    self.assertEqual(os.path.getmtime(path), stamp)
    # No temporary file remains beside the directory.
    self.assertEqual(os.listdir(os.path.join(self.root, 'cyrt')), ['cyrt.hpp.gch'])

  def test_compiler_uses_the_header(self):
    '''g++ finds the header through the include flag for the root.'''
    module = self.compile_module(3)
    cmd = self.compile_command(module)
    root_flag = '-I' + self.root
    # The include flag of the installation is spelled by its real path, so
    # that the flavor of the header does not follow the spelling of
    # SPRITE_HOME.
    install_flag = '-I' + os.path.realpath(config.installed_path('include'))
    self.assertIn(root_flag, cmd)
    self.assertLess(cmd.index(root_flag), cmd.index(install_flag))
    # With -H, g++ marks a precompiled header it loads with a '!'.
    proc = subprocess.run(
        cmd[:1] + ['-H'] + cmd[1:], capture_output=True, text=True
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    member, = self.members()
    self.assertIn('! ' + os.path.join(self.gch_dir, member), proc.stderr.splitlines())

  def test_stale_member_is_rebuilt(self):
    '''
    A member older than a header is built again.  The age of libcyrt.so does
    not count: a relink of the library keeps the member.
    '''
    self.compile_module(4)
    member, = self.members()
    path = os.path.join(self.gch_dir, member)
    pch = toolchain.PrecompiledHeader(
        self.root, config.cxx_tool()
      , toolchain.Cpp2So(curry.getInterpreter())._cxxflags()
      )
    self.assertEqual(pch.filename, path)
    headers = list(pch.header_files())
    self.assertTrue(headers)
    newest_header = max(os.path.getmtime(f) for f in headers)
    # Older than the library, but not older than any header: current.
    before_library = os.path.getmtime(config.cyrt_lib()) - 1
    if before_library >= newest_header:
      os.utime(path, (before_library, before_library))
      self.assertTrue(pch.is_current())
    # Older than a header: stale.
    old = newest_header - 100
    os.utime(path, (old, old))
    self.assertFalse(pch.is_current())
    self.compile_module(5)
    self.assertEqual(self.members(), [member])
    self.assertGreater(os.path.getmtime(path), old)
    self.assertTrue(pch.is_current())

  def test_disabled(self):
    '''An empty SPRITE_CXX_PCH_ROOT compiles without the header.'''
    with binding(os.environ, 'SPRITE_CXX_PCH_ROOT', ''):
      self.assertIsNone(config.cxx_pch_root())
      module = self.compile_module(6)
      cmd = self.compile_command(module)
    self.assertEqual(self.members(), [])
    self.assertNotIn('-I' + self.root, cmd)
    # The default root is the installed include directory.  The toolchain
    # adds no second include flag for it.
    with binding(os.environ, 'SPRITE_CXX_PCH_ROOT', del_):
      self.assertEqual(config.cxx_pch_root(), config.installed_path('include'))

  @unittest.skipIf(
      hasattr(os, 'geteuid') and os.geteuid() == 0
    , 'a read-only directory does not stop the superuser'
    )
  def test_unwritable_root(self):
    '''A root that cannot be written gives one warning, and compiles work.'''
    os.chmod(self.root, 0o500)
    with capture_log('curry.backends.cxx.toolchain') as log:
      self.compile_module(7)
      self.compile_module(8)
    log.checkMessages(self, warning='cannot build the precompiled header')
    self.assertEqual(len(log.data[logging.WARNING]), 1)
    self.assertEqual(self.members(), [])

  def test_header_build_failure(self):
    '''
    A failed build of the header gives one warning and leaves no partial
    file, and the modules compile without the header.  The compiler is
    made to fail on the header and to leave its output behind, as g++ may.
    '''
    real_pexec = toolchain._system.pexec
    header_builds = []
    def pexec(cmd, *args, **kwds):
      if 'c++-header' in cmd:
        header_builds.append(cmd)
        open(cmd[cmd.index('-o') + 1], 'w').close()
        raise exceptions.CompileError('the header build failed')
      return real_pexec(cmd, *args, **kwds)
    with mock.patch.object(toolchain._system, 'pexec', pexec):
      with capture_log('curry.backends.cxx.toolchain') as log:
        self.compile_module(10)
        self.compile_module(11)
    self.assertEqual(len(header_builds), 1)
    log.checkMessages(self, warning='cannot build the precompiled header')
    self.assertEqual(len(log.data[logging.WARNING]), 1)
    self.assertIn('the header build failed', log.data[logging.WARNING][0])
    self.assertEqual(self.members(), [])
    self.assertEqual(os.listdir(os.path.join(self.root, 'cyrt')), ['cyrt.hpp.gch'])

  @cytest.with_flags(backend='cxx', debug=True)
  def test_debug_flavor(self):
    '''The debug build gets a member of its own.'''
    module = self.compile_module(9)
    member, = self.members()
    self.assertTrue(member.startswith('O0g-'), member)
    cmd = self.compile_command(module)
    self.assertIn('-O0', cmd)
    self.assertIn('-g', cmd)
    self.assertNotIn('-O3', cmd)

  def test_flavor_names(self):
    '''The member name follows the flags.  Equal flags share a member.'''
    cxx = config.cxx_tool()
    a = toolchain.PrecompiledHeader(self.root, cxx, ['-O3', '-std=c++17'])
    b = toolchain.PrecompiledHeader(self.root, cxx, ['-O0', '-g'])
    c = toolchain.PrecompiledHeader(self.root, cxx, iter(['-O3', '-std=c++17']))
    self.assertEqual(a.directory, self.gch_dir)
    self.assertEqual(a.filename, c.filename)
    self.assertNotEqual(a.filename, b.filename)
    self.assertTrue(a.flavor.startswith('O3-'))
    self.assertTrue(b.flavor.startswith('O0g-'))
    self.assertFalse(a.is_current())
    headers = list(a.header_files())
    self.assertIn(config.installed_path('include', 'cyrt', 'cyrt.hpp'), headers)

@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'the toolchain belongs to the C++ backend'
  )
class TestFormatStamp(ToolchainTestCase):
  '''
  The emitter stamps every generated file with its format.  A cached file
  with another stamp, or none, is not compiled; the plan starts again from
  the JSON file.  An audit finding: a cache written before the layout of the
  static data changed was compiled against the new runtime, which then read
  the data of a literal case out of bounds.
  '''
  STALE = '#error this file is stale\n'
  IMPORTS = '// IMPORTS: Prelude\n'

  def write_cpp(self, name, lines):
    '''Writes a cached .cpp file for ``name``, newer than its JSON file.'''
    path = self.cached_file(name, '.cpp')
    with open(path, 'w') as stream:
      stream.write(''.join(lines))
    return path

  def stamp(self, version):
    return '// FORMAT: %d\n' % version

  def test_stamp_is_written(self):
    module = self.compile_module(1)
    path = self.cached_file(module.__name__, '.cpp')
    with open(path) as stream:
      head = [next(stream) for _ in range(4)]
    # The stamp follows the import list, before the first include.
    i = head.index(self.IMPORTS)
    self.assertEqual(head[i + 1], self.stamp(compiler.FORMAT_VERSION))
    self.assertTrue(any(line.startswith('#include') for line in head[i + 2:]))
    cpp2so = toolchain.Cpp2So(curry.getInterpreter())
    self.assertEqual(cpp2so.format_version(path), compiler.FORMAT_VERSION)
    self.assertFalse(cpp2so.is_stale(path))

  def test_other_stamp_is_regenerated(self):
    '''A file of another format is written again from the JSON file.'''
    name = self.write_json(2)
    path = self.write_cpp(
        name, [self.IMPORTS, self.stamp(compiler.FORMAT_VERSION + 1), self.STALE]
      )
    cpp2so = toolchain.Cpp2So(curry.getInterpreter())
    self.assertTrue(cpp2so.is_stale(path))
    self.check_value(self.import_module(name), 2)
    text = cytest.readfile(path)
    self.assertIn(self.stamp(compiler.FORMAT_VERSION), text)
    self.assertNotIn('#error', text)

  def test_missing_stamp_is_regenerated(self):
    '''A file from before the stamp has format 1, and is written again.'''
    name = self.write_json(3)
    path = self.write_cpp(name, [self.IMPORTS, self.STALE])
    cpp2so = toolchain.Cpp2So(curry.getInterpreter())
    self.assertEqual(cpp2so.format_version(path), 1)
    self.assertTrue(cpp2so.is_stale(path))
    self.check_value(self.import_module(name), 3)
    self.assertNotIn('#error', cytest.readfile(path))

  def test_current_stamp_is_compiled(self):
    '''A file with the current stamp is the prerequisite, as before.'''
    name = self.write_json(4)
    self.write_cpp(
        name, [self.IMPORTS, self.stamp(compiler.FORMAT_VERSION), self.STALE]
      )
    with self.assertRaises(exceptions.CompileError) as cm:
      self.import_module(name)
    self.assertIn('this file is stale', str(cm.exception))

  def test_object_of_a_stale_file_is_dropped(self):
    '''
    The object built from a stale file goes with it, even when it is newer
    than the runtime library.  The plan then starts from the JSON file.
    '''
    module = self.compile_module(5)
    name = module.__name__
    plan = plans.makeplan(curry.getInterpreter(), plans.MAKE_ALL | plans.ZIP_JSON)
    prereq = _findcurry.currentfile(plan, name, [self.srcdir])
    self.assertEqual(prereq, self.cached_file(name, '.so'))
    self.write_cpp(name, [self.IMPORTS, self.stamp(1), self.STALE])
    prereq = _findcurry.currentfile(plan, name, [self.srcdir])
    self.assertEqual(prereq, self.cached_file(name, '.json.z'))

  def test_source_only_plan_refuses_a_stale_file(self):
    '''
    Under the plan of sprite-make --cxx, which ends at the .cpp file, the
    step that writes the file answers for it: a file of another format is
    written again, although no compile step is in the plan.  A current file
    is kept.
    '''
    name = self.write_json(8)
    path = self.write_cpp(name, [self.IMPORTS, self.stamp(1), self.STALE])
    plan = plans.makeplan(
        curry.getInterpreter()
      , plans.MAKE_ICURRY | plans.MAKE_JSON | plans.MAKE_TARGET_SOURCE
            | plans.ZIP_JSON
      )
    self.assertEqual(plan.suffixes[-1], '.cpp')
    self.assertTrue(plan.is_stale(path))
    self.assertFalse(plan.is_stale(self.cached_file(name, '.json.z')))
    self.assertEqual(
        _findcurry.currentfile(plan, name, [self.srcdir])
      , self.cached_file(name, '.json.z')
      )
    self.assertEqual(makecurry(plan, name, [self.srcdir]), path)
    self.assertFalse(plan.is_stale(path))
    text = cytest.readfile(path)
    self.assertIn(self.stamp(compiler.FORMAT_VERSION), text)
    self.assertNotIn('#error', text)
    written = os.stat(path).st_mtime_ns
    self.assertEqual(makecurry(plan, name, [self.srcdir]), path)
    self.assertEqual(os.stat(path).st_mtime_ns, written)
    self.assertFalse(os.path.exists(self.cached_file(name, '.so')))

  def test_unreadable_stamp_is_an_error(self):
    '''
    The stamp the emitter writes must read back.  Otherwise the plan would
    refuse every cached .cpp file, and every process would write and compile
    every module again.  The compile step checks its input and stops with an
    error instead.  Here the reader (toolchain.format_version, which both
    steps use) is made to misread every stamp.
    '''
    name = self.write_json(6)
    with mock.patch.object(
        toolchain, 'format_version'
      , lambda filename: compiler.FORMAT_VERSION + 1
      ):
      with self.assertRaises(exceptions.CompileError) as cm:
        self.import_module(name)
    self.assertIn('format stamp', str(cm.exception))
    # The emitter did write the stamp; no object was compiled.
    text = cytest.readfile(self.cached_file(name, '.cpp'))
    self.assertIn(self.stamp(compiler.FORMAT_VERSION), text)
    self.assertFalse(os.path.exists(self.cached_file(name, '.so')))

  def test_stamp_reads_back(self):
    '''
    The reader finds the stamp of a generated file, which begins with a
    section comment and the import list, and of a file without section
    comments.
    '''
    module = self.compile_module(7)
    cpp2so = toolchain.Cpp2So(curry.getInterpreter())
    path = self.cached_file(module.__name__, '.cpp')
    with open(path) as stream:
      head = [next(stream) for _ in range(3)]
    self.assertTrue(head[0].startswith('/* SECTION: '), head[0])
    self.assertEqual(head[2], self.stamp(compiler.FORMAT_VERSION))
    self.assertFalse(cpp2so.is_stale(path))
    bare = self.write_cpp(
        'Bare', [self.IMPORTS, self.stamp(compiler.FORMAT_VERSION)]
      )
    self.assertFalse(cpp2so.is_stale(bare))
    # The stamp of a cached file is read once per import, not per line of
    # the file: a long file costs nothing more.
    long = self.write_cpp(
        'Long', [self.IMPORTS, self.stamp(compiler.FORMAT_VERSION)]
                + ['// filler\n'] * 10000
      )
    self.assertFalse(cpp2so.is_stale(long))

@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'the toolchain belongs to the C++ backend'
  )
class TestAbiStamp(ToolchainTestCase):
  '''
  Each shared object gets an ABI stamp: the digest of the installed runtime
  headers it was compiled against and of the flags of its flavor.  An object
  whose stamp is missing or differs from the digest of the installation is
  compiled again (TestFlavor covers the flavors).  An object with the
  same stamp is kept, whatever the time stamps of the runtime library and the
  object say.  Before this, an object older than libcyrt.so was compiled
  again, so every make stage that relinked the library invalidated every
  object, and the first import after it compiled the Prelude again.
  '''
  def setUp(self):
    super().setUp()
    self.plan = plans.makeplan(
        curry.getInterpreter(), plans.MAKE_ALL | plans.ZIP_JSON
      )
    self.cpp2so = toolchain.Cpp2So(curry.getInterpreter())

  def prerequisite(self, name):
    return _findcurry.currentfile(self.plan, name, [self.srcdir])

  def build(self, value):
    '''
    Builds the object of a module whose goal returns ``value`` without
    loading it, so that the object can be compiled again in this process.
    Returns the module name.
    '''
    name = self.write_json(value)
    sofile = makecurry(self.plan, name, [self.srcdir])
    self.assertEqual(sofile, self.cached_file(name, '.so'))
    return name

  def test_stamp_is_written(self):
    '''The compile step writes the stamp beside the object.'''
    module = self.compile_module(1)
    sofile = self.cached_file(module.__name__, '.so')
    stamp = self.cpp2so.stampfile(sofile)
    self.assertEqual(stamp, sofile + '.abi')
    digest = self.cpp2so.digest()
    self.assertEqual(digest, toolchain.object_digest(config.cxx_flavor()))
    self.assertNotEqual(digest, toolchain.runtime_digest())
    self.assertEqual(cytest.readfile(stamp), digest + '\n')
    self.assertEqual(self.cpp2so.read_stamp(sofile), digest)
    self.assertFalse(self.cpp2so.is_stale(sofile))
    self.assertFalse(self.plan.is_stale(sofile))
    self.assertEqual(self.prerequisite(module.__name__), sofile)
    # No temporary file remains.
    names = sorted(os.listdir(self.subdir))
    self.assertEqual(
        names, sorted(
            module.__name__ + suffix
            for suffix in ['.json.z', '.cpp', '.so', '.so.abi']
          )
      )

  def test_object_older_than_the_library_is_kept(self):
    '''The age of the object against libcyrt.so does not matter.'''
    name = self.build(2)
    sofile = self.cached_file(name, '.so')
    old = os.path.getmtime(config.cyrt_lib()) - 100
    for path in sofile, self.cpp2so.stampfile(sofile):
      os.utime(path, (old, old))
    self.assertLess(
        os.path.getmtime(sofile), os.path.getmtime(config.cyrt_lib())
      )
    self.assertFalse(self.cpp2so.is_stale(sofile))
    self.assertEqual(self.prerequisite(name), sofile)
    self.check_value(self.import_module(name), 2)

  def test_other_stamp_is_recompiled(self):
    '''
    An object compiled against other headers goes.  The .cpp file stays and
    is compiled again, and the new object gets the current stamp.
    '''
    name = self.build(3)
    sofile = self.cached_file(name, '.so')
    cppfile = self.cached_file(name, '.cpp')
    with open(self.cpp2so.stampfile(sofile), 'w') as stream:
      stream.write('0123456789abcdef\n')
    self.assertTrue(self.cpp2so.is_stale(sofile))
    self.assertEqual(self.prerequisite(name), cppfile)
    before = os.stat(cppfile).st_mtime_ns, os.stat(sofile).st_mtime_ns
    with capture_log('curry.backends.cxx.toolchain') as log:
      self.assertEqual(makecurry(self.plan, name, [self.srcdir]), sofile)
    log.checkMessages(self, info='Compiling %r' % sofile)
    self.assertEqual(os.stat(cppfile).st_mtime_ns, before[0])
    self.assertNotEqual(os.stat(sofile).st_mtime_ns, before[1])
    self.assertEqual(self.cpp2so.read_stamp(sofile), self.cpp2so.digest())
    self.assertEqual(self.prerequisite(name), sofile)
    self.check_value(self.import_module(name), 3)

  def test_missing_stamp_is_recompiled(self):
    '''An object without a stamp, as an older cache holds, is compiled again.'''
    name = self.build(4)
    sofile = self.cached_file(name, '.so')
    os.unlink(self.cpp2so.stampfile(sofile))
    self.assertIsNone(self.cpp2so.read_stamp(sofile))
    self.assertTrue(self.cpp2so.is_stale(sofile))
    self.assertEqual(self.prerequisite(name), self.cached_file(name, '.cpp'))
    self.check_value(self.import_module(name), 4)
    self.assertEqual(self.cpp2so.read_stamp(sofile), self.cpp2so.digest())

  def test_stamp_is_removed_before_the_compile(self):
    '''
    The old stamp goes before the compiler runs.  A compile that stops
    between the compiler and the new stamp (a kill, a time limit) leaves an
    object without a stamp, which is compiled again, and not an object with
    the stamp of headers it was not compiled against.
    '''
    class Interrupted(Exception):
      pass
    name = self.build(6)
    sofile = self.cached_file(name, '.so')
    cppfile = self.cached_file(name, '.cpp')
    # Another digest forces the compile, which stops after the compiler.
    with open(self.cpp2so.stampfile(sofile), 'w') as stream:
      stream.write('0123456789abcdef\n')
    real_pexec = toolchain._system.pexec
    def interrupted_pexec(cmd, *args, **kwds):
      real_pexec(cmd, *args, **kwds)
      raise Interrupted()
    with mock.patch.object(toolchain._system, 'pexec', interrupted_pexec):
      with self.assertRaises(Interrupted):
        makecurry(self.plan, name, [self.srcdir])
    self.assertTrue(os.path.isfile(sofile))
    self.assertIsNone(self.cpp2so.read_stamp(sofile))
    self.assertTrue(self.cpp2so.is_stale(sofile))
    self.assertEqual(self.prerequisite(name), cppfile)
    # The next compile completes and stamps the object.
    self.assertEqual(makecurry(self.plan, name, [self.srcdir]), sofile)
    self.assertEqual(self.cpp2so.read_stamp(sofile), self.cpp2so.digest())
    self.assertEqual(self.prerequisite(name), sofile)
    self.check_value(self.import_module(name), 6)

  def test_header_tree_problems(self):
    '''
    A header that cannot be read (a staged link into a source tree that is
    gone) is an error that names the installation.  A tree without headers
    gives no digest, and the objects are trusted as they are: such an
    installation cannot compile, so a refused object could not be replaced.
    '''
    broken = os.path.join(self.tmpdir, 'broken')
    os.makedirs(os.path.join(broken, 'cyrt'))
    os.symlink(
        os.path.join(self.tmpdir, 'gone.hpp')
      , os.path.join(broken, 'cyrt', 'cyrt.hpp')
      )
    with self.assertRaises(exceptions.PrerequisiteError) as cm:
      toolchain.runtime_digest(broken)
    self.assertIn(broken, str(cm.exception))
    self.assertIn('cyrt.hpp', str(cm.exception))
    empty = os.path.join(self.tmpdir, 'empty')
    os.makedirs(os.path.join(empty, 'cyrt'))
    self.assertIsNone(toolchain.runtime_digest(empty))
    name = self.build(7)
    sofile = self.cached_file(name, '.so')
    os.unlink(self.cpp2so.stampfile(sofile))
    self.assertTrue(self.cpp2so.is_stale(sofile))
    with mock.patch.object(
        toolchain, 'runtime_digest', lambda include_dir=None: None
      ):
      self.assertFalse(self.cpp2so.is_stale(sofile))
      self.assertEqual(self.prerequisite(name), sofile)
      # Without a digest no stamp is written.
      self.cpp2so.write_stamp(sofile)
      self.assertIsNone(self.cpp2so.read_stamp(sofile))
    self.assertTrue(self.cpp2so.is_stale(sofile))
    self.assertEqual(self.prerequisite(name), self.cached_file(name, '.cpp'))

  def test_digest(self):
    '''
    The digest follows the names and the contents of the headers, not their
    time stamps, and not the precompiled header.
    '''
    digest = toolchain.runtime_digest()
    self.assertRegex(digest, r'^[0-9a-f]{16}$')
    self.assertEqual(
        digest, toolchain.runtime_digest(config.installed_path('include'))
      )
    headers = list(toolchain.runtime_headers())
    self.assertEqual(headers, list(toolchain.runtime_headers()))
    self.assertIn(config.installed_path('include', 'cyrt', 'cyrt.hpp'), headers)
    # A copy of the headers with new time stamps gives the same digest.
    root = os.path.join(self.tmpdir, 'include')
    shutil.copytree(
        config.installed_path('include', 'cyrt'), os.path.join(root, 'cyrt')
      , ignore=shutil.ignore_patterns('*.gch')
      )
    copies = list(toolchain.runtime_headers(root))
    self.assertEqual(len(copies), len(headers))
    now = time.time()
    for path in copies:
      os.utime(path, (now, now))
    self.assertEqual(toolchain.runtime_digest(root), digest)
    # A precompiled header in the tree does not count.
    gch = os.path.join(root, 'cyrt', 'cyrt.hpp.gch')
    os.mkdir(gch)
    open(os.path.join(gch, 'O3-0123456789ab.gch'), 'w').close()
    toolchain.runtime_digest.cache_clear()
    self.assertEqual(toolchain.runtime_digest(root), digest)
    # A change to any header gives another digest.
    with open(copies[-1], 'a') as stream:
      stream.write('// one more line\n')
    toolchain.runtime_digest.cache_clear()
    changed = toolchain.runtime_digest(root)
    self.assertNotEqual(changed, digest)
    self.assertRegex(changed, r'^[0-9a-f]{16}$')
    # So does the name of a header.
    os.rename(copies[-1], copies[-1] + '.renamed.hpp')
    toolchain.runtime_digest.cache_clear()
    self.assertNotEqual(toolchain.runtime_digest(root), changed)
    self.assertEqual(toolchain.runtime_digest(), digest)

  def test_second_process_compiles_nothing(self):
    '''
    A process that imports a module compiled by an earlier process runs no
    compiler: not for the module, not for the Prelude, not for the header.
    '''
    module = self.compile_module(5)
    code = '\n'.join([
        'import curry, json'
      , 'from curry.toolchain import _system'
      , 'commands = []'
      , 'pexec = _system.pexec'
      , 'def counting_pexec(cmd, *args, **kwds):'
      , '  commands.append(cmd)'
      , '  return pexec(cmd, *args, **kwds)'
      , '_system.pexec = counting_pexec'
      , 'module = curry.import_(%r, currypath=%r)'
            % (module.__name__, [self.srcdir] + curry.path)
      , 'value = list(curry.eval(module.goal, converter="topython"))'
      , 'print(json.dumps([commands, value]))'
      ])
    proc = cytest.run_in_subprocess(code, timeout=300)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    commands, value = json.loads(proc.stdout.strip().splitlines()[-1])
    self.assertEqual(commands, [])
    self.assertEqual(value, [5])

def undefined_symbols(path):
  '''The undefined dynamic symbols of a shared object, without versions.'''
  proc = subprocess.run(
      ['nm', '-D', '-u', path], capture_output=True, text=True, check=True
    )
  return set(
      line.split()[-1].split('@')[0]
      for line in proc.stdout.splitlines() if line.strip()
    )

@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'the toolchain belongs to the C++ backend'
  )
@unittest.skipIf(shutil.which('nm') is None, 'nm is not installed')
class TestFlavor(ToolchainTestCase):
  '''
  Generated code comes in two flavors.  The release flavor drops the
  assertions, the stack protector, and the procedure linkage table.  The
  debug flavor keeps the assertions.  A module follows the flavor of the
  installed runtime unless the interpreter flag ``debug`` is set.  The stamp
  of an object names its flavor.  Before this, the optimized build kept its
  assertions: neither Make.config nor the toolchain said -DNDEBUG.
  '''
  ASSERT = '__assert_fail'
  STACK_CHECK = '__stack_chk_fail'
  RELEASE_FLAGS = [
      '-O3', '-DNDEBUG', '-fno-stack-protector', '-fno-plt'
    , '-Wl,-Bsymbolic-functions'
    ]

  def setUp(self):
    super().setUp()
    self.plan = plans.makeplan(
        curry.getInterpreter(), plans.MAKE_ALL | plans.ZIP_JSON
      )
    self.cpp2so = toolchain.Cpp2So(curry.getInterpreter())

  def prerequisite(self, name):
    return _findcurry.currentfile(self.plan, name, [self.srcdir])

  def compile_command(self, cpp2so, name):
    cpp = self.cached_file(name, '.cpp')
    out = os.path.join(self.tmpdir, 'probe.so')
    return list(cpp2so._compileCommand(cpp, out))

  def build(self, value):
    '''Builds the object of a module without loading it.  Returns its name.'''
    name = self.write_json(value)
    sofile = makecurry(self.plan, name, [self.srcdir])
    self.assertEqual(sofile, self.cached_file(name, '.so'))
    return name

  def test_installed_runtime(self):
    '''
    The installation names its flavor.  The runtime library and the Prelude
    the stage compiled are of that flavor: no assertion and no stack check
    in a release build, assertions in a debug build.
    '''
    flavor = config.cxx_flavor()
    self.assertIn(flavor, config.CXX_FLAVORS)
    filename = config.installed_path('sysconfig', 'cxx_flavor')
    self.assertEqual(cytest.readfile(filename).strip(), flavor)
    prelude = self.cpp2so._sofilename('Prelude')
    self.assertEqual(
        self.cpp2so.read_stamp(prelude), toolchain.object_digest(flavor)
      )
    for path in config.cyrt_lib(), prelude:
      symbols = undefined_symbols(path)
      if flavor == 'release':
        self.assertNotIn(self.ASSERT, symbols, path)
        self.assertNotIn(self.STACK_CHECK, symbols, path)
      else:
        self.assertIn(self.ASSERT, symbols, path)

  def test_installed_flavor_file(self):
    '''
    The file sysconfig/cxx_flavor decides.  An installation without the
    file, one staged before the flavors existed, is a release build.
    '''
    root = os.path.join(self.tmpdir, 'install')
    os.makedirs(os.path.join(root, 'sysconfig'))
    variable = config._cxx_flavor
    saved = variable.value
    try:
      with mock.patch.object(
          config, 'installed_path', lambda *parts: os.path.join(root, *parts)
        ):
        variable.value = None
        self.assertEqual(config.cxx_flavor(), 'release')
        cases = [
            ('debug\n', 'debug'), ('release\n', 'release'), ('\n', 'release')
          , ('fast\n', 'release')
          ]
        filename = os.path.join(root, 'sysconfig', 'cxx_flavor')
        for text, flavor in cases:
          with open(filename, 'w') as stream:
            stream.write(text)
          variable.value = None
          self.assertEqual(config.cxx_flavor(), flavor, text)
    finally:
      variable.value = saved

  def test_digest(self):
    '''
    The digest of an object follows the headers and the flavor.  The flavor
    of the installation is the default.  Another installed flavor, after a
    stage of the other build, makes an object stale.
    '''
    release = toolchain.object_digest('release')
    debug = toolchain.object_digest('debug')
    for digest in release, debug:
      self.assertRegex(digest, r'^[0-9a-f]{16}$')
    self.assertNotEqual(release, debug)
    self.assertNotEqual(release, toolchain.runtime_digest())
    self.assertNotEqual(debug, toolchain.runtime_digest())
    self.assertEqual(
        toolchain.object_digest(), toolchain.object_digest(config.cxx_flavor())
      )
    self.assertEqual(
        toolchain.object_digest('release', config.installed_path('include'))
      , release
      )
    self.assertRaises(KeyError, toolchain.object_digest, 'fast')
    self.assertEqual(toolchain.flavor_flags('debug'), ['-O0', '-g'])
    for flag in self.RELEASE_FLAGS[:-1]:
      self.assertIn(flag, toolchain.flavor_flags('release'))
    name = self.build(1)
    sofile = self.cached_file(name, '.so')
    self.assertEqual(self.cpp2so.read_stamp(sofile), self.cpp2so.digest())
    self.assertFalse(self.cpp2so.is_stale(sofile))
    other = 'debug' if config.cxx_flavor() == 'release' else 'release'
    with mock.patch.object(config, 'cxx_flavor', lambda: other):
      self.assertEqual(
          toolchain.object_digest(), toolchain.object_digest(other)
        )
      if not curry.flags['debug']:
        self.assertEqual(self.cpp2so.flavor, other)
        self.assertTrue(self.cpp2so.is_stale(sofile))
        self.assertEqual(
            self.prerequisite(name), self.cached_file(name, '.cpp')
          )
    self.assertFalse(self.cpp2so.is_stale(sofile))

  @unittest.skipIf(
      config.cxx_flavor() != 'release' or curry.flags['debug']
    , 'needs a release installation and a session without the debug flag'
    )
  def test_release_flavor(self):
    '''
    Without the flag a module gets the release flags, imports no assertion
    and no stack check, and carries the release stamp.
    '''
    module = self.compile_module(2)
    self.assertEqual(self.cpp2so.flavor, 'release')
    cmd = self.compile_command(self.cpp2so, module.__name__)
    for flag in self.RELEASE_FLAGS:
      self.assertIn(flag, cmd)
    self.assertNotIn('-O0', cmd)
    self.assertNotIn('-g', cmd)
    sofile = self.cached_file(module.__name__, '.so')
    symbols = undefined_symbols(sofile)
    self.assertNotIn(self.ASSERT, symbols)
    self.assertNotIn(self.STACK_CHECK, symbols)
    self.assertEqual(
        self.cpp2so.read_stamp(sofile), toolchain.object_digest('release')
      )
    self.assertEqual(
        self.cpp2so.accepted_digests(), {toolchain.object_digest('release')}
      )

  @cytest.with_flags(backend='cxx', debug=True)
  def test_debug_flag(self):
    '''
    Under the flag a module gets the debug flags and keeps its assertions,
    and its stamp names the debug flavor.  The objects of the installation
    are kept: the Prelude is not compiled again.
    '''
    cpp2so = toolchain.Cpp2So(curry.getInterpreter())
    self.assertEqual(cpp2so.flavor, 'debug')
    self.assertEqual(cpp2so.digest(), toolchain.object_digest('debug'))
    self.assertEqual(
        cpp2so.accepted_digests()
      , {toolchain.object_digest(), toolchain.object_digest('debug')}
      )
    prelude = cpp2so._sofilename('Prelude')
    self.assertFalse(cpp2so.is_stale(prelude))
    module = self.compile_module(3)
    cmd = self.compile_command(cpp2so, module.__name__)
    self.assertIn('-O0', cmd)
    self.assertIn('-g', cmd)
    self.assertIn('-Wl,-Bsymbolic-functions', cmd)
    for flag in '-O3', '-DNDEBUG', '-fno-stack-protector':
      self.assertNotIn(flag, cmd)
    sofile = self.cached_file(module.__name__, '.so')
    self.assertIn(self.ASSERT, undefined_symbols(sofile))
    self.assertEqual(
        cpp2so.read_stamp(sofile), toolchain.object_digest('debug')
      )

  @unittest.skipIf(
      config.cxx_flavor() != 'release' or curry.flags['debug']
    , 'needs a release installation and a session without the debug flag'
    )
  def test_debug_object_is_compiled_again_without_the_flag(self):
    '''
    A session without the flag compiles an object of the debug flavor again,
    once.  A session with the flag keeps it, and keeps a release object too.
    '''
    name = self.build(4)
    sofile = self.cached_file(name, '.so')
    cppfile = self.cached_file(name, '.cpp')
    release = self.cpp2so
    debug = toolchain.Cpp2So(types.SimpleNamespace(flags={'debug': True}))
    self.assertEqual(release.flavor, 'release')
    self.assertEqual(debug.flavor, 'debug')
    # A release object serves both sessions.
    self.assertFalse(release.is_stale(sofile))
    self.assertFalse(debug.is_stale(sofile))
    # A debug object serves the debug session only.
    debug.write_stamp(sofile)
    self.assertEqual(
        release.read_stamp(sofile), toolchain.object_digest('debug')
      )
    self.assertFalse(debug.is_stale(sofile))
    self.assertTrue(release.is_stale(sofile))
    self.assertEqual(self.prerequisite(name), cppfile)
    with capture_log('curry.backends.cxx.toolchain') as log:
      self.assertEqual(makecurry(self.plan, name, [self.srcdir]), sofile)
    log.checkMessages(self, info='Compiling %r' % sofile)
    self.assertEqual(
        release.read_stamp(sofile), toolchain.object_digest('release')
      )
    self.assertFalse(release.is_stale(sofile))
    self.assertEqual(self.prerequisite(name), sofile)
    self.check_value(self.import_module(name), 4)

@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'the toolchain belongs to the C++ backend'
  )
class TestMissingCompiler(ToolchainTestCase):
  '''
  An installation without a C++ compiler (tools/cxx does not resolve) loads
  the objects that make stage compiled.  A module that needs a compile fails
  with an error that names the missing compiler.
  '''
  def test_compile_without_compiler(self):
    name = self.write_json(12)
    with mock.patch.object(config, 'cxx_tool', lambda cached=None: None):
      with self.assertRaises(exceptions.CompileError) as cm:
        self.import_module(name)
    self.assertIn('no C++ compiler', str(cm.exception))
    self.assertTrue(os.path.exists(self.cached_file(name, '.cpp')))
    self.assertFalse(os.path.exists(self.cached_file(name, '.so')))

  def test_prebuilt_object_loads_without_compiler(self):
    '''
    A new process without a compiler imports a module compiled by an earlier
    process, the Prelude included, and runs no command.
    '''
    module = self.compile_module(13)
    code = '\n'.join([
        'import curry, json'
      , 'from curry import config'
      , 'from curry.toolchain import _system'
      , 'config.cxx_tool = lambda cached=None: None'
      , 'def no_pexec(cmd, *args, **kwds):'
      , '  raise AssertionError("a command ran: %r" % (cmd,))'
      , '_system.pexec = no_pexec'
      , 'module = curry.import_(%r, currypath=%r)'
            % (module.__name__, [self.srcdir] + curry.path)
      , 'print(json.dumps(list(curry.eval(module.goal, converter="topython"))))'
      ])
    proc = cytest.run_in_subprocess(code, timeout=300)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(json.loads(proc.stdout.strip().splitlines()[-1]), [13])
