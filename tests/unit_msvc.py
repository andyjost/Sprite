"""Visual Studio discovery and child environments, mocked on every platform."""
import cytest # from ./lib; must be first
import os
import subprocess
import tempfile
import types
import unittest
from unittest import mock
from curry import config
from curry.backends.cxx import msvc, tiered, toolchain
from curry.interpreter import session
from curry.toolchain import _system


class TestDiscovery(unittest.TestCase):
  def setUp(self):
    self.patches = [
        mock.patch.object(msvc, '_result', None),
        mock.patch.object(msvc.sys, 'platform', 'win32'),
        mock.patch.dict(os.environ, {'ProgramFiles(x86)': 'Programs'}, clear=True),
        mock.patch.object(msvc.shutil, 'which', return_value=None),
        mock.patch.object(msvc.os.path, 'exists', return_value=True),
        mock.patch.object(msvc.subprocess, 'run', side_effect=[
            types.SimpleNamespace(stdout='Visual Studio\r\n'),
            types.SimpleNamespace(stdout='Path=compiler-bin\r\nINCLUDE=headers\r\nLIB=libraries\r\nLIBPATH=metadata\r\n')])]
    self.mocks = [self.enterContext(patch) for patch in self.patches]
    self.enterContext(mock.patch.object(msvc, '_lookup_result', None))
    self.run = self.mocks[-1]

  def test_parser(self):
    self.assertEqual(msvc.parse_environment(
        'banner\r\n=C:=drive\r\nPath=bin\r\nINCLUDE=a=b\r\nEMPTY=\r\n'),
        {'PATH': 'bin', 'INCLUDE': 'a=b', 'EMPTY': ''})

  def test_vswhere_capture_and_cache(self):
    with self.assertLogs(msvc.logger, 'INFO') as logs:
      compiler, env = msvc.discover()
      self.assertEqual(msvc.discover(), (compiler, env))
    self.assertEqual(len(logs.records), 1)
    self.assertIn('Visual Studio Visual Studio: environment from vcvars64.bat', logs.output[0])
    self.assertEqual(compiler, os.path.join('Visual Studio', 'VC', 'Tools', 'Llvm', 'x64', 'bin', 'clang-cl.exe'))
    self.assertEqual(env['LIBPATH'], 'metadata')
    self.assertEqual(self.run.call_count, 2)
    self.assertEqual(self.run.call_args_list[0].args[0], [
        os.path.join('Programs', 'Microsoft Visual Studio', 'Installer', 'vswhere.exe'),
        '-latest', '-products', '*', '-requires',
        'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath', '-utf8'])
    self.assertEqual(self.run.call_args_list[0].kwargs['encoding'], 'utf-8')
    rendered = subprocess.list2cmdline(self.run.call_args.args[0])
    script = os.path.join('Visual Studio', 'VC', 'Auxiliary', 'Build', 'vcvars64.bat')
    self.assertIn('call "%s" ' % script, rendered)
    self.assertNotIn('\\"', rendered)
    self.assertEqual(self.run.call_args.kwargs['encoding'], 'utf-16-le')
    self.assertEqual(self.run.call_args.kwargs['errors'], 'replace')
    self.assertEqual(self.run.call_args.kwargs['stderr'], subprocess.STDOUT)
    self.assertEqual(self.run.call_args.kwargs['timeout'], 120)

  def test_initialized_prompt(self):
    os.environ.update(INCLUDE='prompt-headers', VSINSTALLDIR='Prompt Studio')
    self.mocks[3].return_value = 'prompt-clang'
    with self.assertLogs(msvc.logger, 'INFO') as logs:
      self.assertEqual(msvc.discover(), ('prompt-clang', {}))
      self.assertEqual(msvc.environment()['INCLUDE'], 'prompt-headers')
    self.run.assert_not_called()
    self.assertEqual(len(logs.records), 1)
    self.assertIn('Prompt Studio: environment from developer prompt', logs.output[0])

  def test_vsinstalldir_without_initialized_prompt(self):
    os.environ['VSINSTALLDIR'] = 'Prompt Studio'
    self.run.side_effect = [types.SimpleNamespace(stdout='INCLUDE=headers\nLIB=libraries\n')]
    self.assertIsNotNone(msvc.discover()[0])
    self.assertEqual(self.run.call_count, 1)
    self.assertIn('vcvars64.bat', self.run.call_args.args[0][-4])

  def test_path_compiler_with_uninitialized_environment(self):
    self.mocks[3].return_value = 'path-clang'
    self.assertEqual(msvc.discover()[0], 'path-clang')
    self.assertEqual(self.run.call_count, 2)

  def test_captured_path_compiler(self):
    self.mocks[4].side_effect = [False, True]
    self.mocks[3].side_effect = [None, 'captured-clang', 'captured-clang']
    self.assertEqual(msvc.discover()[0], 'captured-clang')
    self.mocks[3].assert_called_with('clang-cl', path='compiler-bin')

  def test_failure_is_cached_and_logged_once(self):
    for failure in (OSError('not installed'), subprocess.CalledProcessError(1, 'cmd')):
      msvc._result = None
      msvc._lookup_result = None
      self.run.reset_mock()
      self.run.side_effect = failure
      with self.assertLogs(msvc.logger, 'INFO') as logs:
        self.assertEqual(msvc.discover(), (None, {}))
        self.assertEqual(msvc.discover(), (None, {}))
      self.assertEqual(len(logs.records), 1)
      self.assertIn('discovery unavailable', logs.output[0])
      self.assertEqual(self.run.call_count, 1)

  def test_missing_studio_compiler_or_environment(self):
    for output, exists in (('', True), ('Visual Studio', False), ('Visual Studio', True)):
      msvc._result = None
      msvc._lookup_result = None
      self.run.side_effect = [types.SimpleNamespace(stdout=output),
                              types.SimpleNamespace(stdout='')]
      self.mocks[4].return_value = exists
      self.assertEqual(msvc.discover(), (None, {}))
    msvc._result = None
    msvc._lookup_result = None
    self.mocks[4].side_effect = [False, True]
    self.run.side_effect = [types.SimpleNamespace(stdout='Visual Studio'),
                            types.SimpleNamespace(stdout='INCLUDE=h\nLIB=l\n')]
    self.assertEqual(msvc.discover(), (None, {}))

  def test_config_discovers_for_wheels_and_stages(self):
    with mock.patch.object(config, 'installed_path', return_value='compiler-record'), \
         mock.patch.object(config, '_is_wheel_install', return_value=True):
      self.mocks[4].return_value = False
      # The compiler record is absent; discovery still has its own files.
      with mock.patch.object(msvc, 'compiler', return_value='discovered-clang'):
        self.assertEqual(config.cxx_tool(cached=[]), 'discovered-clang')
        with mock.patch.object(config, '_is_wheel_install', return_value=False):
          self.assertEqual(config.cxx_tool(cached=[]), 'discovered-clang')
      self.mocks[4].return_value = True
      with mock.patch('builtins.open', mock.mock_open(read_data='staged-clang')), \
           mock.patch.object(msvc, 'compiler') as lookup, \
           mock.patch.object(msvc, 'discover') as capture:
        self.assertEqual(config.cxx_tool(cached=[]), 'staged-clang')
        lookup.assert_not_called()
        capture.assert_not_called()

  def test_wheel_keeps_explicit_and_path_compilers(self):
    with mock.patch.object(config, 'installed_path', return_value='compiler-record'), \
         mock.patch.object(config, '_is_wheel_install', return_value=True), \
         mock.patch.object(msvc, 'compiler', return_value='discovered-clang'):
      self.mocks[4].return_value = False
      os.environ['CXX'] = 'chosen-clang'
      self.mocks[3].side_effect = lambda name: 'chosen-tool' if name == 'chosen-clang' else None
      self.assertEqual(config.cxx_tool(cached=[]), 'chosen-tool')
      del os.environ['CXX']
      self.mocks[3].side_effect = lambda name: 'path-tool' if name == 'clang-cl' else None
      self.assertEqual(config.cxx_tool(cached=[]), 'path-tool')

  def test_wheel_does_not_pick_cl_from_path(self):
    with mock.patch.object(config, 'installed_path', return_value='compiler-record'), \
         mock.patch.object(config, '_is_wheel_install', return_value=True), \
         mock.patch.object(msvc, 'compiler') as lookup:
      self.mocks[4].return_value = False
      self.mocks[3].side_effect = lambda name: 'cl' if name == 'cl' else None
      for discovered in ('discovered-clang', None):
        with self.subTest(discovered=discovered):
          lookup.return_value = discovered
          self.assertEqual(config.cxx_tool(cached=[]), discovered)
      os.environ['CXX'] = 'cl'
      self.assertEqual(config.cxx_tool(cached=[]), 'cl')

  def test_lookup_does_not_capture(self):
    self.assertIsNotNone(msvc.compiler())
    self.assertIsNotNone(msvc.compiler())
    self.assertEqual(self.run.call_count, 1)
    self.assertNotIn('cmd.exe', self.run.call_args.args[0])
    self.assertIn('LIB', msvc.environment())
    self.assertEqual(self.run.call_count, 2)

  def test_x86_prompt_captures_x64(self):
    os.environ.update(INCLUDE='x86-headers', VSCMD_ARG_TGT_ARCH='x86')
    self.assertEqual(msvc.environment()['INCLUDE'], 'headers')
    self.assertEqual(self.run.call_count, 2)

  def test_prompt_without_clang_skips_capture(self):
    os.environ['INCLUDE'] = 'prompt-headers'
    with self.assertLogs(msvc.logger, 'INFO') as logs:
      self.assertEqual(msvc.discover(), (None, {}))
    self.run.assert_not_called()
    self.assertIn('environment from developer prompt', logs.output[0])
    self.assertNotIn('on PATH', logs.output[0])

  def test_capture_keeps_only_changes(self):
    os.environ['LIBPATH'] = 'metadata'
    _, overrides = msvc.discover()
    self.assertNotIn('LIBPATH', overrides)
    del os.environ['LIBPATH']
    self.assertNotIn('LIBPATH', msvc.environment())

  def test_capture_timeout_is_cached(self):
    self.run.side_effect = [types.SimpleNamespace(stdout='Visual Studio'),
                            subprocess.TimeoutExpired('cmd', 120)]
    self.assertEqual(msvc.discover(), (None, {}))
    self.assertEqual(msvc.discover(), (None, {}))
    self.assertEqual(self.run.call_count, 2)

  def test_environment_merge_and_tiered_child(self):
    os.environ.update(KEEP='current', INCLUDE='old')
    msvc._result = ('clang', {'INCLUDE': 'new', 'LIB': 'libraries'})
    env = msvc.environment()
    self.assertEqual(env['KEEP'], 'current')
    self.assertEqual(env['INCLUDE'], 'new')
    self.assertEqual(os.environ['INCLUDE'], 'old')
    interp = types.SimpleNamespace(flags={'debug': False, 'inline_budget': 0})
    envp = tiered._environment(interp)
    self.assertIn('INCLUDE=new', envp)
    self.assertIn('LIB=libraries', envp)
    self.assertIn('KEEP=current', envp)

  def test_non_windows_does_not_discover(self):
    with mock.patch.object(msvc.sys, 'platform', 'linux'):
      self.assertEqual(msvc.environment(), dict(os.environ))
      self.assertEqual(msvc.discover(), (None, {}))
    self.run.assert_not_called()


class TestChildren(unittest.TestCase):
  def test_make_child_inherits_capture(self):
    from curry.tools import make
    with mock.patch.object(msvc, 'environment', return_value={
        'INCLUDE': 'headers', 'LIB': 'libraries', 'PATH': 'compiler-bin'}):
      env = make.child_environment()
    self.assertEqual(env['INCLUDE'], 'headers')
    self.assertEqual(env['LIB'], 'libraries')
    self.assertEqual(env['PATH'], 'compiler-bin')

  def test_pexec_passes_environment_and_currypath(self):
    child = mock.Mock()
    child.communicate.return_value = (b'ok', b'')
    child.wait.return_value = 0
    env = {'INCLUDE': 'headers'}
    with mock.patch.object(_system.sp, 'Popen', return_value=child) as popen, \
         mock.patch.object(_system, '_child_currypath', mock.Mock(get=lambda: 'modules')):
      self.assertEqual(_system.pexec(['compiler'], env=env), 'ok')
    self.assertEqual(popen.call_args.kwargs['env'], {'INCLUDE': 'headers', 'CURRYPATH': 'modules'})
    self.assertEqual(env, {'INCLUDE': 'headers'})

  def test_saved_launcher_uses_compiler_environment(self):
    with tempfile.TemporaryDirectory() as work, \
         mock.patch.object(toolchain.Cpp2So, '_compileCommand', return_value=['clang-cl', '/LD']), \
         mock.patch.object(msvc, 'environment', return_value={'INCLUDE': 'headers'}), \
         mock.patch.object(_system, 'pexec') as pexec:
      session._save_windows_program(None, os.path.join(work, 'program.exe'), 'import base64\n', work)
    pexec.assert_called_once_with(['clang-cl'], env={'INCLUDE': 'headers'})
