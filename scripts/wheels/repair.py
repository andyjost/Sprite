#!/usr/bin/env python3
"""Repair without renaming Sprite's dlopen libraries; check every shipped ELF.

On macOS nothing is vendored: the runtime library and the compiled Curry
library are files of the wheel, named by @rpath and by install name, and
the wheel is tagged with its deployment target by the build.  The repair
checks every Mach-O file of the wheel (the libraries it loads, its floor,
the run path of the extension) and copies the wheel; --show-only writes the
load commands beside it, as auditwheel show is written on Linux.

On Windows the runtime library is a file of the wheel that the package opens
through os.add_dll_directory before the extension imports; delvewheel vendors
the C and C++ runtimes of Visual Studio (MSVCP140, VCRUNTIME140), which a
machine without the redistributable lacks, into curry.libs under their own
names and makes the package's __init__ add that directory.  The repair checks
the files of the wheel before and after, lists the imports of every DLL and
extension with dumpbin when the developer environment provides it, and
--show-only writes that listing beside the wheel.
"""
import argparse
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
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


# macOS (issue #162, step 4).  The directories of the system libraries;
# every other library a file loads must be a file of the wheel, named by
# @rpath, @loader_path or its install name.
MACOS_SYSTEM_DIRS = ('/usr/lib/', '/System/Library/')
MACHO_MAGICS = {b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe'}


def otool(*args):
  return subprocess.check_output(['otool', *args], text=True)


def macho_files(directory):
  for path in sorted(Path(directory).rglob('*')):
    if path.is_file() and not path.is_symlink():
      with path.open('rb') as stream:
        if stream.read(4) in MACHO_MAGICS:
          yield path


def install_name(path):
  """The install name of a dylib, or None for an executable or a bundle."""
  lines = otool('-D', str(path)).splitlines()
  return lines[1].strip() if len(lines) > 1 and lines[1].strip() else None


def loaded_libraries(path):
  """The libraries a Mach-O file loads, its own install name left out."""
  own = install_name(path)
  lines = otool('-L', str(path)).splitlines()[1:]
  names = [line.split()[0] for line in lines if line.strip()]
  return [name for name in names if name != own]


def macos_floor(path):
  """The minimum macOS of a Mach-O file as a tuple, or None."""
  text = otool('-l', str(path))
  match = re.search(r'LC_BUILD_VERSION.*?minos (\d+(?:\.\d+)*)', text, re.S) \
      or re.search(r'LC_VERSION_MIN_MACOSX.*?version (\d+(?:\.\d+)*)', text, re.S)
  return tuple(map(int, match.group(1).split('.'))) if match else None


def run_paths(path):
  return re.findall(r'LC_RPATH.*?path (\S+)', otool('-l', str(path)), re.S)


def wheel_tag_floor(wheel):
  """The macOS floor and the architecture of the platform tag of a wheel."""
  match = re.search(r'-macosx_(\d+)_(\d+)_(arm64|x86_64)\.whl$', wheel.name)
  assert match, wheel.name
  return (int(match.group(1)), int(match.group(2))), match.group(3)


def inspect_wheel_darwin(wheel, check_floor=True):
  """
  Check every Mach-O file of the wheel; return the report of their load
  commands and the highest floor among them.  With ``check_floor`` a floor
  above the tag's is an error.
  """
  tag_floor, arch = wheel_tag_floor(wheel)
  assert arch == platform.machine(), wheel.name
  report = []
  highest = (0, 0)
  with tempfile.TemporaryDirectory() as directory, zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    assert names.count('curry/_sprite/lib/libcurryrt.dylib') == 1, names
    # delocate vendors into .dylibs; nothing of the kind is expected.
    assert not any('.dylibs/' in n or 'libcurryrt-' in n for n in names), names
    assert not any(n.endswith('.gch') or n.startswith('curry/_sprite/tools/') for n in names)
    assert archive.read('curry/_sprite/sysconfig/cxx_compiler').strip()
    archive.extractall(directory)
    files = list(macho_files(directory))
    install_names = {name for name in (install_name(p) for p in files) if name}
    extension_seen = False
    for path in files:
      relative = path.relative_to(directory)
      libraries = loaded_libraries(path)
      floor = macos_floor(path)
      report.append('%s (minos %s)' % (relative, '.'.join(map(str, floor)) if floor else '?'))
      report.extend('    ' + name for name in libraries)
      for name in libraries:
        assert name.startswith(MACOS_SYSTEM_DIRS) \
            or name.startswith(('@rpath/', '@loader_path/')) \
            or name in install_names, (str(relative), name)
      if floor is not None:
        highest = max(highest, floor)
        assert not check_floor or floor <= tag_floor, (str(relative), floor, tag_floor)
      if '_curryrtbindings.' in path.name:
        extension_seen = True
        assert '@loader_path/../../../_sprite/lib' in run_paths(path), run_paths(path)
        assert any(name.endswith('libcurryrt.dylib') for name in libraries), libraries
    assert extension_seen, 'Missing Python extension'
  return '\n'.join(report) + '\n', highest


def save_report_darwin(wheel):
  report, _ = inspect_wheel_darwin(wheel)
  print(report, flush=True)
  wheel.with_suffix('.otool.txt').write_text(report)


def repair_darwin(wheel, output):
  """
  The wheel is checked and copied: there is nothing to vendor.  A wheel
  whose tag claims a floor below the highest floor of its files is tagged
  with that floor first (the deployment target of the build), as the wheel
  of the front end is (frontend/tag-wheel.py).
  """
  report, highest = inspect_wheel_darwin(wheel, check_floor=False)
  tag_floor, arch = wheel_tag_floor(wheel)
  output.mkdir(parents=True, exist_ok=True)
  if highest > tag_floor:
    # The tags of macOS 11 and later name a major version alone (pip lists
    # macosx_15_0, macosx_14_0, ...), so a floor with a minor version
    # means the next major.
    if highest[0] >= 11 and highest[1] > 0:
      highest = (highest[0] + 1, 0)
    tag = 'macosx_%d_%d_%s' % (highest[0], highest[1], arch)
    print('Tagging %s with %s, the floor of its files' % (wheel.name, tag), flush=True)
    with tempfile.TemporaryDirectory() as directory:
      staged = Path(directory) / wheel.name
      shutil.copy2(wheel, staged)
      subprocess.run([sys.executable, '-m', 'wheel', 'tags', '--remove',
                      '--platform-tag', tag, str(staged)], check=True)
      tagged = list(Path(directory).glob('*.whl'))
      assert len(tagged) == 1, tagged
      target = output / tagged[0].name
      shutil.copy2(tagged[0], target)
  else:
    target = output / wheel.name
    shutil.copy2(wheel, target)
  save_report_darwin(target)


# Windows (the wheels of windows-2025, clang-cl).  The DLLs a file of the
# wheel may import: the system's, the C and C++ runtimes of Visual Studio,
# Python's, and the runtime library of the wheel.
WINDOWS_SYSTEM_DLLS = re.compile(
    r'^(api-ms-win-.*|ext-ms-.*|kernel32|user32|advapi32|ws2_32|shell32|ole32'
    r'|oleaut32|bcrypt|ntdll|msvcrt|ucrtbase|vcruntime140(_1)?|msvcp140(_\d)?'
    r'|concrt140|python3\d*t?|libcurryrt)\.dll$', re.I)


def windows_binaries(directory):
  for path in sorted(Path(directory).rglob('*')):
    if path.is_file() and path.suffix.lower() in ('.dll', '.pyd'):
      yield path


def dumpbin_dependents(path):
  """The DLLs a PE file imports, by dumpbin; None without dumpbin."""
  if shutil.which('dumpbin') is None:
    return None
  text = subprocess.check_output(['dumpbin', '/nologo', '/dependents', str(path)], text=True)
  return re.findall(r'^\s+(\S+\.dll)\s*$', text, re.M | re.I)


# The DLLs delvewheel may vendor into curry.libs: the runtimes of Visual Studio.
WINDOWS_VENDORED = {'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll', 'concrt140.dll',
                    'vcruntime140.dll', 'vcruntime140_1.dll'}


def inspect_wheel_windows(wheel, vendored=None):
  """
  Check the files of the wheel; return the listing of their imports.  With
  ``vendored`` True the runtimes of Visual Studio must be in curry.libs,
  with False nothing may be vendored, with None either is accepted.
  """
  report = []
  with tempfile.TemporaryDirectory() as directory, zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    assert names.count('curry/_sprite/lib/libcurryrt.dll') == 1, names
    assert any('_curryrtbindings.' in n and n.endswith('.pyd') for n in names), names
    assert not any(n.endswith('.so') or 'libcurryrt-' in n for n in names), names
    libs = [n for n in names if '.libs/' in n and not n.endswith('/')]
    assert all(n.startswith('curry.libs/') and n.rsplit('/', 1)[1].lower() in WINDOWS_VENDORED
               for n in libs), libs
    if vendored is True:
      assert libs, 'delvewheel vendored nothing'
    elif vendored is False:
      assert not libs, libs
    assert not any(n.endswith('.gch') or n.startswith('curry/_sprite/tools/') for n in names)
    archive.extractall(directory)
    for path in windows_binaries(directory):
      relative = path.relative_to(directory)
      report.append(str(relative))
      dependents = dumpbin_dependents(path)
      if dependents is None:
        report.append('    (dumpbin is not available; the imports were not listed)')
        continue
      report.extend('    ' + name for name in dependents)
      for name in dependents:
        assert WINDOWS_SYSTEM_DLLS.match(name), (str(relative), name)
      if '_curryrtbindings.' in path.name:
        assert any(name.lower() == 'libcurryrt.dll' for name in dependents), dependents
  return '\n'.join(report) + '\n'


def save_report_windows(wheel):
  report = inspect_wheel_windows(wheel)
  print(report, flush=True)
  wheel.with_suffix('.dumpbin.txt').write_text(report)


def repair_windows(wheel, output):
  """
  delvewheel vendors the runtimes of Visual Studio into curry.libs, their
  names kept because the runtime library imports them by name, the runtime
  library itself left where the package opens it.
  """
  inspect_wheel_windows(wheel, vendored=False)
  output.mkdir(parents=True, exist_ok=True)
  subprocess.run([sys.executable, '-m', 'delvewheel', 'repair', '--no-mangle-all',
                  '--exclude', 'libcurryrt.dll', '--wheel-dir', str(output), str(wheel)],
                 check=True)
  target = output / wheel.name
  assert target.is_file(), sorted(output.glob('*.whl'))
  inspect_wheel_windows(target, vendored=True)
  save_report_windows(target)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('wheel', type=Path)
  parser.add_argument('output', type=Path, nargs='?')
  parser.add_argument('--show-only', action='store_true')
  args = parser.parse_args()
  if sys.platform == 'darwin':
    if args.show_only:
      save_report_darwin(args.wheel)
    elif args.output is None:
      parser.error('repair needs an output directory')
    else:
      repair_darwin(args.wheel, args.output)
    return
  if sys.platform == 'win32':
    if args.show_only:
      save_report_windows(args.wheel)
    elif args.output is None:
      parser.error('repair needs an output directory')
    else:
      repair_windows(args.wheel, args.output)
    return
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
