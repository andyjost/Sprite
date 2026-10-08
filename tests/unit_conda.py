import cytest # from ./lib; must be first
from curry import config, exceptions
from curry.utility.binding import binding, del_
from unittest import mock
import curry, hashlib, json, os, re, shutil, struct, subprocess, sys
import tempfile, unittest

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

def heredoc(script, tag):
  '''The text of the here-document ``tag`` of a shell script.'''
  m = re.search(r"<<'?%s'?\n(.*?)\n%s\n" % (tag, tag), script, re.S)
  assert m is not None, tag
  return m.group(1)

def launcher_text(name):
  '''
  The launcher ``name`` as build.sh writes it: the here-document with the
  name filled in and the escaped dollar signs restored.
  '''
  text = heredoc(readfile(RECIPE, 'build.sh'), 'LAUNCHER_EOF')
  return text.replace('$name', name).replace('\\$', '$') + '\n'

def elf_interpreter(path):
  '''The dynamic loader an ELF64 program names (PT_INTERP), or None.'''
  with open(path, 'rb') as stream:
    header = stream.read(64)
    if header[:4] != b'\x7fELF' or header[4] != 2:
      return None
    order = '<' if header[5] == 1 else '>'
    phoff, = struct.unpack_from(order + 'Q', header, 0x20)
    phentsize, phnum = struct.unpack_from(order + 'HH', header, 0x36)
    for i in range(phnum):
      stream.seek(phoff + i * phentsize)
      p_type, _, p_offset, _, _, p_filesz = struct.unpack_from(
          order + 'IIQQQQ', stream.read(56), 0
        )
      if p_type == 3:
        stream.seek(p_offset)
        return stream.read(p_filesz).rstrip(b'\0').decode()
  return None

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
    # The runtime needs no Boost (the dependency cleanup of 2026-10-07).
    self.assertNotIn('libboost', meta)
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
    # The prebuild step compiles with the compiler of the build.
    self.assertIn('--with-cxx-postinstall="$CXX"', script)
    # The precompiled header of the build compiler goes to a cache directory
    # in the build tree, and the package holds none.
    self.assertIn('export XDG_CACHE_HOME="$SRC_DIR/cache"', script)
    self.assertIn('test ! -e "$SPRITE_HOME/include/cyrt/cyrt.hpp.gch"', script)
    # The launchers and the wrapper resolve their own location, so a link
    # to a launcher from another directory works.
    self.assertEqual(script.count('$(readlink -f "$0")'), 1)
    self.assertEqual(script.count('\\$(readlink -f "\\$0")'), 1)
    # The version is the VERSION file of the repository.
    self.assertIn('load_file_regex(load_file="../../VERSION"', meta)
    self.assertNotIn('set version = "', meta)
    # The file holds one version string; the regex of the recipe reads it
    # as conda render would.  The literal is not pinned here: a version
    # bump must not fail this test.
    version = readfile(ROOT, 'VERSION').strip()
    self.assertRegex(version, r'^\d[\w.]*$')
    pattern = re.search(r'regex_pattern="([^"]+)"', meta).group(1)
    self.assertEqual(re.search(pattern, readfile(ROOT, 'VERSION')).group(1), version)
    # The tests of the package check the writes: no header in the tree, no
    # prefix in a generated file, and the resolved source of the Prelude.
    self.assertIn('test ! -e "$PREFIX/opt/sprite/include/cyrt/cyrt.hpp.gch"', meta)
    self.assertIn('test -d "${XDG_CACHE_HOME:-$HOME/.cache}/sprite/pch"', meta)
    self.assertIn(
        "grep -rlF \"$PREFIX\" \"$PREFIX/opt/sprite/curry\" --include='*.py' --include='*.cpp'"
      , meta
      )
    self.assertIn("os.path.join(curry.config.prefix(), 'curry', 'Prelude.curry')", meta)
    self.assertIn('ln -s ../../../bin/pakcs-frontend "$tools/curry-frontend"', script)
    self.assertIn('SPRITE_CXX', script)
    # No Boost variable and no include flag for it in the build.
    self.assertNotIn('-isystem', script)
    self.assertNotIn('boost', script.lower())
    # conda relocates the compiled library modules at install time.
    self.assertIn('detect_binary_files_with_prefix: true', meta)
    # The C++ backend is the default of the package.
    self.assertIn('--with-default-backend=cxx', script)
    # Each backend is tested through the launcher and through the module:
    # the default backend without a flag, the Python backend by flag; the
    # compiler of the environment through sprite-make, which writes the
    # object and its stamp.  No test names backend:cxx.
    self.assertIn('      sprite-exec Smoke.curry | grep -x 42', meta)
    self.assertIn('      python -m curry Smoke.curry | grep -x 42', meta)
    self.assertIn('SPRITE_INTERPRETER_FLAGS=backend:py sprite-exec Smoke.curry', meta)
    self.assertIn(
        'SPRITE_INTERPRETER_FLAGS=backend:py python -m curry Smoke.curry', meta
      )
    self.assertNotIn('backend:cxx', meta)
    self.assertIn('sprite-make --so Smoke.curry &&', meta)
    self.assertEqual(meta.count('test -s .curry/sprite-pakcs-3.4.1/Smoke.so &&'), 1)
    self.assertEqual(meta.count('test -s .curry/sprite-pakcs-3.4.1/Smoke.so.abi'), 1)
    self.assertEqual(meta.count('test -s .curry/sprite-pakcs-3.4.1/Smoke.py'), 1)
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
      , 'LICENSE', 'Nothing here is published', 'build-packages.sh'
      , 'XDG_CACHE_HOME', 'has_prefix', 'ld_interpreter_path', 'sysroot'
      , 'before publication'
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
      self.assertIn('The Curry front end is not configured.', result.stdout)
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
    file under the prefix of the wrapper.  The wrapper adds no flag.
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
      args = ['-c', 'x.cpp']  # the arguments of the call, as they are
      def compiler(**env):
        result = run([wrapper, '-c', 'x.cpp'], env=dict(ENV, **env))
        self.assertEqual(result.returncode, 0, result.stdout)
        return result.stdout.split()
      # No variable: the compiler of the environment.
      self.assertEqual(compiler(), ['inside-default'] + args)
      # SPRITE_CXX wins.
      self.assertEqual(compiler(SPRITE_CXX=outside, CXX=other), ['outside'] + args)
      # CXX counts when it names a file under the prefix, by path or by name.
      self.assertEqual(compiler(CXX=other), ['inside-other'] + args)
      self.assertEqual(
          compiler(CXX='other-c++', PATH=bindir + ':' + ENV['PATH'])
        , ['inside-other'] + args
        )
      # A CXX outside the prefix, a name with flags, or a missing file does
      # not.
      self.assertEqual(compiler(CXX=outside), ['inside-default'] + args)
      self.assertEqual(
          compiler(CXX='g++', PATH=tmpdir + ':' + ENV['PATH'])
        , ['inside-default'] + args
        )
      self.assertEqual(compiler(CXX='g++ -std=c++17'), ['inside-default'] + args)
      self.assertEqual(
          compiler(CXX=os.path.join(bindir, 'missing-c++')), ['inside-default'] + args
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
      # With the front end, icurry is recorded and is the route requested.
      icurry = self.fake_tool(tmpdir, 'icurry', 'icurry')
      result, text = self.configure(
          tmpdir, '--with-pakcs=', '--with-curry-frontend=' + frontend
        , '--with-icurry=' + icurry, '--curry2icurry', 'icurry'
        )
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertEqual(make_config_value(text, 'CURRY_FRONTEND'), frontend)
      self.assertEqual(make_config_value(text, 'ICURRY_EXECUTABLE'), icurry)
      self.assertEqual(make_config_value(text, 'CURRY2ICURRY_TOOL'), 'icurry')
    # icurry alone is not a route: both routes run the front end (the icurry
    # route rewrites its FlatCurry file before icurry reads it).  A fresh
    # directory: no Make.config of an earlier run is left to read.
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      icurry = self.fake_tool(tmpdir, 'icurry', 'icurry')
      result, text = self.configure(
          tmpdir, '--with-pakcs=', '--with-curry-frontend='
        , '--with-icurry=' + icurry
        )
      self.assertNotEqual(result.returncode, 0)
      self.assertIn('Both routes from Curry to ICurry run it', result.stdout)
      self.assertIsNone(text)

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
    make overlay extracts the test products, and lists them under V=1 alone;
    make overlay-archive packs the five product kinds with fixed metadata and
    the library interfaces.
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
      # The extraction names no member: the list of about six thousand would
      # fill the log of every CI job.  V=1 lists them.
      self.assertIn("tar xzf %s -m --wildcards 'tests/*'" % archive, result.stdout)
      self.assertNotIn('tar xvzf', result.stdout)
      verbose = run(['make', '-C', ROOT, '-n', 'overlay', 'V=1'])
      self.assertEqual(verbose.returncode, 0, verbose.stdout)
      self.assertIn("tar xvzf %s -m --wildcards 'tests/*'" % archive, verbose.stdout)
      # The extraction is followed by the prune and the interface copies.
      self.assertIn('overlay-prune', result.stdout)
      self.assertLess(
          result.stdout.index('overlay-prune'), result.stdout.index('overlay-interfaces')
        )
    else:
      self.assertNotIn('tar', result.stdout)

  def test_default_goal_order(self):
    '''
    A plain make stages first and extracts the overlay archive after the
    stage, in the order of the CI jobs: a product extracted before the stage
    is older than the interfaces of the installed library, and the front end
    would compile its module again at its first use.
    '''
    if not os.path.isfile(os.path.join(ROOT, 'Make.config')):
      raise unittest.SkipTest('Make.config is absent')
    result = run(['make', '-C', ROOT, '-n', 'default-goal'])
    self.assertEqual(result.returncode, 0, result.stdout)
    lines = result.stdout.split('\n')
    def index(goal):
      found = [
          i for i, line in enumerate(lines)
            if re.fullmatch(r'\S*make %s' % goal, line)
        ]
      self.assertEqual(len(found), 1, (goal, found))
      return found[0]
    self.assertLess(lines.index('git submodule update'), index('stage'))
    self.assertLess(index('stage'), index('overlay'))

  def test_overlay_in_a_shallow_clone(self):
    '''
    make overlay in a shallow clone extracts the products, prunes nothing
    and warns: the history ends before the commit that packed the archive,
    and the warning names fetch-depth 0.  The build files of this tree are
    copied into the clone, so the test sees the Makefile of the working
    tree.  One run: the copies of the interfaces take most of its time.
    '''
    if not os.path.isfile(os.path.join(ROOT, 'Make.config')):
      raise unittest.SkipTest('Make.config is absent')
    archive = 'overlay-%s.tgz' % config.frontend_subdir()
    if not os.path.isfile(os.path.join(ROOT, archive)):
      raise unittest.SkipTest('%s is absent' % archive)
    git = shutil.which('git', path=ENV['PATH'])
    if git is None:
      raise unittest.SkipTest('git is absent')
    inside = run([git, '-C', ROOT, 'rev-parse', '--is-inside-work-tree'])
    if inside.returncode != 0 or inside.stdout.strip() != 'true':
      raise unittest.SkipTest('not a git work tree')
    with tempfile.TemporaryDirectory() as tmpdir:
      clone = os.path.join(tmpdir, 'clone')
      result = run([git, 'clone', '--quiet', '--depth', '1', 'file://' + ROOT, clone])
      self.assertEqual(result.returncode, 0, result.stdout)
      for name in ['Makefile', 'Make.include', 'Make.rules', 'Make.validate', 'Make.config']:
        shutil.copy(os.path.join(ROOT, name), clone)
      result = run(['make', '-C', clone, 'overlay'])
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertIn('overlay-prune: WARNING: this is a shallow clone', result.stdout)
      self.assertIn('fetch-depth 0', result.stdout)
      # No member is listed, and the products are in place.
      self.assertNotRegex(result.stdout, r'(?m)^tests/')
      self.assertLess(len(result.stdout.split('\n')), 20)
      product = os.path.join(
          clone, 'tests', 'data', 'curry', 'smap', '.curry', config.frontend_subdir()
        , 'poker_four_of_a_kind.fcy'
        )
      self.assertTrue(os.path.isfile(product), product)

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

class TestBuildScript(cytest.TestCase):
  '''
  conda/build-packages.sh builds the two packages from an export of a
  commit, so that an uncommitted file never ships.  These tests run its dry
  run and its export; conda is not needed.
  '''
  SCRIPT = os.path.join(CONDA, 'build-packages.sh')

  def script(self, *args, **env):
    return run([self.SCRIPT] + list(args), env=dict(ENV, **env))

  def need_git(self):
    '''The plan and the export read the commit; skip outside a checkout.'''
    if run(['git', '-C', ROOT, 'rev-parse', 'HEAD']).returncode != 0:
      raise unittest.SkipTest('not a git checkout')

  def test_help_and_errors(self):
    result = self.script('--help')
    self.assertEqual(result.returncode, 0, result.stdout)
    for option in [
        '--build-root DIR', '--channel DIR', '--conda PATH', '--rev REV'
      , '--overlay PATH', '--jobs N', '--pakcs-archive FILE'
      , '--memory-limit GB', '--timeout SEC', '--skip-frontend'
      , '--export-only', '--dry-run'
      ]:
      self.assertIn(option, result.stdout)
    result = self.script('--dry-run')
    self.assertNotEqual(result.returncode, 0)
    self.assertIn('--build-root is required', result.stdout)
    result = self.script('--build-root', ENV['TMPDIR'], '--bogus')
    self.assertNotEqual(result.returncode, 0)
    self.assertIn('unknown option --bogus', result.stdout)

  def test_dry_run(self):
    '''
    The plan: the export of HEAD and of the pybind11 submodule, the source
    cache entry of the PAKCS archive under the name conda-build uses, the
    scrubbed environment, the limits, and the two conda builds with the
    local channel first.  The values of the passed variables stay out of
    the plan: a proxy variable can hold a credential.
    '''
    self.need_git()
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      archive = os.path.join(tmpdir, 'pakcs-3.4.1-amd64-Linux.tar.gz')
      result = self.script(
          '--build-root', tmpdir, '--dry-run', '--pakcs-archive', archive
        , '--memory-limit', '16', '--jobs', '3', '--timeout', '1234'
        , '--conda', '/opt/conda/bin/conda', '--overlay', 'conda'
        , HTTP_PROXY='http://user:secret-token@proxy.example:3128'
        , CONDA_PKGS_DIRS=os.path.join(tmpdir, 'pkgs')
        )
      self.assertEqual(result.returncode, 0, result.stdout)
      out = result.stdout
      self.assertFalse(os.path.exists(os.path.join(tmpdir, 'src')))
      self.assertIn('git -C %s archive --format=tar HEAD | tar -x -C ' % ROOT, out)
      self.assertIn('/extern/pybind11 archive --format=tar ', out)
      self.assertIn('%% cp -a %s/conda ' % ROOT, out)
      sha256 = re.search(
          r'sha256: ([0-9a-f]{64})', readfile(FRONTEND_RECIPE, 'meta.yaml')
        ).group(1)
      self.assertIn(
          'src_cache/pakcs-3.4.1-amd64-Linux_%s.tar.gz' % sha256[:10], out
        )
      self.assertIn('env -i PATH=', out)
      # The precompiled header of the test step goes under the build root,
      # not under the home directory of the builder.
      self.assertIn('CPU_COUNT=3 XDG_CACHE_HOME=%s/cache [' % tmpdir, out)
      self.assertIn('HTTP_PROXY', out)
      self.assertIn('CONDA_PKGS_DIRS', out)
      self.assertNotIn('secret-token', out)
      self.assertIn(
          'prlimit --as=%d timeout 1234 /opt/conda/bin/conda build' % (16 << 30), out
        )
      builds = [line for line in out.splitlines() if 'conda build' in line]
      self.assertEqual(len(builds), 2)
      self.assertIn('/conda/curry-frontend --croot %s/bld' % tmpdir, builds[0])
      self.assertIn('/conda/recipe --croot %s/bld' % tmpdir, builds[1])
      for line in builds:
        self.assertIn('--output-folder %s/channel' % tmpdir, line)
        self.assertIn(
            '--override-channels -c file://%s/channel -c conda-forge' % tmpdir, line
          )
        self.assertIn('--no-anaconda-upload', line)
      # --skip-frontend drops the first build; --channel moves the channel.
      result = self.script(
          '--build-root', tmpdir, '--dry-run', '--skip-frontend'
        , '--channel', os.path.join(tmpdir, 'out')
        )
      self.assertEqual(result.returncode, 0, result.stdout)
      builds = [line for line in result.stdout.splitlines() if 'conda build' in line]
      self.assertEqual(len(builds), 1)
      self.assertIn('/conda/recipe ', builds[0])
      self.assertIn('--output-folder %s/out' % tmpdir, builds[0])
      self.assertIn('timeout 3600 conda build', builds[0])
      self.assertNotIn('prlimit', builds[0])

  def test_overlay_paths(self):
    '''
    An overlay path is normalized, and a path that leaves the repository or
    names it is refused: "conda/.." would otherwise replace the whole export
    with the working tree, and ".." the whole src directory of the build
    root.
    '''
    self.need_git()
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      def plan(path):
        return self.script(
            '--build-root', tmpdir, '--dry-run', '--skip-frontend'
          , '--overlay', path
          )
      for path in ['conda/..', '..', '.', '', 'conda/../..', 'tests/../..']:
        result = plan(path)
        self.assertNotEqual(result.returncode, 0, path)
        self.assertIn('leaves the repository or names it', result.stdout, path)
        # Nothing is planned after the export.
        self.assertNotIn('rm -rf', result.stdout.split('tar -x -C')[-1], path)
      result = plan('/etc/passwd')
      self.assertNotEqual(result.returncode, 0)
      self.assertIn('a path relative to the repository is needed', result.stdout)
      result = plan('no/such/file')
      self.assertNotEqual(result.returncode, 0)
      self.assertIn('no such file in the working tree', result.stdout)
      # A path with . and .. components names the file it resolves to.
      result = plan('tests/../conda/./recipe/build.sh')
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertIn('%% cp -a %s/conda/recipe/build.sh ' % ROOT, result.stdout)
      self.assertNotIn('/./', result.stdout)
      self.assertNotIn('/../', result.stdout)

  def test_export(self):
    '''
    The export holds the tracked files of HEAD and the pybind11 headers,
    and nothing of the working tree that is not committed, unless an
    overlay names it.
    '''
    self.need_git()
    pybind11 = os.path.join(ROOT, 'extern', 'pybind11', 'include', 'pybind11', 'pybind11.h')
    if not os.path.isfile(pybind11):
      raise unittest.SkipTest('the pybind11 submodule is absent')
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      result = self.script(
          '--build-root', tmpdir, '--export-only', '--overlay', 'tests/unit_conda.py'
        )
      self.assertEqual(result.returncode, 0, result.stdout)
      exports = os.listdir(os.path.join(tmpdir, 'src'))
      self.assertEqual(len(exports), 1)
      self.assertRegex(exports[0], r'^sprite-[0-9a-f]{7,}$')
      src = os.path.join(tmpdir, 'src', exports[0])
      for name in [
          'VERSION', 'configure', 'conda/recipe/meta.yaml', 'conda/recipe/build.sh'
        , 'conda/curry-frontend/meta.yaml'
        , 'extern/pybind11/include/pybind11/pybind11.h'
        , 'src/python/config.py', 'curry/lib/Prelude.curry', 'tests/unit_conda.py'
        ]:
        self.assertTrue(os.path.isfile(os.path.join(src, name)), name)
      # The overlay is the file of the working tree.
      self.assertEqual(
          readfile(src, 'tests', 'unit_conda.py')
        , readfile(ROOT, 'tests', 'unit_conda.py')
        )
      # Nothing of the working tree that git does not track: the staging
      # links, the configuration, the repository itself.
      for name in ['.git', 'install', 'object-root', 'Make.config', 'configure.log']:
        self.assertFalse(os.path.lexists(os.path.join(src, name)), name)
      self.assertFalse(os.path.exists(os.path.join(tmpdir, 'bld')))

class TestPackageRules(cytest.TestCase):
  '''
  The rules of the code that make the package install clean: nothing is
  written into the package at run time, and the generated files of the
  library name no path of the build machine.
  '''

  def test_pch_root_rule(self):
    '''
    The precompiled header lives beside the installed headers, unless the
    include directory cannot be written or the installation lies in a conda
    environment; then it goes to a cache directory of the user, one
    directory per installation.  SPRITE_CXX_PCH_ROOT wins over the rule.
    '''
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      tmpdir = os.path.realpath(tmpdir)
      plain = os.path.join(tmpdir, 'plain')
      env = os.path.join(tmpdir, 'env')
      packaged = os.path.join(env, 'opt', 'sprite')
      cache = os.path.join(tmpdir, 'cache')
      os.makedirs(os.path.join(plain, 'include'))
      os.makedirs(os.path.join(env, 'conda-meta'))
      os.makedirs(os.path.join(packaged, 'include'))
      with binding(os.environ, 'SPRITE_CXX_PCH_ROOT', del_), \
           binding(os.environ, 'XDG_CACHE_HOME', cache):
        self.assertEqual(config.user_cache_dir(), os.path.join(cache, 'sprite'))
        with binding(os.environ, 'SPRITE_HOME', plain):
          self.assertFalse(config.in_conda_prefix(os.path.join(plain, 'include')))
          self.assertEqual(config.cxx_pch_root(), os.path.join(plain, 'include'))
          # An include directory that cannot be written.
          with mock.patch.object(os, 'access', lambda path, mode: False):
            self.assertEqual(config.cxx_pch_root(), config.cxx_pch_cache_dir())
        with binding(os.environ, 'SPRITE_HOME', packaged):
          self.assertTrue(config.in_conda_prefix(os.path.join(packaged, 'include')))
          self.assertTrue(config.in_conda_prefix(env))
          key = hashlib.sha256(packaged.encode('utf-8')).hexdigest()[:16]
          self.assertEqual(config.installation_key(), key)
          self.assertEqual(
              config.cxx_pch_root(), os.path.join(cache, 'sprite', 'pch', key)
            )
          # Two installations get two directories.
          with binding(os.environ, 'SPRITE_HOME', plain):
            self.assertNotEqual(config.installation_key(), key)
          # The variable wins; the empty value disables the header.
          with binding(os.environ, 'SPRITE_CXX_PCH_ROOT', tmpdir):
            self.assertEqual(config.cxx_pch_root(), tmpdir)
          with binding(os.environ, 'SPRITE_CXX_PCH_ROOT', ''):
            self.assertIsNone(config.cxx_pch_root())
      # Without XDG_CACHE_HOME the cache is under the home directory.
      for value in [del_, '']:
        with binding(os.environ, 'XDG_CACHE_HOME', value), \
             binding(os.environ, 'HOME', tmpdir):
          self.assertEqual(
              config.user_cache_dir(), os.path.join(tmpdir, '.cache', 'sprite')
            )

  def test_compile_into_read_only_directory(self):
    '''
    The compile step of the C++ backend names the cause when the directory
    of its object cannot be written, instead of the error of the first
    write.  The case: a read-only installation of the package, whose
    shipped library objects are stale under it (open question 2 of
    conda/README.md), so that sprite-make --so of any program compiles the
    Prelude again and fails.
    '''
    if curry.flags['backend'] != 'cxx':
      raise unittest.SkipTest('the C++ toolchain')
    if os.geteuid() == 0:
      raise unittest.SkipTest('root writes everywhere')
    from curry.backends.cxx import toolchain
    from curry.backends.cxx import compiler as cxxcompiler
    step = toolchain.Cpp2So(curry.getInterpreter())
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      cppfile = os.path.join(tmpdir, 'M.cpp')
      sofile = os.path.join(tmpdir, 'M.so')
      with open(cppfile, 'w') as ostream:
        ostream.write('// FORMAT: %d\n// IMPORTS: \n' % cxxcompiler.FORMAT_VERSION)
      def compile_fails(state):
        os.chmod(tmpdir, 0o555)
        try:
          with self.assertRaises(exceptions.CompileError) as context:
            step(cppfile, config.currypath())
        finally:
          os.chmod(tmpdir, 0o755)
        message = str(context.exception)
        self.assertIn('the directory %r cannot be written' % tmpdir, message)
        self.assertIn(state, message)
        self.assertIn('sprite-exec', message)
        self.assertFalse(os.path.exists(sofile) and os.path.getsize(sofile) > 1)
      # No object; an object without a stamp; a stale object.
      compile_fails('no object exists there')
      open(sofile, 'w').close()
      compile_fails('the object there has no ABI stamp')
      with open(step.stampfile(sofile), 'w') as ostream:
        ostream.write('0123456789abcdef\n')
      compile_fails('names another installation or runtime')
      # The stamp of a stale object is left as it is: nothing was written.
      self.assertEqual(step.read_stamp(sofile), '0123456789abcdef')

  def test_relocated_installation_loads_its_objects(self):
    '''
    A copy of the installation at another path, its stamps rewritten as a
    package manager rewrites the text files that hold the prefix: a process
    under the copy loads the library from the objects of the copy, compiles
    nothing, and maps no object of the original.  The objects name their
    imports by SONAME (format 13 of the generated code), so the copy of
    Data.List finds the copy of the Prelude; before, the NEEDED entries
    named the objects of the original by absolute path.  The precompiled
    header, the bytecode caches and the static archive stay out of the
    copy; the links of the tree are copied as links.
    '''
    if curry.flags['backend'] != 'cxx':
      raise unittest.SkipTest('the objects belong to the C++ backend')
    from curry.backends.cxx import toolchain
    from curry.objects.handle import getHandle
    original = toolchain.installation_path()
    subdir = os.path.join('curry', '.curry', config.intermediate_subdir())
    prelude_so = os.path.join(original, subdir, 'Prelude.so')
    step = toolchain.Cpp2So(curry.getInterpreter())
    if not os.path.isfile(prelude_so) or not step.stamp_is_current(prelude_so):
      raise unittest.SkipTest('the installed library has no current object')
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      copy = os.path.join(os.path.realpath(tmpdir), 'env', 'opt', 'sprite')
      shutil.copytree(
          original, copy, symlinks=True
        , ignore=shutil.ignore_patterns('*.gch', '__pycache__', 'libcyrt.a')
        )
      # The rewrite of the manager: the prefix of the environment in place
      # of the prefix of the build, in every stamp.
      rewritten = 0
      for dirpath, dirnames, filenames in os.walk(os.path.join(copy, 'curry')):
        for filename in filenames:
          if not filename.endswith('.so.abi'):
            continue
          path = os.path.join(dirpath, filename)
          lines = readfile(path).splitlines()
          if len(lines) == 2 and lines[1] == original:
            with open(path, 'w') as ostream:
              ostream.write('%s\n%s\n' % (lines[0], copy))
            rewritten += 1
      self.assertGreater(rewritten, 0)
      code = '\n'.join([
          'import curry, json, os'
        , 'from curry.objects.handle import getHandle'
        , 'from curry.toolchain import _system'
        , 'commands = []'
        , 'pexec = _system.pexec'
        , 'def counting_pexec(cmd, *args, **kwds):'
        , '  commands.append(cmd)'
        , '  return pexec(cmd, *args, **kwds)'
        , '_system.pexec = counting_pexec'
        , 'from curry.lib import Prelude'
        , 'L = curry.import_("Data.List")'
        , 'value = list(curry.eval(curry.expr(L.last, [1, 2, 3]), converter="topython"))'
        , 'with open("/proc/self/maps") as stream:'
        , '  maps = stream.read()'
        , 'print(json.dumps({'
        , '    "commands": commands, "value": value'
        , '  , "package": os.path.realpath(curry.__file__)'
        , '  , "prefix": curry.config.prefix()'
        , '  , "prelude_file": Prelude.__file__'
        , '  , "prelude_object": getHandle(Prelude).sofilename'
        , '  , "list_object": getHandle(L).sofilename'
        , '  , "compile": curry.stats()["compile"]'
        , '  , "original_mapped": %r in maps' % (original + os.sep)
        , '  , "copy_mapped": %r in maps' % (copy + os.sep)
        , '  }))'
        ])
      def snapshot():
        files = {}
        for dirpath, dirnames, filenames in os.walk(os.path.join(copy, 'curry')):
          for filename in filenames:
            path = os.path.join(dirpath, filename)
            files[path] = os.lstat(path).st_mtime_ns
        return files
      before = snapshot()
      # The environment of the copy, as the launcher of the copy would set
      # it (bin/sprite-invoke puts python/ and lib/ of its installation
      # first): the entries of the original leave.
      def relocated(variable, subdir):
        entries = [
            entry for entry in os.environ.get(variable, '').split(os.pathsep)
                  if entry and not entry.startswith(original + os.sep)
          ]
        return os.pathsep.join([os.path.join(copy, subdir)] + entries)
      with mock.patch.dict(os.environ, {
          'SPRITE_HOME': copy
        , 'PYTHONPATH': relocated('PYTHONPATH', 'python')
        , 'LD_LIBRARY_PATH': relocated('LD_LIBRARY_PATH', 'lib')
        , 'SPRITE_INTERPRETER_FLAGS': 'backend:cxx'
        }):
        proc = cytest.run_in_subprocess(code, timeout=300)
      self.assertEqual(proc.returncode, 0, proc.stderr)
      result = json.loads(proc.stdout.strip().splitlines()[-1])
      self.assertEqual(result['commands'], [])
      self.assertEqual(result['value'], [3])
      self.assertEqual(result['prefix'], copy)
      self.assertEqual(result['prelude_file'], os.path.join(copy, 'curry', 'Prelude.curry'))
      self.assertEqual(result['prelude_object'], os.path.join(copy, subdir, 'Prelude.so'))
      self.assertEqual(
          result['list_object']
        , os.path.join(copy, 'curry', 'Data', '.curry', config.intermediate_subdir(), 'List.so')
        )
      self.assertEqual(result['compile'], 0)
      self.assertTrue(result['copy_mapped'])
      self.assertFalse(result['original_mapped'], proc.stdout)
      # Nothing was written into the copy by the run.
      self.assertEqual(snapshot(), before)

  def test_launcher(self):
    '''
    A launcher of the package sets SPRITE_HOME from its own real location,
    so a link to it from another directory works, and runs the script of
    the same name in the tree.
    '''
    text = launcher_text('sprite-exec')
    self.assertNotIn('$name', text)
    self.assertNotIn('\\$', text)
    with tempfile.TemporaryDirectory(dir=ENV['TMPDIR']) as tmpdir:
      tmpdir = os.path.realpath(tmpdir)
      prefix = os.path.join(tmpdir, 'env')
      bindir = os.path.join(prefix, 'bin')
      home = os.path.join(prefix, 'opt', 'sprite')
      os.makedirs(bindir)
      os.makedirs(os.path.join(home, 'bin'))
      launcher = os.path.join(bindir, 'sprite-exec')
      with open(launcher, 'w') as ostream:
        ostream.write(text)
      os.chmod(launcher, 0o755)
      target = os.path.join(home, 'bin', 'sprite-exec')
      with open(target, 'w') as ostream:
        ostream.write('#!/bin/sh\necho "$SPRITE_HOME" "$@"\n')
      os.chmod(target, 0o755)
      elsewhere = os.path.join(tmpdir, 'elsewhere')
      os.makedirs(elsewhere)
      link = os.path.join(elsewhere, 'sprite-exec')
      os.symlink(launcher, link)
      for program in [launcher, link]:
        for env in [ENV, dict(ENV, SPRITE_HOME='/nonexistent')]:
          result = run([program, 'Smoke.curry', '-x'], env=env, cwd=elsewhere)
          self.assertEqual(result.returncode, 0, result.stdout)
          self.assertEqual(result.stdout, '%s Smoke.curry -x\n' % home)

  def test_ld_interpreter_path(self):
    '''
    The sysconfig value ld_interpreter_path is the dynamic loader of this
    machine: the one the Python of the installation names, and a file that
    exists.  The C++ backend writes it into the shared object of a program
    with a main goal (open question 13 of conda/README.md).
    '''
    path = config.ld_interpreter_path()
    self.assertTrue(os.path.isabs(path), path)
    self.assertTrue(os.path.exists(path), path)
    python = os.path.realpath(sys.executable)
    interpreter = elf_interpreter(python)
    if interpreter is None:
      raise unittest.SkipTest('%s is not an ELF64 program' % python)
    self.assertEqual(interpreter, path)

  def test_generated_files_name_no_prefix(self):
    '''
    A generated file of a library module names its source relative to the
    installation, and the module object resolves the name, so the package
    holds no path of the build machine and its bytecode caches stay valid
    after a relocation.  On the C++ backend a module outside the
    installation names its source relative to its object (format 13), and
    the loader resolves the name from the object; on the Python backend it
    keeps its path.
    '''
    from curry.toolchain import _filenames
    from curry.lib import Prelude
    home = config.prefix()
    relative = os.path.join('curry', 'Prelude.curry')
    source = os.path.join(home, relative)
    self.assertEqual(_filenames.installed_relpath(source), relative)
    self.assertEqual(
        _filenames.installed_relpath(os.path.join(os.path.realpath(home), relative))
      , relative
      )
    self.assertIsNone(
        _filenames.installed_relpath(os.path.join(os.sep, 'nonexistent', 'M.curry'))
      )
    self.assertIsNone(_filenames.installed_relpath(None))
    self.assertIsNone(_filenames.installed_relpath(home + '-other' + os.sep + 'M.curry'))
    # The module object names the absolute path, so its interface is found.
    self.assertEqual(os.path.realpath(Prelude.__file__), os.path.realpath(source))
    self.assertEqual(str(curry.typeof(Prelude.length)), '[a] -> Int')
    # The generated file of the library carries the relative name, and no
    # path of the installation.
    text = curry.save(Prelude, module_main=False)
    if 'IModule.fromBOM' in text:
      self.assertIn(
          "filename=curry.config.installed_path('curry/Prelude.curry')", text
        )
    else:
      self.assertIn('/*filename */ "curry/Prelude.curry"', text)
    self.assertNotIn(home, text)
    self.assertNotIn(os.path.realpath(home), text)
    subdir = os.path.join(home, 'curry', '.curry', config.intermediate_subdir())
    for name in ['Prelude.py', 'Prelude.cpp']:
      path = os.path.join(subdir, name)
      if os.path.isfile(path):
        product = readfile(path)
        self.assertNotIn(home, product)
        self.assertNotIn(os.path.realpath(home), product)
    # A module outside the installation: one compiled from text, whose
    # source lies in a temporary directory.  The module object names the
    # absolute path.  The generated C++ names the source relative to the
    # object, "../../CondaProbe.curry", and holds no path of the machine;
    # the generated Python keeps the absolute path.
    Probe = curry.compile('main :: Int\nmain = 1\n', modulename='CondaProbe')
    self.assertTrue(os.path.isabs(Probe.__file__), Probe.__file__)
    self.assertIsNone(_filenames.installed_relpath(Probe.__file__))
    saved = curry.save(Probe, module_main=False)
    if curry.flags['backend'] == 'cxx':
      self.assertIn('/*filename */ "../../CondaProbe.curry"', saved)
      # The path of the source is gone from the record; the metadata of a
      # module from text keeps its temporary directory (all.tmpd).
      self.assertNotIn(Probe.__file__, saved)
    else:
      self.assertIn(Probe.__file__, saved)
