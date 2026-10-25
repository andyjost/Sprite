#!/usr/bin/env python3
"""Extract and maintain release-specific test products (developer tooling only)."""
import argparse
import gzip
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
  return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def interfaces(directory, subdir='pakcs-3.4.1', prefix=None):
  for icy in directory.rglob('*.icy'):
    if icy.parent.name != 'sprite-' + subdir:
      continue
    for suffix in ['.fint', '.icurry']:
      src = icy.parent.parent / subdir / (icy.stem + suffix)
      if src.is_file():
        shutil.copy2(src, icy.with_suffix(suffix))
  provenance(directory, subdir, prefix)


# The import provenance of an extracted .icy (issue #164): the products of
# the archive are trusted as made against the interfaces beside them, as the
# pinned library's are at the stage.  An archive packed by the current
# toolchain carries the records; this writes the missing ones, after every
# interface of the directory is in place.
SEED = '''
import sys
from curry.toolchain import _interfaces
for line in sys.stdin:
  _interfaces.write(line.rstrip('\\n'))
'''


def provenance(directory, subdir='pakcs-3.4.1', prefix=None):
  missing = [str(icy) for icy in sorted(directory.rglob('*.icy'))
             if icy.parent.name == 'sprite-' + subdir
             and not icy.with_name(icy.name + '.imports').is_file()]
  if not missing:
    return
  python = (ROOT / 'install' if prefix is None else prefix) / 'bin/python'
  if not python.is_file():
    print('overlay-interfaces: WARNING: no installation: %d extracted .icy files keep no import'
          ' provenance and are stale (make stage, then make overlay-interfaces)' % len(missing),
          file=sys.stderr)
    return
  subprocess.run([str(python), '-c', SEED], input='\n'.join(missing) + '\n', text=True, check=True)
  print('overlay-interfaces: import provenance written for %d extracted .icy files' % len(missing))


def prune(root, subdir='pakcs-3.4.1'):
  archive = 'overlay-' + subdir + '.tgz'
  try:
    commit = git('log', '-1', '--format=%H', '--', archive)
  except subprocess.CalledProcessError:
    commit = ''
  if not commit:
    print('overlay-prune: no git history; nothing pruned')
    return
  if git('rev-parse', '--is-shallow-repository') == 'true':
    result = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--verify',
                             '--quiet', commit + '^'], capture_output=True)
    if result.returncode:
      print('overlay-prune: WARNING: this is a shallow clone; history may predate the archive; use fetch-depth 0',
            file=sys.stderr)
  for name in git('diff', '--name-only', commit, '--', 'tests/*.curry').splitlines():
    path = Path(name)
    rel = path.stem
    parent = path.parent
    while parent != Path('.'):
      for product in (root / parent / '.curry').glob('*/' + rel + '.*'):
        print('rm', product)
        product.unlink()
      if parent == Path('tests'):
        break
      rel = parent.name + '/' + rel
      parent = parent.parent
  subprocess.run([sys.executable, str(ROOT / 'scripts/stamp-overlay.py'),
                  commit, str(root), 'sprite-' + subdir], check=True)


def archive_products(root, subdir='pakcs-3.4.1', prefix=None):
  products = {
      str(p.relative_to(root)): p
      for p in (root / 'tests').rglob('*') if p.is_file() and '.curry' in p.parts
      and any(part in (subdir, 'sprite-' + subdir) for part in p.parts)
      and any(p.name.endswith(s) for s in ['.fcy', '.fint', '.icurry', '.icy', '.icy.imports', '.icy.source', '.json.z'])
    }
  # The library is built out of source now. Keep its interfaces under the
  # historical curry/lib names in the test archive.
  library = (root / 'install' if prefix is None else prefix) / 'curry/.curry' / subdir
  if not library.is_dir():
    raise RuntimeError('make stage before packing the overlay: library interfaces are missing')
  for path in library.rglob('*'):
    if path.suffix in ('.fcy', '.fint', '.icurry'):
      name = 'curry/lib/.curry/' + subdir + '/' + str(path.relative_to(library))
      products[name] = path
  # Current-tool library oracles live in the archive. The committed ICurry
  # beside the library sources belongs only to the pinned configuration.
  if subdir != 'pakcs-3.4.1':
    libroot = library.parent.parent
    for path in libroot.rglob('*'):
      if path.is_file() and 'sprite-' + subdir in path.parts \
          and any(path.name.endswith(s) for s in ('.icy', '.json.z', '.fint', '.icurry')):
        products['curry/lib/' + str(path.relative_to(libroot))] = path
  return sorted(products.items())


def write_archive(destination, products):
  with destination.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as zipped:
    with tarfile.open(fileobj=zipped, mode='w') as stream:
      for name, path in products:
        info = stream.gettarinfo(path, arcname=name)
        info.uid = info.gid = 0
        info.uname = info.gname = ''
        info.mtime = 946684800
        with path.open('rb') as data:
          stream.addfile(info, data)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('action')
  parser.add_argument('--root', type=Path, default=ROOT)
  parser.add_argument('--directory', type=Path, default=Path('tests'))
  parser.add_argument('--verbose', action='store_true')
  parser.add_argument('--prefix', type=Path,
                      default=Path(os.environ.get('SPRITE_HOME', ROOT / 'install')))
  args = parser.parse_args()
  setting = args.prefix / 'sysconfig/frontend_subdir'
  subdir = setting.read_text().strip() if setting.is_file() else 'pakcs-3.4.1'
  if subdir not in ('pakcs-3.4.1', 'pakcs-3.10.0'):
    parser.error('unsupported overlay release: ' + subdir)
  archive = ROOT / ('overlay-' + subdir + '.tgz')
  if args.action == 'overlay':
    if archive.exists():
      with tarfile.open(archive) as stream:
        for member in stream:
          if not member.name.startswith('tests/'):
            continue
          stream.extract(member, args.root, filter='data')
          path = args.root / member.name
          if path.is_file():
            os.utime(path, None)
          if args.verbose:
            print(member.name)
      prune(args.root, subdir)
      interfaces(args.root / args.directory, subdir, args.prefix)
  elif args.action == 'overlay-prune':
    prune(args.root, subdir)
  elif args.action == 'overlay-interfaces':
    interfaces(args.root / args.directory, subdir, args.prefix)
  elif args.action == 'overlay-archive':
    write_archive(archive, archive_products(ROOT, subdir, args.prefix))


if __name__ == '__main__':
  main()
