#!/usr/bin/env python3
"""Gate publication on the complete interpreter/architecture matrix and sdist."""
import argparse
from email.parser import BytesParser
import os
from pathlib import Path
import tarfile
import zipfile


PYTHONS = [('cp311', 'cp311'), ('cp312', 'cp312'), ('cp313', 'cp313'),
           ('cp314', 'cp314'), ('cp314', 'cp314t'), ('cp315', 'cp315')]
ARCHES = ['x86_64', 'aarch64']
SDIST_FILES = ['pyproject.toml', 'VERSION', 'README.pypi.md', 'LICENSE',
               'CMakeLists.txt', 'scripts/build-package.py',
               'src/curryrt/curryrt.hpp', 'src/python/__init__.pyi',
               'curry/lib/Prelude.curry', 'curry/lib/Prelude.icy',
               'extern/pybind11/include/pybind11/pybind11.h',
               'extern/pybind11/tools/pybind11Common.cmake',
               'extern/pybind11/CMakeLists.txt', 'extern/pybind11/LICENSE']


def check(directory, version, tag=''):
  directory = Path(directory)
  expected = {(py, abi, arch) for py, abi in PYTHONS for arch in ARCHES}
  found = set()
  wheels = sorted(directory.glob('*.whl'))
  assert len(wheels) == 12, f'Expected twelve wheels, got {len(wheels)}'
  for wheel in wheels:
    report = wheel.with_suffix('.auditwheel.txt')
    assert report.is_file(), f'Missing auditwheel show report for {wheel.name}'
    name, actual_version, py, abi, platform = wheel.stem.split('-')
    assert (name, actual_version) == ('currylang', version), wheel
    arch = next((a for a in ARCHES if platform.endswith('_' + a)), None)
    assert 'manylinux_2_28_' + str(arch) in platform.split('.'), wheel
    entry = (py, abi, arch)
    assert entry in expected and entry not in found, entry
    found.add(entry)
    with zipfile.ZipFile(wheel) as archive:
      metadata = BytesParser().parsebytes(archive.read(f'currylang-{version}.dist-info/METADATA'))
      assert metadata['Name'] == 'currylang' and metadata['Version'] == version
      assert metadata.get_all('Requires-Dist') == ['curry-frontend>=2.0.0'], metadata.get_all('Requires-Dist')
      assert 'Development Status :: 3 - Alpha' in metadata.get_all('Classifier')
      assert metadata['License-Expression'] == 'BSD-3-Clause'
  assert found == expected, expected - found
  sdists = list(directory.glob('*.tar.gz'))
  assert len(sdists) == 1 and sdists[0].name == f'currylang-{version}.tar.gz', sdists
  with tarfile.open(sdists[0]) as archive:
    names = set(archive.getnames())
    for name in SDIST_FILES:
      assert f'currylang-{version}/' + name in names, name
  if tag:
    assert tag == 'v' + version, (tag, version)
  print(f'Validated twelve manylinux_2_28 wheels and the sdist for {version}.')


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('directory', type=Path)
  args = parser.parse_args()
  check(args.directory, Path('VERSION').read_text().strip(), os.environ.get('RELEASE_TAG', ''))
