#!/usr/bin/env python3
"""Run the CPM test-suite survey serially, using a private test index.

Invoke with a scratch HOME, the original downloaded index, and a work
folder. Each package gets one wall-clock and address-space budget.
"""
import argparse
import csv
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time


def version(text):
  return tuple(map(int, text.split('.')))


def fits(text, base=(3, 4, 0)):
  for alternative in (text or '').split('||'):
    good = True
    for op, value in re.findall(r'(>=|<=|>|<|\^|=)?\s*(\d+\.\d+\.\d+)', alternative):
      v = version(value)
      good &= {'>=': base >= v, '<=': base <= v, '>': base > v,
               '<': base < v, '=': base == v, '': base == v,
               '^': v <= base < (v[0] + 1, 0, 0)}[op]
    if good:
      return True
  return False


def classify(output, code):
  if code == 124:
    return 'timeout'
  if not code:
    if 'No tests, just compiling' in output:
      return 'Sprite error: CurryCheck unavailable; compilation only'
    return 'pass'
  if 'not implemented' in output:
    return 'missing external: ' + next(line.strip() for line in output.splitlines()
                                      if 'not implemented' in line)
  if any(text in output for text in ('FAILED', 'Falsified', 'falsified')):
    return 'test failure: ' + ' '.join(line.strip() for line in output.splitlines()
                                      if any(t in line for t in ('FAILED', 'Falsified', 'falsified')))[-800:]
  if ('Interface for module' in output and 'not found' in output) or any(
      text in output for text in ('Syntax error', 'syntax error', 'Type error',
                                    'type error', 'Ambiguous', 'Undefined', 'not found in module', 'Unexpected token')):
    return 'front-end error: ' + ' '.join(output.splitlines()[-5:])[-800:]
  lines = [line.strip() for line in output.splitlines()
           if any(t in line for t in ('Error', 'ERROR', 'CRITICAL', 'Exception', 'error:', 'Expected module for'))]
  return 'Sprite error: ' + (' '.join(lines[-3:]) or 'cypm status %d' % code)[-1000:]


def property_results(output):
  """Count completed property reports, not individual generated test cases."""
  passed = re.findall(r'(?m)^.+:\n (?:Passed all available tests:|OK, passed)', output)
  passed += re.findall(r'(?m)^.+: OK$', output)
  failed = re.findall(r'(?m)^.+(?: failed|: FAILED!|: EXECUTION FAILURE:.*|: FAILURE:.*)$', output)
  if not passed and not failed:
    return 'not run', 'not run'
  return len(passed), len(failed)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--cypm', required=True)
  parser.add_argument('--sprite', required=True)
  parser.add_argument('--index', type=Path, required=True)
  parser.add_argument('--work', type=Path, required=True)
  parser.add_argument('--csv', type=Path, default=Path('LANE-INDEX.csv'))
  args = parser.parse_args()
  spec = importlib.util.spec_from_file_location('overlay', Path(__file__).with_name('cpm-test-overlay.py'))
  overlay = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(overlay)
  index = Path(os.environ['HOME']) / 'sprite-index'
  overlay.overlay(args.index, index)
  args.work.mkdir(parents=True, exist_ok=True)
  packages = {}
  for path in index.rglob('package.json'):
    data = json.loads(path.read_text(), strict=False)
    packages.setdefault(data['name'], []).append(data)
  selected = []
  for name, versions in sorted(packages.items()):
    if any(data.get('testsuite') for data in versions):
      candidates = [d for d in versions if fits(d.get('dependencies', {}).get('base', ''))]
      if not candidates:
        raise ValueError('no version fitting base: ' + name)
      selected.append(max(candidates, key=lambda d: version(d['version'])))
  command = [args.cypm, '-d', 'CURRYBIN=' + str(Path(args.sprite).resolve()),
             '-d', 'REPOSITORYPATH=' + str(index)]
  rows = []
  def sanitize(text):
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    for path, replacement in [(str(Path.cwd()), '<worktree>'),
                              (str(Path(os.environ['HOME']).parent), '<scratch>')]:
      text = text.replace(path, replacement)
    # Tool diagnostics may name the compiler's installation outside scratch.
    text = re.sub(r'/(?:[^\s:]+/)+[^\s:]*', '<path>', text)
    return text
  for data in selected:
    name, ver = data['name'], data['version']
    directory = args.work / name
    started = time.monotonic()
    outputs = []
    status = 'pass'
    measurements = {}
    properties = ('not run', 'not run')
    stages = [('checkout', ['checkout', name, ver, '-o', str(directory)], Path.cwd()),
              ('install', ['install'], directory), ('test', ['test'], directory)]
    for stage, arguments, cwd in stages:
      stage_started = time.monotonic()
      while True:
        remaining = max(1, int(1800 - (time.monotonic() - started)))
        result = subprocess.run(['timeout', str(remaining), 'prlimit', '--as=8000000000',
                                 *command, *arguments], cwd=cwd, capture_output=True, text=True)
        output = sanitize(result.stdout + result.stderr)
        outputs.append(stage + '\n' + output)
        # CPM also reads downloaded manifests after acquiring dependencies.
        if stage == 'checkout':
          overlay.patch(directory)
          overlay.patch_downloads([Path(os.environ['HOME']) / '.cpm/packages'])
        changed = 0
        if stage == 'install':
          changed = overlay.patch_downloads([Path(os.environ['HOME']) / '.cpm/packages'])
          changed += overlay.patch(directory / '.cpm/packages')
        if changed and result.returncode != 124 and time.monotonic() - started < 1800:
          outputs.append('Applied compatibility overlay to newly acquired manifests.\n')
          continue
        current = classify(output, result.returncode)
        break
      measurements[stage] = (round(time.monotonic() - stage_started, 1), current)
      if stage == 'test':
        properties = property_results(output)
      if current != 'pass':
        if status == 'pass':
          status = current
        if stage == 'checkout' or result.returncode == 124:
          break
    seconds = round(time.monotonic() - started, 1)
    (args.work / (name + '.log')).write_text('\n'.join(outputs), encoding='ascii', errors='backslashreplace')
    rows.append([name, ver, status, seconds,
                 *measurements.get('install', ('', 'not run')),
                 *measurements.get('test', ('', 'not run')),
                 ('SPRITE_DISABLE_SYSLIB_CHECKS=' + os.environ['SPRITE_DISABLE_SYSLIB_CHECKS']
                  if 'SPRITE_DISABLE_SYSLIB_CHECKS' in os.environ else ''),
                 *properties])
    with args.csv.open('w') as stream:
      writer = csv.writer(stream)
      writer.writerow(['package', 'version', 'result', 'seconds',
                       'install_seconds', 'install_outcome', 'test_seconds',
                       'test_outcome', 'syslib_check_setting', 'properties_passed',
                       'properties_failed'])
      writer.writerows(rows)
    print(name, ver, status, seconds, flush=True)


if __name__ == '__main__':
  main()
