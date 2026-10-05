'''
The status lines, the summary table, and the parse of the unittest output.
'''

import os, re
from . import MIB, TESTDIR

__all__ = [
    'format_status', 'header', 'parse_unittest', 'prepare_header', 'summary'
  , 'tail'
  ]

RAN = re.compile(r'^Ran (\d+) tests? in ([\d.]+)s', re.MULTILINE)
VERDICT = re.compile(r'^(OK|FAILED)(?: \((.*)\))?\s*$', re.MULTILINE)

def parse_unittest(text):
  '''
  The counts of a unittest run from its output: a dict with ``tests``,
  ``failures`` (failures plus errors), ``skipped``, and ``verdict`` ('OK',
  'FAILED', or None when the run did not end).
  '''
  counts = {'tests': None, 'failures': None, 'skipped': 0, 'verdict': None}
  ran = RAN.findall(text)
  if ran:
    counts['tests'] = int(ran[-1][0])
  verdicts = VERDICT.findall(text)
  if verdicts:
    verdict, detail = verdicts[-1]
    counts['verdict'] = verdict
    parts = {}
    for item in detail.split(','):
      key, _, value = item.strip().partition('=')
      if value.isdigit():
        parts[key] = int(value)
    counts['failures'] = parts.get('failures', 0) + parts.get('errors', 0)
    counts['skipped'] = parts.get('skipped', 0)
  return counts

def mb(value):
  '''Bytes as whole MiB, or a dash.'''
  return '-' if value is None else '%d' % round(value / MIB)

def relative(path):
  '''A path relative to the tests directory when it lies under it.'''
  try:
    rel = os.path.relpath(path, TESTDIR)
  except ValueError:
    return path
  return path if rel.startswith('..') else rel

def header(jobs, width, budget, timeout, logdir, available=None):
  '''The line printed before the run.'''
  backends = sorted(set(job.backend for job in jobs))
  files = len(set(job.filename for job in jobs))
  about = '%.1f GB' % (budget / 1024 ** 3)
  if available is not None:
    about += ' (of %.1f GB available)' % (available / 1024 ** 3)
  return (
      'runner: %d file%s on %s, width %d, budget %s, timeout %g s, logs under %s'
    % ( files, '' if files == 1 else 's', '+'.join(backends), width, about
      , timeout, relative(logdir)
      )
    )

def prepare_header(jobs, logdir):
  '''The line printed before a run of the prepare pass alone.'''
  backends = sorted(set(job.backend for job in jobs))
  count = len(set(job.filename for job in jobs))
  return (
      'runner: prepare pass, %d director%s on %s, one process at a time, '
      'logs under %s'
    % ( count, 'y' if count == 1 else 'ies', '+'.join(backends)
      , relative(logdir)
      )
    )

def format_status(job, index=None, total=None):
  '''The line printed when a file finishes.'''
  prefix = '' if index is None else '[%*d/%d] ' % (len(str(total)), index, total)
  tests = '-' if job.tests is None else str(job.tests)
  line = '%s%-16s %-4s %-28s %5s tests %7.1f s  peak %5s MB' % (
      prefix, job.status, job.backend, job.filename, tests, job.duration or 0.0
    , mb(job.peak)
    )
  if job.note:
    line += '  ' + job.note
  if job.status != 'ok' and job.logfile:
    line += '  log: ' + relative(job.logfile)
  return line

COLUMNS = '%-28s %-4s %6s %8s %9s %8s  %s'
HEADINGS = ('file', 'backend', 'tests', 'failures', 'duration', 'peak_mb', 'status')

def summary(jobs, wall=None, interrupted=False):
  '''
  The summary table and its last line, as text.  The counts of the last
  line are of the test files; the advisory jobs (the prepare pass) add a
  clause of their own when one of them did not end well.
  '''
  lines = [COLUMNS % HEADINGS, COLUMNS % tuple('-' * len(h) for h in HEADINGS)]
  for job in jobs:
    lines.append(COLUMNS % (
        job.filename, job.backend
      , '-' if job.tests is None else job.tests
      , '-' if job.failures is None else job.failures
      , '-' if job.duration is None else '%.1f s' % job.duration
      , mb(job.peak), job.status
      ))
  advisory = [job for job in jobs if job.advisory]
  jobs = [job for job in jobs if not job.advisory]
  finished = [job for job in jobs if job.finished]
  failed = [job for job in finished if job.status == 'FAILED']
  killed = [job for job in finished if job.status.startswith('killed')]
  other = [
      job for job in finished
          if job.status not in ('ok', 'FAILED') and not job.status.startswith('killed')
    ]
  pending = [job for job in jobs if not job.finished]
  parts = ['%d of %d run' % (len(finished), len(jobs))]
  parts.append('%d failed' % len(failed))
  if killed:
    parts.append('%d killed' % len(killed))
  if other:
    parts.append('%d crashed' % len(other))
  if pending:
    parts.append('%d not run' % len(pending))
  incomplete = [job for job in advisory if job.finished and not job.ok]
  if incomplete:
    parts.append(
        'prepare: %d of %d incomplete' % (len(incomplete), len(advisory))
      )
  if wall is not None:
    parts.append('wall %.1f s' % wall)
  if interrupted:
    parts.append('interrupted')
  lines.append(', '.join(parts))
  return '\n'.join(lines)

def tail(path, lines=30):
  '''The last lines of a log file, or an empty string.'''
  try:
    with open(path, encoding='utf-8', errors='replace') as stream:
      text = stream.read()
  except OSError:
    return ''
  return '\n'.join(text.splitlines()[-lines:])
