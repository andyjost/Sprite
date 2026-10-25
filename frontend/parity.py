#!/usr/bin/env python3
'''Compile a clean library copy; compare pinned ICurry and reference interfaces.

Run with the staged Sprite Python on PYTHONPATH. No cache or staged Curry
products are used as compiler inputs. Every failure retains its two sides.
Without --baseline this generates reference interfaces and checks pinned ICurry.
'''
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def run(command, cwd, logfile):
  print('+ ' + repr(command), flush=True)
  with logfile.open('w') as log:
    result = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
  if result.returncode:
    print(logfile.read_text(), flush=True)
  return result.returncode == 0


def compare(expected, actual, report):
  if not expected.is_file() or not actual.is_file():
    report.write_text('Missing expected or actual file: '
        + str(expected) + ', ' + str(actual) + '\n')
    return False
  if expected.read_bytes() == actual.read_bytes():
    return True
  report.write_text(''.join(difflib.unified_diff(
      expected.read_text().splitlines(keepends=True)
    , actual.read_text().splitlines(keepends=True)
    , fromfile='expected', tofile='actual'
    )))
  print('DIFFERENCE: ' + str(report), flush=True)
  return False


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--binary', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument('--baseline', type=Path)
  args = parser.parse_args()
  from curry import config
  subdir = config.frontend_subdir()
  flags = config.frontend_flags().split()
  binary = args.binary.resolve()
  dest = args.output.resolve()
  dest.mkdir(parents=True, exist_ok=True)
  sources = dest / 'sources'
  sources.mkdir()
  lib = ROOT / 'curry' / 'lib'
  originals = sorted(lib.rglob('*.curry'))
  if args.baseline:
    manifest = json.loads((args.baseline / 'manifest.json').read_text())
    for relative, digest in manifest['sources'].items():
      path = ROOT / relative
      if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit('Stale reference: source changed: ' + relative)
    for relative, digest in manifest['interfaces'].items():
      path = args.baseline / relative
      if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit('Reference checksum mismatch: ' + relative)
  for path in originals:
    target = sources / path.relative_to(lib)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
  products = dest / 'products'
  expected = dest / 'expected'
  logs = dest / 'logs'
  diffs = dest / 'diffs'
  for d in (products, expected, logs, diffs):
    d.mkdir()
  failures = []
  for original in originals:
    relative = original.relative_to(lib)
    source = sources / relative
    stem = str(relative.with_suffix('')).replace('/', '.')
    command = [
        str(binary), '--flat', '-o', '.curry/' + subdir
      , *flags, '-i', str(source.parent)
      , '-i', str(sources), source.stem
      ]
    if not run(command, source.parent, logs / (stem + '.frontend.log')):
      failures.append(stem + ': front end failed')
  for original in originals:
    relative = original.relative_to(lib)
    source = sources / relative
    stem = str(relative.with_suffix('')).replace('/', '.')
    flat = source.parent / '.curry' / subdir / (source.stem + '.fcy')
    target = products / relative.with_suffix('.icy')
    target.parent.mkdir(parents=True, exist_ok=True)
    if not flat.is_file():
      failures.append(stem + ': no FlatCurry')
      continue
    command = [
        sys.executable, '-m', 'curry.toolchain.flat2icurry', '--rewrite'
      , '--no-icurry-compat', '-i', str(sources), '-o', str(target), str(flat)
      ]
    if not run(command, ROOT, logs / (stem + '.translator.log')):
      failures.append(stem + ': translator failed')
    interface = flat.with_suffix('.fint')
    actual = products / relative.with_suffix('.fint')
    if interface.is_file():
      shutil.copy2(interface, actual)
    else:
      failures.append(stem + ': no .fint')
    pinned = original.with_suffix('.icy')
    if pinned.is_file():
      ref = expected / relative.with_suffix('.icy')
      ref.parent.mkdir(parents=True, exist_ok=True)
      shutil.copy2(pinned, ref)
      if not compare(ref, target, diffs / (stem + '.icy.diff')):
        failures.append(stem + ': ICurry differs')
    if args.baseline:
      baseline = args.baseline / relative.with_suffix('.fint')
      ref = expected / relative.with_suffix('.fint')
      ref.parent.mkdir(parents=True, exist_ok=True)
      if baseline.is_file():
        shutil.copy2(baseline, ref)
      if not compare(ref, actual, diffs / (stem + '.fint.diff')):
        failures.append(stem + ': interface differs')
  manifest = {str(p.relative_to(products)): hashlib.sha256(p.read_bytes()).hexdigest()
      for p in sorted(products.rglob('*')) if p.is_file()}
  summary = dict(modules=len(originals), pinned_icurry=len(list(lib.rglob('*.icy'))),
      interface_comparison=bool(args.baseline), failures=failures, sha256=manifest)
  (dest / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
  print(json.dumps(summary, indent=2), flush=True)
  return bool(failures)


if __name__ == '__main__':
  sys.exit(main())
