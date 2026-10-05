'''
The record format of the harness.

A record is one JSON object, written as one line (JSON Lines).  It describes
N repetitions of one measurement: a program on a backend in a suite, under a
variant such as the state of a cache.  The fields, in order:

    schema       The number of this format: 1.
    suite        throughput, compile, import, memory, or split.
    program      The program, or the name of the item of the suite.
    backend      cxx, py, or pakcs.
    variant      The variant of the item (cold, warm, collector=off; whole
                 or K/I in the split suite), or None.
    commit       The commit of the repository, with -dirty when the tree
                 has changes; None without git.
    date         The time of the run, UTC, ISO 8601.
    label        A label for the machine or the run, from --label.
    repeat       The number of measured repetitions.
    warmup       The number of warm-up runs before them.
    status       ok when every repetition succeeded; else the status of
                 the first failure, fail or timeout.
    error        One line about the first failure, or None.
    wall         Median wall seconds of the child process.
    cpu          Median CPU seconds (user plus system) of the child process
                 and its descendants.
    peak_rss     Median peak resident set size in bytes: the largest of the
                 child and its descendants, measured by GNU time.  Without
                 GNU time the value comes from wait4 and is never below the
                 resident set of the harness itself (see measure.py);
                 meta.rss_source tells which.
    eval_wall    Median wall seconds of the evaluation alone: the -t time of
                 sprite-exec, the elapsed time of PAKCS, or the time to the
                 first value of an expression.
    eval_cpu     Median run time that PAKCS reports; None for Sprite.
    compile      Median seconds spent compiling: the compile field of
                 sprite-exec --stats, or the time of curry.compile.
    steps        Rewrite steps, from --stats; the same in every repetition,
                 else None with a warning.
    forks        Forks, likewise.
    collections  Collections of the node collector, likewise.
    samples      The numbers of each measured repetition, in order.
    warnings     Messages about the repetitions, such as counters that
                 differ.
    meta         Facts about the machine, the tools, and the settings.

The medians cover the successful repetitions only.  A median of an even
number of values is the mean of the middle two.
'''

import datetime, json, platform, subprocess
from . import BACKENDS, SUITES

__all__ = [
    'COUNTERS', 'FIELDS', 'MEDIANS', 'SCHEMA', 'STATUSES', 'commit'
  , 'cpu_model', 'key', 'median', 'now', 'read', 'sample', 'summarize'
  , 'validate', 'write'
  ]

SCHEMA = 1
MEDIANS = ('wall', 'cpu', 'peak_rss', 'eval_wall', 'eval_cpu', 'compile')
COUNTERS = ('steps', 'forks', 'collections')
STATUSES = ('ok', 'fail', 'timeout')

_NONE = type(None)
_NUMBER = (int, float, _NONE)

# Every field of a record, in order, with the types allowed.
FIELDS = (
    ('schema', int), ('suite', str), ('program', str), ('backend', str)
  , ('variant', (str, _NONE)), ('commit', (str, _NONE)), ('date', str)
  , ('label', str), ('repeat', int), ('warmup', int), ('status', str)
  , ('error', (str, _NONE)), ('wall', _NUMBER), ('cpu', _NUMBER)
  , ('peak_rss', (int, _NONE)), ('eval_wall', _NUMBER), ('eval_cpu', _NUMBER)
  , ('compile', _NUMBER), ('steps', (int, _NONE)), ('forks', (int, _NONE))
  , ('collections', (int, _NONE)), ('samples', list), ('warnings', list)
  , ('meta', dict)
  )


def median(values):
  '''The median of a non-empty sequence of numbers.'''
  values = sorted(values)
  if not values:
    raise ValueError('median of no values')
  mid = len(values) // 2
  if len(values) % 2:
    return values[mid]
  return (values[mid - 1] + values[mid]) / 2


def sample(run, fields=None):
  '''
  The sample of one repetition: the numbers of the child process from
  ``run`` and the ``fields`` read from its output.
  '''
  result = {
      'status': run.status, 'returncode': run.returncode, 'error': run.error
    , 'wall': run.wall, 'cpu': run.cpu, 'peak_rss': run.peak_rss
    , 'eval_wall': None, 'eval_cpu': None, 'compile': None, 'steps': None
    , 'forks': None, 'collections': None, 'extra': {}
    }
  result.update(fields or {})
  return result


def summarize(
    suite, program, backend, variant, samples, meta, label='', warmup=0
  , commit=None, date=None
  ):
  '''
  Builds the record of one item from the samples of its repetitions.  The
  medians cover the successful samples.  A counter is recorded when every
  successful sample agrees on it; otherwise it is None and a warning says
  so.
  '''
  if not samples:
    raise ValueError('a record needs at least one sample')
  good = [s for s in samples if s['status'] == 'ok']
  failed = [s for s in samples if s['status'] != 'ok']
  record = {
      'schema': SCHEMA, 'suite': suite, 'program': program
    , 'backend': backend, 'variant': variant, 'commit': commit
    , 'date': date or now(), 'label': label, 'repeat': len(samples)
    , 'warmup': warmup
    , 'status': failed[0]['status'] if failed else 'ok'
    , 'error': failed[0]['error'] if failed else None
    }
  warnings = []
  for name in MEDIANS:
    values = [s[name] for s in good if s[name] is not None]
    record[name] = median(values) if values else None
  if record['peak_rss'] is not None:
    record['peak_rss'] = int(round(record['peak_rss']))
  for name in COUNTERS:
    values = [s[name] for s in good if s[name] is not None]
    if not values:
      record[name] = None
    elif all(value == values[0] for value in values):
      record[name] = values[0]
    else:
      record[name] = None
      warnings.append('%s differs between repetitions: %s' % (name, values))
  record['samples'] = samples
  record['warnings'] = warnings
  record['meta'] = meta
  return record


def key(record):
  '''The identity of a measurement: suite, program, backend, variant.'''
  return (
      record['suite'], record['program'], record['backend'], record['variant']
    )


def validate(record):
  '''Raises ValueError unless ``record`` has every field with a legal value.'''
  if not isinstance(record, dict):
    raise ValueError('a record is a JSON object')
  for name, types in FIELDS:
    if name not in record:
      raise ValueError('field %r is missing' % name)
    if not isinstance(record[name], types) or isinstance(record[name], bool):
      raise ValueError('field %r has a bad value: %r' % (name, record[name]))
  if record['schema'] != SCHEMA:
    raise ValueError('schema %r is not %r' % (record['schema'], SCHEMA))
  legal_values = ('suite', SUITES), ('backend', BACKENDS), ('status', STATUSES)
  for name, legal in legal_values:
    if record[name] not in legal:
      raise ValueError('field %r has a bad value: %r' % (name, record[name]))
  if not all(isinstance(s, dict) for s in record['samples']):
    raise ValueError('samples are JSON objects')


def write(stream, record):
  '''Writes one record as one line.'''
  validate(record)
  stream.write(json.dumps(record) + '\n')


def read(filename):
  '''Reads the records of a JSON Lines file; a bad line raises ValueError.'''
  records = []
  with open(filename) as stream:
    for lineno, line in enumerate(stream, 1):
      if not line.strip():
        continue
      try:
        record = json.loads(line)
        validate(record)
      except ValueError as exc:
        raise ValueError('%s, line %d: %s' % (filename, lineno, exc))
      records.append(record)
  return records


def now():
  '''The time, UTC, ISO 8601, to the second.'''
  return datetime.datetime.now(datetime.timezone.utc).strftime(
      '%Y-%m-%dT%H:%M:%SZ'
    )


def commit(root):
  '''
  The short commit of the repository at ``root``, with -dirty when the
  tracked files differ from it; None without git or outside a repository.
  '''
  def git(*args):
    proc = subprocess.run(
        ['git', '-C', root] + list(args), capture_output=True, text=True
      , timeout=60
      )
    return proc.stdout.strip() if proc.returncode == 0 else None
  try:
    head = git('rev-parse', '--short=12', 'HEAD')
    if head is None:
      return None
    changes = git('status', '--porcelain', '--untracked-files=no')
  except (OSError, subprocess.TimeoutExpired):
    return None
  return head + ('-dirty' if changes else '')


def cpu_model():
  '''The model name of the processor, or None.'''
  try:
    with open('/proc/cpuinfo') as stream:
      for line in stream:
        if line.startswith('model name'):
          return line.split(':', 1)[1].strip()
  except OSError:
    pass
  return platform.processor() or None
