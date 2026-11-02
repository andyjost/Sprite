"""CPM must execute properties on Sprite rather than only compile modules."""
import cytest # from ./lib; must be first
from curry import config
from pathlib import Path
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
  @unittest.expectedFailure
  def test_local_properties(self):
    # Known integration blocker: CurryCheck's base dependency excludes Sprite,
    # and CurryCheck currently hard-codes its compiling system's bin/curry.
    # Keep this acceptance test until the owner chooses the integration route.
    build = (ROOT / 'object-root').resolve().parent
    home = build / 'cpmhome'
    home.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=build, prefix='cpm-repl-test-') as work:
      project = Path(work) / 'project'
      shutil.copytree(ROOT / 'tests/data/cpm/repl', project)
      # A local index describes the base provided by the selected system.
      # No package downloads or global index updates belong in this test.
      index = Path(work) / 'index'
      base = index / 'base' / config.currylib_version()
      base.mkdir(parents=True)
      (base / 'package.json').write_text(json.dumps({
          'name': 'base', 'version': config.currylib_version(),
          'author': 'Sprite', 'synopsis': 'The installed base library',
          'dependencies': {}}) + '\n')
      env = dict(os.environ, HOME=str(home), LC_ALL='C.UTF-8')
      sprite = config.installed_path('bin', 'sprite')
      # Empty download URLs make this test independent of network access.
      command = [CYPM, '-d', 'CURRYBIN=' + sprite,
          '-d', 'REPOSITORYPATH=' + str(index),
          '-d', 'PACKAGEINDEXURL=', '-d', 'PACKAGETARFILESURL=', 'test']
      result = subprocess.run(command, cwd=project, env=env,
          capture_output=True, text=True, timeout=180)
      output = result.stdout + result.stderr
      self.assertEqual(result.returncode, 0, output)
      self.assertIn('Running CurryCheck', output)
      self.assertNotIn('No tests, just compiling', output)
      self.assertNotIn('FAILED', output)
