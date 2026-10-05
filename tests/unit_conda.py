import cytest # from ./lib; must be first
from curry import config
import os, re, shutil, subprocess, sys, tempfile, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CONDA = os.path.join(ROOT, 'conda')
RECIPE = os.path.join(CONDA, 'recipe')
FRONTEND_RECIPE = os.path.join(CONDA, 'curry-frontend')
ENV = {
    'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')
  , 'HOME': os.environ.get('HOME', '/')
  , 'LC_ALL': 'C.UTF-8'
  , 'TMPDIR': os.environ.get('TMPDIR', tempfile.gettempdir())
  }

def readfile(*parts):
  with open(os.path.join(*parts)) as istream:
    return istream.read()

def run(cmd, **kwds):
  kwds.setdefault('env', ENV)
  kwds.setdefault('stdout', subprocess.PIPE)
  kwds.setdefault('stderr', subprocess.STDOUT)
  kwds.setdefault('text', True)
  kwds.setdefault('timeout', 600)
  return subprocess.run(cmd, **kwds)

def make_config_value(text, name):
  '''The value of a variable in a Make.config text.'''
  m = re.search(r'^%s[ \t]*:=[ \t]*(.*)$' % re.escape(name), text, re.M)
  assert m is not None, name
  return m.group(1).strip()

class TestCondaRecipe(cytest.TestCase):
  '''
  Tests for the conda recipe scaffold under conda/.  The recipes are not
  built here; see conda/README.md.  These tests check the files and the
  build options the recipe relies on.
  '''

  def test_files(self):
    '''The recipe files exist, and the shell scripts parse.'''
    for name in ['meta.yaml', 'build.sh', 'conda_build_config.yaml']:
      self.assertTrue(os.path.isfile(os.path.join(RECIPE, name)), name)
      self.assertTrue(os.path.isfile(os.path.join(FRONTEND_RECIPE, name)), name)
    self.assertTrue(os.path.isfile(os.path.join(CONDA, 'README.md')))
    self.assertTrue(
        os.path.isfile(os.path.join(FRONTEND_RECIPE, 'LICENSE.curry-frontend'))
      )
    for recipe in [RECIPE, FRONTEND_RECIPE]:
      script = os.path.join(recipe, 'build.sh')
      self.assertTrue(os.access(script, os.X_OK), script)
      result = run(['bash', '-n', script])
      self.assertEqual(result.returncode, 0, result.stdout)

  def test_sprite_recipe(self):
    '''The Sprite recipe names the dependencies and the layout of the task.'''
    meta = readfile(RECIPE, 'meta.yaml')
    self.assertIn('name: sprite', meta)
    self.assertIn('path: ../..', meta)
    self.assertIn('skip: true  # [not linux64]', meta)
    for dep in ['python 3.14.*', 'curry-frontend 2.0.0.*', 'cxx-compiler']:
      self.assertIn(dep, meta)
    self.assertIn("{{ compiler('cxx') }}", meta)
    self.assertIn('libboost-headers', meta)
    self.assertIn('opt/sprite/lib', meta)
    for notice in ['curry/lib/LICENSE', 'curry/lib/NOTICE', 'extern/pybind11/LICENSE']:
      self.assertIn(notice, meta)
    script = readfile(RECIPE, 'build.sh')
    self.assertIn('SPRITE_HOME="$PREFIX/opt/sprite"', script)
    self.assertIn("--with-pakcs=''", script)
    self.assertIn('--with-curry-frontend="$PREFIX/bin/pakcs-frontend"', script)
    self.assertIn('install PREFIX="$SPRITE_HOME"', script)
    self.assertIn('-ffile-prefix-map=$SRC_DIR=.', script)
    self.assertIn('rm -f "$SPRITE_HOME/lib/libcyrt.a"', script)
    self.assertIn('sprite.pth', script)
    # The tool links are relative; the compiler is resolved at run time.
    self.assertIn('ln -s "../../../bin/python$pyver" "$tools/python"', script)
    self.assertIn('\nmake install PREFIX="$SPRITE_HOME"\n', script)
    # A parallel build with the jobs conda-build grants; no ccache.
    self.assertIn('--jobs "${CPU_COUNT:-1}"', script)
    self.assertIn("--with-ccache=''", script)
    # The prebuild step compiles with a wrapper in the build tree that names
    # the include directory of the host environment.
    self.assertIn('cxx_build="$SRC_DIR/conda-build-cxx"', script)
    self.assertIn('--with-cxx-postinstall="$cxx_build"', script)
    # The precompiled header of the build compiler stays out of the package.
    self.assertIn('rm -rf "$SPRITE_HOME/include/cyrt/cyrt.hpp.gch"', script)
    self.assertIn('ln -s ../../../bin/pakcs-frontend "$tools/curry-frontend"', script)
    self.assertIn('SPRITE_CXX', script)
    self.assertIn('-isystem', script)
    meta_run = meta.split('  run:')[1]
    self.assertIn('libboost-headers', meta_run)
    # conda relocates the compiled library modules at install time.
    self.assertIn('detect_binary_files_with_prefix: true', meta)
    # Each backend is tested through the launcher and through the module;
    # the C++ tests check the products that only the C++ backend writes.
    self.assertIn('python -m curry Smoke.curry | grep -x 42', meta)
    self.assertIn(
        'SPRITE_INTERPRETER_FLAGS=backend:cxx python -m curry Smoke.curry', meta
      )
    self.assertEqual(meta.count('test -s .curry/sprite-pakcs-3.4.1/Smoke.so &&'), 2)
    self.assertEqual(meta.count('test -s .curry/sprite-pakcs-3.4.1/Smoke.so.abi'), 2)
    self.assertNotIn('$SRC_DIR/', script.split('-ffile-prefix-map=$SRC_DIR=.')[-1])

  def test_frontend_recipe(self):
    '''The front-end recipe repackages the upstream binary with its notices.'''
    meta = readfile(FRONTEND_RECIPE, 'meta.yaml')
    self.assertIn('name: curry-frontend', meta)
    self.assertIn('pakcs-{{ pakcs_version }}-amd64-Linux.tar.gz', meta)
    self.assertIn('set pakcs_version = "3.4.1"', meta)
    self.assertIn('set version = "2.0.0"', meta)
    self.assertRegex(meta, r'sha256: [0-9a-f]{64}')
    self.assertIn('- gmp', meta)
    self.assertIn('license: BSD-3-Clause', meta)
    self.assertIn('- LICENSE\n', meta)
    self.assertIn('- LICENSE.curry-frontend', meta)
    notice = readfile(FRONTEND_RECIPE, 'LICENSE.curry-frontend')
    self.assertIn('Wolfgang Lux', notice)
    self.assertIn('Michael Hanus', notice)
    self.assertIn('Redistribution and use in source and binary forms', notice)
    script = readfile(FRONTEND_RECIPE, 'build.sh')
    self.assertIn('bin/pakcs-frontend', script)
    self.assertIn('curry-frontend', script)

  def test_readme(self):
    '''The README covers the two recipes and the open questions.'''
    text = readfile(CONDA, 'README.md')
    for topic in [
        'curry-frontend', 'opt/sprite', 'macOS', 'Windows', 'compiler'
      , 'LICENSE', 'Nothing here is published'
      ]:
      self.assertIn(topic, text)

  def configure(self, tmpdir, *args, write=True, fast=True):
    '''
    Runs a copy of configure in a scratch directory with the staged tools.
    Returns the completed process and the text of Make.config, if written.
    ``fast`` skips the checks that run the tools (configure -f).
    '''
    script = os.path.join(tmpdir, 'configure')
    shutil.copy(os.path.join(ROOT, 'configure'), script)
    cmd = [
        sys.executable, script
      , '--with-python=' + sys.executable
      , '--with-cc=' + readfile(ROOT, 'Make.config').split('CC  := ')[1].split('\n')[0].strip()
      , '--with-cxx=' + readfile(ROOT, 'Make.config').split('CXX := ')[1].split('\n')[0].strip()
      , '--with-cxx-postinstall=' + config.cxx_tool()
      , '--with-icurry='
      ] + list(args)
    if fast:
      cmd.append('-f')
    if not write:
      cmd.append('--check-prereqs')
    result = run(cmd, cwd=tmpdir)
    conf = os.path.join(tmpdir, 'Make.config')
    text = readfile(conf) if os.path.isfile(conf) else None
    return result, text

  def test_configure_without_pakcs(self):
    '''
    configure --with-pakcs '' builds without PAKCS when the front end is
    named.  The pinned release names the intermediate directories.
    '''
    if config.curry_frontend() is None:
      raise unittest.SkipTest('the Curry front end is not configured')
    frontend = os.path.realpath(config.curry_frontend())
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      result, text = self.configure(
          tmpdir, '--with-pakcs=', '--with-curry-frontend=' + frontend, fast=False
        )
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertIn('Configuration succeeded', result.stdout)
      self.assertEqual(make_config_value(text, 'PAKCS'), '')
      self.assertEqual(make_config_value(text, 'PAKCS_HOME'), '')
      self.assertEqual(make_config_value(text, 'PAKCS_NAME'), 'pakcs')
      self.assertEqual(make_config_value(text, 'PAKCS_VERSION'), '3.4.1')
      self.assertEqual(make_config_value(text, 'CURRY_FRONTEND'), frontend)
      self.assertEqual(
          make_config_value(text, 'CURRY_FRONTEND_FLAGS'), '--extended -D__PAKCS__=304'
        )
      self.assertEqual(make_config_value(text, 'CURRY2ICURRY_TOOL'), 'frontend')
      self.assertEqual(make_config_value(text, 'ICURRY_EXECUTABLE'), '')
      # The same subdirectory names as the committed products.
      self.assertEqual(config.frontend_subdir(), 'pakcs-3.4.1')
      self.assertEqual(config.intermediate_subdir(), 'sprite-pakcs-3.4.1')
    # The prerequisite check passes without PAKCS.
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      result, text = self.configure(
          tmpdir, '--with-pakcs=', '--with-curry-frontend=' + frontend, write=False
        )
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertIn('Found 0 problems.', result.stdout)
      self.assertIsNone(text)
    # Without PAKCS and without the front end, nothing translates Curry.
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      result, text = self.configure(
          tmpdir, '--with-pakcs=', '--with-curry-frontend='
        )
      self.assertNotEqual(result.returncode, 0)
      self.assertIn('Neither the Curry front end nor icurry', result.stdout)
      self.assertIsNone(text)

  def fake_tool(self, tmpdir, name, output, with_args=False):
    '''
    Writes an executable script that prints ``output``, followed by its
    arguments if ``with_args``.
    '''
    path = os.path.join(tmpdir, name)
    with open(path, 'w') as ostream:
      ostream.write('#!/bin/sh\necho %s%s\n' % (output, ' "$@"' if with_args else ''))
    os.chmod(path, 0o755)
    return path

  def test_cxx_wrapper(self):
    '''
    The tools/cxx wrapper of the package runs SPRITE_CXX when set, else the
    compiler of the environment.  An ambient CXX counts only when it names a
    file under the prefix of the wrapper.  The wrapper adds the include
    directory of the environment.
    '''
    script = readfile(RECIPE, 'build.sh')
    m = re.search(r"<<'CXX_EOF'\n(.*?)\nCXX_EOF\n", script, re.S)
    self.assertIsNotNone(m)
    text = m.group(1).replace('@HOST@', 'fake-host')
    self.assertNotIn('@HOST@', text)
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      tmpdir = os.path.realpath(tmpdir)
      prefix = os.path.join(tmpdir, 'env')
      bindir = os.path.join(prefix, 'bin')
      tools = os.path.join(prefix, 'opt', 'sprite', 'tools')
      os.makedirs(bindir)
      os.makedirs(tools)
      wrapper = os.path.join(tools, 'cxx')
      with open(wrapper, 'w') as ostream:
        ostream.write(text + '\n')
      os.chmod(wrapper, 0o755)
      self.fake_tool(bindir, 'fake-host-g++', 'inside-default', with_args=True)
      other = self.fake_tool(bindir, 'other-c++', 'inside-other', with_args=True)
      outside = self.fake_tool(tmpdir, 'g++', 'outside', with_args=True)
      isystem = ['-isystem', os.path.join(prefix, 'include'), '-c', 'x.cpp']
      def compiler(**env):
        result = run([wrapper, '-c', 'x.cpp'], env=dict(ENV, **env))
        self.assertEqual(result.returncode, 0, result.stdout)
        return result.stdout.split()
      # No variable: the compiler of the environment.
      self.assertEqual(compiler(), ['inside-default'] + isystem)
      # SPRITE_CXX wins.
      self.assertEqual(compiler(SPRITE_CXX=outside, CXX=other), ['outside'] + isystem)
      # CXX counts when it names a file under the prefix, by path or by name.
      self.assertEqual(compiler(CXX=other), ['inside-other'] + isystem)
      self.assertEqual(
          compiler(CXX='other-c++', PATH=bindir + ':' + ENV['PATH'])
        , ['inside-other'] + isystem
        )
      # A CXX outside the prefix, a name with flags, or a missing file does
      # not.
      self.assertEqual(compiler(CXX=outside), ['inside-default'] + isystem)
      self.assertEqual(
          compiler(CXX='g++', PATH=tmpdir + ':' + ENV['PATH'])
        , ['inside-default'] + isystem
        )
      self.assertEqual(compiler(CXX='g++ -std=c++17'), ['inside-default'] + isystem)
      self.assertEqual(
          compiler(CXX=os.path.join(bindir, 'missing-c++')), ['inside-default'] + isystem
        )

  def test_configure_frontend_version(self):
    '''
    configure accepts the front end of the pinned PAKCS only.  The committed
    ICurry files and the oracle depend on its FlatCurry.
    '''
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      fake = self.fake_tool(tmpdir, 'curry-frontend', '3.3.0')
      result, text = self.configure(
          tmpdir, '--with-pakcs=', '--with-curry-frontend=' + fake, fast=False
        )
      self.assertNotEqual(result.returncode, 0)
      self.assertIn("Acceptable Curry front end versions are: ['2.0.0']", result.stdout)
      self.assertIsNone(text)
      # The pinned version passes.
      fake = self.fake_tool(tmpdir, 'curry-frontend', '2.0.0')
      result, text = self.configure(
          tmpdir, '--with-pakcs=', '--with-curry-frontend=' + fake, fast=False
        )
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertEqual(make_config_value(text, 'CURRY_FRONTEND'), fake)

  def test_configure_curry2icurry(self):
    '''--curry2icurry names the default route, which must be configured.'''
    if config.curry_frontend() is None:
      raise unittest.SkipTest('the Curry front end is not configured')
    frontend = os.path.realpath(config.curry_frontend())
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      # icurry is requested but not configured.
      result, text = self.configure(
          tmpdir, '--with-pakcs=', '--with-curry-frontend=' + frontend
        , '--curry2icurry', 'icurry'
        )
      self.assertNotEqual(result.returncode, 0)
      self.assertIn('--curry2icurry=icurry was requested', result.stdout)
      self.assertIn('not configured', result.stdout)
      self.assertIsNone(text)
      # The front end is requested by name.
      result, text = self.configure(
          tmpdir, '--with-pakcs=', '--with-curry-frontend=' + frontend
        , '--curry2icurry', 'frontend'
        )
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertEqual(make_config_value(text, 'CURRY2ICURRY_TOOL'), 'frontend')
      # Without the front end, icurry is required and is the default route.
      icurry = self.fake_tool(tmpdir, 'icurry', 'icurry')
      result, text = self.configure(
          tmpdir, '--with-pakcs=', '--with-curry-frontend='
        , '--with-icurry=' + icurry
        )
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertEqual(make_config_value(text, 'CURRY_FRONTEND'), '')
      self.assertEqual(make_config_value(text, 'ICURRY_EXECUTABLE'), icurry)
      self.assertEqual(make_config_value(text, 'CURRY2ICURRY_TOOL'), 'icurry')

  def test_make_without_pakcs(self):
    '''
    make accepts an empty PAKCS and installs no pakcs link.  The tools
    directory is installed into a scratch prefix.
    '''
    tools = os.path.join(ROOT, 'src', 'export', 'tools')
    if not os.path.isfile(os.path.join(ROOT, 'Make.config')):
      raise unittest.SkipTest('Make.config is absent')
    # icurry is set on the command line, so the test does not depend on the
    # value in Make.config.
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      result = run([
          'make', '-C', tools, 'install', 'PREFIX=' + tmpdir, 'PAKCS=', 'PAKCS_HOME='
        , 'ICURRY_EXECUTABLE='
        ])
      self.assertEqual(result.returncode, 0, result.stdout)
      installed = sorted(os.listdir(os.path.join(tmpdir, 'tools')))
      self.assertNotIn('pakcs', installed)
      self.assertNotIn('icurry', installed)
      self.assertIn('curry-frontend', installed)
      self.assertIn('python', installed)
      self.assertIn('cxx', installed)
    # A configured icurry is linked.  Any executable file stands in for it.
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      result = run([
          'make', '-C', tools, 'install', 'PREFIX=' + tmpdir, 'PAKCS=', 'PAKCS_HOME='
        , 'ICURRY_EXECUTABLE=' + sys.executable
        ])
      self.assertEqual(result.returncode, 0, result.stdout)
      installed = sorted(os.listdir(os.path.join(tmpdir, 'tools')))
      self.assertIn('icurry', installed)
      self.assertEqual(os.readlink(os.path.join(tmpdir, 'tools', 'icurry')), sys.executable)
    # An empty version is an error.
    result = run(['make', '-C', tools, '-n', 'install', 'PAKCS_VERSION='])
    self.assertNotEqual(result.returncode, 0)
    self.assertIn('PAKCS_VERSION is not set', result.stdout)

  def test_make_validate_tools(self):
    '''Make.validate checks the route from Curry to ICurry.'''
    tools = os.path.join(ROOT, 'src', 'export', 'tools')
    if not os.path.isfile(os.path.join(ROOT, 'Make.config')):
      raise unittest.SkipTest('Make.config is absent')
    def dry_run(*settings):
      return run(['make', '-C', tools, '-n', 'install'] + list(settings))
    result = dry_run('CURRY2ICURRY_TOOL=bogus')
    self.assertNotEqual(result.returncode, 0)
    self.assertIn('CURRY2ICURRY_TOOL should be frontend or icurry, not "bogus"', result.stdout)
    result = dry_run('CURRY_FRONTEND=', 'ICURRY_EXECUTABLE=')
    self.assertNotEqual(result.returncode, 0)
    self.assertIn('Neither CURRY_FRONTEND nor ICURRY_EXECUTABLE is set', result.stdout)
    missing = os.path.join(ROOT, 'no-such-tool')
    result = dry_run('CURRY_FRONTEND=' + missing)
    self.assertNotEqual(result.returncode, 0)
    self.assertIn('Not an executable file: CURRY_FRONTEND=' + missing, result.stdout)
    result = dry_run('ICURRY_EXECUTABLE=' + missing)
    self.assertNotEqual(result.returncode, 0)
    self.assertIn('Not an executable file: ICURRY_EXECUTABLE=' + missing, result.stdout)
    # Either tool alone is accepted.
    result = dry_run('CURRY_FRONTEND=', 'ICURRY_EXECUTABLE=' + sys.executable)
    self.assertEqual(result.returncode, 0, result.stdout)
    result = dry_run('CURRY_FRONTEND=' + sys.executable, 'ICURRY_EXECUTABLE=')
    self.assertEqual(result.returncode, 0, result.stdout)

  def test_overlay_rules(self):
    '''
    make overlay extracts the test products; make overlay-archive packs the
    five product kinds with fixed metadata and the library interfaces.
    '''
    if not os.path.isfile(os.path.join(ROOT, 'Make.config')):
      raise unittest.SkipTest('Make.config is absent')
    archive = 'overlay-%s.tgz' % config.frontend_subdir()
    result = run(['make', '-C', ROOT, '-n', 'overlay-archive'])
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertIn('make -C curry interfaces', result.stdout)
    self.assertIn("find tests curry/lib -type f -path '*/.curry/*%s/*'"
                  % config.frontend_subdir(), result.stdout)
    for kind in ['fcy', 'fint', 'icurry', 'icy', 'json.z']:
      self.assertIn("-name '*.%s'" % kind, result.stdout)
    for flag in ['--sort=name', '--owner=0', '--group=0', '--numeric-owner', '--mtime=']:
      self.assertIn(flag, result.stdout)
    self.assertIn('gzip -n > ' + archive, result.stdout)
    result = run(['make', '-C', ROOT, '-n', 'overlay'])
    self.assertEqual(result.returncode, 0, result.stdout)
    if os.path.isfile(os.path.join(ROOT, archive)):
      self.assertIn("tar xvzf %s --wildcards 'tests/*'" % archive, result.stdout)
      # The extraction is followed by the prune and the interface copies.
      self.assertIn('overlay-prune', result.stdout)
      self.assertLess(
          result.stdout.index('overlay-prune'), result.stdout.index('overlay-interfaces')
        )
    else:
      self.assertNotIn('tar', result.stdout)

  def test_sprite_home_default(self):
    '''
    The package finds its home from its own location when SPRITE_HOME is not
    set, and the extension module finds libcyrt.so without LD_LIBRARY_PATH.
    '''
    home = config.prefix()
    env = dict(ENV, PYTHONPATH=os.path.join(home, 'python'))
    code = 'import curry, os\n' \
           'print(os.environ["SPRITE_HOME"])\n' \
           'print(curry.config.prefix())\n' \
           'import curry.backends.cxx.cyrtbindings\n'
    result = run([sys.executable, '-B', '-c', code], env=env)
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertEqual(result.stdout.split('\n')[:2], [home, home])
    # A SPRITE_HOME that is set wins, and a bad one is still rejected.
    result = run(
        [sys.executable, '-B', '-c', 'import curry']
      , env=dict(env, SPRITE_HOME='/nonexistent')
      )
    self.assertNotEqual(result.returncode, 0)
    self.assertIn('SPRITE_HOME is not a directory', result.stdout)
