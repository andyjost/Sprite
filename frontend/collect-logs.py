#!/usr/bin/env python3
'''Copy Haskell tool logs into the artifact tree, including failed builds.'''
import argparse
import os
from pathlib import Path
import shutil


def collect(roots, destination):
  for label, root in roots.items():
    if not root.is_dir():
      print('No logs at ' + str(root), flush=True)
      continue
    for path in sorted(root.rglob('*.log')):
      if path.is_file():
        target = destination / label / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        print(str(path) + ' -> ' + str(target), flush=True)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--source', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  roots = {
      'ghcup-user': Path.home() / '.ghcup/logs'
    , 'ghcup-system': Path('/usr/local/.ghcup/logs')
    , 'cabal': Path(os.environ.get('CABAL_DIR', Path.home() / '.cabal')) / 'logs'
    , 'stack': Path(os.environ.get('STACK_ROOT', Path.home() / '.stack')) / 'logs'
    , 'stack-project': args.source / '.stack-work'
    }
  if os.environ.get('GHCUP_INSTALL_BASE_PREFIX'):
    roots['ghcup-prefix'] = Path(os.environ['GHCUP_INSTALL_BASE_PREFIX']) / '.ghcup/logs'
  collect(roots, args.output)


if __name__ == '__main__':
  main()
