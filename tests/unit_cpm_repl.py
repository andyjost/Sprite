"""CPM must execute properties on Sprite rather than only compile modules."""
import cytest # from ./lib; must be first
from curry import config
from pathlib import Path
import sys
import json
import os
import shutil
import subprocess
import tempfile
import unittest


CYPM = shutil.which('cypm')
if CYPM is None:
  pakcs = Path(config.installed_path('tools', 'pakcs')).resolve()
  candidate = pakcs.parent / 'cypm'
  if candidate.is_file():
    CYPM = str(candidate)
ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(CYPM, 'cypm is absent')
class TestCPMREPL(cytest.TestCase):
  # CurryCheck's EasyCheck dependency hits the reserved library-name guard.
  # See tests/data/cpm/repro_library/reproduce.py and the Round 4 report.
  @unittest.expectedFailure
  def test_local_properties(self):
    build = (ROOT / 'object-root').resolve().parent
    home = Path(os.environ.get('CPM_TEST_HOME', str(build / 'cpmhome')))
    home.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=build, prefix='cpm-repl-test-') as work:
      project = Path(work) / 'project'
      shutil.copytree(ROOT / 'tests/data/cpm/repl', project)
      original = Path(work) / 'index'
      base = original / 'base' / config.currylib_version()
      base.mkdir(parents=True)
      (original / 'README.md').write_text('Private test index.\n')
      (base / 'package.json').write_text(json.dumps({
          'name': 'base', 'version': config.currylib_version(),
          'author': 'Sprite', 'synopsis': 'The installed base library',
          'dependencies': {}, 'compilerCompatibility': {'pakcs': '>= 3.0.0'}}) + '\n')
      index = home / 'local-property-index'
      env = dict(os.environ, HOME=str(home), LC_ALL='C.UTF-8',
                 SPRITE_DISABLE_SYSLIB_CHECKS='1',
                 PATH=str(home / '.cpm/bin') + os.pathsep + os.environ['PATH'])
      subprocess.run([sys.executable,
          str(ROOT / 'scripts/cpm-test-overlay.py'), str(original), str(index)],
          check=True, capture_output=True, text=True)
      sprite = config.installed_path('bin', 'sprite')
      command = [CYPM, '-d', 'CURRYBIN=' + sprite,
          '-d', 'REPOSITORYPATH=' + str(index),
          'test']
      result = subprocess.run(command, cwd=project, env=env,
          capture_output=True, text=True, timeout=600)
      output = result.stdout + result.stderr
      self.assertEqual(result.returncode, 0, output)
      self.assertIn('Running CurryCheck', output)
      self.assertNotIn('No tests, just compiling', output)
      self.assertNotIn('FAILED', output)
