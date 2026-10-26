#!/usr/bin/env python3
"""Prepare the staged package and compile its Curry library with its own tools.

CMake builds the native files first. This step owns the source inventories,
interfaces and pinned products; it never writes products into the checkout.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys


def copy(source, target):
  target.parent.mkdir(parents=True, exist_ok=True)
  if target.is_file() and source.read_bytes() == target.read_bytes():
    return
  if target.is_symlink():
    target.unlink()
  shutil.copy2(source, target)


def link(source, target):
  target.parent.mkdir(parents=True, exist_ok=True)
  if target.is_symlink() or target.exists():
    target.unlink()
  target.symlink_to(source)


def compiler_tool(prefix, compiler, launcher=''):
  """
  tools/cxx, the compiler of generated code: a link to the compiler, or a
  wrapper script where a link named cxx cannot run it.  ccache resolves the
  compiler by the name it is invoked as, and the compiler shims of macOS
  (/usr/bin/c++) dispatch on their invoked name through xcode-select, which
  knows no tool called cxx.
  """
  path = prefix / 'tools/cxx'
  if compiler:
    link(compiler, path)
  elif path.exists() or path.is_symlink():
    path.unlink()
  by_name = Path(compiler).resolve().name == 'ccache' if compiler else False
  if compiler and (launcher or by_name or sys.platform == 'darwin'):
    import shlex
    path.unlink()
    command = ([launcher] if launcher else []) + [compiler]
    path.write_text('#!/bin/sh\nexec %s "$@"\n' % shlex.join(command))
    path.chmod(0o755)


def build_environment(prefix):
  env = os.environ.copy()
  for key in list(env):
    if key.startswith('SPRITE_') and key not in ('SPRITE_PRODUCT_CACHE',):
      env.pop(key)
  for key in ['CURRYPATH', 'CFLAGS', 'CXXFLAGS']:
    env.pop(key, None)
  # The package of the stage first, then the path of the caller: in the
  # isolated build of pip (the sdist) it names the site of the build
  # environment, where an explicitly selected front-end console script
  # finds its module. The front end can run twice in a stage,
  # once from here over the library and once from the staged sprite-make,
  # so the one environment of the stage carries the path.
  pythonpath = os.pathsep.join(
      p for p in [str(Path(prefix) / 'python'), os.environ.get('PYTHONPATH', '')]
        if p)
  env.update(SPRITE_HOME=str(prefix), PYTHONPATH=pythonpath,
             SPRITE_FRONTEND_WARNINGS='0')
  return env


def main():
  import library_pins
  parser = argparse.ArgumentParser(description=__doc__)
  for name in ['source', 'prefix', 'frontend', 'pakcs', 'icurry', 'cxx', 'ccache']:
    parser.add_argument('--' + name, default='')
  parser.add_argument('--wheel', action='store_true')
  parser.add_argument('--jobs', default='auto')
  parser.add_argument('--rebuild-icy', default='OFF')
  args = parser.parse_args()
  args.jobs = os.environ.get('SPRITE_BUILD_JOBS', args.jobs)
  source, prefix = Path(args.source).resolve(), Path(args.prefix).resolve()
  package = prefix / 'python/curry'
  for path in package.rglob('*.py'):
    if not (source / 'src/python' / path.relative_to(package)).is_file():
      path.unlink()
      shutil.rmtree(path.parent / '__pycache__', ignore_errors=True)
  for path in sorted(package.rglob('*'), reverse=True):
    if path.is_dir() and not any(path.iterdir()):
      path.rmdir()
  for path in (prefix / 'curry').rglob('*.py'):
    path.unlink()
  for path in (source / 'src/python').rglob('*'):
    if path.suffix not in ('.py', '.pyi', '.typed'):
      continue
    copy(path, prefix / 'python/curry' / path.relative_to(source / 'src/python'))
  for path in (source / 'src/curryrt').rglob('*'):
    if path.suffix in ('.hpp', '.hxx', '.def'):
      copy(path, prefix / 'include/curryrt' / path.relative_to(source / 'src/curryrt'))
  for name, value in [('python', sys.executable),
                      ('curry-frontend', args.frontend), ('pakcs', args.pakcs),
                      ('icurry', args.icurry)]:
    target = prefix / 'tools' / name
    if value:
      link(value, target)
    elif target.is_symlink() or target.exists():
      target.unlink()
  compiler_tool(prefix, args.cxx, args.ccache)
  for path in (source / 'src/export/bin').glob('*.script'):
    target = prefix / 'bin' / path.stem
    copy(path, target)
    target.chmod(0o755)
  for name in ['python', 'pakcs', 'coverage']:
    link('sprite-invoke', prefix / 'bin' / name)
  lib = prefix / 'curry'
  sources = sorted((source / 'curry/lib').rglob('*.curry'))
  sources = [p for p in sources if '.curry' not in p.parts]
  for path in sources + [source / 'curry/lib' / n for n in ['LICENSE', 'NOTICE']]:
    copy(path, lib / path.relative_to(source / 'curry/lib'))
  env = build_environment(prefix)
  def run(*command, cwd=lib):
    print(' '.join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), cwd=cwd, env=env, check=True)
  modules = (prefix / 'sysconfig/currylib_module_names').read_text().split()
  unsupported = (prefix / 'sysconfig/currylib_unsupported_modules').read_text().split()
  def setting(name):
    return (prefix / 'sysconfig' / name).read_text().strip()
  frontend_subdir = setting('frontend_subdir')
  intermediate_subdir = setting('intermediate_subdir')
  frontend_flags = shlex.split(setting('frontend_flags'))
  rebuild = args.rebuild_icy.upper() in ('1', 'ON', 'TRUE')
  use_pinned = setting('frontend_version') == '3.1.0' and not rebuild
  flat = lib / '.curry' / frontend_subdir
  suffixes = ['.fcy', '.fint', '.icurry']
  needs_interfaces = any(
      not (flat / path.relative_to(source / 'curry/lib').with_suffix(s)).exists()
      or (flat / path.relative_to(source / 'curry/lib').with_suffix(s)).stat().st_mtime
          < path.stat().st_mtime
      for path in sources for s in suffixes)
  if needs_interfaces and args.frontend:
    run(args.frontend, '--flat', '-o', flat, '--no-verb', '--no-warn',
        '--no-overlap-warn', *frontend_flags, '-i', '.', *modules)
  for path in sources:
    rel = path.relative_to(source / 'curry/lib')
    dest = lib / rel.parent / '.curry' / intermediate_subdir / rel.stem
    pinned = library_pins.product(path)
    valid_pin = use_pinned and library_pins.problem(path) is None
    if not args.frontend and not valid_pin:
      raise RuntimeError('%s: %s' % (rel, library_pins.problem(path)))
    for suffix in ['.fint', '.icurry']:
      interface = flat / rel.with_suffix(suffix) if args.frontend else pinned.with_suffix(suffix)
      copy(interface, dest.with_suffix(suffix))
      if not args.frontend:
        copy(interface, flat / rel.with_suffix(suffix))
    if valid_pin:
      icy = dest.with_suffix('.icy')
      marker = Path(str(icy) + '.pinned')
      bundle = hashlib.sha256()
      for suffix in library_pins.SUFFIXES:
        bundle.update(suffix.encode('ascii') + b'\0')
        bundle.update(pinned.with_suffix(suffix).read_bytes())
        bundle.update(b'\0')
      digest = bundle.hexdigest()
      if not icy.exists() or not marker.exists() or marker.read_text() != digest:
        if icy.exists() and icy.read_bytes() != pinned.read_bytes():
          # Package extraction can preserve older times, and .source may
          # still match: invalidate derivatives of changed pinned bytes.
          # Keep the published object until its replacement is ready.
          for suffix in ('.json', '.json.z', '.cpp', '.so.abi'):
            dest.with_suffix(suffix).unlink(missing_ok=True)
        copy(pinned, icy)
        for suffix in ('.icy.source', '.icy.imports'):
          copy(pinned.with_suffix(suffix), dest.with_suffix(suffix))
        marker.write_text(digest)
        # The pin already carries the import record of these interfaces.
      elif not Path(str(icy) + '.imports').exists():
        copy(pinned.with_suffix('.icy.imports'), dest.with_suffix('.icy.imports'))
      # A copied pinned artifact is current even in a fresh checkout.
      if dest.with_suffix('.icy').stat().st_mtime < (lib / rel).stat().st_mtime:
        os.utime(dest.with_suffix('.icy'), None)
    elif rebuild:
      # A forced retranslation can change bytes without changing the source
      # digest. Remove derived products rather than trusting their stamps.
      for suffix in ('.icy', '.json', '.json.z', '.cpp', '.so.abi'):
        dest.with_suffix(suffix).unlink(missing_ok=True)
      run(sys.executable, '-m', 'curry.tools.make', '--rewrite-flat', lib / rel,
          '-o', dest.with_suffix('.icy'))
  make = [sys.executable, '-m', 'curry.tools.make']
  run(*make, '--json', '-zc', *modules)
  supported = [m for m in modules if m not in unsupported]
  run(*make, '--so', '--jobs', args.jobs, '-zc', *supported)
  # Wheel installers need not preserve file times or extraction order.
  # These existing provenance sidecars identify unchanged shipped sources.
  for path in sources:
    rel = path.relative_to(source / 'curry/lib')
    icy = lib / rel.parent / '.curry' / intermediate_subdir / (rel.stem + '.icy')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    Path(str(icy) + '.source').write_text(digest)
  if args.wheel:
    # pip has no post-install prefix rewrite. Keep the digest and express
    # its installation provenance relative to the stamp's own directory.
    for stamp in lib.rglob('*.so.abi'):
      lines = stamp.read_text().splitlines()
      lines[1] = os.path.relpath(prefix, stamp.parent)
      stamp.write_text('\n'.join(lines) + '\n')
  for suffix in ['.json.z', '.so', '.so.abi']:
    if not (lib / '.curry' / intermediate_subdir / ('Prelude' + suffix)).is_file():
      raise RuntimeError('prebuild did not write Prelude' + suffix)


if __name__ == '__main__':
  main()
