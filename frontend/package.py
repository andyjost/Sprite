#!/usr/bin/env python3
'''Bundle an existing front end and build a wheel without fetching anything.

Example: python frontend/package.py --binary install/tools/curry-frontend
  --output /tmp/frontend-wheel
Requires setuptools, wheel, and (for dynamic GMP) patchelf.
'''
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
SYSTEM_LIBS = {
    'libc.so.6', 'libm.so.6', 'libpthread.so.0', 'libdl.so.2', 'librt.so.1'
  , 'libutil.so.1', 'libgcc_s.so.1'
  }


def output(*args):
  return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def glibc_versions(path):
  return sorted({tuple(map(int, v.split('.'))) for v in
      re.findall(r'\bGLIBC_(\d+(?:\.\d+)+)', output('readelf', '-V', str(path)))})


def bundle(binary, destination, licenses):
  destination.mkdir(parents=True, exist_ok=True)
  target = destination / 'curry-frontend'
  shutil.copy2(binary, target)
  target.chmod(0o755)
  elf = target.read_bytes()[:20]
  if elf[:5] != b'\x7fELF\x02':
    raise ValueError('expected a Linux ELF64 executable')
  machine = struct.unpack('<H' if elf[5] == 1 else '>H', elf[18:20])[0]
  arch = {62: 'x86_64', 183: 'aarch64'}[machine]
  if output(str(target), '--numeric-version').strip() != '2.0.0':
    raise ValueError('the executable must be front end 2.0.0')
  dynamic = output('readelf', '-d', str(target))
  needed = re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic)
  unknown = set(needed) - SYSTEM_LIBS - {'libgmp.so.10'}
  if unknown:
    raise ValueError('unhandled shared libraries: ' + repr(sorted(unknown)))
  ldd = ''
  if 'libgmp.so.10' in needed:
    ldd = output('ldd', str(target))
    match = re.search(r'libgmp\.so\.10 => (\S+)', ldd)
    if not match or not Path(match[1]).is_file():
      raise ValueError('cannot locate libgmp.so.10:\n' + ldd)
    gmp = destination / 'libgmp.so.10'
    shutil.copy2(match[1], gmp)
    # Do not embed a runner prefix or require LD_LIBRARY_PATH.
    subprocess.run(['patchelf', '--set-rpath', '$ORIGIN', str(target)], check=True)
    # Keep the distributor's notice intact when vendoring GMP.
    notice = Path('/usr/share/doc/libgmp10/copyright')
    if not notice.is_file():
      raise ValueError('GMP copyright missing; supply it in this build environment')
    shutil.copy2(notice, licenses / 'LICENSE-GMP')
  versions = {v for path in destination.iterdir() for v in glibc_versions(path)}
  info = dict(
      version='2.0.0', packaging_version='2.0.0.post2', architecture=arch
    , linkage='dynamic' if needed else 'static', needed=needed
    , glibc_required='.'.join(map(str, max(versions))) if versions else None
    , rpath='$ORIGIN' if 'libgmp.so.10' in needed else None
    )
  print(json.dumps(info, indent=2), flush=True)
  if ldd:
    print(ldd, flush=True)
  return info


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--binary', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument('--licenses', type=Path, default=ROOT / 'licenses')
  parser.add_argument('--bundle-only', action='store_true',
      help='write bin/, licenses/, build-info.json; do not build a wheel')
  args = parser.parse_args()
  args.output.mkdir(parents=True, exist_ok=True)
  with tempfile.TemporaryDirectory(prefix='frontend-package-') as tmp:
    project = Path(tmp)
    shutil.copytree(ROOT / 'curry_frontend', project / 'curry_frontend',
        ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('pyproject.toml', 'setup.py'):
      shutil.copy2(ROOT / name, project / name)
    shutil.copytree(args.licenses, project / 'licenses')
    for name in ('LICENSE-PAKCS', 'LICENSE.curry-frontend'):
      if not (project / 'licenses' / name).is_file():
        raise ValueError('required license missing: ' + name)
    package = project / 'curry_frontend'
    info = bundle(args.binary.resolve(), package / 'bin', project / 'licenses')
    shutil.copytree(project / 'licenses', package / 'licenses')
    (package / 'build-info.json').write_text(json.dumps(info, indent=2) + '\n')
    (args.output / 'build-info.json').write_text(json.dumps(info, indent=2) + '\n')
    if args.bundle_only:
      shutil.copytree(package, args.output, dirs_exist_ok=True)
    else:
      subprocess.run([
          sys.executable, '-m', 'pip', 'wheel', '--no-index', '--no-deps'
        , '--no-build-isolation', '--wheel-dir', str(args.output.resolve())
        , str(project)
        ], check=True)


if __name__ == '__main__':
  main()
