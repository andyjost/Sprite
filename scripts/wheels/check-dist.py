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
# The platform tag of each target and the report beside its wheels:
# auditwheel show on Linux, the load commands on macOS (repair.py).
PLATFORMS = [('manylinux_2_28_x86_64', '.auditwheel.txt'),
             ('manylinux_2_28_aarch64', '.auditwheel.txt'),
             ('macosx_14_0_arm64', '.otool.txt'),
             ('macosx_14_0_x86_64', '.otool.txt')]
SDIST_FILES = ['pyproject.toml', 'VERSION', 'README.pypi.md', 'LICENSE',
               'CMakeLists.txt', 'scripts/build-package.py',
               'src/curryrt/curryrt.hpp', 'src/python/__init__.pyi',
               'scripts/library_pins.py', 'curry/lib/Prelude.curry',
               *['curry/lib/.curry/sprite-pakcs-3.10.0/Prelude' + suffix
                 for suffix in ('.icy', '.fint', '.icurry', '.icy.imports', '.icy.source')],
               'extern/pybind11/include/pybind11/pybind11.h',
               'extern/pybind11/tools/pybind11Common.cmake',
               'extern/pybind11/CMakeLists.txt', 'extern/pybind11/LICENSE']


def check(directory, version, tag=''):
  directory = Path(directory)
  expected = {(py, abi, tag) for py, abi in PYTHONS for tag, _ in PLATFORMS}
  found = set()
  wheels = sorted(directory.glob('*.whl'))
  assert len(wheels) == 24, f'Expected twenty-four wheels, got {len(wheels)}'
  for wheel in wheels:
    name, actual_version, py, abi, platform = wheel.stem.split('-')
    assert (name, actual_version) == ('curry', version), wheel
    tags = platform.split('.')
    matches = [(t, suffix) for t, suffix in PLATFORMS if t in tags]
    assert len(matches) == 1, wheel
    platform_tag, suffix = matches[0]
    report = wheel.with_suffix(suffix)
    kind = 'auditwheel show' if suffix == '.auditwheel.txt' else 'load commands'
    assert report.is_file(), f'Missing {kind} report for {wheel.name}'
    entry = (py, abi, platform_tag)
    assert entry in expected and entry not in found, entry
    found.add(entry)
    with zipfile.ZipFile(wheel) as archive:
      metadata = BytesParser().parsebytes(archive.read(f'curry-{version}.dist-info/METADATA'))
      assert metadata['Name'] == 'curry' and metadata['Version'] == version
      assert metadata.get_all('Requires-Dist') == ['curry-frontend>=3.1.0'], metadata.get_all('Requires-Dist')
      assert 'Development Status :: 3 - Alpha' in metadata.get_all('Classifier')
      assert metadata['License-Expression'] == 'BSD-3-Clause'
  assert found == expected, expected - found
  sdists = list(directory.glob('*.tar.gz'))
  assert len(sdists) == 1 and sdists[0].name == f'curry-{version}.tar.gz', sdists
  with tarfile.open(sdists[0]) as archive:
    names = set(archive.getnames())
    for name in SDIST_FILES:
      assert f'curry-{version}/' + name in names, name
  if tag:
    assert tag == 'v' + version, (tag, version)
  print(f'Validated twenty-four wheels, manylinux_2_28 and macOS, and the sdist for {version}.')


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('directory', type=Path)
  args = parser.parse_args()
  check(args.directory, Path('VERSION').read_text().strip(), os.environ.get('RELEASE_TAG', ''))
