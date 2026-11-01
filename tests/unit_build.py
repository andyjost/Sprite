import cytest # from ./lib; must be first
from email.parser import BytesParser
import importlib.util
import io
from pathlib import Path
from cytest.buildtools import cmake_executable
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import unittest
from unittest import mock
import zipfile


ROOT = Path(__file__).resolve().parent.parent


def script(name):
  spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/wheels' / (name + '.py'))
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


# The Requires-Dist lines of the wheels and the sdist, in order: the front
# end, llvmlite for the LLVM backend (no wheel for Intel macOS), the alias
# extra jit.
REQUIREMENTS = ('curry-frontend>=3.1.0',
                'llvmlite>=0.50; sys_platform != "darwin" or platform_machine != "x86_64"',
                'llvmlite>=0.50; extra == "jit"')


class TestDistribution(cytest.TestCase):
  def test_windows_wheel_rejects_transient_objects(self):
    repair = script('repair')
    with tempfile.TemporaryDirectory() as directory:
      wheel = Path(directory) / 'fixture.whl'
      for name in ('Prelude.dll.123.1.tiered', 'Prelude.dll.old-123-1'):
        member = 'curry/_sprite/curry/.curry/products/' + name
        with zipfile.ZipFile(wheel, 'w') as archive:
          archive.writestr(member, b'transient')
        with self.subTest(name=name), self.assertRaises(AssertionError) as error:
          repair.inspect_wheel_windows(wheel)
        self.assertIn(member, str(error.exception))

  def test_optional_jit_stage_fill(self):
    spec = importlib.util.spec_from_file_location('build_package',
        ROOT / 'scripts/build-package.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as directory:
      source = Path(directory) / 'Tiny.curry'
      source.write_text('module Tiny where\nmain :: Int\nmain = 1\n')
      cases = [
          '',
          "llvmjit.available = lambda: False; llvmjit._reason = 'no helpers'\n",
        ]
      if importlib.util.find_spec('llvmlite') is not None:
        # The emitter runs only where llvmlite imports; without it the fill
        # says so and stops before any module.
        cases.append(
            "curry.import_ = lambda name: (_ for _ in ()).throw(ValueError('emitter'))\n")
      for prelude in cases:
        with mock.patch.dict(os.environ, SPRITE_STAGE_JIT_CACHE='1'):
          code = module.jit_cache_fill([str(source)])
        code = code.replace("if not llvmjit.available():", prelude + "if not llvmjit.available():")
        result = subprocess.run([sys.executable, '-c', code],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        if prelude:
          self.assertIn('no helpers' if 'False' in prelude else 'emitter', result.stdout)

  def test_metadata(self):
    data = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    project = data['project']
    self.assertEqual(project['name'], 'curry')
    self.assertEqual(project['authors'], [{'name': 'Andy Jost'}])
    frontend = tomllib.loads((ROOT / 'frontend/pyproject.toml').read_text())['project']
    self.assertEqual(frontend['name'], 'curry-frontend')
    self.assertEqual(frontend['authors'], [{'name': 'Andy Jost'}])
    self.assertIn('Sprite', project['description'])
    self.assertEqual((ROOT / 'VERSION').read_text().strip(), '0.9.0a3')
    self.assertEqual(project['license'], 'BSD-3-Clause')
    self.assertIn('Development Status :: 3 - Alpha', project['classifiers'])
    self.assertTrue((ROOT / project['readme']).is_file())
    self.assertEqual(set(project['urls']), {'Homepage', 'Documentation', 'Source', 'Issues'})
    self.assertEqual(project['dependencies'], [
        'curry-frontend>=3.1.0',
        "llvmlite>=0.50; sys_platform != 'darwin' or platform_machine != 'x86_64'"])
    self.assertEqual(project['optional-dependencies'], {'jit': ['llvmlite>=0.50']})
    self.assertEqual(data['build-system']['requires'],
        ['scikit-build-core>=1.1', 'cmake>=3.24', 'ninja'])
    for name in project['license-files']:
      self.assertTrue((ROOT / name).is_file(), name)

  def test_sdist_from_backend(self):
    '''The actual backend archives the vendored headers and pinned Curry products.'''
    with tempfile.TemporaryDirectory() as directory:
      result = subprocess.run([
          sys.executable, '-c',
          'from scikit_build_core.build import build_sdist; import sys; build_sdist(sys.argv[1])',
          directory], cwd=ROOT, text=True, capture_output=True)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      paths = list(Path(directory).glob('*.tar.gz'))
      self.assertEqual(len(paths), 1)
      with tarfile.open(paths[0]) as archive:
        prefix = paths[0].name.removesuffix('.tar.gz') + '/'
        names = set(archive.getnames())
        for name in script('check-dist').SDIST_FILES:
          self.assertIn(prefix + name, names)
        self.assertNotIn(prefix + 'CODEX-REPORT.md', names)
        self.assertFalse(any(n.startswith(prefix + 'curry/lib/')
                             and n.endswith('.img') for n in names))
        for source in (ROOT / 'curry/lib').rglob('*.curry'):
          if '.curry' in source.relative_to(ROOT / 'curry/lib').parts:
            continue
          stem = source.parent / '.curry/sprite-pakcs-3.10.0' / source.stem
          for suffix in ('.icy', '.fint', '.icurry', '.icy.imports', '.icy.source'):
            self.assertIn(prefix + str(stem.with_suffix(suffix).relative_to(ROOT)), names)
        self.assertFalse(any('/object-root/' in n or '/install/' in n for n in names))
        metadata = BytesParser().parsebytes(archive.extractfile(prefix + 'PKG-INFO').read())
        self.assertEqual(metadata['Author'], 'Andy Jost')
        self.assertIsNone(metadata['Author-email'])
        # The front end, llvmlite except on Intel macOS, and the alias extra jit.
    self.assertEqual(metadata.get_all('Requires-Dist'), list(REQUIREMENTS))
    self.assertEqual(metadata.get_all('Provides-Extra'), ['jit'])

  def test_stage_without_frontend(self):
    '''A fresh native build uses only shipped products, including typed calls.'''
    cmake = cmake_executable()
    if not cmake or not shutil.which('ninja'):
      self.skipTest('CMake and Ninja are required')
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      bindir = root / 'bin'
      bindir.mkdir()
      # Keep the build tools and Python, hiding both names of the front end
      # even when one shares their directory. Do not inherit runtime overrides.
      # A ccache masquerade (``/usr/lib/ccache/cc`` on the CI runners) is
      # skipped: linked under the compiler's name, ccache finds only itself
      # on this PATH; the real compiler is linked from its own directory.
      for directory in os.get_exec_path():
        if not Path(directory).is_dir():
          continue
        for tool in Path(directory).iterdir():
          if tool.name not in ('curry-frontend', 'pakcs-frontend', 'pakcs') \
              and tool.is_file() and os.access(tool, os.X_OK):
            resolved = tool.resolve()
            if resolved.name == 'ccache' and tool.name != 'ccache':
              continue
            target = bindir / tool.name
            if not target.exists():
              target.symlink_to(resolved)
      python = bindir / 'build-python'
      python.symlink_to(sys.executable)
      env = {k: v for k, v in os.environ.items()
             if not k.startswith(('SPRITE_', 'CURRY', 'PAKCS', 'PYTHONPATH'))}
      env.update(PATH=str(bindir), LC_ALL='C.UTF-8', SPRITE_STAGE_JIT_CACHE='0')
      build, prefix = root / 'build', root / 'install'
      def run(*command):
        result = subprocess.run(['timeout', '600', *map(str, command)],
            env=env, text=True, capture_output=True, timeout=610)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result
      run(cmake, '-S', ROOT, '-B', build, '-G', 'Ninja',
          '-DPython_EXECUTABLE=' + str(python), '-DWITH_PAKCS=',
          '-DWITH_CURRY_FRONTEND=', '-DWITH_ICURRY=', '-DJOBS=1')
      built = run(cmake, '--build', build, '--parallel', '1')
      if sys.platform != 'win32':
        self.assertEqual(built.stdout.count('library JIT cache fill skipped:'), 1)
      run(cmake, '--install', build, '--prefix', prefix)
      self.assertFalse([p for p in prefix.rglob('*')
                        if '.tiered' in p.name or '.old-' in p.name])
      env.update(SPRITE_HOME=str(prefix), PYTHONPATH=str(prefix / 'python'))
      result = run(python, '-c', '''
import curry
from curry import config
assert config.curry_frontend() is None
module = curry.import_('Data.List')
assert list(curry.eval(module.intersperse(0, [1, 2, 3]))) == [[1, 0, 2, 0, 3]]
try:
  curry.compile('main = 42')
except Exception as error:
  assert str(error) == 'no Curry front end found; set SPRITE_FRONTEND or put pakcs-frontend on PATH', str(error)
  print(error)
else:
  raise AssertionError('new Curry text needs a front end')
''')
      self.assertIn('no Curry front end found;', result.stdout)
      run(python, ROOT / 'scripts/wheels/smoke.py')

  REQUIREMENTS = REQUIREMENTS

  def distributions(self, directory, requirements=REQUIREMENTS):
    '''A matrix fixture for testing the publication gate, without native code.'''
    gate = script('check-dist')
    metadata = ('Metadata-Version: 2.4\nName: curry\nVersion: 0.9.0a3\n'
                'Author: Andy Jost\n'
                'License-Expression: BSD-3-Clause\n'
                'Classifier: Development Status :: 3 - Alpha\n'
                'Provides-Extra: jit\n'
                + ''.join('Requires-Dist: %s\n' % req for req in requirements) + '\n')
    for py, abi in gate.PYTHONS:
      for tag, suffix in gate.PLATFORMS:
        path = Path(directory) / f'curry-0.9.0a3-{py}-{abi}-{tag}.whl'
        with zipfile.ZipFile(path, 'w') as archive:
          archive.writestr('curry-0.9.0a3.dist-info/METADATA', metadata)
          archive.writestr('curry/_sprite/lib/curryrt-helpers.bc', b'BC')
          archive.writestr('curry/_sprite/sysconfig/jit_bitcode', 'lib/curryrt-helpers.bc\n')
        path.with_suffix(suffix).write_text('Report fixture\n')
    with tarfile.open(Path(directory) / 'curry-0.9.0a3.tar.gz', 'w:gz') as archive:
      for name in gate.SDIST_FILES:
        info = tarfile.TarInfo('curry-0.9.0a3/' + name)
        archive.addfile(info, io.BytesIO())
    return gate

  def test_complete_matrix(self):
    with tempfile.TemporaryDirectory() as directory:
      gate = self.distributions(directory)
      gate.check(directory, '0.9.0a3', 'v0.9.0a3')

  def test_wrong_distribution_identity(self):
    for old, new in [('curry-', 'currylang-'), ('0.9.0a3', '0.9.0a1')]:
      with self.subTest(replacement=new), tempfile.TemporaryDirectory() as directory:
        gate = self.distributions(directory)
        path = next(Path(directory).glob('*.whl'))
        renamed = path.with_name(path.name.replace(old, new))
        path.rename(renamed)
        suffix = next(s for tag, s in gate.PLATFORMS if tag in path.name)
        path.with_suffix(suffix).rename(renamed.with_suffix(suffix))
        with self.assertRaises(AssertionError):
          gate.check(directory, '0.9.0a3')

  def test_missing_freethreaded_wheel(self):
    with tempfile.TemporaryDirectory() as directory:
      gate = self.distributions(directory)
      next(Path(directory).glob('*-cp314-cp314t-manylinux_2_28_x86_64.whl')).unlink()
      with self.assertRaisesRegex(AssertionError, 'thirty wheels'):
        gate.check(directory, '0.9.0a3')

  def test_missing_jit_bitcode(self):
    '''A wheel without the bitcode of the JIT helpers fails the gate.'''
    with tempfile.TemporaryDirectory() as directory:
      gate = self.distributions(directory)
      path = next(Path(directory).glob('*-cp312-cp312-manylinux_2_28_aarch64.whl'))
      with zipfile.ZipFile(path) as archive:
        entries = [(info.filename, archive.read(info.filename)) for info in archive.infolist()]
      with zipfile.ZipFile(path, 'w') as archive:
        for name, data in entries:
          if name != 'curry/_sprite/lib/curryrt-helpers.bc':
            archive.writestr(name, data)
      with self.assertRaisesRegex(AssertionError, 'no bitcode of the JIT helpers'):
        gate.check(directory, '0.9.0a3')

  def test_runtime_dependencies(self):
    for requirements in [(), ('curry-frontend>=3.1.0', 'uv'), REQUIREMENTS[:2]]:
      with self.subTest(requirements=requirements):
        with tempfile.TemporaryDirectory() as directory:
          gate = self.distributions(directory, requirements=requirements)
          with self.assertRaises(AssertionError):
            gate.check(directory, '0.9.0a3')

  def test_wrong_platform(self):
    with tempfile.TemporaryDirectory() as directory:
      gate = self.distributions(directory)
      path = next(Path(directory).glob('*-cp311-*manylinux_2_28_x86_64.whl'))
      renamed = path.with_name(path.name.replace('manylinux_2_28', 'linux'))
      path.rename(renamed)
      path.with_suffix('.auditwheel.txt').rename(renamed.with_suffix('.auditwheel.txt'))
      with self.assertRaises(AssertionError):
        gate.check(directory, '0.9.0a3')

  def test_missing_auditwheel_evidence(self):
    with tempfile.TemporaryDirectory() as directory:
      gate = self.distributions(directory)
      next(Path(directory).glob('*.auditwheel.txt')).unlink()
      with self.assertRaisesRegex(AssertionError, 'Missing auditwheel show report'):
        gate.check(directory, '0.9.0a3')

  def test_wrong_release_tag(self):
    with tempfile.TemporaryDirectory() as directory:
      gate = self.distributions(directory)
      with self.assertRaises(AssertionError):
        gate.check(directory, '0.9.0a3', 'v0.9.0')

  def test_elf_symbol_floor(self):
    repair = script('repair')
    repair.check_versions('GLIBC_2.28 GLIBCXX_3.4.25 CXXABI_1.3.11')
    for version in ['GLIBC_2.29', 'GLIBCXX_3.4.26', 'CXXABI_1.3.12']:
      with self.subTest(version=version), self.assertRaisesRegex(ValueError, 'baseline'):
        repair.check_versions(version)

  def test_auditwheel_symbol_verdict(self):
    repair = script('repair')
    # The filename alone must never be enough to pass an audit.
    report = ('curry-0.9.0a3-cp311-cp311-manylinux_2_28_x86_64.whl is '
              'consistent with the following platform tag: "linux_x86_64".')
    with self.assertRaises(AssertionError):
      repair.check_auditwheel_report(report)
    repair.check_auditwheel_report(report + '\nThis constrains the platform tag '
                                  'to "manylinux_2_28_x86_64".')
    with self.assertRaises(AssertionError):
      repair.check_auditwheel_report(report + '\nThis constrains the platform tag '
                                    'to "manylinux_2_34_x86_64".')


if __name__ == '__main__':
  unittest.main()
