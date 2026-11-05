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
import io
from contextlib import closing, redirect_stderr
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
        (directory / 'package.json').write_text(json.dumps({
            'name': name, 'version': '1.0.0', 'compilerCompatibility': compilers}))
      (source / 'REPOSITORY_CACHE_SMALL').write_text('stale')
      self.assertEqual(module.overlay(source, target), 1)
      self.assertEqual(json.loads((target / 'pakcs/package.json').read_text())[
          'compilerCompatibility'], {'pakcs': '>= 3.0.0', 'sprite': '>= 0.9.0'})
      self.assertNotIn('sprite', (source / 'pakcs/package.json').read_text())
      self.assertEqual((target / 'other/package.json').read_bytes(),
                       (source / 'other/package.json').read_bytes())
      self.assertFalse((target / 'REPOSITORY_CACHE_SMALL').exists())
      self.assertFalse((source / 'REPOSITORY_CACHE.db').exists())
      module.validate_cache(target)
      with closing(sqlite3.connect(target / 'REPOSITORY_CACHE.db')) as database, database:
        self.assertEqual(database.execute('SELECT COUNT(*) FROM IndexEntry').fetchone(), (3,))
        self.assertEqual(database.execute('SELECT Dependencies, Category, SourceDirs, '
            'ExportedModules, ExecutableSpec FROM IndexEntry WHERE Name = ?',
            ('pakcs',)).fetchone(), ('[]', '[]', '[]', '[]', 'Nothing'))
      self.assertEqual(module.overlay(source, target), 1)
      module.validate_cache(target)
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
      with closing(sqlite3.connect(source / 'REPOSITORY_CACHE.db')) as database, database:
        database.execute('CREATE TABLE IndexEntry ('
            'Key INTEGER PRIMARY KEY, Name string NOT NULL, Version string NOT NULL, '
            'Dependencies string, CompilerCompatibility string, Synopsis string, '
            'Category string, SourceDirs string, ExportedModules string, ExecutableSpec string)')
        database.executemany('INSERT INTO IndexEntry (Key, Name, Version, CompilerCompatibility) '
                             'VALUES (?, ?, ?, ?)',
                             [(1, 'first', '(1,0,0,Nothing)', original),
                              (2, 'second', '(1,0,0,Nothing)', other)])
        database.execute("UPDATE IndexEntry SET Dependencies = '[]', Synopsis = '', Category = '[]', SourceDirs = '[]', ExportedModules = '[]', ExecutableSpec = 'Nothing'")
      for name, compilers in [('first', {'pakcs': '>= 3.0.0'}),
                               ('second', {'kics2': '>= 0.0.0'})]:
        directory = source / name / '1.0.0'
        directory.mkdir(parents=True)
        (directory / 'package.json').write_text(json.dumps({
            'name': name, 'version': '1.0.0', 'compilerCompatibility': compilers}))
      module.overlay(source, target)
      with closing(sqlite3.connect(target / 'REPOSITORY_CACHE.db')) as database, database:
        rows = database.execute('SELECT CompilerCompatibility FROM IndexEntry ORDER BY Key').fetchall()
      self.assertEqual(rows, [(original[:-1] + ',' +
          r'(CompilerCompatibility \"sprite\" [[(VGte (0,9,0,Nothing))]])]',), (other,)])
      with closing(sqlite3.connect(source / 'REPOSITORY_CACHE.db')) as database, database:
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
          with closing(sqlite3.connect(source / 'REPOSITORY_CACHE.db')) as database, database:
            database.execute(sql, parameters)
            database.commit()
          try:
            with self.assertRaisesRegex(ValueError, message):
              module.overlay(source, Path(work) / label)
          finally:
            # Restore the source fixture for the next independent case.
            shutil.copy2(target / 'REPOSITORY_CACHE.db', source / 'REPOSITORY_CACHE.db')
            with closing(sqlite3.connect(source / 'REPOSITORY_CACHE.db')) as database, database:
              database.execute('UPDATE IndexEntry SET CompilerCompatibility = ? WHERE Key = 1',
                               (original,))

  def test_overlay_builds_database(self):
    spec = importlib.util.spec_from_file_location('overlay', ROOT / 'scripts/cpm-test-overlay.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as work:
      source, target = Path(work) / 'index', Path(work) / 'overlay'
      package = source / 'example/1.2.3'
      package.mkdir(parents=True)
      (package / 'package.json').write_text(json.dumps({
          'name': 'example', 'version': '1.2.3', 'synopsis': 'Example package',
          'dependencies': {'base': '>= 3.0.0, < 4.0.0'},
          'compilerCompatibility': {'pakcs': '>= 3.0.0'},
          'category': ['Test'], 'sourceDirs': ['src'], 'exportedModules': ['Example'],
          'executable': {'name': 'example', 'options': {'pakcs': ':set v0'}}}))
      module.overlay(source, target)
      module.validate_cache(target)
      with closing(sqlite3.connect(target / 'REPOSITORY_CACHE.db')) as database, database:
        row = database.execute('SELECT Name, Version, Dependencies, Synopsis, Category, '
            'SourceDirs, ExportedModules, ExecutableSpec FROM IndexEntry').fetchone()
      self.assertEqual(row, ('example', '(1,2,3,Nothing)',
          r'[(Dependency \"base\" [[(VGte (3,0,0,Nothing)),(VLt (4,0,0,Nothing))]])]',
          'Example package', r'[\"Test\"]', r'[\"src\"]', r'[\"Example\"]',
          r'(Just (PackageExecutable \"example\" \"Main\" [(\"pakcs\",\":set v0\")]))'))
      # SQL values encode a Curry string; term strings add another layer.
      special = 'a "quoted" value\\with a slash'
      self.assertEqual(json.loads('"' + module.sql_string(special) + '"'), special)
      self.assertEqual(json.loads(json.loads('"' + module.string_term(special) + '"')), special)
      before = (target / 'REPOSITORY_CACHE.db').read_bytes()
      shutil.copytree(package, source / 'duplicate/1.2.3')
      with self.assertRaisesRegex(ValueError, 'duplicate repository package/version'):
        module.overlay(source, target)
      self.assertEqual((target / 'REPOSITORY_CACHE.db').read_bytes(), before)

  def test_overlay_preserves_mapped_pairs(self):
    module = runpy.run_path(str(ROOT / 'scripts/cpm-test-overlay.py'))
    with tempfile.TemporaryDirectory() as work:
      root = Path(work)
      (root / 'package.json').write_text(
          '{"name":"example","version":"1.0.0",'
          '"dependencies":{"base":">= 3.0.0","base":"< 4.0.0"},'
          '"compilerCompatibility":{"pakcs":">= 3.0.0","pakcs":"< 4.0.0"},'
          '"executable":{"name":"example","options":{"pakcs":"-O","pakcs":"-v"}}}')
      module['create_cache'](root)
      with closing(sqlite3.connect(root / 'REPOSITORY_CACHE.db')) as connection, connection:
        deps, compilers, executable = connection.execute(
            'SELECT Dependencies, CompilerCompatibility, ExecutableSpec FROM IndexEntry').fetchone()
      self.assertEqual(deps, '[' + ','.join(
          '(Dependency ' + module['string_term']('base') + ' ' +
          module['constraint_term'](value) + ')' for value in ('>= 3.0.0', '< 4.0.0')) + ']')
      self.assertEqual(compilers.count('CompilerCompatibility'), 2)
      self.assertIn('-O', executable)
      self.assertIn('-v', executable)
      # This is also a supplied CPM database: both entries must validate.
      module['validate_cache'](root)
      destination = root.parent / (root.name + '-overlay')
      try:
        module['overlay'](root, destination)
        module['validate_cache'](destination)
        self.assertEqual((destination / 'package.json').read_text().count('"base"'), 2)
      finally:
        shutil.rmtree(destination, ignore_errors=True)

  def test_overlay_carried_fixes(self):
    module = runpy.run_path(str(ROOT / 'scripts/cpm-test-overlay.py'))
    with tempfile.TemporaryDirectory() as work:
      root = Path(work)
      package = root / 'package.json'
      data = {'name': 'example', 'version': '1.0.0',
              'dependencies': {'base': '>= 3.0.0'}, 'synopsis': 'example',
              'category': ['Test'], 'sourceDirs': ['src'],
              'exportedModules': ['Example'], 'executable': {'name': 'example'}}
      package.write_text(json.dumps(data))
      module['create_cache'](root)
      database = root / 'REPOSITORY_CACHE.db'
      before = database.read_bytes()
      self.assertEqual(module['constraint_term']('^ 1.0.0'),
                       '[[(VMajCompatible (1,0,0,Nothing))]]')
      for column in ('Dependencies', 'Synopsis', 'Category', 'SourceDirs',
                     'ExportedModules', 'ExecutableSpec'):
        with self.subTest(column=column):
          with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute('UPDATE IndexEntry SET ' + column + " = 'wrong'")
          with self.assertRaisesRegex(ValueError, 'field mismatch: ' + column):
            module['validate_cache'](root)
          database.write_bytes(before)
      for extra, key, value in (
          ('"synopsis":"kept","synopsis":"lost"', 'synopsis', 'kept'),
          ('"executable":{"name":"kept","name":"lost"}', 'name', {'name': 'kept'})):
        package.write_text('{"name":"example","version":"1.0.0",' + extra + '}')
        warning = io.StringIO()
        with redirect_stderr(warning):
          kept = module['read_package'](package)
        self.assertEqual(kept['synopsis' if key == 'synopsis' else 'executable'], value)
        self.assertEqual(warning.getvalue(),
            'package.json of example-1.0.0: duplicate key %s, the first value kept\n' % key)
        with redirect_stderr(io.StringIO()):
          module['create_cache'](root, replace=True)
          module['validate_cache'](root)
        with closing(sqlite3.connect(database)) as connection, connection:
          row = connection.execute('SELECT Synopsis, ExecutableSpec FROM IndexEntry').fetchone()
        self.assertIn('kept', row[0 if key == 'synopsis' else 1])
        with tempfile.TemporaryDirectory() as destination:
          warning = io.StringIO()
          with redirect_stderr(warning):
            module['overlay'](root, Path(destination) / 'index')
          self.assertEqual(warning.getvalue(),
              'package.json of example-1.0.0: duplicate key %s, the first value kept\n' % key)
      database.write_bytes(before)
      for field in ('synopsis', 'category', 'sourceDirs', 'exportedModules'):
        for control in ('\x00', '\x01', '\x7f'):
          bad = dict(data, **{field: control if field == 'synopsis' else [control]})
          with self.assertRaisesRegex(ValueError, 'control character'):
            module['package_row'](bad)
      self.assertEqual(module['sql_string']('\a\b\f\n\r\t\v'), r'\a\b\f\n\r\t\v')
      # CDBI reads these two escaping layers with Curry read.
      import curry
      for value in ('line\nnext', '\a\b\f\r\t\v', chr(233)):
        expression = 'read "' + module['string_term'](value) + '" :: String'
        self.assertEqual(curry.eval(curry.parse(expression)).one(), value)
      package.write_text(json.dumps(data))
      # Failure during validation must leave the previously usable database intact.
      with mock.patch('sqlite3.connect', side_effect=RuntimeError('injected failure')):
        with self.assertRaisesRegex(RuntimeError, 'injected failure'):
          module['create_cache'](root, replace=True)
      self.assertEqual(database.read_bytes(), before)
      with mock.patch.dict(module['create_cache'].__globals__,
                           validate_cache=mock.Mock(side_effect=ValueError('invalid replacement'))):
        with self.assertRaisesRegex(ValueError, 'invalid replacement'):
          module['create_cache'](root, replace=True)
      self.assertEqual(database.read_bytes(), before)
      self.assertEqual(list(root.glob('.repository-*')), [])
      with mock.patch('os.replace', wraps=os.replace) as publish:
        module['create_cache'](root, replace=True)
      self.assertEqual(publish.call_count, 1)
      module['validate_cache'](root)

  @cytest.posix_only('the shell fragment belongs to the POSIX CI workflow')
  def test_ci_install_requires_success(self):
    workflow = (ROOT / '.github/workflows/ci.yml').read_text()
    start = workflow.index('          timeout 1800 cypm', workflow.index('--packages'))
    end = workflow.index('          timeout 600 cypm', start)
    script = workflow[start:end]
    with tempfile.TemporaryDirectory() as work:
      root = Path(work)
      command = root / 'cypm'
      for status in (0, 1, 7):
        command.write_text('#!/bin/sh\necho install-details\nexit %d\n' % status)
        command.chmod(0o755)
        result = subprocess.run(['bash', '-e', '-c', script], capture_output=True,
            text=True, env=dict(os.environ, HOME=work, GITHUB_WORKSPACE=str(ROOT),
                                PATH=work + os.pathsep + os.environ['PATH']))
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        self.assertIn('install-details', result.stdout)

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
        launcher = prefix / 'curry/bin' / name
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
      self.assertTrue((prefix / 'curry/bin/sprite-frontend').is_file())
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
      call.assert_called_once()
      args = call.call_args.args[0]
      self.assertEqual(args[:4], ['frontend', '--extended', '-D__PAKCS__=310', '-P'])
      self.assertEqual(args[5:-2], ['--flat', 'Main'])
      self.assertEqual(args[-2:], ['-i', args[4]])

  def test_frontend_cross_drive_output(self):
    with tempfile.TemporaryDirectory() as work:
      output = str(Path(work) / 'output')
      def frontend_call(arguments):
        library = Path(arguments[arguments.index('-P') + 1])
        nested = library.joinpath(*Path(output).parts[1:], 'Prelude.fint')
        self.assertTrue(nested.is_file())
        self.assertTrue((library / 'Prelude.fint').is_file())
        return 0
      for options in (['-o', output], ['--outdir=' + output]):
        with self.subTest(options=options), \
             mock.patch.object(config, 'curry_frontend', return_value='frontend'), \
             mock.patch.object(sys, 'argv', ['sprite-frontend', *options, 'Main']), \
             mock.patch.object(sys, 'path', list(sys.path)), \
             mock.patch('os.path.relpath', side_effect=ValueError('different drives')), \
             mock.patch('subprocess.call', side_effect=frontend_call) as call:
          with self.assertRaises(SystemExit):
            runpy.run_path(str(ROOT / 'src/export/bin/sprite-frontend.script'), run_name='__main__')
          self.assertEqual(call.call_args.args[0][-len(options)-3:-2], [*options, 'Main'])

  def test_frontend_library_interfaces(self):
    if config.curry_frontend() is None:
      self.skipTest('Curry front end is absent')
    with tempfile.TemporaryDirectory() as work:
      root = Path(work)
      (root / 'Probe.curry').write_text(
          "module Probe where\nimport Data.Char\nvalue = digitToInt '1'\n")
      result = subprocess.run([sys.executable, str(ROOT / 'src/export/bin/sprite-frontend.script'),
          '--acy', '-o', '.curry/sprite-0.9.0', 'Probe'], cwd=root,
          env=dict(os.environ, LC_ALL='C.UTF-8'), capture_output=True, text=True)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      self.assertTrue((root / '.curry/sprite-0.9.0/Probe.acy').is_file())
      for output in ('a/../out', str(root / 'absolute')):
        with self.subTest(output=output):
          (root / 'a').mkdir(exist_ok=True)
          result = subprocess.run([sys.executable,
              str(ROOT / 'src/export/bin/sprite-frontend.script'),
              '--acy', '-f', '-o', output, 'Probe'], cwd=root,
              env=dict(os.environ, LC_ALL='C.UTF-8'), capture_output=True, text=True)
          self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
          self.assertTrue((root / output / 'Probe.acy').is_file())
      # Caller paths precede the pinned interface fallback.
      override = root / 'override/Data/Char.curry'
      override.parent.mkdir(parents=True)
      override.write_text('module Data.Char where\nmarker :: Bool\nmarker = True\n')
      (root / 'Probe.curry').write_text(
          'module Probe where\nimport Data.Char\nvalue = marker\n')
      result = subprocess.run([sys.executable, str(ROOT / 'src/export/bin/sprite-frontend.script'),
          '--acy', '-f', '-i', str(root / 'override'),
          '-o', '.curry/sprite-0.9.0', 'Probe'], cwd=root,
          env=dict(os.environ, LC_ALL='C.UTF-8'), capture_output=True, text=True)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

  def test_staged_launchers(self):
    self.exercise(Path(config.installed_path()))

  def test_shipped_library_frontend_without_compiler(self):
    library = Path(config.system_curry_path())
    products = list((library / '.curry' / config.analysis_subdir()).rglob('*'))
    before = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in products if p.is_file()}
    with tempfile.TemporaryDirectory() as directory:
      env = dict(os.environ, SPRITE_FRONTEND='')
      command = [sys.executable, config.installed_path('curry', 'bin', 'sprite-frontend'),
                 '--flat', '--acy', '-i', str(library),
                 '-o', '.curry/' + config.analysis_subdir(), '--no-verb',
                 'Prelude', 'Data.List']
      result = subprocess.run(command, cwd=directory, env=env, capture_output=True, text=True)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      # A user module with the same name must reach the front end instead.
      (Path(directory) / 'Data').mkdir()
      (Path(directory) / 'Data/List.curry').write_text('module Data.List where\nx = 1\n')
      for options in ([], ['-f'], ['--uacy']):
        result = subprocess.run(command + options, cwd=directory, env=env,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no Curry front end found', result.stderr)
    self.assertEqual(before, {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in before})

  def test_stage_uses_configured_python(self):
    alternate = shutil.which('python3', path=os.defpath)
    if alternate is None or Path(alternate).resolve() == Path(sys.executable).resolve():
      self.skipTest('no different Python is available')
    env = {k: v for k, v in os.environ.items() if k not in ('SPRITE_HOME', 'PYTHONPATH')}
    result = subprocess.run([alternate, config.installed_path('curry', 'bin', 'curry'),
                             '--compiler-name'], env=env, capture_output=True,
                            text=True, timeout=60)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    self.assertEqual(result.stdout, 'sprite\n')

  def test_wheel_resource_launchers(self):
    # Model the wheel layout with the actual package and its resources. The
    # same launchers must bootstrap without the staged python directory.
    with tempfile.TemporaryDirectory() as work:
      package = Path(work) / 'curry'
      shutil.copytree(Path(config.installed_path('python/curry')), package, symlinks=True)
      resources = package / '_sprite'
      resources.mkdir(exist_ok=True)
      for name in ('lib', 'sysconfig', 'include', 'tools'):
        (resources / name).symlink_to(Path(config.installed_path(name)).resolve(), target_is_directory=True)
      (resources / 'curry/bin').mkdir(parents=True)
      (resources / 'curry/lib').symlink_to(Path(config.system_curry_path()).resolve(), target_is_directory=True)
      for name in ('curry', 'cleancurry', 'sprite-frontend', 'cypm'):
        target = resources / 'curry/bin' / name
        shutil.copy2(ROOT / 'src/export/bin' / (name + '.script'), target)
        target.chmod(0o755)
      self.exercise(resources)
    scripts = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['scripts']
    self.assertNotIn('curry', scripts)
    self.assertNotIn('cleancurry', scripts)
    self.assertNotIn('sprite-frontend', scripts)
