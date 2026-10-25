'''Frontend packaging works independently of the Sprite runtime.'''
import importlib.util
import hashlib, json, os, pathlib, runpy, shutil, subprocess, sys, tempfile, unittest
import sysconfig, zipfile


class TestFrontendWheel(unittest.TestCase):
  @unittest.skipUnless(importlib.util.find_spec('setuptools') and
      importlib.util.find_spec('wheel'), 'requires setuptools and wheel')
  def test_distribution_and_offline_install(self):
    root = pathlib.Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix='frontend wheel ') as tmp:
      tmp = pathlib.Path(tmp)
      project = tmp / 'project'
      project.mkdir()
      for name in ('pyproject.toml', 'setup.py', 'README.pypi.md'):
        shutil.copy2(root / 'frontend' / name, project / name)
      shutil.copytree(root / 'frontend/licenses', project / 'licenses')
      package = project / 'curry_frontend'
      shutil.copytree(root / 'frontend/curry_frontend', package,
          ignore=shutil.ignore_patterns('__pycache__'))
      (package / 'bin').mkdir()
      binary = package / 'bin/curry-frontend'
      binary.write_text('#!/bin/sh\necho 2.0.0\n')
      binary.chmod(0o755)
      wheels = tmp / 'wheels'
      result = subprocess.run([sys.executable, '-m', 'pip', 'wheel',
          '--no-index', '--no-deps', '--no-build-isolation',
          '--wheel-dir', str(wheels), str(project)],
          capture_output=True, text=True, timeout=60)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      platform = sysconfig.get_platform().replace('-', '_').replace('.', '_')
      wheel, = wheels.glob('*.whl')
      self.assertEqual(wheel.name, 'curry_frontend-2.0.0.post6-py3-none-%s.whl' % platform)
      with zipfile.ZipFile(wheel) as archive:
        metadata = archive.read('curry_frontend-2.0.0.post6.dist-info/METADATA').decode()
      self.assertIn('\nName: curry-frontend\n', metadata)
      # The description of the PyPI page: the release workflow's strict twine
      # check refuses a wheel without one.
      self.assertIn('\nDescription-Content-Type: text/markdown\n', metadata)
      self.assertIn('# curry-frontend\n', metadata)
      env = tmp / 'env'
      subprocess.run([sys.executable, '-m', 'venv', str(env)], check=True, timeout=60)
      result = subprocess.run([str(env / 'bin/python'), '-m', 'pip', 'install',
          '--no-index', '--no-deps', str(wheel)],
          capture_output=True, text=True, timeout=60)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      result = subprocess.run([str(env / 'bin/curry-frontend'), '--numeric-version'],
          capture_output=True, text=True, timeout=30)
      self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '2.0.0\n', ''))


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
  def test_dynamic_build_uses_stack_without_static_options(self):
    self.check_stack_build('2.0.0', 'lts-16.9', 'x86_64')

  @unittest.skipUnless(shutil.which('cc') and shutil.which('readelf'),
      'requires a C compiler and readelf for a real dynamic ELF')
  def test_current_build_uses_source_resolver_on_both_architectures(self):
    for arch in ('x86_64', 'aarch64'):
      with self.subTest(arch=arch):
        self.check_stack_build('3.1.0', 'lts-23.19', arch)

  def check_stack_build(self, version, resolver, arch):
    root = pathlib.Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix='frontend build ') as tmp:
      tmp = pathlib.Path(tmp)
      scripts, source, tools = (tmp / name for name in ('scripts', 'source', 'tools'))
      for path in (scripts, source, tools):
        path.mkdir()
      shutil.copy2(root / 'frontend/build.sh', scripts / 'build.sh')
      (source / 'frontend.cabal').write_text('executable curry-frontend\n')
      (source / 'stack.yaml').write_text('resolver: ' + resolver + '\n')
      c_source = tmp / 'frontend.c'
      c_source.write_text('#include <stdio.h>\nint main(void) { puts("%s"); }\n' % version)
      binary = tmp / 'frontend'
      subprocess.run(['cc', str(c_source), '-o', str(binary)], check=True)
      elf = subprocess.check_output(['readelf', '-l', '-d', str(binary)], text=True)
      if 'INTERP' not in elf:
        self.skipTest('system C compiler defaults to static linking')
      stubs = {
          'uname': '#!/bin/bash\necho ' + arch + '\n'
        , 'ghc': '#!/bin/bash\necho fixture-ghc\n'
        , 'ghc-pkg': '#!/bin/bash\necho fixture-packages\n'
        , 'cabal': '#!/bin/bash\necho fixture-cabal\n'
        , 'stack': '#!' + sys.executable + '\n'
            'import os, pathlib, shutil, sys\n'
            'with open(os.environ["FRONTEND_TEST_COMMANDS"], "a") as log:\n'
            '  log.write(repr(sys.argv[1:]) + "\\n")\n'
            'if any(arg in sys.argv for arg in ("--no-shared", "--disable-shared")):\n'
            '  sys.exit("unsupported Stack option")\n'
            'if any("-optl-static" in arg for arg in sys.argv):\n'
            '  sys.exit("GMP archive unavailable")\n'
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
          FRONTEND_TEST_ELF=str(binary), FRONTEND_TEST_COMMANDS=str(tmp / 'commands'))
      command = ['bash', str(scripts / 'build.sh'), str(source), str(dest)]
      if version != '2.0.0':
        command.append(version)
      result = subprocess.run(command,
          env=env, capture_output=True, text=True, timeout=30)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      self.assertEqual((dest / 'linkage-requested.txt').read_text(), 'dynamic\n')
      self.assertTrue((dest / 'dynamic.log').is_file())
      self.assertIn('INTERP', (dest / 'dynamic-elf.txt').read_text())
      import ast
      commands = [ast.literal_eval(line) for line in (tmp / 'commands').read_text().splitlines()]
      builds = [args for args in commands if 'build' in args]
      self.assertEqual(len(builds), 1)
      self.assertIn('--system-ghc', builds[0])
      self.assertIn('--no-install-ghc', builds[0])


class TestCurrentFrontend(unittest.TestCase):
  def test_source_pins(self):
    root = pathlib.Path(__file__).resolve().parent.parent
    sources = runpy.run_path(str(root / 'frontend/fetch.py'))['SOURCES']
    url, digest = sources['3.1.0']
    self.assertEqual(url, 'https://api.github.com/repos/cau-placc/curry-frontend/tarball/v3.1.0')
    self.assertEqual(digest, '13d68be89369a3fdfd1ef2d6e8d4657ab286876f9063bb0b27332de54c6be75c')

  def test_versioned_references_cover_the_current_library(self):
    root = pathlib.Path(__file__).resolve().parent.parent
    sources = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (root / 'curry/lib').rglob('*.curry')}
    for version, pakcs, macro in [('2.0.0', '3.4.1', '304'), ('3.1.0', '3.10.0', '310')]:
      with self.subTest(version=version):
        reference = root / 'frontend/reference' / version
        manifest = json.loads((reference / 'manifest.json').read_text())
        self.assertEqual(manifest['frontend_version'], version)
        self.assertEqual(manifest['pakcs_version'], pakcs)
        self.assertIn('-D__PAKCS__=' + macro, manifest['flags'])
        self.assertEqual(manifest['sources'], sources)
        self.assertEqual(len(manifest['products']), 3 * len(sources))
        for name, digest in manifest['products'].items():
          self.assertEqual(hashlib.sha256((reference / name).read_bytes()).hexdigest(), digest)

  @unittest.skipUnless(os.environ.get('CURRY_FRONTEND_TEST_WHEEL'),
      'set CURRY_FRONTEND_TEST_WHEEL to smoke the real local 3.1.0 wheel')
  def test_local_current_wheel(self):
    wheel = pathlib.Path(os.environ['CURRY_FRONTEND_TEST_WHEEL']).resolve()
    with zipfile.ZipFile(wheel) as archive:
      metadata = archive.read('curry_frontend-3.1.0.post1.dist-info/METADATA').decode()
      self.assertIn('Version: 3.1.0.post1\n', metadata)
      info = json.loads(archive.read('curry_frontend/build-info.json'))
      self.assertEqual(info['version'], '3.1.0')
      self.assertEqual(info['packaging_version'], '3.1.0.post1')
      self.assertIn('curry_frontend/licenses/LICENSE.curry-frontend', archive.namelist())
      if 'libgmp.so.10' in info['needed']:
        self.assertIn('curry_frontend/bin/libgmp.so.10', archive.namelist())
        self.assertEqual(info['rpath'], '$ORIGIN')
    with tempfile.TemporaryDirectory() as tmp:
      env = pathlib.Path(tmp) / 'env'
      subprocess.run([sys.executable, '-m', 'venv', str(env)], check=True, timeout=60)
      result = subprocess.run([str(env / 'bin/python'), '-m', 'pip', 'install',
          '--no-index', '--no-deps', str(wheel)], capture_output=True, text=True, timeout=60)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      result = subprocess.run(['timeout', '30', str(env / 'bin/curry-frontend'),
          '--numeric-version'], capture_output=True, text=True, timeout=40)
      self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '3.1.0\n', ''))


if __name__ == '__main__':
  unittest.main()
