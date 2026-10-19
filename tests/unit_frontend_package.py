'''Frontend packaging works independently of the Sprite runtime.'''
import json, os, pathlib, runpy, shutil, subprocess, sys, tempfile, unittest


class TestFrontendLogs(unittest.TestCase):
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


class TestFrontendLauncher(unittest.TestCase):
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


class TestGmpLicenses(unittest.TestCase):
  def test_distributor_notices(self):
    root = pathlib.Path(__file__).resolve().parent.parent
    copy_notices = runpy.run_path(str(root / 'frontend/package.py'))['copy_gmp_licenses']
    for distro in ('debian', 'rpm'):
      with self.subTest(distro=distro), tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        paths = (['usr/share/doc/libgmp10/copyright'] if distro == 'debian' else
            ['usr/share/licenses/gmp/COPYINGv3',
             'usr/share/licenses/gmp/COPYING.LESSERv3'])
        originals = []
        for path in paths:
          notice = tmp / path
          notice.parent.mkdir(parents=True, exist_ok=True)
          contents = (path + '\nNotice: café\n').encode()
          notice.write_bytes(contents)
          originals.append(contents)
        dest = tmp / 'bundle'
        dest.mkdir()
        copy_notices(dest, tmp)
        self.assertEqual(sorted(p.read_bytes() for p in dest.iterdir()),
            sorted(originals))

  def test_missing_notices(self):
    root = pathlib.Path(__file__).resolve().parent.parent
    copy_notices = runpy.run_path(str(root / 'frontend/package.py'))['copy_gmp_licenses']
    with tempfile.TemporaryDirectory() as tmp:
      with self.assertRaisesRegex(ValueError, 'GMP licenses missing'):
        copy_notices(pathlib.Path(tmp), pathlib.Path(tmp))


class TestFrontendLinkage(unittest.TestCase):
  @unittest.skipUnless(shutil.which('cc') and shutil.which('readelf'),
      'requires a C compiler and readelf for a real dynamic ELF')
  def test_static_attempt_cannot_silently_deliver_dynamic_elf(self):
    root = pathlib.Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix='frontend build ') as tmp:
      tmp = pathlib.Path(tmp)
      scripts, source, tools = (tmp / name for name in ('scripts', 'source', 'tools'))
      for path in (scripts, source, tools):
        path.mkdir()
      shutil.copy2(root / 'frontend/build.sh', scripts / 'build.sh')
      (source / 'frontend.cabal').write_text('executable curry-frontend\n')
      (source / 'stack.yaml').write_text('resolver: lts-16.9\n')
      c_source = tmp / 'frontend.c'
      c_source.write_text('#include <stdio.h>\nint main(void) { puts("2.0.0"); }\n')
      binary = tmp / 'frontend'
      subprocess.run(['cc', str(c_source), '-o', str(binary)], check=True)
      elf = subprocess.check_output(['readelf', '-l', '-d', str(binary)], text=True)
      if 'INTERP' not in elf:
        self.skipTest('system C compiler defaults to static linking')
      stubs = {
          'uname': '#!/bin/bash\necho x86_64\n'
        , 'ghc': '#!/bin/bash\necho fixture-ghc\n'
        , 'ghc-pkg': '#!/bin/bash\necho fixture-packages\n'
        , 'cabal': '#!/bin/bash\necho fixture-cabal\n'
        , 'stack': '#!' + sys.executable + '\n'
            'import os, pathlib, shutil, sys\n'
            'if "--local-bin-path" in sys.argv:\n'
            '  dest = pathlib.Path(sys.argv[sys.argv.index("--local-bin-path") + 1])\n'
            '  dest.mkdir(parents=True, exist_ok=True)\n'
            '  shutil.copy2(os.environ["FRONTEND_TEST_ELF"], dest / "curry-frontend")\n'
        }
      for name, contents in stubs.items():
        tool = tools / name
        tool.write_text(contents)
        tool.chmod(0o755)
      dest = tmp / 'output'
      env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'],
          FRONTEND_TEST_ELF=str(binary))
      result = subprocess.run(['bash', str(scripts / 'build.sh'), str(source), str(dest)],
          env=env, capture_output=True, text=True, timeout=30)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      self.assertEqual((dest / 'linkage-requested.txt').read_text(), 'dynamic\n')
      self.assertIn('rejecting the static attempt', (dest / 'static.log').read_text())
      self.assertTrue((dest / 'dynamic.log').is_file())


if __name__ == '__main__':
  unittest.main()
