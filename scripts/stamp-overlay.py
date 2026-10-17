#!/usr/bin/env python3
'''Record the source of archived products verified against their packing commit.'''
import argparse
import hashlib
from pathlib import Path
import subprocess


def git(*args):
  return subprocess.check_output(['git', *args], stderr=subprocess.DEVNULL)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('commit')
  parser.add_argument('root', type=Path)
  parser.add_argument('intermediate')
  args = parser.parse_args()
  if git('rev-parse', '--is-shallow-repository').strip() == b'true':
    try:
      git('rev-parse', '--verify', args.commit + '^')
    except subprocess.CalledProcessError:
      return
  sources = git('ls-tree', '-r', '--name-only', args.commit, '--', 'tests')
  for name in sources.decode().splitlines():
    source = Path(name)
    if source.suffix not in ('.curry', '.lcurry') or not source.is_file():
      continue
    text = source.read_bytes()
    if text != git('show', args.commit + ':' + name):
      continue
    digest = hashlib.sha256(text).hexdigest()
    directory = source.parent
    while directory != Path('.'):
      relative = source.relative_to(directory).with_suffix('.icy')
      product = args.root / directory / '.curry' / args.intermediate / relative
      if product.is_file():
        Path(str(product) + '.source').write_text(digest)
      directory = directory.parent


if __name__ == '__main__':
  main()
