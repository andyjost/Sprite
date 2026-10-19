#!/usr/bin/env python3
"""Repair without renaming Sprite's dlopen libraries; check every shipped ELF."""
import argparse
from pathlib import Path
import platform
import re
import subprocess
import tempfile
import zipfile


LIMITS = {'GLIBC': (2, 28), 'GLIBCXX': (3, 4, 25), 'CXXABI': (1, 3, 11)}
SYSTEM_LIBS = {'libc.so.6', 'libdl.so.2', 'libgcc_s.so.1', 'libm.so.6',
               'libpthread.so.0', 'librt.so.1', 'libstdc++.so.6', 'libutil.so.1',
               'ld-linux-x86-64.so.2', 'ld-linux-aarch64.so.1'}


def check_versions(text):
  for namespace, limit in LIMITS.items():
    versions = re.findall(r'\b' + namespace + r'_(\d+(?:\.\d+)+)\b', text)
    for version in versions:
      if tuple(map(int, version.split('.'))) > limit:
        raise ValueError(f'{namespace}_{version} exceeds the manylinux_2_28 baseline')


def check_auditwheel_report(report):
  text = ' '.join(report.split())
  # show has no --exclude option: its overall tag can be linux because
  # Curry imports are opened by the runtime rather than found by ldd.
  # Its symbol constraint still audits every ELF against manylinux.
  tags = re.findall(r'(?:following platform tag:|constrains the platform tag to) '
                    r'"manylinux_(\d+)_(\d+)_', text)
  assert tags and all(tuple(map(int, version)) <= (2, 28) for version in tags), report
  check_versions(report)


def inspect_wheel(wheel):
  """Read all ELF objects, including the Curry library outside the extension."""
  sonames, needed = set(), set()
  with tempfile.TemporaryDirectory() as directory, zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    assert names.count('curry/_sprite/lib/libcurryrt.so') == 1, names
    assert not any('.libs/' in n or 'libcurryrt-' in n for n in names), names
    assert not any(n.endswith('.gch') or n.startswith('curry/_sprite/tools/') for n in names)
    assert archive.read('curry/_sprite/sysconfig/cxx_compiler').strip()
    extension_seen = False
    for name in names:
      if not name.endswith('.so'):
        continue
      path = Path(archive.extract(name, directory))
      dynamic = subprocess.check_output(['readelf', '-d', str(path)], text=True)
      versions = subprocess.check_output(['readelf', '--version-info', str(path)], text=True)
      check_versions(versions)
      sonames.update(re.findall(r'\(SONAME\).*\[(.*?)\]', dynamic))
      needed.update(re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic))
      if '_curryrtbindings.' in name:
        extension_seen = True
        assert '$ORIGIN/../../../_sprite/lib' in dynamic, dynamic
        assert 'libcurryrt.so' in dynamic, dynamic
    assert extension_seen, 'Missing Python extension'
    assert 'libcurryrt.so' in sonames, sonames
    # The runtime loader opens imports in order by SONAME. They need no
    # filesystem aliases, and auditwheel must leave those names alone too.
    sprite_imports = {n for n in needed if n.startswith('sprite-')}
    assert sprite_imports <= sonames, sprite_imports - sonames
    assert needed <= sonames | SYSTEM_LIBS, needed - sonames - SYSTEM_LIBS
    return sonames


def save_report(wheel):
  report = subprocess.check_output(['auditwheel', 'show', str(wheel)], text=True)
  print(report, flush=True)
  # auditwheel may report an older compatible symbol floor. It must never
  # require a newer glibc or libstdc++; the requested tag is checked below.
  check_auditwheel_report(report)
  assert 'manylinux_2_28_' + platform.machine() in wheel.name
  with wheel.with_suffix('.auditwheel.txt').open('w') as stream:
    stream.write(report)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('wheel', type=Path)
  parser.add_argument('output', type=Path, nargs='?')
  parser.add_argument('--show-only', action='store_true')
  args = parser.parse_args()
  if args.show_only:
    save_report(args.wheel)
    return
  if args.output is None:
    parser.error('repair needs an output directory')
  sonames = inspect_wheel(args.wheel)
  args.output.mkdir(parents=True, exist_ok=True)
  command = ['auditwheel', 'repair', '--plat', 'manylinux_2_28_' + platform.machine(),
             '--exclude', 'libcurryrt.so']
  for name in sorted(sonames):
    if name.startswith('sprite-'):
      command += ['--exclude', name]
  subprocess.run(command + ['--wheel-dir', str(args.output), str(args.wheel)], check=True)
  repaired = list(args.output.glob(args.wheel.name.split('-linux_')[0] + '-manylinux*.whl'))
  assert len(repaired) == 1, repaired
  inspect_wheel(repaired[0])
  save_report(repaired[0])


if __name__ == '__main__':
  main()
