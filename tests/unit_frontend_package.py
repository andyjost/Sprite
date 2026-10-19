'''The wheel launcher preserves arguments and replaces its own process.'''
import cytest # from ./lib; must be first
import json, os, pathlib, runpy, shutil, subprocess, sys, tempfile, unittest


class TestFrontendLogs(cytest.TestCase):
  def test_collect_partial_build(self):
    root = pathlib.Path(__file__).resolve().parent.parent
    collect = runpy.run_path(str(root / 'frontend/collect-logs.py'))['collect']
    with tempfile.TemporaryDirectory() as tmp:
      tmp = pathlib.Path(tmp)
      roots = {name: tmp / name for name in ('ghcup', 'stack', 'missing')}
      for name in ('ghcup', 'stack'):
        logs = roots[name] / 'nested'
        logs.mkdir(parents=True)
        (logs / 'build.log').write_text(name + ' failed\n')
        (logs / 'object.o').write_bytes(b'not a log')
      dest = tmp / 'artifact'
      collect(roots, dest)
      self.assertEqual(sorted(str(p.relative_to(dest)) for p in dest.rglob('*')
          if p.is_file()), ['ghcup/nested/build.log', 'stack/nested/build.log'])
      for name in ('ghcup', 'stack'):
        self.assertEqual((dest / name / 'nested/build.log').read_text(),
            name + ' failed\n')


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
