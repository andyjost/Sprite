"""Private CurryCheck launchers and test-only package compatibility."""
import cytest # from ./lib; must be first
from curry import config
import importlib.util
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import tomllib
import json
import runpy
import os
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent


class TestPrivateLaunchers(cytest.TestCase):
  def test_overlay(self):
    spec = importlib.util.spec_from_file_location('overlay', ROOT / 'scripts/cpm-test-overlay.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as work:
      source, target = Path(work) / 'index', Path(work) / 'overlay'
      source.mkdir()
      for name, compilers in [('pakcs', {'pakcs': '>= 3.0.0'}),
                              ('other', {'kics2': '>= 3.0.0'}), ('empty', {})]:
        directory = source / name
        directory.mkdir()
        (directory / 'package.json').write_text(json.dumps({'compilerCompatibility': compilers}))
      (source / 'REPOSITORY_CACHE_SMALL').write_text('stale')
      self.assertEqual(module.overlay(source, target), 1)
      self.assertEqual(json.loads((target / 'pakcs/package.json').read_text())[
          'compilerCompatibility'], {'pakcs': '>= 3.0.0', 'sprite': '>= 0.9.0'})
      self.assertNotIn('sprite', (source / 'pakcs/package.json').read_text())
      self.assertEqual((target / 'other/package.json').read_bytes(),
                       (source / 'other/package.json').read_bytes())
      self.assertFalse((target / 'REPOSITORY_CACHE_SMALL').exists())
      with mock.patch.dict(os.environ, HOME=work):
        self.assertEqual(module.patch_downloads([source]), 1)
      self.assertIn('sprite', (source / 'pakcs/package.json').read_text())
      self.assertEqual(module.patch(source), 0)
      with mock.patch.dict(os.environ, HOME=str(target)):
        with self.assertRaises(ValueError):
          self.assertEqual(module.patch_downloads([source]), 1)

  def test_overlay_database(self):
    spec = importlib.util.spec_from_file_location('overlay', ROOT / 'scripts/cpm-test-overlay.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as work:
      source, target = Path(work) / 'index', Path(work) / 'overlay'
      source.mkdir()
      original = r'[(CompilerCompatibility \"pakcs\" [[(VGte (3,0,0,Nothing))]])]'
      other = r'[(CompilerCompatibility \"kics2\" [[(VGte (0,0,0,Nothing))]])]'
      with sqlite3.connect(source / 'REPOSITORY_CACHE.db') as database:
        database.execute('CREATE TABLE IndexEntry ('
            'Key INTEGER PRIMARY KEY, Name string NOT NULL, Version string NOT NULL, '
            'Dependencies string, CompilerCompatibility string, Synopsis string, '
            'Category string, SourceDirs string, ExportedModules string, ExecutableSpec string)')
        database.executemany('INSERT INTO IndexEntry (Key, Name, Version, CompilerCompatibility) '
                             'VALUES (?, ?, ?, ?)',
                             [(1, 'first', '(1,0,0,Nothing)', original),
                              (2, 'second', '(1,0,0,Nothing)', other)])
      for name, compilers in [('first', {'pakcs': '>= 3.0.0'}),
                               ('second', {'kics2': '>= 0.0.0'})]:
        directory = source / name / '1.0.0'
        directory.mkdir(parents=True)
        (directory / 'package.json').write_text(json.dumps({
            'name': name, 'version': '1.0.0', 'compilerCompatibility': compilers}))
      module.overlay(source, target)
      module.patch_cache(target)
      with sqlite3.connect(target / 'REPOSITORY_CACHE.db') as database:
        rows = database.execute('SELECT CompilerCompatibility FROM IndexEntry ORDER BY Key').fetchall()
      self.assertEqual(rows, [(original[:-1] + ',' +
          r'(CompilerCompatibility \"sprite\" [[(VGte (0,9,0,Nothing))]])]',), (other,)])
      with sqlite3.connect(source / 'REPOSITORY_CACHE.db') as database:
        self.assertEqual(database.execute(
            'SELECT CompilerCompatibility FROM IndexEntry WHERE Key = 1').fetchone(), (original,))
      for label, sql, parameters, message in [
          ('ordinary quotes', 'UPDATE IndexEntry SET CompilerCompatibility = ? WHERE Key = 1',
           (original.replace(chr(92) + '"', '"'),), 'encoding'),
          ('malformed term', 'UPDATE IndexEntry SET CompilerCompatibility = ? WHERE Key = 1',
           (original + 'junk',), 'encoding'),
          ('constraint mismatch', 'UPDATE IndexEntry SET CompilerCompatibility = ? WHERE Key = 1',
           (original.replace('(3,0,0,Nothing)', '(4,0,0,Nothing)'),), 'compatibility mismatch'),
          ('version mismatch', "UPDATE IndexEntry SET Version = '(2,0,0,Nothing)' WHERE Key = 1",
           (), 'package/version mismatch'),
          ('missing row', 'DELETE FROM IndexEntry WHERE Key = 1', (), 'package/version mismatch'),
          ('duplicate row', 'UPDATE IndexEntry SET Name = \'first\' WHERE Key = 2',
           (), 'package/version mismatch'),
          ('schema', 'ALTER TABLE IndexEntry RENAME COLUMN Name TO Other', (), 'schema')]:
        with self.subTest(label=label):
          with sqlite3.connect(source / 'REPOSITORY_CACHE.db') as database:
            database.execute(sql, parameters)
            database.commit()
          try:
            with self.assertRaisesRegex(ValueError, message):
              module.overlay(source, Path(work) / label)
          finally:
            # Restore the source fixture for the next independent case.
            shutil.copy2(target / 'REPOSITORY_CACHE.db', source / 'REPOSITORY_CACHE.db')
            with sqlite3.connect(source / 'REPOSITORY_CACHE.db') as database:
              database.execute('UPDATE IndexEntry SET CompilerCompatibility = ? WHERE Key = 1',
                               (original,))
      with sqlite3.connect(target / 'REPOSITORY_CACHE.db') as database:
        database.execute('UPDATE IndexEntry SET CompilerCompatibility = ? WHERE Key = 1',
            (original[:-1] + ',' + r'(CompilerCompatibility \"sprite\" [])]',))
      with self.assertRaisesRegex(ValueError, 'unexpected Sprite compatibility'):
        module.patch_cache(target)

  def test_ci_guard_only_error(self):
    workflow = (ROOT / '.github/workflows/ci.yml').read_text()
    start = workflow.index('            errors=$(')
    end = workflow.index('\n            echo "::notice::', start)
    check = workflow[start:end]
    guard = ("ERROR: Curry module 'Test.Prop' from 'Prop.curry' conflicts with "
             "the installed library module 'Prop.curry'.; searched curry.path")
    with tempfile.TemporaryDirectory() as home:
      for log, accepted in [
          ('INFO  Compiling...\n' + guard + '\n', True),
          (guard + '\nERROR: another failure\n', False),
          ('ERROR: another failure\n' + guard + '\n', False),
          (guard + '\nCRITICAL another failure\n', False),
          (guard + '\n\x1b[31mERROR: another failure\x1b[0m\n', False),
          (guard + '\nfile.curry:1:1:Error: another failure\n', False),
          (guard + '\nfile.curry:1:1 Error: another failure\n', False),
          (guard + '\nTraceback (most recent call last):\n', False),
          (guard + '\n' + guard + '\n', False),
          ('INFO  Compiling...\n', False)]:
        with self.subTest(log=log):
          (Path(home) / 'currycheck-install.log').write_text(log)
          result = subprocess.run(['bash', '-e', '-c', check],
              env=dict(os.environ, HOME=home), capture_output=True)
          self.assertEqual(result.returncode == 0, accepted)

  @cytest.linux_only('The Ubuntu workflow sampler uses Linux ps options.')
  def test_ci_memory_sampler(self):
    workflow = (ROOT / '.github/workflows/ci.yml').read_text()
    start = workflow.index("          (\n            trap 'exit 0' TERM")
    end = workflow.index('\n          exit "$status"', start)
    script = workflow[start:end] + '\nexit "$status"\n'
    with tempfile.TemporaryDirectory() as work:
      work = Path(work)
      log = work / '.cache/runner/cxx/unit_cpm_repl.py.log'
      log.parent.mkdir(parents=True)
      log.write_text('test failure details\n')
      runner = work / 'run_tests'
      for status in (0, 7):
        with self.subTest(status=status):
          runner.write_text('#!/bin/sh\nsleep 0.1\nexit ' + str(status) + '\n')
          runner.chmod(0o755)
          result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script],
              cwd=work, capture_output=True, text=True, timeout=15)
          self.assertEqual(result.returncode, status, result.stdout + result.stderr)
          self.assertIn('RSS', result.stdout)
          self.assertEqual('test failure details' in result.stdout.splitlines(), status != 0)

      with self.subTest(early_exit=True):
        trap_end = script.index('\n', script.index('trap stop_sampler EXIT'))
        early_exit = script[:trap_end] + '\nprintf "%s\\n" "$sampler" > sampler.pid\nsleep 0.1\nexit 9\n'
        process = subprocess.Popen(['bash', '-e', '-o', 'pipefail', '-c', early_exit],
            cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, start_new_session=True)
        try:
          # The sampler inherits these pipes, so EOF also bounds its lifetime.
          stdout, stderr = process.communicate(timeout=15)
          self.assertEqual(process.returncode, 9, stdout + stderr)
          sampler = int((work / 'sampler.pid').read_text())
          with self.assertRaises(ProcessLookupError):
            os.kill(sampler, 0)
        finally:
          # Also clean up if a broken EXIT trap leaves the sampler alive.
          try:
            os.killpg(process.pid, signal.SIGKILL)
          except ProcessLookupError:
            pass
          process.communicate()

  def test_survey_classification(self):
    spec = importlib.util.spec_from_file_location('survey', ROOT / 'scripts/cpm-index-run.py')
    survey = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(survey)
    self.assertEqual(survey.property_results('No tests, just compiling'),
                     ('not run', 'not run'))
    self.assertEqual(survey.property_results(
        'p:\n OK, passed 100 tests.\nq: OK\nr failed\nFalsified by first test.'),
        (2, 1))
    self.assertTrue(survey.fits('>= 3.0.0, < 4.0.0'))
    self.assertTrue(survey.fits('^ 3.2.0'))
    self.assertFalse(survey.fits('>= 4.0.0'))
    self.assertEqual(survey.classify('all properties passed', 0), 'pass')
    self.assertEqual(survey.classify('', 124), 'timeout')
    self.assertTrue(survey.classify(
        "Curry module 'Test.Prop' conflicts with the installed library module",
        1).startswith('guard:'))
    self.assertTrue(survey.classify('No tests, just compiling', 0).startswith('Sprite error:'))
    self.assertIn('Expected module for XML, but found FlatCurry.XML',
        survey.classify('ERROR: Error:\n Expected module for XML, but found FlatCurry.XML', 1))
    self.assertEqual(survey.classify('System.X.f: not implemented', 1),
                     'missing external: System.X.f: not implemented')
    self.assertTrue(survey.classify('propSort FAILED', 1).startswith('test failure:'))
    self.assertTrue(survey.classify('Syntax error in M', 1).startswith('front-end error:'))
    self.assertTrue(survey.classify("UI.curry:106:17 Error: Unexpected token `class'",
                                  1).startswith('front-end error:'))
    self.assertTrue(survey.classify('Error: Interface for module AllSolutions not found',
                                  1).startswith('front-end error:'))

  def exercise(self, prefix):
    with tempfile.TemporaryDirectory() as work:
      work = Path(work)
      product = work / '.curry' / config.intermediate_subdir()
      product.mkdir(parents=True)
      for name in ('Main.icy', 'Main.so.abi', 'Main.img', 'Other.icy'):
        (product / name).write_text('fixture')
      frontend_product = work / '.curry/sprite-0.9.0'
      frontend_product.mkdir()
      (frontend_product / 'Main.fcy').write_text('fixture')
      foreign = work / '.curry' / 'pakcs-fixture'
      foreign.mkdir()
      (foreign / 'Main.fcy').write_text('foreign')
      def run(name, *args):
        launcher = prefix / 'bin' / name
        self.assertTrue(launcher.is_file(), launcher)
        env = {k: v for k, v in os.environ.items()
               if k not in ('SPRITE_HOME', 'PYTHONPATH')}
        command = [sys.executable, str(launcher)] if sys.platform == 'win32' else [str(launcher)]
        result = subprocess.run([*command, *args],
            cwd=work, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout
      self.assertEqual(run('curry', '--compiler-name'), 'sprite\n')
      self.assertEqual(run('curry', ':eval', '1+1', ':quit').strip(), '2')
      # frontend-exec derives this private name from curryCompiler.
      self.assertTrue((prefix / 'bin/sprite-frontend').is_file())
      run('cleancurry', 'Main.curry')
      self.assertEqual([p.name for p in product.iterdir()], ['Other.icy'])
      self.assertFalse((frontend_product / 'Main.fcy').exists())
      child = work / 'Parent/.curry' / config.intermediate_subdir() / 'Child.img'
      child.parent.mkdir(parents=True)
      child.write_text('fixture')
      frontchild = frontend_product / 'Parent/Child.fcy'
      frontchild.parent.mkdir(parents=True)
      frontchild.write_text('fixture')
      run('cleancurry', 'Parent.Child')
      self.assertFalse(child.exists())
      self.assertFalse(frontchild.exists())
      run('cleancurry')
      self.assertFalse(product.exists())
      self.assertTrue((foreign / 'Main.fcy').is_file())

  def test_frontend_forwarding(self):
    with mock.patch.object(config, 'curry_frontend', return_value='frontend'), \
         mock.patch.object(config, 'frontend_flags', return_value='--extended -D__PAKCS__=310'), \
         mock.patch.object(sys, 'argv', ['sprite-frontend', '--flat', 'Main']), \
         mock.patch.object(sys, 'path', list(sys.path)), \
         mock.patch('subprocess.call', return_value=7) as call:
      with self.assertRaises(SystemExit) as result:
        runpy.run_path(str(ROOT / 'src/export/bin/sprite-frontend.script'), run_name='__main__')
      self.assertEqual(result.exception.code, 7)
      call.assert_called_once_with(['frontend', '--extended', '-D__PAKCS__=310', '--flat', 'Main'])

  def test_staged_launchers(self):
    self.exercise(Path(config.installed_path()))

  def test_stage_uses_configured_python(self):
    alternate = shutil.which('python3', path=os.defpath)
    if alternate is None or Path(alternate).resolve() == Path(sys.executable).resolve():
      self.skipTest('no different Python is available')
    env = {k: v for k, v in os.environ.items() if k not in ('SPRITE_HOME', 'PYTHONPATH')}
    result = subprocess.run([alternate, config.installed_path('bin', 'curry'),
                             '--compiler-name'], env=env, capture_output=True,
                            text=True, timeout=60)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    self.assertEqual(result.stdout, 'sprite\n')

  def test_wheel_resource_launchers(self):
    # Model the wheel layout with the actual package and its resources. The
    # same launchers must bootstrap without the staged python directory.
    with tempfile.TemporaryDirectory() as work:
      package = Path(work) / 'curry'
      shutil.copytree(ROOT / 'install/python/curry', package, symlinks=True)
      resources = package / '_sprite'
      resources.mkdir(exist_ok=True)
      for name in ('lib', 'sysconfig', 'curry', 'include', 'tools'):
        (resources / name).symlink_to((ROOT / 'install' / name).resolve(), target_is_directory=True)
      (resources / 'bin').mkdir(exist_ok=True)
      for name in ('curry', 'cleancurry', 'sprite-frontend'):
        target = resources / 'bin' / name
        shutil.copy2(ROOT / 'src/export/bin' / (name + '.script'), target)
        target.chmod(0o755)
      self.exercise(resources)
    scripts = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['scripts']
    self.assertNotIn('curry', scripts)
    self.assertNotIn('cleancurry', scripts)
    self.assertNotIn('sprite-frontend', scripts)
