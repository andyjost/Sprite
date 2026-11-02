#!/usr/bin/env python3
"""Make a private CPM index copy for testing Sprite's PAKCS compatibility.

Never install this script or use its output as a user's package index.
"""
import argparse
import json
import os
from pathlib import Path
import shutil


def overlay(source, destination):
  source, destination = Path(source).resolve(), Path(destination).resolve()
  if source == destination or source in destination.parents:
    raise ValueError('the overlay must be separate from the original index')
  shutil.copytree(source, destination, dirs_exist_ok=True)
  count = patch(destination)
  # CPM's optional repository cache contains the original compatibility data.
  for path in destination.glob('REPOSITORY_CACHE*'):
    path.unlink()
  return count


def patch(root):
  """Apply the overlay to metadata in a private index or downloaded copies."""
  count = 0
  for path in Path(root).rglob('package.json'):
    data = json.loads(path.read_text(), strict=False)
    compilers = data.get('compilerCompatibility', {})
    if 'pakcs' in compilers and compilers.get('sprite') != '>= 0.9.0':
      compilers['sprite'] = '>= 0.9.0'
      path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + '\n')
      count += 1
  return count


def patch_downloads(roots):
  home = Path(os.environ['HOME']).resolve()
  count = 0
  for root in roots:
    if home not in Path(root).resolve().parents:
      raise ValueError('downloaded copies must be inside the scratch HOME')
    count += patch(root)
  return count


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('source', type=Path)
  parser.add_argument('destination', type=Path)
  parser.add_argument('--packages', nargs='*', type=Path, default=[],
                      help='downloaded package copies inside the scratch HOME')
  args = parser.parse_args()
  print('Updated %d package specifications' % overlay(args.source, args.destination))
  patch_downloads(args.packages)
