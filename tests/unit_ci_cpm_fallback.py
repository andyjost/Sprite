'''The docs job can use a restored CPM index during a server outage.'''
import cytest # from ./lib; must be first
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


HELPER = Path(__file__).resolve().parent.parent / '.github/scripts/cpm-update-or-cached.sh'


@cytest.posix_only('executes a CI bash script and a fake cypm executable')
@unittest.skipUnless(shutil.which('bash') and shutil.which('timeout'),
                     'requires bash and timeout')
class TestCpmFallback(cytest.TestCase):
  def setUp(self):
    directory = tempfile.TemporaryDirectory(prefix='sprite-cpm-fallback-')
    self.addCleanup(directory.cleanup)
    self.work = Path(directory.name)
    self.home = self.work / 'home'
    self.home.mkdir()
    binary = self.work / 'bin'
    binary.mkdir()
    cypm = binary / 'cypm'
    cypm.write_text('#!/bin/bash\n'
                    '[ "$#" -eq 1 ] && [ "$1" = update ] || exit 99\n'
                    'exit "$CPM_TEST_STATUS"\n')
    cypm.chmod(0o755)
    self.output = self.work / 'output'
    self.env = dict(os.environ, HOME=str(self.home),
                    GITHUB_OUTPUT=str(self.output),
                    PATH=str(binary) + os.pathsep + os.environ['PATH'])

  def run_helper(self, status):
    return subprocess.run(['bash', str(HELPER)],
        env=dict(self.env, CPM_TEST_STATUS=str(status)),
        capture_output=True, text=True, timeout=10)

  def test_success(self):
    result = self.run_helper(0)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    self.assertEqual(self.output.read_text(), 'fresh=true\n')
    self.assertNotIn('::warning', result.stdout)
    self.assertNotIn('::error', result.stdout)

  def test_failure_with_cached_index(self):
    readme = self.home / '.cpm/index/README.md'
    readme.parent.mkdir(parents=True)
    readme.write_text('cached package index\n')
    os.utime(readme, (1577836800, 1577836800))
    result = self.run_helper(1)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    self.assertIn('::warning title=CPM server unreachable::', result.stdout)
    self.assertIn('2020-01-01 00:00:00 UTC', result.stdout)
    self.assertEqual(self.output.read_text(), 'fresh=false\n')
    self.assertEqual(readme.read_text(), 'cached package index\n')
    self.assertEqual(readme.stat().st_mtime, 1577836800)

  def test_failure_without_cached_index(self):
    # An empty directory is not a restored package index.
    (self.home / '.cpm/index').mkdir(parents=True)
    result = self.run_helper(1)
    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
    self.assertIn('::error title=Infrastructure failure::', result.stdout)
    self.assertIn('CPM server did not answer and no cached index exists', result.stdout)
    self.assertFalse(self.output.exists())

  def test_success_without_github_output(self):
    self.env.pop('GITHUB_OUTPUT')
    result = self.run_helper(0)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    self.assertFalse(self.output.exists())
