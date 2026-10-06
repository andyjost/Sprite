'''
Tests for configure and the build settings it writes into Make.config: the
job count of make (--jobs) and ccache in front of the compilers
(--with-ccache).

configure runs as a copy in a scratch directory, so the staged installation
of this tree stays as it is.  The make side is checked without a build: dry
runs, the rule database (make -p), and a small install of src/export/tools
into a scratch prefix, which writes five links or four links and the ccache
wrapper.
'''
import cytest # from ./lib; must be first
from curry import config
import os, re, shutil, stat, subprocess, sys, tempfile, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CONFIGURE = os.path.join(ROOT, 'configure')
MAKE_CONFIG = os.path.join(ROOT, 'Make.config')
ENV = {
    'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')
  , 'HOME': os.environ.get('HOME', '/')
  , 'LC_ALL': 'C.UTF-8'
  , 'TMPDIR': os.environ.get('TMPDIR', tempfile.gettempdir())
  }
OLD = 946684800 # 2000-01-01, older than any file of the tree.

def readfile(*parts):
  with open(os.path.join(*parts)) as istream:
    return istream.read()

def run(cmd, **kwds):
  kwds.setdefault('env', ENV)
  kwds.setdefault('stdout', subprocess.PIPE)
  kwds.setdefault('stderr', subprocess.STDOUT)
  kwds.setdefault('text', True)
  kwds.setdefault('timeout', 300)
  return subprocess.run(cmd, **kwds)

def make_config_value(text, name):
  '''The value of a variable in a Make.config text.'''
  m = re.search(r'^%s[ \t]*:=[ \t]*(.*)$' % re.escape(name), text, re.M)
  assert m is not None, name
  return m.group(1).strip()

def default_jobs():
  '''The default of --jobs, as configure defines it.'''
  m = re.search(r"^DEFAULT_JOBS = '([^']*)'", readfile(CONFIGURE), re.M)
  assert m is not None
  return m.group(1)

def write_script(filename, text):
  with open(filename, 'w') as ostream:
    ostream.write(text)
  os.chmod(filename, 0o755)

def write_stub_ccache(dirname):
  '''
  A stand-in for ccache.  It writes its arguments, one per line, to argv.txt
  beside itself and runs nothing.
  '''
  os.makedirs(dirname, exist_ok=True)
  stub = os.path.join(dirname, 'ccache')
  write_script(
      stub
    , '#!/bin/sh\nprintf "%%s\\n" "$@" > "%s"\n' % os.path.join(dirname, 'argv.txt')
    )
  return stub

def make(*args, **kwds):
  '''Runs make in a directory of this tree with the clean environment.'''
  return run(['make'] + list(args), **kwds)

class ConfigureTestCase(cytest.TestCase):
  '''Runs copies of configure in scratch directories.'''

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    if not os.path.isfile(MAKE_CONFIG):
      raise unittest.SkipTest('this tree is not configured')
    if config.curry_frontend() is None:
      raise unittest.SkipTest('the Curry front end is not configured')
    text = readfile(MAKE_CONFIG)
    cls.cc = make_config_value(text, 'CC')
    cls.cxx = make_config_value(text, 'CXX')
    cls.cxx_postinstall = config.cxx_tool()
    cls.frontend = os.path.realpath(config.curry_frontend())

  def configure(self, tmpdir, *args, write=True, env=None):
    '''
    Runs a copy of configure in ``tmpdir`` with the staged tools and the
    checks that run the tools skipped (-f).  Returns the completed process
    and the text of Make.config, if written.
    '''
    script = os.path.join(tmpdir, 'configure')
    if not os.path.exists(script):
      shutil.copy(CONFIGURE, script)
    cmd = [
        sys.executable, script, '-f'
      , '--with-python=' + sys.executable
      , '--with-cc=' + self.cc
      , '--with-cxx=' + self.cxx
      , '--with-cxx-postinstall=' + self.cxx_postinstall
      , '--with-pakcs='
      , '--with-curry-frontend=' + self.frontend
      , '--with-icurry='
      ] + list(args)
    if not write:
      cmd.append('--check-prereqs')
    conf = os.path.join(tmpdir, 'Make.config')
    if os.path.exists(conf):
      os.unlink(conf)
    result = run(cmd, cwd=tmpdir, env=ENV if env is None else env)
    text = readfile(conf) if os.path.isfile(conf) else None
    return result, text

class TestConfigureOptions(ConfigureTestCase):
  '''The options --jobs and --with-ccache and the lines they write.'''

  def test_help(self):
    '''configure -h documents the two options.'''
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      result = run([sys.executable, CONFIGURE, '-h'], cwd=tmpdir)
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertIn('--jobs N|auto', result.stdout)
    self.assertIn('--with-ccache', result.stdout)
    self.assertIn('default: %s' % default_jobs(), result.stdout)

  def test_defaults(self):
    '''
    Without the options, Make.config names the default job count and no
    ccache, under comments that name the options.
    '''
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      result, text = self.configure(tmpdir)
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertIn('Configuration succeeded', result.stdout)
    self.assertEqual(make_config_value(text, 'JOBS'), default_jobs())
    self.assertEqual(make_config_value(text, 'CCACHE'), '')
    self.assertIn('# Parallel build (configure --jobs)', text)
    self.assertIn('# ccache (configure --with-ccache)', text)
    # The compilers are not touched by the option.
    self.assertEqual(make_config_value(text, 'CXX'), self.cxx)
    self.assertEqual(make_config_value(text, 'CXX_POSTINSTALL'), self.cxx_postinstall)

  def test_jobs(self):
    '''--jobs takes a count or auto; -j is its short form.'''
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      for args, expected in [
          (['--jobs=4'], '4'), (['--jobs', 'auto'], 'auto'), (['-j', '03'], '3')
        ]:
        result, text = self.configure(tmpdir, *args)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(make_config_value(text, 'JOBS'), expected, args)

  def test_jobs_invalid(self):
    '''A count below one, or a word other than auto, is refused at once.'''
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      for value in ['0', '-2', 'two', '']:
        result, text = self.configure(tmpdir, '--jobs=' + value)
        self.assertEqual(result.returncode, 2, (value, result.stdout))
        self.assertIn('expected a positive integer or auto', result.stdout)
        self.assertIsNone(text, value)

  def test_with_ccache(self):
    '''
    --with-ccache names ccache by path or by name (searched in PATH), the
    environment variable CCACHE does the same, an empty value leaves it out,
    and a program that does not exist aborts the configuration.
    '''
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      bindir = os.path.join(tmpdir, 'bin')
      stub = write_stub_ccache(bindir)
      # By path.
      result, text = self.configure(tmpdir, '--with-ccache=' + stub)
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertEqual(make_config_value(text, 'CCACHE'), stub)
      self.assertEqual(make_config_value(text, 'CXX'), self.cxx)
      self.assertEqual(make_config_value(text, 'CXX_POSTINSTALL'), self.cxx_postinstall)
      # By name, through PATH.
      env = dict(ENV, PATH=bindir + ':' + ENV['PATH'])
      result, text = self.configure(tmpdir, '--with-ccache', env=env)
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertEqual(make_config_value(text, 'CCACHE'), stub)
      # Through the environment.
      env = dict(ENV, CCACHE=stub)
      result, text = self.configure(tmpdir, env=env)
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertEqual(make_config_value(text, 'CCACHE'), stub)
      # Left out by request, even with CCACHE in the environment.
      result, text = self.configure(tmpdir, '--with-ccache=', env=env)
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertEqual(make_config_value(text, 'CCACHE'), '')
      # A program that does not exist.
      missing = os.path.join(tmpdir, 'no-such-ccache')
      result, text = self.configure(tmpdir, '--with-ccache=' + missing)
      self.assertEqual(result.returncode, 1, result.stdout)
      self.assertIn('Aborted', result.stdout)
      self.assertIsNone(text)

  def test_with_ccache_missing_prereq(self):
    '''
    When ccache is requested by name and PATH has none, the prerequisite
    check reports it with its installation step.
    '''
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      emptybin = os.path.join(tmpdir, 'emptybin')
      os.mkdir(emptybin)
      env = dict(ENV, PATH=emptybin)
      result, text = self.configure(tmpdir, '--with-ccache', write=False, env=env)
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertIn('Missing: ccache', result.stdout)
    self.assertIn('Install ccache', result.stdout)
    self.assertIsNone(text)

  def test_front_end_required_with_icurry(self):
    '''
    Both routes from Curry to ICurry run the front end (the icurry route
    rewrites its FlatCurry file before icurry reads it), so configure
    refuses a front end left out, also when icurry is given.
    '''
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      result, text = self.configure(
          tmpdir, '--with-curry-frontend=', '--with-icurry=' + sys.executable
        )
    self.assertNotEqual(result.returncode, 0, result.stdout)
    self.assertIn('The Curry front end is not configured.', result.stdout)
    self.assertIn('Both routes from Curry to ICurry run it', result.stdout)
    self.assertIsNone(text)

class TestMakeSide(cytest.TestCase):
  '''
  The Makefiles under the settings of Make.config: the job count, the
  compiler prefix, and the wrapper of the post-install compiler.
  '''

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    if not os.path.isfile(MAKE_CONFIG):
      raise unittest.SkipTest('this tree is not configured')
    if shutil.which('make', path=ENV['PATH']) is None:
      raise unittest.SkipTest('make is not installed')
    cls.cxx = make_config_value(readfile(MAKE_CONFIG), 'CXX')

  def print_makeflags(self, *args):
    '''The MAKEFLAGS of the top-level make with the given arguments.'''
    result = make('-s', *args, 'print-MAKEFLAGS', cwd=ROOT)
    return result, result.stdout.split('set to [')[-1].split(']')[0]

  def test_jobs_to_makeflags(self):
    '''
    JOBS becomes -j of the top-level make: a count as it is, auto as the
    processor count, 1 as a serial build.  A -j on the command line wins.
    An invalid value is an error with a clear message.
    '''
    result, flags = self.print_makeflags('JOBS=4')
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertIn('-j4', flags.split())
    result, flags = self.print_makeflags('JOBS=1')
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertNotIn('-j', flags)
    result, flags = self.print_makeflags('-j2', 'JOBS=4')
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertIn('-j2', flags.split())
    self.assertNotIn('-j4', flags.split())
    nproc = shutil.which('nproc', path=ENV['PATH'])
    if nproc is not None:
      count = run([nproc]).stdout.strip()
      result, flags = self.print_makeflags('JOBS=auto')
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertIn('-j' + count, flags.split())
    for value in ['0', 'many']:
      result = make('-s', 'JOBS=' + value, 'print-MAKEFLAGS', cwd=ROOT)
      self.assertEqual(result.returncode, 2, (value, result.stdout))
      self.assertIn('JOBS should be a count or auto', result.stdout)

  def test_recipes_pass_the_job_server(self):
    '''
    The recipes of the root Makefile that run make say $(MAKE), so a
    parallel make reaches them.  A dry run of stage shows the recursion.
    '''
    text = readfile(ROOT, 'Makefile')
    self.assertIsNone(re.search(r'^\t[@+-]*make\b', text, re.M))
    result = make('-n', 'stage', cwd=ROOT)
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertIn('-C src install', result.stdout)
    self.assertIn('-C curry install', result.stdout)

  def database(self, directory):
    '''The rule database of a make in ``directory`` (make -p).'''
    result = make('-p', '-s', 'print-ROOT_DIR', cwd=os.path.join(ROOT, directory))
    self.assertEqual(result.returncode, 0, result.stdout[-2000:])
    return result.stdout

  def assertRule(self, database, pattern):
    '''Asserts that one line of the database matches the pattern.'''
    self.assertRegex(database, re.compile(pattern, re.M))

  def test_build_order(self):
    '''
    The order-only prerequisites that keep make -j safe: curry after src,
    python after cyrt, shlibs after libs, the nested make that archives the
    objects of the cyrt subdirectories after the archive of cyrt itself, and
    the installed archive after that nested make.
    '''
    self.assertRule(self.database('.'), r'^curry: \| src$')
    src = self.database('src')
    self.assertRule(src, r'^python: \| cyrt$')
    self.assertRule(src, r'^shlibs:: \| libs$')
    cyrt = self.database(os.path.join('src', 'cyrt'))
    self.assertRule(cyrt, r'^shlib_extra: \| \S+/object-root/cyrt/libcyrt\.a$')
    self.assertRule(
        cyrt, r'^\S+/libcyrt\.so: \S+/object-root/cyrt/libcyrt\.a \| shlib_extra$'
      )
    self.assertRule(
        cyrt, r'^\S+/lib/libcyrt\.a: \S+/object-root/cyrt/libcyrt\.a \| shlib_extra$'
      )
    self.assertIn('.NOTPARALLEL:', readfile(ROOT, 'curry', 'Makefile'))

  def test_compile_through_ccache(self):
    '''
    With CCACHE set, an object is compiled by ccache in front of the
    compiler; without it, by the compiler alone.  A what-if dry run (-W)
    shows the command.  The tree may be configured with ccache, so the plain
    case clears CCACHE on the command line.
    '''
    def compile_line(*args):
      result = make(
          '-n', '-W', 'builtins.cpp', 'objs', *args
        , cwd=os.path.join(ROOT, 'src', 'cyrt')
        )
      self.assertEqual(result.returncode, 0, result.stdout)
      lines = [
          line for line in result.stdout.splitlines()
          if 'builtins.o' in line and ' -c ' in line
        ]
      self.assertEqual(len(lines), 1, result.stdout)
      return lines[0]
    line = compile_line('CCACHE=')
    self.assertTrue(line.startswith(self.cxx + ' '), line)
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      stub = write_stub_ccache(tmpdir)
      line = compile_line('CCACHE=' + stub)
    self.assertTrue(line.startswith(stub + ' ' + self.cxx + ' '), line)

  def test_tools_cxx(self):
    '''
    Without ccache, tools/cxx is a link to the post-install compiler.  With
    ccache, it is a script that runs ccache in front of that compiler, by
    absolute paths, so no compiler-name detection is needed.  The script
    replaces an old link without a write through it, and a configuration
    without ccache turns it into a link again.
    '''
    tools_dir = os.path.join(ROOT, 'src', 'export', 'tools')
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      prefix = os.path.join(tmpdir, 'prefix')
      os.mkdir(prefix)
      stub = write_stub_ccache(os.path.join(tmpdir, 'bin'))
      compiler = os.path.join(tmpdir, 'bin', 'fake-g++')
      compiler_text = '#!/bin/sh\necho fake compiler\n'
      write_script(compiler, compiler_text)
      cxx = os.path.join(prefix, 'tools', 'cxx')
      def install(*args):
        result = make(
            '-s', '-C', tools_dir, 'install', 'PREFIX=' + prefix
          , 'CXX_POSTINSTALL=' + compiler, *args
          )
        self.assertEqual(result.returncode, 0, result.stdout)
      # Without ccache: a link.
      install('CCACHE=')
      self.assertTrue(os.path.islink(cxx))
      self.assertEqual(os.readlink(cxx), compiler)
      self.assertTrue(os.path.islink(os.path.join(prefix, 'tools', 'python')))
      # With ccache: a script, over the old link.  The link looks old, as
      # after a new configuration, so the rule runs again.
      os.utime(compiler, (OLD, OLD))
      install('CCACHE=' + stub)
      self.assertFalse(os.path.islink(cxx))
      self.assertTrue(os.path.isfile(cxx))
      self.assertTrue(os.stat(cxx).st_mode & stat.S_IXUSR)
      text = readfile(cxx)
      self.assertTrue(text.startswith('#!/bin/sh\n'), text)
      self.assertIn('exec "%s" "%s" "$@"' % (stub, compiler), text)
      self.assertEqual(readfile(compiler), compiler_text)
      result = run([cxx, '-c', 'x.cpp', '-o', 'x.o'])
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertEqual(
          readfile(tmpdir, 'bin', 'argv.txt').split('\n')[:-1]
        , [compiler, '-c', 'x.cpp', '-o', 'x.o']
        )
      # Without ccache again: a link.  The script is older than Make.config,
      # as after a new configuration.
      os.utime(cxx, (OLD, OLD))
      install('CCACHE=')
      self.assertTrue(os.path.islink(cxx))
      self.assertEqual(os.readlink(cxx), compiler)

class TestWorktreeScript(cytest.TestCase):
  '''scripts/new-worktree.sh passes the build settings on.'''

  def test_script(self):
    script = os.path.join(ROOT, 'scripts', 'new-worktree.sh')
    result = run(['bash', '-n', script])
    self.assertEqual(result.returncode, 0, result.stdout)
    text = readfile(script)
    self.assertIn('cp "$here/Make.config" "$path/Make.config"', text)
    self.assertIn('JOBS', text)
    self.assertIn('CCACHE', text)
