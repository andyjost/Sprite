"""Native configuration, runtime facts and the thin developer wrappers."""
import cytest # from ./lib; must be first
from curry import config
from cytest.buildtools import cmake_executable
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwds):
  return subprocess.run(list(map(str, args)), stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT, text=True, timeout=180, **kwds)


class TestCMake(cytest.TestCase):
  def setUp(self):
    self.directory = tempfile.TemporaryDirectory()
    self.addCleanup(self.directory.cleanup)
    self.build = Path(self.directory.name) / 'build'
    self.frontend = config.curry_frontend()
    if not cmake_executable() or not self.frontend:
      self.skipTest('CMake and the staged Curry front end are required')

  def configure(self, *options, build=None, env=None, frontend=True):
    '''Configures a build directory; ``frontend=False`` leaves the choice to CMake.'''
    args = [cmake_executable(), '-S', ROOT, '-B', self.build if build is None else build,
            '-G', 'Ninja', '-DPython_EXECUTABLE=' + sys.executable, '-DWITH_PAKCS=']
    if frontend:
      args.append('-DWITH_CURRY_FRONTEND=' + os.path.realpath(self.frontend))
    return run(*args, *options, env=env)

  def cache(self, name):
    for line in (self.build / 'CMakeCache.txt').read_text().splitlines():
      if line.startswith(name + ':'):
        return line.split('=', 1)[1]
    self.fail('missing cache setting ' + name)

  def test_defaults_and_runtime_facts(self):
    result = self.configure()
    self.assertEqual(result.returncode, 0, result.stdout)
    for name, value in [('JOBS', 'auto'), ('GC', 'wdgc'), ('CMAKE_BUILD_TYPE', 'Release'),
                        ('WITH_CCACHE', ''), ('WITH_PAKCS', ''),
                        ('CURRY2ICURRY_TOOL', 'frontend')]:
      self.assertEqual(self.cache(name), value)
    facts = self.build / 'stage/sysconfig'
    self.assertEqual(len(list(facts.iterdir())), 17)
    for path in facts.iterdir():
      self.assertNotIn(str(self.build), path.read_text())
      self.assertNotIn(str(ROOT), path.read_text())
    for name, value in [('cxx_gc', 'wdgc'),
                        ('default_sprite_cache_file', 'cache.db'),
                        ('enable_icurry_cache', '0'),
                        ('frontend_version', config.frontend_version()),
                        ('frontend_subdir', config.frontend_subdir()),
                        ('intermediate_subdir', config.intermediate_subdir()),
                        ('frontend_flags', config.frontend_flags())]:
      self.assertEqual((facts / name).read_text().strip(), value)
    self.assertEqual((facts / 'cxx_compiler').read_text().strip(), config.cxx_compiler())
    ninja = (self.build / 'build.ninja').read_text()
    self.assertIn('libcurryrt' + config.shared_library_suffix(), ninja)
    self.assertIn('currylib: phony', ninja)
    self.assertIn('_curryrtbindings', ninja)
    self.assertIn('build-package.py', ninja)

  def test_options_and_validation(self):
    result = self.configure('-DJOBS=3', '-DGC=wdgc',
                            '-DCMAKE_BUILD_TYPE=Debug', '-DGC_WRITE_COUNTERS=ON',
                            '-DENABLE_ICURRY_CACHE=ON')
    self.assertEqual(result.returncode, 0, result.stdout)
    facts = self.build / 'stage/sysconfig'
    for name, value in [('cxx_gc', 'wdgc'),
                        ('default_sprite_cache_file', 'cache.db'),
                        ('enable_icurry_cache', '1'),
                        ('cxx_flavor', 'debug'), ('cxx_gc_write_counters', '1')]:
      self.assertEqual((facts / name).read_text().strip(), value)
    for option, message in [('-DJOBS=0', 'positive integer or auto'),
                            ('-DGC=bad', 'GC must be'),
                            ('-DCURRY2ICURRY_TOOL=bad', 'must be frontend or icurry')]:
      result = self.configure('-DJOBS=auto', '-DGC=wdgc',
                              '-DCURRY2ICURRY_TOOL=frontend', option)
      self.assertNotEqual(result.returncode, 0, result.stdout)
      self.assertIn(message, result.stdout)

  def test_frontend_and_optional_route(self):
    for option, message in [('-DWITH_CURRY_FRONTEND=', 'needs the Curry front end'),
                            ('-DCURRY2ICURRY_TOOL=icurry', 'needs WITH_ICURRY'),
                            ('-DWITH_ICURRY=/nonexistent/icurry', 'SPRITE_ICURRY')]:
      result = self.configure(option)
      self.assertNotEqual(result.returncode, 0, result.stdout)
      self.assertIn(message, result.stdout)
      # Remove the failed cache setting before the next case.
      shutil.rmtree(self.build)
    fake = Path(self.directory.name) / 'frontend'
    fake.write_text('#!/bin/sh\necho 1.0.0\n')
    fake.chmod(0o755)
    result = self.configure('-DWITH_CURRY_FRONTEND=' + str(fake))
    self.assertNotEqual(result.returncode, 0, result.stdout)
    self.assertIn('Expected Curry front end 2.0.0', result.stdout)

  def test_release_pairs(self):
    """Each accepted front end selects its matching release and macro."""
    frontend = Path(self.directory.name) / 'frontend'
    pakcs = Path(self.directory.name) / 'pakcs'
    for version, release, macro in [('2.0.0', '3.4.1', '304'),
                                    ('3.1.0', '3.10.0', '310')]:
      with self.subTest(frontend=version):
        frontend.write_text('#!/bin/sh\necho ' + version + '\n')
        frontend.chmod(0o755)
        pakcs.write_text('#!/bin/sh\ncase "$1" in\n'
                         '  --compiler-name) echo pakcs ;;\n'
                         '  --numeric-version) echo ' + release + ' ;;\nesac\n')
        pakcs.chmod(0o755)
        result = self.configure('-DWITH_CURRY_FRONTEND=' + str(frontend),
                                '-DWITH_PAKCS=' + str(pakcs))
        self.assertEqual(result.returncode, 0, result.stdout)
        facts = self.build / 'stage/sysconfig'
        expected = [('frontend_version', version),
                    ('frontend_subdir', 'pakcs-' + release),
                    ('intermediate_subdir', 'sprite-pakcs-' + release),
                    ('frontend_flags', '--extended -D__PAKCS__=' + macro),
                    ('currylib_version', '3.4.0')]
        for name, value in expected:
          self.assertEqual((facts / name).read_text().strip(), value)
        other = '3.10.0' if release == '3.4.1' else '3.4.1'
        pakcs.write_text(pakcs.read_text().replace(release, other))
        result = self.configure('-DWITH_CURRY_FRONTEND=' + str(frontend),
                                '-DWITH_PAKCS=' + str(pakcs))
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('Expected PAKCS ' + release, result.stdout)

  def test_auto_uses_current_pair(self):
    """AUTO ignores a legacy executable beside the current tools."""
    bindir = Path(self.directory.name) / 'current-bin'
    bindir.mkdir()
    for name, version in [('pakcs', '3.10.0'), ('pakcs-frontend', '2.0.0'),
                          ('curry-frontend', '3.1.0')]:
      script = bindir / name
      script.write_text('#!/bin/sh\ncase "$1" in\n'
          '  --compiler-name) echo pakcs ;;\n'
          '  --numeric-version) echo ' + version + ' ;;\nesac\n')
      script.chmod(0o755)
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ['PATH'])
    for name in ('SPRITE_FRONTEND', 'CURRY_FRONTEND', 'PAKCS'):
      env.pop(name, None)
    result = self.configure('-DWITH_PAKCS=AUTO', frontend=False, env=env)
    self.assertEqual(result.returncode, 0, result.stdout)
    facts = self.build / 'stage/sysconfig'
    for name, value in [('frontend_version', '3.1.0'),
                        ('frontend_subdir', 'pakcs-3.10.0'),
                        ('intermediate_subdir', 'sprite-pakcs-3.10.0'),
                        ('currylib_version', '3.4.0')]:
      self.assertEqual((facts / name).read_text().strip(), value)
    ninja = (self.build / 'build.ninja').read_text()
    self.assertIn(str(bindir / 'curry-frontend'), ninja)
    self.assertNotIn(str(bindir / 'pakcs-frontend'), ninja)

  def test_optional_icurry_probe(self):
    """The optional route must translate into the pinned product directory."""
    program = Path(self.directory.name) / 'icurry'
    subdir = '.curry/' + config.frontend_subdir()
    date = '17/10/22' if config.frontend_version() == '3.1.0' else '28/07/21'
    help_command = ('if [ "$1" = --help ]; then\n'
                    '  echo "ICurry Compiler (Version of ' + date + ')"\n'
                    '  exit 0\nfi\n')
    program.write_text('#!/bin/sh\n' + help_command + 'mkdir -p ' + subdir + '\n'
                       'echo sample > ' + subdir + '/sample.icy\n')
    program.chmod(0o755)
    options = ['-DWITH_ICURRY=' + str(program), '-DCURRY2ICURRY_TOOL=icurry']
    result = self.configure(*options)
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertEqual((self.build / 'stage/sysconfig/curry2icurry_tool').read_text().strip(), 'icurry')
    # An old result cannot make a later broken translator pass its probe.
    program.write_text('#!/bin/sh\n' + help_command + 'exit 0\n')
    result = self.configure(*options)
    self.assertNotEqual(result.returncode, 0, result.stdout)
    self.assertIn('failed its translation probe', result.stdout)

  def test_icurry_version_pairs(self):
    """Reject mismatched compilers even if their product directory matches."""
    frontend = Path(self.directory.name) / 'frontend'
    program = Path(self.directory.name) / 'icurry'
    for version, release, expected, date in [
        ('2.0.0', '3.4.1', '3.1.0', '28/07/21'),
        ('3.1.0', '3.10.0', '3.3.0', '17/10/22')]:
      frontend.write_text('#!/bin/sh\necho ' + version + '\n')
      frontend.chmod(0o755)
      for banner in [date, '17/10/22' if date == '28/07/21' else '28/07/21']:
        with self.subTest(frontend=version, banner=banner):
          program.write_text('#!/bin/sh\nif [ "$1" = --help ]; then\n'
              'echo "ICurry Compiler (Version of ' + banner + ')"\nexit 0\nfi\n'
              'mkdir -p .curry/pakcs-' + release + '\n'
              'echo sample > .curry/pakcs-' + release + '/sample.icy\n')
          program.chmod(0o755)
          result = self.configure('-DWITH_CURRY_FRONTEND=' + str(frontend),
                                  '-DWITH_ICURRY=' + str(program))
          if banner == date:
            self.assertEqual(result.returncode, 0, result.stdout)
          else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn('Expected icurry ' + expected, result.stdout)

  def test_ccache_launches_native_compilation(self):
    launcher = Path(self.directory.name) / 'ccache'
    launcher.write_text('#!/bin/sh\nexec "$@"\n')
    launcher.chmod(0o755)
    result = self.configure('-DWITH_CCACHE=' + str(launcher))
    self.assertEqual(result.returncode, 0, result.stdout)
    result = run('ninja', '-C', self.build, '-t', 'commands', 'curryrt')
    self.assertEqual(result.returncode, 0, result.stdout)
    commands = result.stdout.splitlines()
    self.assertTrue(any(str(launcher) in line and ' -c ' in line for line in commands))


  def test_frontend_selection(self):
    '''SPRITE_FRONTEND, CURRY_FRONTEND and an explicit name select the front end.'''
    bindir = Path(self.directory.name) / 'bin'
    bindir.mkdir()
    packaged = bindir / 'curry-frontend'
    override = bindir / 'other-frontend'
    for script in [packaged, override]:
      script.write_text('#!/bin/sh\necho 2.0.0\n')
      script.chmod(0o755)
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ.get('PATH', ''))
    env.pop('SPRITE_FRONTEND', None)
    env.pop('CURRY_FRONTEND', None)
    cases = [
        # The environment decides an AUTO configuration.
        ('SPRITE_FRONTEND', 'other-frontend', [], override)
        # The older variable is the default of the option.
      , ('CURRY_FRONTEND', 'other-frontend', [], override)
        # An explicit name on the command line wins over the environment.
      , ('SPRITE_FRONTEND', 'other-frontend', ['-DWITH_CURRY_FRONTEND=curry-frontend'], packaged)
      ]
    for i, (variable, value, options, expected) in enumerate(cases):
      with self.subTest(variable=variable, options=options):
        build = Path(self.directory.name) / ('build%d' % i)
        case_env = dict(env)
        case_env[variable] = value
        result = self.configure(*options, build=build, env=case_env, frontend=False)
        self.assertEqual(result.returncode, 0, result.stdout)
        ninja = (build / 'build.ninja').read_text()
        other = override if expected is packaged else packaged
        self.assertIn(str(expected.resolve()), ninja)
        self.assertNotIn(str(other.resolve()), ninja)

  def test_frontend_runtime_selection(self):
    '''Environment changes take effect; a missing staged link falls to PATH.'''
    bindir = Path(self.directory.name) / 'runtime'
    bindir.mkdir()
    packaged = bindir / 'curry-frontend'
    packaged.write_text('#!/bin/sh\necho 2.0.0\n')
    packaged.chmod(0o755)
    missing = str(bindir / 'missing')
    # No script beside the interpreter: the lookup falls to PATH.
    interpreter = str(Path(self.directory.name) / 'interpreter' / 'python')
    with mock.patch.dict(os.environ, PATH=str(bindir)), \
         mock.patch.object(sys, 'executable', interpreter):
      os.environ.pop('SPRITE_FRONTEND', None)
      with mock.patch.object(config, 'installed_path', return_value=missing):
        self.assertEqual(config.curry_frontend(), str(packaged))
        os.environ['SPRITE_FRONTEND'] = self.frontend
        self.assertEqual(config.curry_frontend(), self.frontend)
        os.environ['SPRITE_FRONTEND'] = 'missing'
        self.assertIsNone(config.curry_frontend())
        os.environ['SPRITE_FRONTEND'] = ''
        self.assertIsNone(config.curry_frontend())


class TestWrappers(cytest.TestCase):
  def test_stage_order_and_parallelism(self):
    for args, count in [(['JOBS=3'], '3'), (['-j2', 'JOBS=4'], '2'),
                        (['-j', 'JOBS=4'], 'auto')]:
      result = run('make', '-n', '-C', ROOT, 'stage', *args)
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertIn('SPRITE_BUILD_JOBS=' + count, result.stdout)
      self.assertLess(result.stdout.index('cmake -S'), result.stdout.index('cmake --build'))
      self.assertLess(result.stdout.index('cmake --build'), result.stdout.index('cmake --install'))
    result = run('make', '-n', '-C', ROOT, 'default-goal')
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertLess(result.stdout.index('cmake --install'), result.stdout.index('scripts/overlay.py'))

  def test_job_override_keeps_the_configured_count(self):
    """make -jN overrides this build and leaves the CMake setting intact."""
    with tempfile.TemporaryDirectory() as directory:
      directory = Path(directory)
      build = directory / 'build'
      build.mkdir()
      cache = build / 'CMakeCache.txt'
      cache.write_text('JOBS:STRING=3\n')
      cmake = directory / 'cmake'
      cmake.write_text('#!' + sys.executable + '\n' +
          'import json, os, pathlib, sys\n'
          'if "-S" in sys.argv:\n'
          '  for arg in sys.argv:\n'
          '    if arg.startswith("-DJOBS="):\n'
          '      pathlib.Path(sys.argv[sys.argv.index("-B")+1], "CMakeCache.txt").write_text("JOBS:STRING="+arg.split("=",1)[1]+"\\n")\n'
          'elif "--build" in sys.argv:\n'
          '  print("BUILD_JOBS="+os.environ.get("SPRITE_BUILD_JOBS", ""))\n')
      cmake.chmod(0o755)
      def stage(*args, configured='3'):
        result = run('make', '-s', '-C', ROOT, 'stage', 'CMAKE=' + str(cmake),
                     'BUILD_DIR=' + str(build), *args)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(cache.read_text(), 'JOBS:STRING=' + configured + '\n')
        return result.stdout
      self.assertIn('BUILD_JOBS=2', stage('-j2'))
      self.assertIn('BUILD_JOBS=3', stage())
      self.assertIn('BUILD_JOBS=1', stage('JOBS=1'))
      self.assertIn('BUILD_JOBS=4', stage('CMAKE_ARGS=-DJOBS=4', configured='4'))
      self.assertIn('BUILD_JOBS=2', stage('-j2', configured='4'))
      self.assertIn('BUILD_JOBS=4', stage(configured='4'))

  def test_worktree_settings(self):
    result = run('bash', '-n', ROOT / 'scripts/new-worktree.sh')
    self.assertEqual(result.returncode, 0, result.stdout)
    with tempfile.TemporaryDirectory() as directory:
      cache = Path(directory) / 'cache'
      cache.write_text('JOBS:STRING=3\nWITH_CCACHE:FILEPATH=/tools/ccache\n'
                       'CMAKE_HOME_DIRECTORY:INTERNAL=/old/tree\n')
      result = run(sys.executable, ROOT / 'scripts/build-settings.py', cache)
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertEqual(result.stdout.splitlines(), ['-DJOBS=3', '-DWITH_CCACHE=/tools/ccache'])

  def test_runtime_compiler_alias(self):
    """A ccache compiler alias retains its basename behind tools/cxx."""
    spec = importlib.util.spec_from_file_location('sprite_build_package',
        ROOT / 'scripts/build-package.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      launcher = root / 'ccache'
      launcher.write_text('#!/bin/sh\nprintf "%s\\n" "$0" "$@"\n')
      launcher.chmod(0o755)
      alias = root / 'c++'
      alias.symlink_to(launcher)
      module.compiler_tool(root / 'prefix', str(alias))
      result = run(root / 'prefix/tools/cxx', '-c', 'module.cpp')
      self.assertEqual(result.returncode, 0, result.stdout)
      self.assertEqual(result.stdout.splitlines(), [str(alias), '-c', 'module.cpp'])
      self.assertEqual(launcher.read_text(), '#!/bin/sh\nprintf "%s\\n" "$0" "$@"\n')

  def test_compiler_discovery_respects_staged_install(self):
    """Missing tools/cxx still disables compilation in a traditional prefix."""
    with mock.patch.object(config, 'installed_path', return_value='/nonexistent/compiler'), \
         mock.patch.object(config.shutil, 'which', return_value='/compiler/g++'), \
         mock.patch.object(config, '__file__', '/package/curry/config.py'):
      with mock.patch.object(config, 'prefix', return_value='/stage'):
        self.assertIsNone(config.cxx_tool(cached=[]))
      with mock.patch.object(config, 'prefix', return_value='/package/curry/_sprite'):
        self.assertEqual(config.cxx_tool(cached=[]), '/compiler/g++')

  def test_packaged_tool_discovery(self):
    """Wheel launches use their interpreter's scripts and frontend override."""
    with tempfile.TemporaryDirectory() as directory:
      directory = Path(directory)
      make = directory / 'sprite-make'
      frontend = directory / 'frontend'
      beside = directory / 'curry-frontend'
      for path in [make, frontend, beside]:
        path.write_text('#!/bin/sh\nexit 0\n')
        path.chmod(0o755)
      with mock.patch.object(config, 'installed_path', return_value='/nonexistent/tool'), \
           mock.patch.object(sys, 'executable', str(directory / 'python')), \
           mock.patch.dict(os.environ, PATH='', SPRITE_FRONTEND=str(frontend)):
        self.assertEqual(config.sprite_make(cached=[]), str(make))
        self.assertEqual(config.curry_frontend(), str(frontend))
        # The console script of curry-frontend beside the interpreter serves
        # a virtual environment that is not activated; PATH is empty here.
        del os.environ['SPRITE_FRONTEND']
        self.assertEqual(config.curry_frontend(), str(beside))

  def test_prerequisite_diagnostic(self):
    env = dict(os.environ, PATH='')
    result = run(sys.executable, ROOT / 'scripts/check-prereqs.py', '--with-curry-frontend=/nonexistent/frontend', env=env)
    self.assertEqual(result.returncode, 1, result.stdout)
    for name in ['cmake', 'ninja', 'C++ compiler', 'Curry front end']:
      self.assertIn(name + ': MISSING', result.stdout)
    self.assertIn('sqlite3: available', result.stdout)
    self.assertNotIn('Boost', result.stdout)
    self.assertFalse((ROOT / 'configure').exists())
