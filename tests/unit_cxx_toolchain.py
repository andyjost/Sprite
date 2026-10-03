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
'''
import cytest # from ./lib; must be first
from cytest.logging import capture_log
from curry import config, exceptions
from curry.backends.cxx import compiler, toolchain
from curry.toolchain import plans, _findcurry
from curry.utility.binding import binding, del_
from unittest import mock
import curry, itertools, logging, os, shutil, subprocess, tempfile, unittest, zlib

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
    install_flag = '-I' + config.installed_path('include')
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
    '''A member older than libcyrt.so is built again.'''
    self.compile_module(4)
    member, = self.members()
    path = os.path.join(self.gch_dir, member)
    old = os.path.getmtime(config.cyrt_lib()) - 100
    os.utime(path, (old, old))
    pch = toolchain.PrecompiledHeader(
        self.root, config.cxx_tool()
      , toolchain.Cpp2So(curry.getInterpreter())._cxxflags()
      )
    self.assertEqual(pch.filename, path)
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
