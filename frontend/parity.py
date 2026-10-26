#!/usr/bin/env python3
'''Compile a clean library copy and compare versioned PAKCS reference products.

Use a matching staged Sprite installation. --write-reference generates a
baseline from a trusted PAKCS binary; normal runs select references by version.
'''
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def run(command, cwd, logfile):
  print('+ ' + repr(command), flush=True)
  with logfile.open('w') as log:
    result = subprocess.run(['timeout', '300', *command], cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
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
  parser.add_argument('--baseline', type=Path, default=ROOT / 'frontend/reference')
  parser.add_argument('--write-reference', type=Path, help='generate a versioned reference from the trusted PAKCS binary')
  args = parser.parse_args()
  from curry import config
  subdir = config.frontend_subdir()
  flags = shlex.split(config.frontend_flags())
  binary = args.binary.resolve()
  version = subprocess.check_output(['timeout', '30', str(binary), '--numeric-version'],
      text=True).strip()
  if version != config.frontend_version():
    raise SystemExit('Use a Sprite installation configured for front end ' + version)
  baseline = args.baseline / version
  if not baseline.is_dir():
    baseline = args.baseline  # Legacy 2.0.0 references stay readable.
  if args.write_reference:
    baseline = None
  dest = args.output.resolve()
  dest.mkdir(parents=True, exist_ok=True)
  sources = dest / 'sources'
  sources.mkdir()
  lib = ROOT / 'curry' / 'lib'
  originals = sorted(p for p in lib.rglob('*.curry') if p.is_file())
  if baseline:
    manifest = json.loads((baseline / 'manifest.json').read_text())
    if manifest['frontend_version'] != version:
      raise SystemExit('Reference version does not match binary')
    if manifest['flags'] != ['--flat', *flags]:
      raise SystemExit('Reference flags do not match installation')
    for relative, digest in manifest['sources'].items():
      path = ROOT / relative
      if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit('Stale reference: source changed: ' + relative)
    for relative, digest in manifest.get('products', manifest['interfaces']).items():
      path = baseline / relative
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
    # Preserve the front end's FlatCurry before the in-place rewrite.
    flat_product = products / relative.with_suffix('.fcy')
    shutil.copy2(flat, flat_product)
    command = [
        sys.executable, '-m', 'curry.toolchain.flat2icurry', '--rewrite'
      , '--no-icurry-compat', '-i', str(sources), '-o', str(target), str(flat)
      ]
    if not run(command, ROOT, logs / (stem + '.translator.log')):
      failures.append(stem + ': translator failed')
    # Current-pair pins must agree with the runtime route used above.
    if version == '3.1.0':
      pinned = original.parent / '.curry/sprite-pakcs-3.10.0' / (original.stem + '.icy')
      if not compare(pinned, target, diffs / (stem + '.pinned.diff')):
        failures.append(stem + ': pinned .icy differs')
    interface = flat.with_suffix('.fint')
    actual = products / relative.with_suffix('.fint')
    if interface.is_file():
      shutil.copy2(interface, actual)
    else:
      failures.append(stem + ': no .fint')
    if baseline:
      for suffix in ('.fint', '.fcy', '.icy'):
        reference = baseline / relative.with_suffix(suffix)
        # Legacy references have interfaces alone.
        if suffix != '.fint' and 'products' not in manifest and not reference.is_file():
          continue
        actual_product = products / relative.with_suffix(suffix)
        ref = expected / relative.with_suffix(suffix)
        ref.parent.mkdir(parents=True, exist_ok=True)
        if reference.is_file():
          shutil.copy2(reference, ref)
        if not compare(ref, actual_product, diffs / (stem + suffix + '.diff')):
          failures.append(stem + ': ' + suffix + ' differs')
  manifest = {str(p.relative_to(products)): hashlib.sha256(p.read_bytes()).hexdigest()
      for p in sorted(products.rglob('*')) if p.is_file()}
  summary = dict(modules=len(originals),
      frontend_version=version, interface_comparison=bool(baseline), failures=failures, sha256=manifest)
  if args.write_reference and not failures:
    reference = args.write_reference / version
    reference.mkdir(parents=True, exist_ok=True)
    for path in sorted(products.rglob('*')):
      if path.is_file():
        target = reference / path.relative_to(products)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    metadata = dict(frontend_version=version,
        executable_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
        pakcs_version=config.frontend_subdir().removeprefix('pakcs-'),
        flags=['--flat', *flags],
        sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in originals},
        interfaces={k: v for k, v in manifest.items() if k.endswith('.fint')},
        products=manifest)
    (reference / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
  (dest / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
  print(json.dumps(summary, indent=2), flush=True)
  return bool(failures)


if __name__ == '__main__':
  sys.exit(main())
