#!/usr/bin/env python3
"""Extract and maintain the pinned test products (developer tooling only)."""
import argparse
import gzip
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'overlay-pakcs-3.4.1.tgz'
INTERMEDIATE = 'sprite-pakcs-3.4.1'


def git(*args):
  return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def interfaces(directory):
  for icy in directory.rglob('*.icy'):
    if icy.parent.name != INTERMEDIATE:
      continue
    for suffix in ['.fint', '.icurry']:
      src = icy.parent.parent / 'pakcs-3.4.1' / (icy.stem + suffix)
      if src.is_file():
        shutil.copy2(src, icy.with_suffix(suffix))


def prune(root):
  try:
    commit = git('log', '-1', '--format=%H', '--', ARCHIVE)
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
                  commit, str(root), INTERMEDIATE], check=True)


def archive_products(root):
  products = {
      str(p.relative_to(root)): p
      for p in (root / 'tests').rglob('*') if p.is_file() and '.curry' in p.parts
      and any(p.name.endswith(s) for s in ['.fcy', '.fint', '.icurry', '.icy', '.json.z'])
    }
  # The library is built out of source now. Keep its interfaces under the
  # historical curry/lib names in the test archive.
  library = root / 'install/curry/.curry/pakcs-3.4.1'
  if not library.is_dir():
    raise RuntimeError('make stage before packing the overlay: library interfaces are missing')
  for path in library.rglob('*'):
    if path.suffix in ('.fcy', '.fint', '.icurry'):
      name = 'curry/lib/.curry/pakcs-3.4.1/' + str(path.relative_to(library))
      products[name] = path
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
  args = parser.parse_args()
  archive = ROOT / ARCHIVE
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
      prune(args.root)
      interfaces(args.root / args.directory)
  elif args.action == 'overlay-prune':
    prune(args.root)
  elif args.action == 'overlay-interfaces':
    interfaces(args.root / args.directory)
  elif args.action == 'overlay-archive':
    write_archive(archive, archive_products(ROOT))


if __name__ == '__main__':
  main()
