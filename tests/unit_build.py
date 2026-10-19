import cytest # from ./lib; must be first
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import unittest
import zipfile


ROOT = Path(__file__).resolve().parent.parent


def script(name):
  spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/wheels' / (name + '.py'))
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


class TestDistribution(cytest.TestCase):
  def test_metadata(self):
    data = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    project = data['project']
    self.assertEqual(project['name'], 'currylang')
    self.assertIn('Sprite', project['description'])
    self.assertEqual((ROOT / 'VERSION').read_text().strip(), '0.9.0a1')
    self.assertEqual(project['license'], 'BSD-3-Clause')
    self.assertIn('Development Status :: 3 - Alpha', project['classifiers'])
    self.assertTrue((ROOT / project['readme']).is_file())
    self.assertEqual(set(project['urls']), {'Homepage', 'Documentation', 'Source', 'Issues'})
    self.assertNotIn('dependencies', project)
    self.assertEqual(data['build-system']['requires'],
        ['scikit-build-core>=1.1', 'cmake>=3.24', 'ninja', 'curry-frontend>=2.0.0'])
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
        self.assertFalse(any('/object-root/' in n or '/install/' in n for n in names))

  def distributions(self, directory):
    '''A matrix fixture for testing the publication gate, without native code.'''
    gate = script('check-dist')
    metadata = ('Metadata-Version: 2.4\nName: currylang\nVersion: 0.9.0a1\n'
                'License-Expression: BSD-3-Clause\n'
                'Classifier: Development Status :: 3 - Alpha\n\n')
    for py, abi in gate.PYTHONS:
      for arch in gate.ARCHES:
        path = Path(directory) / f'currylang-0.9.0a1-{py}-{abi}-manylinux_2_28_{arch}.whl'
        with zipfile.ZipFile(path, 'w') as archive:
          archive.writestr('currylang-0.9.0a1.dist-info/METADATA', metadata)
        path.with_suffix('.auditwheel.txt').write_text('Audit report fixture\n')
    with tarfile.open(Path(directory) / 'currylang-0.9.0a1.tar.gz', 'w:gz') as archive:
      for name in gate.SDIST_FILES:
        info = tarfile.TarInfo('currylang-0.9.0a1/' + name)
        archive.addfile(info, io.BytesIO())
    return gate

  def test_complete_matrix(self):
    with tempfile.TemporaryDirectory() as directory:
      gate = self.distributions(directory)
      gate.check(directory, '0.9.0a1', 'v0.9.0a1')

  def test_missing_freethreaded_wheel(self):
    with tempfile.TemporaryDirectory() as directory:
      gate = self.distributions(directory)
      next(Path(directory).glob('*-cp314-cp314t-*x86_64.whl')).unlink()
      with self.assertRaisesRegex(AssertionError, 'twelve wheels'):
        gate.check(directory, '0.9.0a1')

  def test_wrong_platform(self):
    with tempfile.TemporaryDirectory() as directory:
      gate = self.distributions(directory)
      path = next(Path(directory).glob('*-cp311-*x86_64.whl'))
      renamed = path.with_name(path.name.replace('manylinux_2_28', 'linux'))
      path.rename(renamed)
      path.with_suffix('.auditwheel.txt').rename(renamed.with_suffix('.auditwheel.txt'))
      with self.assertRaises(AssertionError):
        gate.check(directory, '0.9.0a1')

  def test_missing_auditwheel_evidence(self):
    with tempfile.TemporaryDirectory() as directory:
      gate = self.distributions(directory)
      next(Path(directory).glob('*.auditwheel.txt')).unlink()
      with self.assertRaisesRegex(AssertionError, 'Missing auditwheel show report'):
        gate.check(directory, '0.9.0a1')

  def test_wrong_release_tag(self):
    with tempfile.TemporaryDirectory() as directory:
      gate = self.distributions(directory)
      with self.assertRaises(AssertionError):
        gate.check(directory, '0.9.0a1', 'v0.9.0')

  def test_elf_symbol_floor(self):
    repair = script('repair')
    repair.check_versions('GLIBC_2.28 GLIBCXX_3.4.25 CXXABI_1.3.11')
    for version in ['GLIBC_2.29', 'GLIBCXX_3.4.26', 'CXXABI_1.3.12']:
      with self.subTest(version=version), self.assertRaisesRegex(ValueError, 'baseline'):
        repair.check_versions(version)

  def test_auditwheel_symbol_verdict(self):
    repair = script('repair')
    # The filename alone must never be enough to pass an audit.
    report = ('currylang-0.9.0a1-cp311-cp311-manylinux_2_28_x86_64.whl is '
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
