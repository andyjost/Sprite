'''The wheel launcher preserves arguments and replaces its own process.'''
import cytest # from ./lib; must be first
import json, os, pathlib, shutil, subprocess, sys, tempfile, unittest


class TestFrontendLauncher(cytest.TestCase):
  def test_exec(self):
    root = pathlib.Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix='frontend package ') as tmp:
      package = pathlib.Path(tmp) / 'curry_frontend'
      shutil.copytree(root / 'frontend/curry_frontend', package,
          ignore=shutil.ignore_patterns('__pycache__'))
      (package / 'bin').mkdir()
      binary = package / 'bin/curry-frontend'
      binary.write_text('#!' + sys.executable + '\n'
          'import json, os, sys\n'
          'print(json.dumps([os.getpid(), sys.argv[1:]]))\n')
      binary.chmod(0o755)
      args = ['--numeric-version', 'a b', '$(literal)', 'café']
      env = dict(os.environ, PYTHONPATH=tmp)
      proc = subprocess.Popen([sys.executable, '-c',
          'from curry_frontend import main; main()', *args],
          env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
      out, err = proc.communicate(timeout=30)
      self.assertEqual(proc.returncode, 0, err)
      pid, received = json.loads(out)
      self.assertEqual(pid, proc.pid)
      self.assertEqual(received, args)


if __name__ == '__main__':
  unittest.main()
