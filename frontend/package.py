#!/usr/bin/env python3
'''Bundle an existing front end and build a wheel without fetching anything.

Example: python frontend/package.py --binary install/tools/curry-frontend
  --output /tmp/frontend-wheel
Requires setuptools, wheel, and (for dynamic GMP) patchelf on Linux, or
install_name_tool and codesign of the Xcode command line tools on macOS,
where the executable is a Mach-O file and GMP comes from Homebrew.
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
PACKAGING_VERSIONS = {'2.0.0': '2.0.0.post5', '3.1.0': '3.1.0.post1'}
# Mach-O 64-bit, little-endian magic and the cputype field that follows it.
MACHO_MAGIC_64 = b'\xcf\xfa\xed\xfe'
MACHO_CPUTYPES = {0x0100000c: 'arm64', 0x01000007: 'x86_64'}
# The directories of the system libraries of macOS; anything else that a
# binary loads must be vendored.
MACOS_SYSTEM_DIRS = ('/usr/lib/', '/System/Library/')


def output(*args):
  return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, timeout=30)


def glibc_versions(path):
  return sorted({tuple(map(int, v.split('.'))) for v in
      re.findall(r'\bGLIBC_(\d+(?:\.\d+)+)', output('readelf', '-V', str(path)))})


def copy_gmp_licenses(destination, system_root=Path('/')):
  notice = system_root / 'usr/share/doc/libgmp10/copyright'
  if notice.is_file():
    shutil.copy2(notice, destination / 'LICENSE-GMP')
    return
  # manylinux 2.28 uses RPM license directories. Carry every original
  # notice there, including the alternative GPL/LGPL texts, verbatim.
  license_root = system_root / 'usr/share/licenses'
  notices = sorted(p for p in license_root.glob('gmp*/**/*') if p.is_file())
  if not notices:
    raise ValueError('GMP licenses missing; supply the distributor notices in this build environment')
  for notice in notices:
    name = 'LICENSE-GMP-' + '-'.join(notice.relative_to(license_root).parts)
    shutil.copy2(notice, destination / name)


def copy_gmp_licenses_darwin(destination, dylib):
  '''Homebrew keeps the notices of GMP (COPYING*) in the prefix of the formula.'''
  prefix = Path(os.path.realpath(dylib)).parent.parent
  notices = sorted(p for p in prefix.glob('COPYING*') if p.is_file())
  if not notices:
    raise ValueError('GMP licenses missing under ' + str(prefix))
  for notice in notices:
    shutil.copy2(notice, destination / ('LICENSE-GMP-' + notice.name))


def macho_dylibs(path):
  '''The libraries a Mach-O file loads, as otool -L names them.'''
  lines = output('otool', '-L', str(path)).splitlines()[1:]
  return [line.split()[0] for line in lines if line.strip()]


def macos_min_version(path):
  '''The minimum macOS of a Mach-O file (LC_BUILD_VERSION or the older command), or None.'''
  commands = output('otool', '-l', str(path))
  match = re.search(r'LC_BUILD_VERSION.*?minos (\d+(?:\.\d+)*)', commands, re.S) \
      or re.search(r'LC_VERSION_MIN_MACOSX.*?version (\d+(?:\.\d+)*)', commands, re.S)
  return match.group(1) if match else None


def bundle_macho(target, destination, licenses, head, version):
  '''
  The bundle of a Mach-O executable (macOS): the system libraries stay, GMP
  from Homebrew is vendored beside the executable with @loader_path, and the
  two files are signed again ad hoc, since install_name_tool invalidates the
  signature and arm64 refuses an unsigned executable.  The floor is the
  minimum macOS of the files.
  '''
  cputype = struct.unpack('<I', head[4:8])[0]
  arch = MACHO_CPUTYPES.get(cputype)
  if arch is None:
    raise ValueError('unknown Mach-O cputype 0x%x' % cputype)
  needed = macho_dylibs(target)
  system = [d for d in needed if d.startswith(MACOS_SYSTEM_DIRS)]
  gmp = [d for d in needed if os.path.basename(d).startswith('libgmp')]
  unknown = set(needed) - set(system) - set(gmp)
  if unknown:
    raise ValueError('unhandled shared libraries: ' + repr(sorted(unknown)))
  rpath = None
  if gmp:
    source = Path(gmp[0])
    if not source.is_file():
      raise ValueError('cannot locate ' + str(source))
    vendored = destination / source.name
    shutil.copy2(source, vendored)
    vendored.chmod(0o755)
    loader_name = '@loader_path/' + source.name
    subprocess.run(['install_name_tool', '-id', loader_name, str(vendored)], check=True)
    subprocess.run(['install_name_tool', '-change', str(source), loader_name, str(target)], check=True)
    for path in vendored, target:
      subprocess.run(['codesign', '--force', '--sign', '-', str(path)], check=True)
    copy_gmp_licenses_darwin(licenses, source)
    rpath = '@loader_path'
  versions = [v for v in (macos_min_version(p) for p in destination.iterdir()) if v]
  floor = max(versions, key=lambda v: tuple(map(int, v.split('.')))) if versions else None
  info = dict(
      version=version, packaging_version=PACKAGING_VERSIONS[version], architecture=arch
    , platform='darwin', linkage='dynamic', needed=needed, glibc_required=None
    , macos_required=floor, rpath=rpath
    )
  print(json.dumps(info, indent=2), flush=True)
  print(output('otool', '-L', str(target)), flush=True)
  return info


def bundle(binary, destination, licenses):
  destination.mkdir(parents=True, exist_ok=True)
  target = destination / 'curry-frontend'
  shutil.copy2(binary, target)
  target.chmod(0o755)
  elf = target.read_bytes()[:20]
  version = output(str(target), '--numeric-version').strip()
  if version not in PACKAGING_VERSIONS:
    raise ValueError('the executable must be front end 2.0.0 or 3.1.0')
  if elf[:4] == MACHO_MAGIC_64:
    return bundle_macho(target, destination, licenses, elf, version)
  if elf[:5] != b'\x7fELF\x02':
    raise ValueError('expected an ELF64 or a 64-bit Mach-O executable')
  machine = struct.unpack('<H' if elf[5] == 1 else '>H', elf[18:20])[0]
  arch = {62: 'x86_64', 183: 'aarch64'}[machine]
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
    copy_gmp_licenses(licenses)
  versions = {v for path in destination.iterdir() for v in glibc_versions(path)}
  info = dict(
      version=version, packaging_version=PACKAGING_VERSIONS[version], architecture=arch
    , platform='linux', linkage='dynamic' if needed else 'static', needed=needed
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
    for name in ('pyproject.toml', 'setup.py', 'README.pypi.md'):
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
        ], check=True, env=dict(os.environ, CURRY_FRONTEND_VERSION=info['version']))


if __name__ == '__main__':
  main()
