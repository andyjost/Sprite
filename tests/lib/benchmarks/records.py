'''
The record format of the harness.

A record is one JSON object, written as one line (JSON Lines).  It describes
N repetitions of one measurement: a program on a backend in a suite, under a
variant such as the state of a cache.  The fields, in order:

    schema       The number of this format: 2.  Schema 1 lacked the field
                 instructions; see below.
    suite        throughput, compile, import, memory, split, applications,
                 or community.
    program      The program, or the name of the item of the suite; an
                 origin/program name in the community suite.
    backend      cxx, or pakcs; in the applications suite also an
                 opponent: resolvelib, python, or clang.
    variant      The variant of the item (cold, warm, collector=off; whole
                 or K/I in the split suite; SIZE/CASE in the dependency
                 item of the applications suite), or None.
    commit       The commit of the repository, with -dirty when the tree
                 has changes; None without git.
    date         The time of the run, UTC, ISO 8601.
    label        A label for the machine or the run, from --label.
    repeat       The number of measured repetitions.
    warmup       The number of warm-up runs before them.
    status       ok when every measured repetition succeeded; else the
                 status of the first failure, fail or timeout. excluded
                 records name an unavailable preprocessor in error, have
                 no samples, repeat=warmup=0, and null measurements.
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
                 sprite-exec, a timed evaluation probe, or the time to the
                 first value of an expression.
    eval_cpu     Median evaluation CPU seconds (user plus system) for the
                 timed Sprite probe, Python, and PAKCS's "elapsed" field.
    eval_wall_clock, eval_cpu_clock
                 Optional explicit clock names: wall and cpu_user_system.
                 Ratios require matching, known clocks on both records.
    compile      Median seconds spent compiling: the compile field of
                 sprite-exec --stats, or the time of curry.compile.
    steps        Rewrite steps, from --stats; the same in every repetition,
                 else None with a warning.
    forks        Forks, likewise.
    collections  Collections of the node collector, likewise.
    instructions User-space instructions retired by the child process and
                 its descendants, counted by perf stat in one more
                 repetition after the measured ones (see measure.py).  The
                 median when there are several such repetitions.  None when
                 perf is not available, when the repetition under perf
                 failed, or when its counters differ from the measured
                 ones; meta.instructions_source and the warnings tell why.
    ratios       Optional map of Curry/opponent evaluation time ratios
                 for throughput. Values above 1 mean Curry took longer.
    samples      The numbers of each repetition, in order: the measured
                 repetitions, then the repetitions under perf, which carry
                 "perf": true.  The wall and CPU seconds of a repetition
                 under perf include the overhead of perf and do not enter
                 the medians.
    warnings     Messages about the repetitions, such as counters that
                 differ.
    meta         Facts about the machine, the tools, and the settings.  The
                 machine context is cpu_model, cores (logical processors),
                 and mem_gb (GiB, one decimal), without a host name.
                 rss_source and instructions_source tell how the peak
                 resident set and the instructions were measured, or why
                 they were not. meta.env records the effective interpreter
                 flags and rotation. meta.mode holds resolved flags, backend
                 (selected JIT), execution (aot for interpret:off), and
                 llvmlite (whether the import succeeded). Old records may
                 omit mode and ratios. meta.requested_inline_budget is the
                 resolved request. meta.aot_inline_budgets contains one map
                 of probe module names to checked object budgets per sample
                 (null for an unknown budget). Samples also retain the probe's
                 object and stamp identities, without paths. All repetitions
                 share one untimed probe, checked after the final repetition.
                 With no warm-up the probe follows measurement, and products
                 changed since measurement began have unknown budgets.
                 meta.aot_provenance is untimed-probe, or fresh-products for
                 compile items: their temporary products use the requested
                 budget and have no persistent identity to check; shared
                 dependencies still use checked receipts.
                 meta.aot_adoption_possible marks routes that can adopt other
                 objects during measurement. meta.aot_probe_warnings records
                 object replacements detected by the final identity check.
                 The object's ABI input receipt supplies these budgets;
                 a regenerated image need not describe an older AOT object.

The medians cover the successful measured repetitions only.  A median of an
even number of values is the mean of the middle two.

Records of schema 1 load as well: read() adds the field instructions with
the value None.  Their meta names the machine context cpu and cpus;
machine() reads both namings.
'''

import datetime, json, os, platform, subprocess
from . import BACKENDS, OPPONENTS, SUITES

__all__ = [
    'ADDED', 'COUNTERS', 'FIELDS', 'MEDIANS', 'SCHEMA', 'SCHEMAS', 'STATUSES'
  , 'add_ratios', 'commit', 'cpu_model', 'exclusion', 'key', 'machine', 'median', 'memory_gb', 'now'
  , 'program_width', 'read', 'sample', 'summarize', 'upgrade', 'validate', 'write', 'write_ratios'
  ]

SCHEMA = 2
SCHEMAS = (1, 2)
MEDIANS = ('wall', 'cpu', 'peak_rss', 'eval_wall', 'eval_cpu', 'compile')
COUNTERS = ('steps', 'forks', 'collections')
STATUSES = ('ok', 'fail', 'timeout', 'excluded')
# The fields that a later schema added, with the schema that added them.  A
# record of an earlier schema may lack them.
ADDED = {'instructions': 2}

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
  , ('collections', (int, _NONE)), ('instructions', (int, _NONE))
  , ('samples', list), ('warnings', list), ('meta', dict)
  )


def exclusion(suite, program, backend, variant, reason, meta, label='', commit=None):
  '''A baseline entry for an optional preprocessor absent from PATH.'''
  record = {name: None for name, _ in FIELDS}
  record.update(
      schema=SCHEMA, suite=suite, program=program, backend=backend,
      variant=variant, commit=commit, date=now(), label=label, repeat=0,
      warmup=0, status='excluded', error=reason, samples=[], warnings=[],
      meta=meta
    )
  return record


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
  ``run`` and the ``fields`` read from its output.  ``perf`` tells whether
  the run was under perf; ``instructions`` is its count, else None.
  '''
  result = {
      'status': run.status, 'returncode': run.returncode, 'error': run.error
    , 'wall': run.wall, 'cpu': run.cpu, 'peak_rss': run.peak_rss
    , 'eval_wall': None, 'eval_cpu': None, 'compile': None, 'steps': None
    , 'forks': None, 'collections': None, 'instructions': run.instructions
    , 'perf': run.perf, 'extra': {}
    }
  result.update(fields or {})
  return result


def summarize(
    suite, program, backend, variant, samples, meta, label='', warmup=0
  , commit=None, date=None
  ):
  '''
  Builds the record of one item from the samples of its repetitions.  The
  medians cover the successful measured samples.  A sample with "perf" set,
  the repetition under perf, contributes its instructions and its counters
  only.  A counter is recorded when every successful sample agrees on it;
  otherwise it is None and a warning says so.
  '''
  measured = [s for s in samples if not s.get('perf')]
  under_perf = [s for s in samples if s.get('perf')]
  if not measured:
    raise ValueError('a record needs at least one measured sample')
  good = [s for s in measured if s['status'] == 'ok']
  failed = [s for s in measured if s['status'] != 'ok']
  record = {
      'schema': SCHEMA, 'suite': suite, 'program': program
    , 'backend': backend, 'variant': variant, 'commit': commit
    , 'date': date or now(), 'label': label, 'repeat': len(measured)
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
    values = [
        s[name] for s in samples
            if s['status'] == 'ok' and s[name] is not None
      ]
    if not values:
      record[name] = None
    elif all(value == values[0] for value in values):
      record[name] = values[0]
    else:
      record[name] = None
      warnings.append('%s differs between repetitions: %s' % (name, values))
  for field in ('eval_wall_clock', 'eval_cpu_clock'):
    clocks = {s.get(field) for s in good}
    if len(clocks) == 1 and None not in clocks:
      record[field] = clocks.pop()
  record['instructions'] = _instructions(under_perf, good, warnings)
  record['samples'] = samples
  record['warnings'] = warnings
  record['meta'] = meta
  return record


def _instructions(under_perf, good, warnings):
  '''
  The median instructions of the repetitions under perf that succeeded and
  agree with the measured repetitions on the counters; None without one.
  A repetition left out gets a warning.
  '''
  values = []
  reference = good[0] if good else None
  for s in under_perf:
    if s['status'] != 'ok':
      warnings.append(
          'instructions: the repetition under perf failed: %s' % s['error']
        )
    elif s.get('instructions') is None:
      warnings.append('instructions: perf reported no count')
    elif reference is not None and not _agrees(s, reference):
      warnings.append(
          'instructions: the repetition under perf has other counters than '
          'the measured ones: %s' % _counters_text(s, reference)
        )
    else:
      values.append(s['instructions'])
  return int(round(median(values))) if values else None


def _agrees(s, reference):
  '''Whether ``s`` has the counters of ``reference``, where it has any.'''
  return all(
      reference[name] is None or s[name] == reference[name]
          for name in COUNTERS
    )


def _counters_text(s, reference):
  return ', '.join(
      '%s %s (measured %s)' % (name, s[name], reference[name])
          for name in COUNTERS if s[name] != reference[name]
    )


def key(record):
  '''The identity of a measurement: suite, program, backend, variant.'''
  return (
      record['suite'], record['program'], record['backend'], record['variant']
    )


def add_ratios(recs):
  '''Pair evaluation times only when both records explicitly name the same clock.'''
  def identity(r):
    return (r['suite'], r['program'], r['variant'], r.get('commit'), r.get('label'))
  sprite = {identity(r): r for r in recs
      if r['backend'] == 'cxx' and r['status'] == 'ok'}
  for r in recs:
    if r['suite'] != 'throughput' or r['backend'] not in ('python', 'pakcs'):
      continue
    c = sprite.get(identity(r))
    metric = 'eval_cpu' if r['backend'] == 'pakcs' else 'eval_wall'
    clock = metric + '_clock'
    if (c and r['status'] == 'ok' and r.get(metric)
        and c.get(metric) is not None and c.get(clock) is not None
        and c.get(clock) == r.get(clock)):
      ratio = c[metric] / r[metric]
      c.setdefault('ratios', {})[r['backend']] = ratio
      r.setdefault('ratios', {})['curry_to_' + r['backend']] = ratio


def write_ratios(stream, recs):
  add_ratios(recs)
  for r in recs:
    if r['backend'] == 'cxx':
      for opponent, ratio in r.get('ratios', {}).items():
        stream.write('%s Curry / %s: %.3fx (evaluation %s seconds)\n'
            % (r['program'], opponent, ratio,
               'CPU user + system' if opponent == 'pakcs' else 'wall'))


def program_width(records):
  '''Keep qualified community names visible in console tables.'''
  return max([16] + [
      len(r['program']) for r in records if r['suite'] == 'community'
    ])


def machine(record):
  '''
  The machine context of a record: a dict with cpu_model, cores, and
  mem_gb; None for what the record does not say.  Schema 1 named the first
  two cpu and cpus and had no mem_gb.
  '''
  meta = record.get('meta') or {}
  return {
      'cpu_model': meta.get('cpu_model', meta.get('cpu'))
    , 'cores': meta.get('cores', meta.get('cpus'))
    , 'mem_gb': meta.get('mem_gb')
    }


def validate(record):
  '''
  Raises ValueError unless ``record`` has every field with a legal value.
  A record of an earlier schema may lack the fields added later.
  '''
  if not isinstance(record, dict):
    raise ValueError('a record is a JSON object')
  schema = record.get('schema')
  if schema not in SCHEMAS or isinstance(schema, bool):
    raise ValueError('schema %r is not in %s' % (schema, list(SCHEMAS)))
  for name, types in FIELDS:
    if name not in record:
      if ADDED.get(name, 1) > schema:
        continue
      raise ValueError('field %r is missing' % name)
    if not isinstance(record[name], types) or isinstance(record[name], bool):
      raise ValueError('field %r has a bad value: %r' % (name, record[name]))
  legal_values = (
      ('suite', SUITES), ('backend', BACKENDS + OPPONENTS), ('status', STATUSES)
    )
  for name, legal in legal_values:
    if record[name] not in legal:
      raise ValueError('field %r has a bad value: %r' % (name, record[name]))
  if not all(isinstance(s, dict) for s in record['samples']):
    raise ValueError('samples are JSON objects')


def upgrade(record):
  '''Adds the fields of the current schema that ``record`` lacks, as None.'''
  for name in ADDED:
    record.setdefault(name, None)
  return record


def write(stream, record):
  '''Writes one record as one line.'''
  validate(record)
  stream.write(json.dumps(record) + '\n')


def read(filename):
  '''
  Reads the records of a JSON Lines file; a bad line raises ValueError.  A
  record of an earlier schema gets the fields it lacks, as None.
  '''
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
      records.append(upgrade(record))
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


def memory_gb():
  '''
  The memory of the machine in GiB, to one decimal: MemTotal of
  /proc/meminfo, else the physical pages of sysconf; None when unknown.
  '''
  try:
    with open('/proc/meminfo') as stream:
      for line in stream:
        if line.startswith('MemTotal:'):
          return round(int(line.split()[1]) / 1048576.0, 1)
  except (OSError, ValueError, IndexError):
    pass
  try:
    total = os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE')
  except (ValueError, OSError, AttributeError):
    return None
  return round(total / 1024.0 ** 3, 1)
