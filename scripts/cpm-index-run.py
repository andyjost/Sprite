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
                                     'Failed to connect', 'curl: (')) or re.search(
      r'(?:could not|cannot|failed to|unable to) (?:download|fetch|clone|access)|download failed',
      output, re.I):
    urls = re.findall(r'https?://[^\s\"\']+', output)
    return 'network: ' + (' '.join(dict.fromkeys(urls)) or 'download connection failed')
  if code == 124:
    downloads = re.findall(r'(?:Downloading|Cloning|Fetching)[^\n]*?(https?://[^\s\"\']+)', output, re.I)
    if downloads and not re.search(r'Compiling|Executing all tests|Running CurryCheck', output.split(downloads[-1])[-1]):
      return 'network: ' + ' '.join(dict.fromkeys(downloads))
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


def normalize_failure(text):
  """Remove locations and generated identifiers, preserving diagnostic meaning."""
  text = re.sub(r'\x1b\[[0-9;]*m', '', text)
  text = re.sub(r' ?\d+\x08+', '', text).replace('\x08', '')
  text = re.sub(r'\(module ([^,]+), line \d+\)', r'(module \1)', text)
  text = re.sub(r'0x[0-9a-fA-F]+', '<address>', text)
  text = re.sub(r'(?:<(?:scratch|worktree|path)>)*(?:[A-Za-z]:[\\/]|/)?'
                r'(?:[\w.-][^\s:<>/\\]*[\\/])*([\w.-][^\s:<>/\\]*\.curry)', r'\1', text)
  text = re.sub(r'\b(?:TEST|MAIN)\d+\b', '<generated>', text)
  text = re.sub(r'(?<![:/\w])/(?:[^\s:]+/)+[^\s:]*', '<path>', text)
  text = re.sub(r'\b[A-Za-z]:\\(?:[^\s:]+\\)*[^\s:]*', '<path>', text)
  text = re.sub(r'(?:<scratch>|<worktree>)(?:<path>)?', '<path>', text)
  text = re.sub(r'(?<=:)\d+(?::\d+)?(?:-\d+(?::\d+)?)?(?=[: ])', '<location>', text)
  text = re.sub(r'not found in path .*', 'not found in path <search-path>', text)
  text = re.sub(r'\bline \d+\b', 'line <number>', text)
  text = re.sub(r'(?m)^\s*\d+ \|', ' <location> |', text)
  text = re.sub(r'(?m)^(\s*\|)\s*\^+\s*$', r'\1 <location>', text)
  return ' '.join(text.split())


def failure_set(stage, output, code=1, outcome=None):
  """Complete stage failure set; never truncate to the first/last diagnostic."""
  outcome = outcome or classify(output, code)
  if outcome == 'pass':
    return []
  kind = outcome.split(':', 1)[0]
  failures = {stage + ': class: ' + kind}
  # Property headers and all error diagnostics, including every external.
  markers = ('FAILED', 'Falsified', 'falsified', ': FAILURE:',
             ': EXECUTION FAILURE:', 'Arguments exhausted after',
             'not implemented', 'ERROR', 'CRITICAL',
             'error:', 'Expected module for', 'terminate called', 'what():',
             'Segmentation fault', 'Assertion', 'Aborted', 'std::bad_alloc',
             '*** Evaluation suspended!', 'not found', 'not found!')
  previous = ''
  module = ''
  lines = output.splitlines()
  index = 0
  while index < len(lines):
    line = lines[index]
    index += 1
    context = re.search(r"(?:Analyzing module|Module) '([^']+)'", line)
    if context:
      module = context[1]
    # Front-end headers introduce complete blocks, not standalone errors.
    # Keep source excerpts and message lines associated with their file/module.
    compiler = re.search(r':\d+(?::\d+)?(?:-\d+(?::\d+)?)? Error:', line)
    module_header = re.match(r"Module '[^']+': incorrect source program:", line)
    if compiler or module_header or line.strip() == 'Error:':
      block = [line]
      while index < len(lines):
        following = lines[index]
        if following.strip() and not following[:1].isspace():
          if (module_header and not following.startswith('ERROR:')) or re.fullmatch(r'[-=]{3,}', following):
            break
          next_header = re.search(r':\d+(?::\d+)?(?:-\d+(?::\d+)?)? Error:', following)
          if next_header or following.startswith(("Module '", 'ERROR:', 'Error:')):
            if not (module_header and following.startswith('ERROR:')):
              break
          elif not block[-1].strip():
            break
        block.append(following)
        index += 1
      association = ('module ' + module + ': ') if module and '.curry:' not in line else ''
      failures.add(stage + ': diagnostic: ' + association + normalize_failure('\n'.join(block)))
      previous = line
      continue

    diagnostic = re.search(r'\b(?:Error|Exception)\b|[A-Za-z]+Error:', line)
    if line.lstrip().startswith(('raise ', 'throw ')):
      continue
    if diagnostic or any(marker in line for marker in markers) or re.fullmatch(
        r"[A-Za-z_][\w.']* failed", line.strip()):
      if 'Arguments exhausted after' in line or 'Falsified' in line or 'falsified' in line:
        failures.add(stage + ': diagnostic: ' + normalize_failure(previous))
      failures.add(stage + ': diagnostic: ' + normalize_failure(line))
    if line.strip():
      previous = line
  if len(failures) == 1:
    failures.add(stage + ': diagnostic: ' + normalize_failure(outcome))
  if code < 0 or code >= 128 or code == 124:
    failures.add(stage + ': termination: ' + str(code))
  return sorted(failures)


def recorded_failure_set(row, logs=None):
  if row.get('failure_set'):
    return set(json.loads(row['failure_set']) if isinstance(row['failure_set'], str)
               else row['failure_set'])
  if row['result'] == 'pass':
    return set()
  if logs is None:
    raise ValueError('complete failure set required for ' + row['package'])
  output = (Path(logs) / (row['package'] + '.log')).read_text()
  # Oracle output must never become part of the Sprite baseline.
  output = re.split(r'(?m)^PAKCS (?:test|isolated install)\n', output)[0]
  chunks = re.split(r'(?m)^(checkout|install|test)\n', output)
  failures = set()
  for stage, text in zip(chunks[1::2], chunks[2::2]):
    outcome = row.get(stage + '_outcome', 'pass')
    if outcome in ('pass', 'not run', ''):
      continue
    code = 124 if outcome == 'timeout' else 139 if 'Segmentation fault' in text else 1
    failures.update(failure_set(stage, text, code, outcome))
  if not failures:
    raise ValueError('raw stage evidence required for ' + row['package'])
  return failures


def compare(rows, expected, logs=None):
  failures, improvements = [], []
  for row in rows:
    if row['result'].startswith(('network:', 'infrastructure:')):
      continue  # Infrastructure is reported independently with status 2.
    wanted = expected['packages'][row['package']]
    if row['version'] != wanted['version']:
      failures.append(row['package'] + ': wrong pinned version')
    elif wanted['result'] == 'pass' and row['result'] != 'pass':
      failures.append(row['package'] + ': ' + row['result'])
    elif wanted['result'] in ('exception', 'open'):
      if row['result'] == 'pass':
        improvements.append(row['package'] + ': ' + wanted['result'] + ' now passes')
      else:
        actual = recorded_failure_set(row, logs)
        baseline = set(wanted['failure_set'])
        if not actual <= baseline:
          failures.append(row['package'] + ': new failures: ' + '; '.join(sorted(actual - baseline)))
        elif actual < baseline:
          improvements.append(row['package'] + ': failure set shrank')
  return failures, improvements


def comparison_status(rows, expected, logs=None):
  infrastructure = [r for r in rows if r['result'].startswith(('network:', 'infrastructure:'))]
  failures, improvements = compare(rows, expected, logs)
  summary = 'CPM index: %d packages, %d regressions, %d infrastructure failures\n' % (
      len(rows), len(failures), len(infrastructure))
  summary += ''.join('- ' + line + '\n' for line in [*failures, *improvements])
  summary += ''.join('- infrastructure: ' + r['package'] + ': ' + r['result'] + '\n'
                     for r in infrastructure)
  print(summary, end='')
  if os.environ.get('GITHUB_STEP_SUMMARY'):
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
      stream.write(summary)
  return 2 if infrastructure else int(bool(failures))


def acquisition(command, package, url=None, **kwargs):
  """Retry failed downloads even when the index host remains available."""
  for attempt in range(3):
    result = subprocess.run(command, capture_output=True, text=True, **kwargs)
    outcome = classify(result.stdout + result.stderr, result.returncode)
    if not outcome.startswith('network:'):
      return result
    if attempt < 2:
      try:
        wait_for_proxy()
      except ConnectionError:
        break
      time.sleep(1)
  print('Infrastructure failure: ' + package + ': ' + outcome +
        (' (' + url + ')' if url else ''), file=sys.stderr)
  return result


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--compare', type=Path, help='offline raw CSV comparison')
  parser.add_argument('--logs', type=Path, help='raw stage logs (default: beside CSV)')
  parser.add_argument('--acquire', nargs=argparse.REMAINDER, help='retry a setup acquisition command')
  parser.add_argument('--url', help='source URL for setup acquisition diagnostics')
  parser.add_argument('--label', default='CPM setup', help='package or setup acquisition name')
  parser.add_argument('--cypm')
  parser.add_argument('--sprite')
  parser.add_argument('--index', type=Path)
  parser.add_argument('--work', type=Path)
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
  if args.acquire:
    result = acquisition(args.acquire, args.label, args.url)
    output = result.stdout + result.stderr
    print(output, end='')
    return 2 if classify(output, result.returncode).startswith('network:') else result.returncode
  if not 0 <= args.shard < args.shards:
    parser.error('shard must be in [0, shards)')
  expected = json.loads(args.expected.read_text()) if args.expected else None
  if expected is not None:
    if expected.get('complete') is False and not args.newer:
      parser.error('expected results are incomplete; finish the survey before enabling CI')
    if not expected.get('packages'):
      parser.error('expected results must contain packages')
    for name, pin in expected['packages'].items():
      if pin.get('result') not in ('pass', 'exception', 'open') or (
          pin['result'] != 'pass' and not pin.get('reason')) or (
          pin['result'] == 'open' and not all(pin.get(key) for key in
              ('issue', 'failure_class', 'failure_set'))) or (
          pin['result'] == 'exception' and not all(pin.get(key) for key in
              ('failure_class', 'failure_set'))):
        parser.error('invalid expected result for ' + name)
  if args.compare:
    if expected is None:
      parser.error('--compare requires --expected')
    with args.compare.open() as stream:
      rows = list(csv.DictReader(stream))
    return comparison_status(rows, expected, args.logs or args.compare.parent)
  if not all((args.cypm, args.sprite, args.index, args.work)):
    parser.error('a live run requires --cypm, --sprite, --index and --work')
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
            'pakcs_properties_passed', 'pakcs_properties_failed', 'failure_set']
  rows = []
  if args.resume and args.csv.exists():
    with args.csv.open() as stream:
      selected_ids = {(d['name'], d['version']) for d in selected}
      rows = [r for r in csv.DictReader(stream)
              if (r['package'], r['version']) in selected_ids and
              not r['result'].startswith(('network:', 'infrastructure:', 'not run:'))]
  done = {(r['package'], r['version']) for r in rows}
  def sanitize(text):
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    text = re.sub(r' ?\d+\x08+', '', text).replace('\x08', '')
    for path, replacement in [(str(Path.cwd()), '<worktree>'),
                              (str(Path(os.environ['HOME']).parent), '<scratch>')]:
      text = text.replace(path, replacement)
    # Tool diagnostics may name the compiler's installation outside scratch.
    text = re.sub(r'(?:[A-Za-z]:[\\/]|/)(?:[^\s:]+[\\/])*([^\s:]+\.curry)',
                  r'<path>\1', text)
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
    observed_failures = set()
    measurements = {}
    properties = ('not run', 'not run')
    stages = ([] if (directory / 'package.json').exists() else
              [('checkout', ['checkout', name, ver, '-o', str(directory)], Path.cwd())]) + [
              ('install', ['install'], directory), ('test', ['test'], directory)]
    for stage, arguments, cwd in stages:
      print(name, ver, stage, flush=True)
      stage_started = time.monotonic()
      download_attempts = 0
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
        current = classify(output, result.returncode)
        if current.startswith('network:') and not re.search(r'https?://', current):
          urls = re.findall(r'https?://[^\s\"\']+', json.dumps(data.get('source', {})))
          current += '; package source: ' + ' '.join(urls or [
              'https://cpm.curry-lang.org/PACKAGES/' + name + '-' + ver + '.tar.gz'])
        if changed and not current.startswith('network:') and result.returncode != 124 and time.monotonic() - started < 1800:
          outputs.append('Applied compatibility overlay to newly acquired manifests.\n')
          continue
        if current.startswith('network:'):
          download_attempts += 1
          if download_attempts < 3:
            try:
              wait_for_proxy()
            except ConnectionError:
              break
            time.sleep(1)
            outage = time.monotonic() - attempt_started
            started += outage
            stage_started += outage
            outputs.append('Retrying failed acquisition.\n')
            continue
        break
      observed_failures.update(failure_set(stage, output, result.returncode, current))
      measurements[stage] = (round(time.monotonic() - stage_started, 1), current)
      if stage == 'test':
        properties = property_results(output)
      if current != 'pass':
        if status == 'pass' or current.startswith('network:'):
          status = current
        if stage == 'checkout' or result.returncode == 124 or current.startswith('network:'):
          break
    seconds = round(time.monotonic() - started, 1)
    baseline, baseline_seconds, baseline_properties = 'not run', '', ('not run', 'not run')
    if args.pakcs and not status.startswith('network:') and status != 'pass' and (directory / 'package.json').exists():
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
                 *properties, baseline, baseline_seconds, *baseline_properties, json.dumps(sorted(observed_failures))])))
    temporary_csv = args.csv.with_suffix(args.csv.suffix + '.tmp')
    with temporary_csv.open('w') as stream:
      writer = csv.DictWriter(stream, fieldnames=fields)
      writer.writeheader()
      writer.writerows(rows)
    temporary_csv.replace(args.csv)
    print(name, ver, status, seconds, flush=True)
  if expected:
    return comparison_status(rows, expected, args.work)
  return 2 if any(r['result'].startswith('network:') for r in rows) else 0


if __name__ == '__main__':
  sys.exit(main())
