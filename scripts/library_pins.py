"""Inventory and source receipts of the shipped current-pair library products."""
import hashlib
from pathlib import Path
import sys


SUBDIR = 'sprite-pakcs-3.10.0'
SUFFIXES = ('.icy', '.fint', '.icurry', '.icy.imports', '.icy.source')


def product(source):
  return source.parent / '.curry' / SUBDIR / (source.stem + '.icy')


def problem(source):
  icy = product(source)
  for suffix in SUFFIXES:
    if not icy.with_suffix(suffix).is_file():
      return 'missing ' + suffix
  receipt = icy.with_suffix('.icy.source').read_text().strip()
  if receipt != hashlib.sha256(source.read_bytes()).hexdigest():
    return 'source receipt differs from source'
  return None


def check(root):
  for source in sorted(Path(root).rglob('*.curry')):
    if '.curry' in source.relative_to(root).parts:
      continue
    error = problem(source)
    if error:
      name = '.'.join(source.relative_to(root).with_suffix('').parts)
      raise SystemExit('Pinned library module %s: %s; rebuild with the Curry front end.'
                       % (name, error))


if __name__ == '__main__':
  check(sys.argv[1])
