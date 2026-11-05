"""Selection and regression decisions for the serial CPM index job."""
import cytest # from ./lib; must be first
import csv
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sqlite3
import sys
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('cpm_index', ROOT / 'scripts/cpm-index-run.py')
survey = importlib.util.module_from_spec(spec)
spec.loader.exec_module(survey)
spec = importlib.util.spec_from_file_location('cpm_framework', ROOT / 'scripts/cpm-currycheck-prepare.py')
framework = importlib.util.module_from_spec(spec)
spec.loader.exec_module(framework)


class TestCPMIndex(cytest.TestCase):
  def test_snapshot_excludes_uploads_and_rejects_changed_metadata(self):
    with tempfile.TemporaryDirectory() as work:
      root = Path(work)
      source, target = root / 'source', root / 'overlay'
      pinned = source / 'sample/1.0.0/package.json'
      pinned.parent.mkdir(parents=True)
      data = {'name': 'sample', 'version': '1.0.0',
              'compilerCompatibility': {'pakcs': '>= 3.0.0'}}
      pinned.write_text(json.dumps(data))
      original = pinned.read_bytes()
      snapshot = {'versions': {'sample': ['1.0.0']},
                  'sha256': survey.index_digest(source)}
      upload = source / 'sample/1.1.0/package.json'
      upload.parent.mkdir(parents=True)
      upload.write_text(json.dumps({'name': 'sample', 'version': '1.1.0',
          'compilerCompatibility': {'future': 'a future constraint syntax'}}))
      survey.overlay.overlay(source, target, snapshot)
      self.assertFalse((target / 'sample/1.1.0').exists())
      self.assertEqual(pinned.read_bytes(), original)
      with sqlite3.connect(target / 'REPOSITORY_CACHE.db') as connection:
        self.assertEqual(connection.execute('SELECT count(*) FROM IndexEntry').fetchone(), (1,))
      data['synopsis'] = 'Changed pinned metadata'
      pinned.write_text(json.dumps(data))
      with self.assertRaisesRegex(ValueError, 'snapshot manifest digest'):
        survey.overlay.overlay(source, target, snapshot)

  def test_framework_preparation_preserves_properties(self):
    with tempfile.TemporaryDirectory() as work:
      home = Path(work)
      project = home / 'framework'
      (project / 'src').mkdir(parents=True)
      manifest = project / 'package.json'
      manifest.write_text(json.dumps({'name': 'currycheck', 'version': '4.0.0'}))
      source = project / 'src/CurryCheck.curry'
      source.write_text(framework.BEFORE + '\n' + framework.TYPE_BEFORE + '\npropertyBody = True\n')
      with mock.patch.dict(os.environ, HOME=str(home)):
        self.assertTrue(framework.prepare(project))
        self.assertIn('curryCompiler == "sprite"', source.read_text())
        self.assertTrue(source.read_text().endswith('\npropertyBody = True\n'))
        self.assertFalse(framework.prepare(project))
        before = source.read_bytes()
        manifest.write_text(json.dumps({'name': 'currycheck', 'version': '4.1.0'}))
        with self.assertRaisesRegex(ValueError, 'pinned CurryCheck'):
          framework.prepare(project)
        self.assertEqual(source.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'private CPM home'):
          framework.prepare(home.parent / 'outside')

  def test_incomplete_expectations_fail_before_running_packages(self):
    with tempfile.TemporaryDirectory() as work:
      root = Path(work)
      expected = root / 'expected.json'
      expected.write_text(json.dumps({'complete': False, 'packages': {}}))
      result = subprocess.run([sys.executable, str(ROOT / 'scripts/cpm-index-run.py'),
          '--expected', str(expected), '--cypm', 'unused', '--sprite', 'unused',
          '--index', str(root), '--work', str(root / 'uncreated')],
          text=True, capture_output=True)
      self.assertEqual(result.returncode, 2, result.stderr)
      self.assertIn('expected results are incomplete', result.stderr)
      self.assertFalse((root / 'uncreated').exists())

  def test_selection_and_missing_pin(self):
    with tempfile.TemporaryDirectory() as work:
      root = Path(work)
      for ver, base, suite in [('1.0.0', '>= 3.0.0', True),
                                ('2.0.0', '>= 4.0.0', True),
                                ('1.1.0', '>= 3.0.0', False)]:
        directory = root / 'sample' / ver
        directory.mkdir(parents=True)
        (directory / 'package.json').write_text(json.dumps({
            'name': 'sample', 'version': ver, 'testsuite': suite,
            'dependencies': {'base': base}}))
      self.assertEqual(survey.select_packages(root)[0]['version'], '1.0.0')
      expected = {'packages': {'sample': {'version': '1.0.0', 'result': 'pass'}}}
      self.assertEqual(survey.select_packages(root, expected)[0]['version'], '1.0.0')
      expected['packages']['sample']['version'] = '9.0.0'
      with self.assertRaisesRegex(ValueError, 'pinned versions missing'):
        survey.select_packages(root, expected)

  def test_comparison_does_not_bless_regressions(self):
    expected = {'packages': {
        'good': {'version': '1.0.0', 'result': 'pass'},
        'upstream': {'version': '1.0.0', 'result': 'exception',
                     'reason': 'fails under PAKCS 3.10.0 too'}}}
    rows = [{'package': name, 'version': '1.0.0', 'result': result}
            for name, result in [('good', 'timeout'), ('upstream', 'pass')]]
    failures, improvements = survey.compare(rows, expected)
    self.assertEqual(failures, ['good: timeout'])
    self.assertEqual(improvements, ['upstream: exception now passes'])
    rows[0].update(version='2.0.0', result='pass')
    self.assertEqual(survey.compare(rows, expected)[0], ['good: wrong pinned version'])

  def test_compilation_is_not_property_execution(self):
    self.assertTrue(survey.classify('No tests, just compiling', 0).startswith('Sprite error:'))
    self.assertEqual(survey.classify('OK', 124), 'timeout')
    self.assertTrue(survey.classify('prop: FAILED!', 1).startswith('test failure:'))
    self.assertEqual(survey.property_results('prop: OK\nother: FAILED!\n'), (1, 1))
    self.assertEqual(survey.property_results('Compiling Main\n'), ('not run', 'not run'))
    self.assertIn('std::bad_alloc', survey.classify('what(): std::bad_alloc', 134))
    self.assertEqual(survey.classify('*** Evaluation suspended!', 1),
                     'Sprite error: *** Evaluation suspended!')

  def test_network_retains_source_url(self):
    self.assertEqual(survey.classify('curl: (7) Failed to connect\nRecovered from cache', 0), 'pass')
    url = 'https://example.org/package.tar.gz'
    self.assertEqual(survey.classify(url + '\ncurl: (28) Connection timed out', 1),
                     'network: ' + url)
    kiel = 'https://www.informatik.uni-kiel.de/package.tar.gz'
    self.assertEqual(survey.classify('Downloading ' + kiel, 124), 'network: ' + kiel)

  def test_snapshot_is_stable_and_covers_manifest_bytes(self):
    with tempfile.TemporaryDirectory() as work:
      root = Path(work)
      manifest = root / 'package.json'
      manifest.write_text('{}\n')
      digest = survey.index_digest(root)
      (root / 'REPOSITORY_CACHE.db').write_bytes(b'ignored')
      self.assertEqual(survey.index_digest(root), digest)
      manifest.write_text('{"name":"sample"}\n')
      self.assertNotEqual(survey.index_digest(root), digest)

  @cytest.posix_only('the survey uses timeout and prlimit')
  def test_pinned_run_fails_and_records_oracle(self):
    with tempfile.TemporaryDirectory() as work:
      root = Path(work)
      home = root / 'home'
      home.mkdir()
      index = root / 'index' / 'sample' / '1.0.0'
      index.mkdir(parents=True)
      (index / 'package.json').write_text(json.dumps({
          'name': 'sample', 'version': '1.0.0', 'testsuite': [{'modules': ['Main']}]}))
      expected = root / 'expected.json'
      expected.write_text(json.dumps({'packages': {
          'sample': {'version': '1.0.0', 'result': 'pass'}}}))
      cypm = root / 'cypm'
      cypm.write_text('#!' + sys.executable + '\n' + '''
import json, os, pathlib, sys
args = sys.argv[1:]
if 'checkout' in args:
    target = pathlib.Path(args[args.index('-o') + 1])
    target.mkdir()
    (target / 'package.json').write_text('{"name":"sample","version":"1.0.0"}')
elif 'test' in args:
    if os.environ['PATH'].split(os.pathsep)[0].endswith('oracle'):
        print('prop: OK')
    else:
        print('prop: FAILED!')
        sys.exit(1)
''')
      cypm.chmod(0o755)
      # The test driver already imposes a smaller hard address-space cap.
      # Check the requested survey cap without trying to raise that hard cap.
      limiter = root / 'prlimit'
      limiter.write_text('#!/bin/sh\n[ "$1" = --as=8000000000 ] || exit 9\nshift\nexec "$@"\n')
      limiter.chmod(0o755)
      result = subprocess.run([sys.executable, str(ROOT / 'scripts/cpm-index-run.py'),
          '--cypm', str(cypm), '--sprite', sys.executable,
          '--index', str(root / 'index'), '--work', str(home / 'work'),
          '--csv', str(root / 'results.csv'), '--expected', str(expected),
          '--pakcs', sys.executable, '--pakcs-checker', str(root / 'oracle')],
          env=dict(os.environ, HOME=str(home), PATH=str(root) + os.pathsep + os.environ['PATH']),
          capture_output=True, text=True)
      self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
      self.assertIn('1 regressions', result.stdout)
      with (root / 'results.csv').open() as stream:
        row, = list(csv.DictReader(stream))
      self.assertEqual(row['pakcs_result'], 'pass', str(row) + result.stdout +
                       (home / 'work/sample.log').read_text())
      self.assertEqual(row['pakcs_properties_passed'], '1')
      self.assertEqual(row['properties_failed'], '1')
      self.assertIn('PAKCS test\nprop: OK', (home / 'work/sample.log').read_text())
      before = (root / 'results.csv').read_bytes()
      (home / 'work/STOP').touch()
      stopped = subprocess.run(result.args, env=dict(os.environ, HOME=str(home)),
                               capture_output=True, text=True)
      self.assertEqual(stopped.returncode, 130, stopped.stdout + stopped.stderr)
      self.assertIn('Stopped between packages', stopped.stdout)
      self.assertEqual((root / 'results.csv').read_bytes(), before)
      (home / 'work/STOP').unlink()
      row['result'] = 'not run: survey stopped'
      with (root / 'results.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
      resumed = subprocess.run([*result.args, '--resume'],
          env=dict(os.environ, HOME=str(home), PATH=str(root) + os.pathsep + os.environ['PATH']),
          capture_output=True, text=True)
      self.assertEqual(resumed.returncode, 1, resumed.stdout + resumed.stderr)
      with (root / 'results.csv').open() as stream:
        retried, = list(csv.DictReader(stream))
      self.assertTrue(retried['result'].startswith('test failure:'), retried)

