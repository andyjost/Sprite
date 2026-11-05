import cytest # from ./lib; must be first
from curry import config
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import runpy
from unittest import mock


class TestREPLArguments(cytest.TestCase):
  def test_initial_program_name(self):
    code = """import curry
from curry.tools.repl.repl import REPL
repl = REPL([])
assert repl.module.__name__ == 'Prelude'
E = curry.import_('System.Environment')
assert curry.eval(E.getProgName).one() == 'Prelude'
assert curry.eval(E.getArgs).one() == []
"""
    result = subprocess.run([sys.executable, '-c', code],
        text=True, capture_output=True)
    self.assertEqual(result.returncode, 0, result.stderr)

  def test_environment_through_eval(self):
    with tempfile.TemporaryDirectory() as directory:
      source = Path(directory) / 'REPLArguments.curry'
      source.write_text('module REPLArguments where\nimport System.Environment\n'
          'args :: IO [String]\nargs = getArgs\nname :: IO String\nname = getProgName\n')
      commands = ':load %s\n:eval args\n:eval name\n:quit\n' % source
      result = subprocess.run(cytest.tool_command([config.sprite_exec()]), input=commands,
          text=True, capture_output=True)
      self.assertEqual(result.returncode, 0, result.stderr)
      self.assertIn('> []', result.stdout)
      self.assertIn('> "REPLArguments"', result.stdout)

  def run_sprite(self, *args, cwd=None):
    return subprocess.run([sys.executable, '-m', 'curry.tools.repl', *args],
        cwd=cwd, text=True, capture_output=True, timeout=120)

  def test_version_probe(self):
    result = self.run_sprite('--compiler-name', '--numeric-version', '--base-version')
    self.assertEqual(result.returncode, 0, result.stderr)
    name, version, base = result.stdout.splitlines()
    self.assertEqual(name, 'sprite')
    self.assertRegex(version, r'^\d+\.\d+\.\d+$')
    self.assertEqual(base, '3.4.0')
    for option, expected in zip(('--compiler-name', '--numeric-version', '--base-version'),
        (name, version, base)):
      self.assertEqual(self.run_sprite(option).stdout, expected + '\n')

  def test_version_probes_with_startup_options(self):
    for args in [('--nocypm', '--compiler-name'),
        ('--compiler-name', '--noreadline', '--numeric-version', '-q',
         '--base-version')]:
      result = self.run_sprite(*args)
      self.assertEqual(result.returncode, 0, result.stderr)
      self.assertEqual(result.stdout.splitlines()[0], 'sprite')
      self.assertEqual(len(result.stdout.splitlines()),
          sum(arg.startswith(('--compiler', '--numeric', '--base')) for arg in args))

  def test_saved_program_moves_with_dependencies_and_name(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      source, binary, run = (root / name for name in ('source', 'bin', 'run'))
      for path in (source, binary, run):
        path.mkdir()
      (source / 'Helper.curry').write_text(
          'module Helper where\nanswer :: Int\nanswer = 42\n')
      (source / 'Main.curry').write_text(
          'module Main where\nimport Helper\nimport System.Environment\n'
          'main :: IO ()\nmain = print answer >> (getProgName >>= putStrLn)\n')
      for expression in ([], ['main >> putStrLn "expression"']):
        result = self.run_sprite(':set', 'path', str(source),
            ':load', 'Main', ':save', *expression,
            ':quit', cwd=source)
        self.assertEqual(result.returncode, 0, result.stderr)
        program = binary / 'installed-main'
        shutil.move(str(source / 'Main'), program)
        hidden = root / 'hidden'
        source.rename(hidden)
        try:
          env = dict(os.environ)
          env.pop('CURRYPATH', None)
          result = subprocess.run([str(program)], cwd=run, env=env,
              text=True, capture_output=True, timeout=120)
          self.assertEqual(result.returncode, 0, result.stderr)
          self.assertEqual(result.stdout, '42\ninstalled-main\n' +
              ('expression\n' if expression else ''))
        finally:
          hidden.rename(source)

  def test_quiet_batch_options(self):
    for verbosity in range(5):
      result = self.run_sprite('--nocypm', '--noreadline', '-q',
          ':set', 'v%d' % verbosity, ':set', '-time', ':set', 'parser', '-Wnone',
          ':eval', '1 + 2 :: Int', ':quit')
      self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '3\n', ''))

  def test_batch_statuses(self):
    for expression, status in [('True', 0), ('failed :: Bool', 2),
        ('error "test error" :: Bool', 1)]:
      result = self.run_sprite(':eval', expression, ':quit')
      self.assertEqual(result.returncode, status, result.stderr)
    for args in [('--unknown-option',), (':set', 'unknown', 'True', ':quit'),
        (':set', 'v5', ':quit'), (':set', 'parser', '-unknown', ':quit')]:
      result = self.run_sprite(*args)
      self.assertEqual(result.returncode, 1)
      self.assertIn('ERROR:', result.stderr)

  def test_batch_without_quit_has_no_prompt(self):
    result = self.run_sprite(':eval', 'True')
    self.assertEqual((result.returncode, result.stdout), (0, 'True\n'))

  def test_program_arguments(self):
    result = self.run_sprite(':load', 'System.Environment', ':eval', 'getArgs',
        ':quit', '--', 'one', '-q', ':quit', 'two words')
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(result.stdout, '["one","-q",":quit","two words"]\n')

  def test_save_executable(self):
    with tempfile.TemporaryDirectory() as directory:
      source = Path(directory) / 'SavedArguments.curry'
      source.write_text('module SavedArguments where\nimport System.Environment\n'
          'main :: IO ()\nmain = getArgs >>= mapM_ putStrLn\n')
      for expression in ([], ['putStrLn "other main"']):
        result = self.run_sprite(':load', str(source), ':save', *expression,
            ':quit', cwd=directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        program = Path(directory) / 'SavedArguments'
        if os.name == 'nt':
          self.assertEqual(program.read_bytes()[:2], b'MZ')
        else:
          self.assertTrue(program.stat().st_mode & 0o111)
        result = subprocess.run([str(program), '--', 'one', '-q', 'two words'],
            text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
            'other main\n' if expression else 'one\n-q\ntwo words\n')
        arguments = ['--keep', '--verbose=4', '-t', '-g', 'main', 'two words']
        result = subprocess.run([str(program), *arguments],
            text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'other main\n' if expression else
                         '\n'.join(arguments) + '\n')

  def test_load_local_basename_with_explicit_package_path(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      dependencies = root / 'dependencies'
      dependencies.mkdir()
      (root / 'Nested').mkdir()
      (root / 'LocalDependency.curry').write_text(
          'module LocalDependency where\nvalue :: Int\nvalue = 42\n')
      (root / 'Nested/Consumer.curry').write_text(
          'module Nested.Consumer where\nimport qualified LocalDependency\n'
          'value :: Int\nvalue = LocalDependency.value\n')
      (root / 'LocalDriver.curry').write_text(
          'module LocalDriver where\nimport qualified Nested.Consumer\n'
          'value :: Int\nvalue = Nested.Consumer.value\n')
      result = subprocess.run([sys.executable, '-m', 'curry.tools.repl',
          '--nocypm', ':set', 'path', str(dependencies),
          ':load', 'LocalDriver', ':eval', 'value', ':quit'], cwd=root,
          env=dict(os.environ, CURRYPATH=str(dependencies)),
          text=True, capture_output=True, timeout=120)
      self.assertEqual((result.returncode, result.stdout, result.stderr),
                       (0, '42\n', ''))

  def test_entrypoints(self):
    commands = [[config.installed_path('bin', 'sprite')],
        [sys.executable, '-m', 'curry'], [config.sprite_exec()]]
    for command in commands:
      result = subprocess.run(cytest.tool_command(command + [':set', 'v0', ':eval', 'True', ':quit']),
          text=True, capture_output=True, timeout=120)
      self.assertEqual((result.returncode, result.stdout, result.stderr),
          (0, 'True\n', ''))

  @cytest.posix_only('executes external shebang commands')
  def test_private_cpm_launcher_selects_sprite_and_avoids_itself(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      for name in ('bin', 'tools', 'fallback', 'python/curry'):
        (root / name).mkdir(parents=True, exist_ok=True)
      launcher = root / 'bin/cypm'
      shutil.copyfile(config.installed_path('bin', 'cypm'), launcher)
      launcher.chmod(0o755)
      (root / 'python/curry/__init__.py').write_text('')
      (root / 'python/curry/config.py').write_text(
          'from pathlib import Path\n'
          'def installed_path(*parts):\n'
          '  return str(Path(__file__).resolve().parents[2].joinpath(*parts))\n')
      (root / 'tools/pakcs').write_text('configured tool\n')
      for name in ('tools', 'fallback'):
        tool = root / name / 'cypm'
        tool.write_text('#!' + sys.executable + '\nimport sys\n'
                        'print(' + repr(name) + ')\nprint("\\n".join(sys.argv[1:]))\n')
        tool.chmod(0o755)
      for selected in ('tools', 'fallback'):
        result = subprocess.run([str(launcher), 'test'], text=True,
            capture_output=True, timeout=120,
            env=dict(os.environ, PATH=os.pathsep.join([
                str(launcher.parent), str(root / 'fallback'), os.environ['PATH']])))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
            (0, selected + '\n-d\nCURRYBIN=' + str(root / 'bin/curry') + '\ntest\n', ''))
        if selected == 'tools':
          (root / 'tools/cypm').unlink()

  def test_private_cpm_launcher_selection_without_executing_scripts(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      for name in ('bin', 'tools', 'fallback'):
        (root / name).mkdir()
      launcher = root / 'bin/cypm'
      shutil.copyfile(config.installed_path('bin', 'cypm'), launcher)
      (root / 'tools/pakcs').touch()
      for name in ('tools', 'fallback'):
        (root / name / 'cypm').touch()
      for selected in ('tools', 'fallback'):
        with mock.patch.object(config, 'installed_path', side_effect=lambda *p: str(root.joinpath(*p))), \
             mock.patch.object(os, 'get_exec_path', return_value=[str(root / 'bin'), str(root / 'fallback')]), \
             mock.patch.object(os, 'access', return_value=True), \
             mock.patch.object(os, 'execv', side_effect=RuntimeError('selected')) as execute, \
             mock.patch.dict(os.environ), mock.patch.object(sys, 'path', sys.path[:]), \
             mock.patch.object(sys, 'argv', [str(launcher), 'test']):
          os.environ.pop('SPRITE_CPM_FORWARDED', None)
          with self.assertRaisesRegex(RuntimeError, 'selected'):
            runpy.run_path(str(launcher), run_name='__main__')
          command, arguments = execute.call_args.args
          self.assertEqual(Path(command), (root / selected / 'cypm').resolve())
          self.assertEqual(arguments[1:], ['-d', 'CURRYBIN=' + str(root / 'bin/curry'), 'test'])
          self.assertEqual(os.environ['SPRITE_CPM_FORWARDED'], '1')
        if selected == 'tools':
          (root / 'tools/cypm').unlink()

  @cytest.posix_only('executes two external shebang launchers')
  def test_two_private_cpm_launchers_refuse_forwarding_loop(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      launchers = []
      for name in ('first', 'second'):
        prefix = root / name
        (prefix / 'bin').mkdir(parents=True)
        (prefix / 'python/curry').mkdir(parents=True)
        (prefix / 'python/curry/__init__.py').write_text('')
        (prefix / 'python/curry/config.py').write_text(
            'def installed_path(*parts): return "missing-pakcs"\n')
        launcher = prefix / 'bin/cypm'
        shutil.copyfile(config.installed_path('bin', 'cypm'), launcher)
        launcher.chmod(0o755)
        launchers.append(launcher)
      environment = dict(os.environ, PATH=os.pathsep.join(
          [str(p.parent) for p in launchers] + [os.environ['PATH']]))
      environment.pop('SPRITE_CPM_FORWARDED', None)
      result = subprocess.run([sys.executable, str(launchers[0]), 'test'],
          env=environment, text=True, capture_output=True, timeout=10)
      self.assertNotEqual(result.returncode, 0)
      self.assertIn('Stock CPM is missing', result.stderr)

  def test_search_path_and_runtime_settings(self):
    with tempfile.TemporaryDirectory(prefix='repl path ') as directory:
      source = Path(directory) / 'PathGoal.curry'
      source.write_text('module PathGoal where\nvalue :: Int\nvalue = 42\n')
      result = self.run_sprite(':set', 'path', directory, ':set', 'rts', '-T',
          ':load', 'PathGoal', ':eval', 'value', ':quit')
      self.assertEqual((result.returncode, result.stdout, result.stderr),
          (0, '42\n', ''))
    result = self.run_sprite(':set', 'args', 'one "two words"',
        ':load', 'System.Environment', ':eval', 'getArgs', ':quit')
    self.assertEqual((result.returncode, result.stdout, result.stderr),
        (0, '["one","two words"]\n', ''))

  def test_script_program_arguments_stay_opaque(self):
    with tempfile.TemporaryDirectory() as directory:
      source = Path(directory) / 'OpaqueArguments.curry'
      source.write_text('module OpaqueArguments where\nimport System.Environment\n'
          'main :: IO ()\nmain = getArgs >>= mapM_ putStrLn\n')
      result = subprocess.run(cytest.tool_command([config.sprite_exec(), str(source), '--',
          ':quit', '--numeric-version']), text=True, capture_output=True, timeout=120)
      self.assertEqual((result.returncode, result.stdout, result.stderr),
          (0, ':quit\n--numeric-version\n', ''))

  def test_empty_runtime_arguments_clear_previous_values(self):
    result = self.run_sprite(':load', 'System.Environment',
        ':set', 'args', 'previous', ':eval', 'getArgs',
        ':set', 'args', ':eval', 'getArgs', ':quit')
    self.assertEqual((result.returncode, result.stdout, result.stderr),
        (0, '["previous"]\n[]\n', ''))

  def test_startup_settings_read_commands_and_add_import_from_stdin(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      (root / 'LocalModel.curry').write_text(
          'module LocalModel where\nvalue :: Int\nvalue = 42\n')
      (root / 'ModelWriter.curry').write_text(
          'module ModelWriter where\nwriteModel :: String -> Int -> IO ()\n'
          'writeModel path value = writeFile path (show value)\n')
      result = subprocess.run([sys.executable, '-m', 'curry.tools.repl',
          '--nocypm', ':set', 'v0'], cwd=root, text=True, capture_output=True,
          input=':load LocalModel\n:add ModelWriter\n:set jit off\n'
                ':eval writeModel "result.txt" value\n:quit\n', timeout=120)
      self.assertEqual(result.returncode, 0, result.stderr)
      self.assertEqual((root / 'result.txt').read_text(), '42')
