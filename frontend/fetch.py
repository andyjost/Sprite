#!/usr/bin/env python3
'''Fetch a checksum-pinned front-end source, separately from compilation.'''
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
SOURCES = {
    '2.0.0': (
        'https://www.curry-lang.org/pakcs/download/pakcs-3.4.1-src.tar.gz',
        '71e8030e2efb2295c5862e0c09c9ea2497cfc3b971d8903ce40df66d25e47c22'),
    '3.1.0': (
        'https://api.github.com/repos/cau-placc/curry-frontend/tarball/v3.1.0',
        '13d68be89369a3fdfd1ef2d6e8d4657ab286876f9063bb0b27332de54c6be75c'),
}


def download(url, path):
  print('Fetching ' + url, flush=True)
  with urlopen(url, timeout=120) as response, path.open('wb') as dest:
    shutil.copyfileobj(response, dest)
  digest = hashlib.sha256(path.read_bytes()).hexdigest()
  print(digest + '  ' + path.name, flush=True)
  path.with_suffix(path.suffix + '.sha256').write_text(digest + '  ' + path.name + '\n')
  return digest


def extract(archive, destination):
  destination.mkdir(parents=True, exist_ok=True)
  # data_filter is available since the minimum supported Python 3.11.4.
  with tarfile.open(archive) as tar:
    tar.extractall(destination, filter='data')


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', required=True, type=Path)
  parser.add_argument('--version', choices=SOURCES, default='2.0.0')
  parser.add_argument('--archive', type=Path, help='use a local archive with the same checksum pin')
  parser.add_argument('--url')
  parser.add_argument('--sha256')
  args = parser.parse_args()
  if bool(args.url) != bool(args.sha256):
    parser.error('--url and --sha256 must be supplied together')
  dest = args.output.resolve()
  dest.mkdir(parents=True, exist_ok=True)
  archive = dest / 'source.tar.gz'
  pinned_url, pinned_digest = SOURCES[args.version]
  url = args.url or pinned_url
  expected_digest = args.sha256 or pinned_digest
  origin = 'pinned-url' if args.url else ('pakcs-3.4.1-source' if args.version == '2.0.0'
      else 'github-curry-frontend-v3.1.0')
  if args.archive:
    shutil.copy2(args.archive, archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
  else:
    digest = download(url, archive)
  if digest != expected_digest:
    raise SystemExit('Source checksum mismatch: ' + digest)
  extract(archive, dest / 'unpacked')
  cabals = sorted((dest / 'unpacked').rglob('*.cabal'))
  matches = [p for p in cabals if re.search(
      r'^name:\s*curry-frontend\s*$', p.read_text(), re.M | re.I)]
  if len(matches) != 1:
    raise SystemExit('Expected one curry-frontend cabal file; found ' + repr(cabals))
  cabal = matches[0]
  if not re.search(r'^version:\s*' + re.escape(args.version) + r'\s*$', cabal.read_text(), re.M | re.I):
    raise SystemExit('Source does not declare curry-frontend version ' + args.version)
  source = cabal.parent
  shutil.copytree(source, dest / 'source')
  licenses = dest / 'licenses'
  shutil.copytree(ROOT / 'licenses', licenses)
  shutil.copy2(source / 'LICENSE', licenses / 'LICENSE.curry-frontend')
  if args.version == '2.0.0':
    # The PAKCS source archive's top-level license takes precedence.
    roots = list((dest / 'unpacked').iterdir())
    if len(roots) == 1 and roots[0].is_dir() and (roots[0] / 'LICENSE').is_file():
      shutil.copy2(roots[0] / 'LICENSE', licenses / 'LICENSE-PAKCS')
  info = dict(url=url, sha256=digest, origin=origin, version=args.version)
  (dest / 'source-info.json').write_text(json.dumps(info, indent=2) + '\n')
  print(json.dumps(info, indent=2), flush=True)
  for p in sorted((dest / 'source').glob('*')):
    print(p.name, flush=True)
    if p.suffix in ('.cabal', '.yaml') or p.name in ('Makefile', 'cabal.project'):
      print(p.read_text(), flush=True)


if __name__ == '__main__':
  main()
