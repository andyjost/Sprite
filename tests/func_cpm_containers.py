"""Optional network smoke test of packages installed by the real cypm."""
import cytest # from ./lib; must be first
import json, os, shlex, shutil, subprocess, sys, tempfile
from pathlib import Path


class TestCpmContainers(cytest.TestCase):
  def test_containers(self):
    cypm = shutil.which('cypm')
    if not cypm:
      self.skipTest('cypm is not available')
    with tempfile.TemporaryDirectory() as root:
      Path(root, 'src').mkdir()
      Path(root, 'package.json').write_text(json.dumps({
          'name': 'sprite-cpm-smoke', 'version': '0.0.1',
          'synopsis': 'Sprite package smoke test',
          'dependencies': {'containers': '>= 3.0.0, < 4.0.0'}}), encoding='ascii')
      try:
        installed = subprocess.run([cypm, 'install'], cwd=root, text=True,
                                   capture_output=True, timeout=180)
      except subprocess.TimeoutExpired:
        self.skipTest('cypm install timed out; the network may be unavailable')
      if installed.returncode:
        # Only network failures skip; configuration or package errors fail.
        output = installed.stdout + installed.stderr
        if any(word in output.lower() for word in (
            'could not resolve', 'unable to access', 'network is unreachable',
            'connection timed out', 'failed to connect', 'connection refused',
            'temporary failure in name resolution', 'could not download',
            'failed to download')):
          self.skipTest('the package network is unavailable')
        self.fail(output)
      code = ('import curry; M = curry.import_("Data.Map"); '
              'print(curry.eval(M.size(M.empty)).one())')
      env = os.environ.copy()
      env.pop('CURRYPATH', None)
      env.pop('SPRITE_CPM_PATH', None)
      for command in ([cypm, 'exec', shlex.join([sys.executable, '-c', code])],
                      [sys.executable, '-c', code]):
        child_env = dict(env, SPRITE_CPM_PATH='0') if command[0] == cypm else env
        child = subprocess.run(command, cwd=root, env=child_env, text=True,
                               capture_output=True, timeout=180)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        self.assertEqual(child.stdout.strip(), '0')
