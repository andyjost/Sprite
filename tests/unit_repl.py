import cytest # from ./lib; must be first
from curry import config
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile


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
        self.assertTrue(program.stat().st_mode & 0o111)
        result = subprocess.run([str(program), '--', 'one', '-q', 'two words'],
            text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
            'other main\n' if expression else 'one\n-q\ntwo words\n')

  def test_entrypoints(self):
    commands = [[config.installed_path('bin', 'sprite')],
        [sys.executable, '-m', 'curry'], [config.sprite_exec()]]
    for command in commands:
      result = subprocess.run(cytest.tool_command(command + [':set', 'v0', ':eval', 'True', ':quit']),
          text=True, capture_output=True, timeout=120)
      self.assertEqual((result.returncode, result.stdout, result.stderr),
          (0, 'True\n', ''))

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
