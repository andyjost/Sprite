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
import socket
import subprocess
import sys
import time


spec = importlib.util.spec_from_file_location('overlay', Path(__file__).with_name('cpm-test-overlay.py'))
overlay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overlay)


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
  if not code:
    if 'No tests, just compiling' in output:
      return 'Sprite error: CurryCheck unavailable; compilation only'
    return 'pass'
  if any(text in output for text in ('Could not resolve host', 'Connection timed out',
                                     'Failed to connect', 'curl: (28)', 'curl: (7)')):
    urls = re.findall(r'https?://[^\s\"\']+', output)
    return 'network: ' + (' '.join(dict.fromkeys(urls)) or 'download connection failed')
  if code == 124:
    kiel = re.findall(r'https?://(?:www\.informatik|git\.ps\.informatik)\.uni-kiel\.de/[^\s\"\']+', output)
    if kiel:
      return 'network: ' + ' '.join(dict.fromkeys(kiel))
    return 'timeout'
  if 'not implemented' in output:
    return 'missing external: ' + next(line.strip() for line in output.splitlines()
                                      if 'not implemented' in line)
  failure_markers = ('FAILED', 'Falsified', 'falsified', ': FAILURE:',
                     ': EXECUTION FAILURE:', 'Arguments exhausted after')
  if any(text in output for text in failure_markers):
    return 'test failure: ' + ' '.join(line.strip() for line in output.splitlines()
                                      if line.endswith(' failed') or
                                      any(t in line for t in failure_markers))[-800:]
  if ('Interface for module' in output and 'not found' in output) or any(
      text in output for text in ('Syntax error', 'syntax error', 'Type error',
                                    'type error', 'Ambiguous', 'Undefined', 'not found in module', 'Unexpected token')):
    return 'front-end error: ' + ' '.join(output.splitlines()[-5:])[-800:]
  lines = [line.strip() for line in output.splitlines()
           if any(t in line for t in ('Error', 'ERROR', 'CRITICAL', 'Exception', 'error:',
               'Expected module for', 'terminate called', 'what():',
               'Segmentation fault', 'Assertion', 'Aborted', 'std::bad_alloc',
               '*** Evaluation suspended!'))]
  return 'Sprite error: ' + (' '.join(lines[-3:]) or 'cypm status %d' % code)[-1000:]


def property_results(output):
  """Count completed property reports, not individual generated test cases."""
  passed = re.findall(r'(?m)^.+:\n (?:Passed all available tests:|OK, passed)', output)
  passed += re.findall(r'(?m)^.+: OK$', output)
  failed = re.findall(r'(?m)^.+(?:: FAILED!|: EXECUTION FAILURE:.*|: FAILURE:.*)$', output)
  failed += re.findall(r"(?m)^[A-Za-z_][\w.']* failed$", output)
  failed += re.findall(r'(?m)^.+:\n Arguments exhausted after', output)
  if not passed and not failed:
    return 'not run', 'not run'
  return len(passed), len(failed)


def select_packages(index, expected=None):
  packages = {}
  for path in sorted(index.rglob('package.json')):
    data = overlay.read_package(path, warn=False)
    packages.setdefault(data['name'], []).append(data)
  selected = []
  for name, versions in sorted(packages.items()):
    if expected is not None:
      if name not in expected['packages']:
        continue
      candidates = [d for d in versions
                    if d['version'] == expected['packages'][name]['version']]
    else:
      candidates = [d for d in versions if d.get('testsuite') and
                    fits(d.get('dependencies', {}).get('base', ''))]
    if candidates:
      selected.append(max(candidates, key=lambda d: version(d['version'])))
  if expected is not None:
    missing = set(expected['packages']) - {d['name'] for d in selected}
    if missing:
      raise ValueError('pinned versions missing from index: ' + ', '.join(sorted(missing)))
  return selected


def index_digest(index):
  """SHA256 of sorted relative manifest names, NUL, bytes, NUL."""
  return overlay.manifest_digest(index)


def wait_for_proxy():
  """Probe the public index, allowing thirty minutes for proxy recovery."""
  def available():
    return subprocess.run(['curl', '--silent', '--fail', '--head', '--max-time', '15',
        'https://cpm.curry-lang.org/PACKAGES/INDEX.tar.gz'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
  if available():
    return False
  for _ in range(30):
    print('Proxy unavailable; retrying in one minute.', flush=True)
    time.sleep(60)
    if available():
      return True
  raise ConnectionError('proxy unavailable after thirty minutes; retry this package on resume')


def compare(rows, expected):
  failures, improvements = [], []
  for row in rows:
    wanted = expected['packages'][row['package']]
    if row['version'] != wanted['version']:
      failures.append(row['package'] + ': wrong pinned version')
    elif wanted['result'] == 'pass' and row['result'] != 'pass':
      failures.append(row['package'] + ': ' + row['result'])
    elif wanted['result'] in ('exception', 'open', 'network'):
      if row['result'] == 'pass':
        improvements.append(row['package'] + ': ' + wanted['result'] + ' now passes')
      elif wanted['result'] == 'open' and (
          row['result'].split(':', 1)[0] != wanted['failure_class'] or
          wanted.get('failure_match', '') not in row['result']):
        failures.append(row['package'] + ': worse than ' + wanted['issue'] + ': ' + row['result'])
      elif wanted['result'] == 'network' and not row['result'].startswith('network:'):
        failures.append(row['package'] + ': ' + row['result'])
  return failures, improvements


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--cypm', required=True)
  parser.add_argument('--sprite', required=True)
  parser.add_argument('--index', type=Path, required=True)
  parser.add_argument('--work', type=Path, required=True)
  parser.add_argument('--csv', type=Path, default=Path('LANE-INDEX.csv'))
  parser.add_argument('--expected', type=Path, help='test pinned versions and fail on regressions')
  parser.add_argument('--packages', nargs='+', help='run only these package names')
  parser.add_argument('--shard', type=int, default=0, help='zero-based shard number')
  parser.add_argument('--shards', type=int, default=1)
  parser.add_argument('--resume', action='store_true', help='keep completed CSV rows')
  parser.add_argument('--stop-file', type=Path,
                      help='stop between packages when this file exists (default: WORK/STOP)')
  parser.add_argument('--newer', action='store_true', help='list newer compatible versions and exit')
  parser.add_argument('--pakcs', help='PAKCS 3.10.0 system for failed-package comparisons')
  parser.add_argument('--pakcs-checker', type=Path,
                      help='directory containing a PAKCS-built curry-check')
  args = parser.parse_args()
  if not 0 <= args.shard < args.shards:
    parser.error('shard must be in [0, shards)')
  expected = json.loads(args.expected.read_text()) if args.expected else None
  if expected is not None:
    if expected.get('complete') is False and not args.newer:
      parser.error('expected results are incomplete; finish the survey before enabling CI')
    if not expected.get('packages'):
      parser.error('expected results must contain packages')
    for name, pin in expected['packages'].items():
      if pin.get('result') not in ('pass', 'exception', 'open', 'network') or (
          pin['result'] != 'pass' and not pin.get('reason')) or (
          pin['result'] == 'open' and not all(pin.get(key) for key in
              ('issue', 'failure_class', 'failure_match'))) or (
          pin['result'] == 'network' and not pin.get('url')):
        parser.error('invalid expected result for ' + name)
  selected = select_packages(args.index, expected)
  if args.newer:
    if expected is None:
      parser.error('--newer needs --expected')
    for data in select_packages(args.index):
      pin = expected['packages'].get(data['name'])
      if pin is None or version(data['version']) > version(pin['version']):
        print(data['name'], data['version'], '(new)' if pin is None else '(pinned ' + pin['version'] + ')')
    return 0
  selected = [d for i, d in enumerate(selected)
              if (args.packages is None or d['name'] in args.packages) and
              (expected['packages'][d['name']].get('shard', i % args.shards)
               if expected and args.shards > 1 else i % args.shards) == args.shard]
  if not selected:
    parser.error('no packages selected')
  if args.pakcs and not args.pakcs_checker:
    parser.error('--pakcs requires --pakcs-checker to avoid running Sprite CurryCheck')
  index = Path(os.environ['HOME']) / 'sprite-index'
  snapshot = expected.get('index') if expected and expected.get('index', {}).get('versions') else None
  overlay.overlay(args.index, index, snapshot)
  args.work.mkdir(parents=True, exist_ok=True)
  command = [args.cypm, '-d', 'CURRYBIN=' + str(Path(args.sprite).resolve()),
             '-d', 'REPOSITORYPATH=' + str(index)]
  fields = ['package', 'version', 'result', 'seconds',
            'install_seconds', 'install_outcome', 'test_seconds',
            'test_outcome', 'syslib_check_setting', 'properties_passed',
            'properties_failed', 'pakcs_result', 'pakcs_seconds',
            'pakcs_properties_passed', 'pakcs_properties_failed']
  rows = []
  if args.resume and args.csv.exists():
    with args.csv.open() as stream:
      selected_ids = {(d['name'], d['version']) for d in selected}
      rows = [r for r in csv.DictReader(stream)
              if (r['package'], r['version']) in selected_ids and
              not r['result'].startswith(('network:', 'not run:'))]
  done = {(r['package'], r['version']) for r in rows}
  def sanitize(text):
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    text = re.sub(r' ?\d+\x08+', '', text).replace('\x08', '')
    for path, replacement in [(str(Path.cwd()), '<worktree>'),
                              (str(Path(os.environ['HOME']).parent), '<scratch>')]:
      text = text.replace(path, replacement)
    # Tool diagnostics may name the compiler's installation outside scratch.
    text = re.sub(r'(?<![:/\w])/(?:[^\s:]+/)+[^\s:]*', '<path>', text)
    identities = [(socket.gethostname(), '<test system>')]
    identities += [(os.environ.get(name), '<user>') for name in ('USER', 'LOGNAME', 'USERNAME')]
    for identity, replacement in identities:
      if identity:
        text = re.sub(r'(?<!\w)' + re.escape(identity) + r'(?!\w)', replacement, text)
    return text.encode('ascii', errors='backslashreplace').decode('ascii')
  for data in selected:
    if (args.stop_file or args.work / 'STOP').exists():
      print('Stopped between packages; CSV and logs retained.', flush=True)
      return 130
    name, ver = data['name'], data['version']
    if (name, ver) in done:
      continue
    directory = args.work / name
    if (directory / 'package.json').exists():
      checkout = json.loads((directory / 'package.json').read_text(), strict=False)
      if (checkout.get('name'), checkout.get('version')) != (name, ver):
        raise ValueError('existing checkout has a different package/version: ' + name)
    started = time.monotonic()
    outputs = []
    log = args.work / (name + '.log')
    def write_log():
      log.write_text('\n'.join(outputs), encoding='ascii', errors='backslashreplace')
    status = 'pass'
    measurements = {}
    properties = ('not run', 'not run')
    stages = ([] if (directory / 'package.json').exists() else
              [('checkout', ['checkout', name, ver, '-o', str(directory)], Path.cwd())]) + [
              ('install', ['install'], directory), ('test', ['test'], directory)]
    for stage, arguments, cwd in stages:
      print(name, ver, stage, flush=True)
      stage_started = time.monotonic()
      while True:
        attempt_started = time.monotonic()
        remaining = max(1, int(1800 - (time.monotonic() - started)))
        result = subprocess.run(['timeout', str(remaining), 'prlimit', '--as=8000000000',
                                 *command, *arguments], cwd=cwd, capture_output=True, text=True)
        output = sanitize(result.stdout + result.stderr)
        outputs.append(stage + '\n' + output)
        write_log()
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
        if current.startswith('network:'):
          if wait_for_proxy():
            # An infrastructure outage does not spend the package's budget.
            outage = time.monotonic() - attempt_started
            started += outage
            stage_started += outage
            outputs.append('Proxy recovered; retrying the interrupted package stage.\n')
            continue
        break
      measurements[stage] = (round(time.monotonic() - stage_started, 1), current)
      if stage == 'test':
        properties = property_results(output)
      if current != 'pass':
        if status == 'pass':
          status = current
        if stage == 'checkout' or result.returncode == 124 or current.startswith('network:'):
          break
    seconds = round(time.monotonic() - started, 1)
    baseline, baseline_seconds, baseline_properties = 'not run', '', ('not run', 'not run')
    if args.pakcs and status != 'pass' and (directory / 'package.json').exists():
      print(name, ver, 'PAKCS test', flush=True)
      baseline_started = time.monotonic()
      baseline_command = [args.cypm, '-d', 'CURRYBIN=' + str(Path(args.pakcs).resolve()),
                          '-d', 'REPOSITORYPATH=' + str(index), 'test']
      environment = dict(os.environ, PATH=str(args.pakcs_checker.resolve()) +
                         os.pathsep + os.environ['PATH'])
      oracle_install = None
      if data.get('executable') or data.get('executables'):
        # Test scripts invoke package tools by name. Never compare PAKCS
        # through the executable just built with Sprite.
        oracle_bin = (args.work / 'pakcs-tools' / name / 'bin').resolve()
        oracle_bin.mkdir(parents=True, exist_ok=True)
        environment['PATH'] = str(oracle_bin) + os.pathsep + environment['PATH']
        oracle_install = subprocess.run(['timeout', '1800', 'prlimit', '--as=8000000000',
            *baseline_command[:-1], '-d', 'BININSTALLPATH=' + str(oracle_bin), 'install'],
            cwd=directory, env=environment, capture_output=True, text=True)
        outputs.append('PAKCS isolated install\n' + sanitize(
            oracle_install.stdout + oracle_install.stderr))
      remaining = max(1, int(1800 - (time.monotonic() - baseline_started)))
      result = oracle_install if oracle_install and oracle_install.returncode else subprocess.run(
          ['timeout', str(remaining), 'prlimit', '--as=8000000000', *baseline_command],
          cwd=directory, env=environment, capture_output=True, text=True)
      output = sanitize(result.stdout + result.stderr)
      outputs.append('PAKCS test\n' + output)
      baseline = classify(output, result.returncode)
      baseline_properties = property_results(output)
      baseline_seconds = round(time.monotonic() - baseline_started, 1)
    write_log()
    rows.append(dict(zip(fields, [name, ver, status, seconds,
                 *measurements.get('install', ('', 'not run')),
                 *measurements.get('test', ('', 'not run')),
                 ('SPRITE_DISABLE_SYSLIB_CHECKS=' + os.environ['SPRITE_DISABLE_SYSLIB_CHECKS']
                  if 'SPRITE_DISABLE_SYSLIB_CHECKS' in os.environ else ''),
                 *properties, baseline, baseline_seconds, *baseline_properties])))
    temporary_csv = args.csv.with_suffix(args.csv.suffix + '.tmp')
    with temporary_csv.open('w') as stream:
      writer = csv.DictWriter(stream, fieldnames=fields)
      writer.writeheader()
      writer.writerows(rows)
    temporary_csv.replace(args.csv)
    print(name, ver, status, seconds, flush=True)
  if expected:
    failures, improvements = compare(rows, expected)
    summary = 'CPM index: %d packages, %d regressions\n\n' % (len(rows), len(failures))
    summary += '\n'.join('- ' + line for line in [*failures, *improvements]) + '\n'
    print(summary)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
      with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
        stream.write(summary)
    return bool(failures)
  return 0


if __name__ == '__main__':
  sys.exit(main())
