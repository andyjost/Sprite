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
  # environment, where the console script of the front end, a build
  # requirement, finds its module.  The front end runs twice in a stage,
  # once from here over the library and once from the staged sprite-make,
  # so the one environment of the stage carries the path.
  pythonpath = os.pathsep.join(
      p for p in [str(Path(prefix) / 'python'), os.environ.get('PYTHONPATH', '')]
        if p)
  env.update(SPRITE_HOME=str(prefix), PYTHONPATH=pythonpath,
             SPRITE_FRONTEND_WARNINGS='0')
  return env


def main():
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
    if path.suffix not in ('.py', '.pyi', '.typed') or 'llvm' in path.parts:
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
  flat = lib / '.curry/pakcs-3.4.1'
  suffixes = ['.fcy', '.fint', '.icurry']
  needs_interfaces = any(
      not (flat / path.relative_to(source / 'curry/lib').with_suffix(s)).exists()
      or (flat / path.relative_to(source / 'curry/lib').with_suffix(s)).stat().st_mtime
          < path.stat().st_mtime
      for path in sources for s in suffixes)
  if needs_interfaces:
    run(args.frontend, '--flat', '-o', flat, '--no-verb', '--no-warn',
        '--no-overlap-warn', '--extended', '-D__PAKCS__=304', '-i', '.', *modules)
  for path in sources:
    rel = path.relative_to(source / 'curry/lib')
    dest = lib / rel.parent / '.curry/sprite-pakcs-3.4.1' / rel.stem
    for suffix in ['.fint', '.icurry']:
      copy(flat / rel.with_suffix(suffix), dest.with_suffix(suffix))
    pinned = path.with_suffix('.icy')
    if pinned.exists() and args.rebuild_icy.upper() not in ('1', 'ON', 'TRUE'):
      copy(pinned, dest.with_suffix('.icy'))
      # A copied pinned artifact is current even in a fresh checkout.
      if dest.with_suffix('.icy').stat().st_mtime < (lib / rel).stat().st_mtime:
        os.utime(dest.with_suffix('.icy'), None)
    elif pinned.exists():
      dest.with_suffix('.icy').unlink(missing_ok=True)
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
    icy = lib / rel.parent / '.curry/sprite-pakcs-3.4.1' / (rel.stem + '.icy')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    Path(str(icy) + '.source').write_text(digest)
  if args.wheel:
    # pip has no post-install prefix rewrite. Keep the digest and express
    # its installation provenance relative to the stamp's own directory.
    for stamp in lib.rglob('*.so.abi'):
      digest = stamp.read_text().splitlines()[0]
      stamp.write_text('%s\n%s\n' % (
          digest, os.path.relpath(prefix, stamp.parent)))
  for suffix in ['.json.z', '.so', '.so.abi']:
    if not (lib / '.curry/sprite-pakcs-3.4.1' / ('Prelude' + suffix)).is_file():
      raise RuntimeError('prebuild did not write Prelude' + suffix)


if __name__ == '__main__':
  main()
