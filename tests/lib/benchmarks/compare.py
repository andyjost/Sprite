'''
The compare command: joins two record files and shows the change per item.

Items are matched on suite, program, backend, and variant; the last record of
an item in a file counts.  The ratio is NEW over OLD of one metric (CPU
seconds by default).  A ratio within the noise threshold of 1 is the same.
The exact counters, steps and forks, must agree; a change in them means a
change in the program or the compiler, not in the machine.  The column
``instr`` shows the ratio of the instructions when both records have them.

With --deterministic the columns that do not depend on the load of the
machine decide: the metric is the instructions, with a tolerance of 1
percent by default; steps, forks, and collections are listed under
``counters`` when they move beyond the tolerance; wall and CPU seconds are
advisory and appear as the ratios ``~cpu`` and ``~wall``.

The rule: the deterministic columns decide the intermediate steps of a
change, on any machine, loaded or quiet; CPU seconds on a quiet machine
decide the gates; CPU seconds never compare across machines.  The command
prints the machine of each file and warns when the machines differ.

With --strict the status is 1 when an item is slower, a counter changed, a
run failed, or an item lacks the metric: a gate that could not measure has
not passed.  So a deterministic gate fails on records without instructions
(perf missing, or --no-perf) instead of passing with no comparison made.
'''

import argparse, sys
from . import records

__all__ = [
    'ADVISORY', 'COUNTERS', 'DETERMINISTIC_COUNTERS'
  , 'DETERMINISTIC_THRESHOLD', 'METRICS', 'THRESHOLD', 'VERDICTS', 'compare'
  , 'describe', 'latest', 'machines_differ', 'main', 'parse_args', 'ratio'
  , 'summary'
  ]

METRICS = (
    'wall', 'cpu', 'eval_wall', 'eval_cpu', 'peak_rss', 'compile'
  , 'instructions'
  )
# The counters that must agree, and those of the deterministic mode.
COUNTERS = ('steps', 'forks')
DETERMINISTIC_COUNTERS = ('steps', 'forks', 'collections')
# The seconds shown as advisory ratios in the deterministic mode.
ADVISORY = ('cpu', 'wall')
THRESHOLD = 0.10
DETERMINISTIC_THRESHOLD = 0.01
VERDICTS = (
    'same', 'faster', 'slower', 'fail', 'no-metric', 'only-old', 'only-new'
  )
COLUMNS = '%-10s %-16s %-7s %-13s %10s %10s %6s %6s  %-9s %s'
HEADINGS = (
    'suite', 'program', 'backend', 'variant', 'old', 'new', 'ratio', 'instr'
  , 'verdict', 'counters'
  )
DETERMINISTIC_COLUMNS = '%-10s %-16s %-7s %-13s %10s %10s %6s %6s %6s  %-9s %s'
DETERMINISTIC_HEADINGS = (
    'suite', 'program', 'backend', 'variant', 'old', 'new', 'ratio', '~cpu'
  , '~wall', 'verdict', 'counters'
  )


def parse_args(argv):
  parser = argparse.ArgumentParser(
      prog='run_benchmarks compare'
    , description='Compare two record files of the benchmark harness.  The '
                  'ratio is NEW over OLD of the chosen metric; a ratio within '
                  'the noise threshold of 1 counts as the same.  The exact '
                  'counters, steps and forks, must agree.  The deterministic '
                  'columns (instructions, steps, forks, collections) decide '
                  'intermediate steps of a change on any machine; CPU seconds '
                  'on a quiet machine decide the gates; CPU seconds never '
                  'compare across machines.'
    )
  parser.add_argument(
      'old', metavar='OLD', help='the record file of the baseline'
    )
  parser.add_argument('new', metavar='NEW', help='the record file to compare')
  parser.add_argument(
      '-m', '--metric', choices=METRICS, default=None
    , help='the metric to compare [default: cpu]'
    )
  parser.add_argument(
      '-t', '--threshold', type=float, default=None, metavar='FRACTION'
    , help='noise threshold: a ratio within 1 +/- FRACTION is the same '
           '[default: %g; %g with --deterministic, where it is the '
           'tolerance of the counters as well]'
           % (THRESHOLD, DETERMINISTIC_THRESHOLD)
    )
  parser.add_argument(
      '--deterministic', action='store_true'
    , help='compare the columns that do not depend on the load of the '
           'machine: the instructions decide, with the tolerance of -t; '
           'steps, forks, and collections are listed when they move beyond '
           'it; wall and CPU seconds are advisory (columns ~cpu and ~wall)'
    )
  parser.add_argument(
      '--strict', action='store_true'
    , help='exit with status 1 when an item is slower, a counter changed, '
           'a run failed, or an item lacks the metric'
    )
  args = parser.parse_args(argv)
  if args.deterministic:
    if args.metric not in (None, 'instructions'):
      parser.error('--deterministic compares the instructions; drop -m')
    args.metric = 'instructions'
    if args.threshold is None:
      args.threshold = DETERMINISTIC_THRESHOLD
  else:
    if args.metric is None:
      args.metric = 'cpu'
    if args.threshold is None:
      args.threshold = THRESHOLD
  if args.threshold < 0:
    parser.error('--threshold must not be negative')
  return args


def latest(recs):
  '''The last record of each item, keyed, in the order of first appearance.'''
  out = {}
  for record in recs:
    out[records.key(record)] = record
  return out


def ratio(old, new):
  '''
  NEW over OLD; None without both values; 1 for zero over zero, and
  infinity for a rise from zero.
  '''
  if old is None or new is None:
    return None
  if old == 0:
    return 1.0 if new == 0 else float('inf')
  return new / old


def change(name, old, new):
  '''The text of a counter that changed, with the change in percent.'''
  if old:
    return '%s %s->%s (%+.1f%%)' % (name, old, new, 100.0 * (new - old) / old)
  return '%s %s->%s' % (name, old, new)


def compare(old, new, metric, threshold, counters=COUNTERS, tolerance=0.0):
  '''
  The row of one item: the two values of the metric, their ratio, the
  verdict, the counters that changed beyond ``tolerance`` (a fraction; 0
  lists every change) and those that changed within it, and the ratios of
  the instructions and the advisory seconds.  Either record may be None.
  '''
  row = {
      'key': records.key(old or new), 'old': None, 'new': None, 'ratio': None
    , 'verdict': None, 'counters': [], 'within': [], 'ratios': {}
    }
  if old is None:
    row['verdict'] = 'only-new'
    return row
  if new is None:
    row['verdict'] = 'only-old'
    return row
  if old['status'] != 'ok' or new['status'] != 'ok':
    row['verdict'] = 'fail'
    return row
  row['old'], row['new'] = old.get(metric), new.get(metric)
  row['ratio'] = ratio(row['old'], row['new'])
  if row['ratio'] is None:
    row['verdict'] = 'no-metric'
  elif row['ratio'] > 1 + threshold:
    row['verdict'] = 'slower'
  elif row['ratio'] < 1 - threshold:
    row['verdict'] = 'faster'
  else:
    row['verdict'] = 'same'
  for name in counters:
    a, b = old.get(name), new.get(name)
    if a is None or b is None or a == b:
      continue
    if tolerance and a and abs(b - a) <= tolerance * abs(a):
      row['within'].append(name)
    else:
      row['counters'].append(change(name, a, b))
  for name in ('instructions',) + ADVISORY:
    row['ratios'][name] = ratio(old.get(name), new.get(name))
  return row


def number(value, metric):
  if value is None:
    return '-'
  if metric == 'peak_rss':
    return '%.1fM' % (value / 1048576.0)
  if metric == 'instructions':
    return '%.1fM' % (value / 1e6)
  return '%.4f' % value


def fraction(value):
  return '-' if value is None else '%.2f' % value


def write_row(stream, row, metric, deterministic=False):
  suite, program, backend, variant = row['key']
  if row['counters']:
    counters = ', '.join(row['counters'])
  elif row['verdict'] in ('only-old', 'only-new', 'fail'):
    counters = '-'
  elif row['within']:
    counters = 'within'
  else:
    counters = 'equal'
  fields = [
      suite, program[:16], backend, variant or '-', number(row['old'], metric)
    , number(row['new'], metric), fraction(row['ratio'])
    ]
  if deterministic:
    fields += [fraction(row['ratios'].get(name)) for name in ADVISORY]
    columns = DETERMINISTIC_COLUMNS
  else:
    fields.append(fraction(row['ratios'].get('instructions')))
    columns = COLUMNS
  fields += [row['verdict'], counters]
  stream.write(columns % tuple(fields) + '\n')


def distinct(values):
  out = []
  for value in values:
    if value not in out:
      out.append(value)
  return out


def machine_text(m):
  '''
  One phrase about a machine context: the processor, the cores, and the
  memory, as far as the record says.
  '''
  parts = [m['cpu_model'] or 'unknown processor']
  if m['cores'] is not None:
    parts.append('%s cores' % m['cores'])
  if m['mem_gb'] is not None:
    parts.append('%s GiB' % m['mem_gb'])
  return ', '.join(parts)


def describe(recs):
  '''
  One line about the records of a file: the labels, the commits, and the
  machines, each as the distinct values in the order of appearance.
  '''
  if not recs:
    return 'no records'
  labels = distinct(r['label'] for r in recs if r['label'])
  commits = distinct(r['commit'] or 'unknown' for r in recs)
  machines = distinct(machine_text(records.machine(r)) for r in recs)
  parts = []
  if labels:
    parts.append('label ' + ' or '.join(repr(label) for label in labels))
  parts.append('commit ' + ' or '.join(commits))
  parts.append(' or '.join(machines) or 'unknown machine')
  return ', '.join(parts)


def same_machine(a, b):
  '''Whether two machine contexts agree on everything both of them say.'''
  return all(
      a[name] is None or b[name] is None or a[name] == b[name] for name in a
    )


def machines_differ(old_recs, new_recs):
  '''Whether the records of the two files come from different machines.'''
  old_machines = distinct(records.machine(r) for r in old_recs)
  new_machines = distinct(records.machine(r) for r in new_recs)
  return any(
      not same_machine(a, b) for a in old_machines for b in new_machines
    )


def summary(rows, metric, threshold, deterministic=False):
  '''
  The counts of the verdicts of ``rows`` by name, with 'changed' for the
  rows whose counters differ, and the one-line summary that names them and
  the settings of the comparison.
  '''
  counts = {verdict: 0 for verdict in VERDICTS}
  for row in rows:
    counts[row['verdict']] += 1
  counts['changed'] = sum(1 for row in rows if row['counters'])
  percent = '%g' % (threshold * 100)
  if deterministic:
    settings = 'deterministic: metric instructions, tolerance %s%%; wall ' \
               'and CPU seconds advisory' % percent
  else:
    settings = 'metric %s, threshold %s%%' % (metric, percent)
  line = (
      '%d items: %d same, %d faster, %d slower, %d failed, %d without the '
      'metric, %d only in one file; %d with changed counters (%s)' % (
          len(rows), counts['same'], counts['faster'], counts['slower']
        , counts['fail'], counts['no-metric']
        , counts['only-old'] + counts['only-new'], counts['changed'], settings
        )
    )
  return counts, line


def main(argv=None):
  args = parse_args(sys.argv[1:] if argv is None else argv)
  try:
    old_recs = records.read(args.old)
    new_recs = records.read(args.new)
  except (OSError, ValueError) as exc:
    sys.exit('compare: %s' % exc)
  old, new = latest(old_recs), latest(new_recs)
  if args.deterministic:
    counters, tolerance = DETERMINISTIC_COUNTERS, args.threshold
  else:
    counters, tolerance = COUNTERS, 0.0
  keys = list(old) + [k for k in new if k not in old]
  rows = [
      compare(
          old.get(k), new.get(k), args.metric, args.threshold, counters
        , tolerance
        )
          for k in keys
    ]
  percent = '%g' % (args.threshold * 100)
  out = sys.stdout
  out.write('old: %s\n' % describe(old_recs))
  out.write('new: %s\n' % describe(new_recs))
  if machines_differ(old_recs, new_recs):
    if args.deterministic:
      out.write(
          'note: the machines differ; the deterministic columns compare, '
          'the advisory columns ~cpu and ~wall do not\n'
        )
    else:
      out.write(
          'warning: the machines differ; wall and CPU seconds do not '
          'compare across machines; use --deterministic\n'
        )
  if args.deterministic:
    out.write(
        'deterministic: the instructions decide (tolerance %s%%); counters '
        'lists steps, forks, and collections beyond it; ~cpu and ~wall are '
        'advisory\n' % percent
      )
    out.write(DETERMINISTIC_COLUMNS % DETERMINISTIC_HEADINGS + '\n')
  else:
    out.write(COLUMNS % HEADINGS + '\n')
  for row in rows:
    write_row(out, row, args.metric, args.deterministic)
  counts, line = summary(rows, args.metric, args.threshold, args.deterministic)
  out.write(line + '\n')
  missing = {}
  for name, side in ('OLD', old), ('NEW', new):
    missing[name] = sum(
        1 for k in keys
          if k in side and side[k]['status'] == 'ok'
             and side[k].get('instructions') is None
      )
  if any(missing.values()):
    out.write(
        'instructions: missing in OLD for %d items and in NEW for %d items '
        '(records written without perf, or by an older harness)\n'
        % (missing['OLD'], missing['NEW'])
      )
  out.flush()
  if args.strict and (
      counts['slower'] or counts['fail'] or counts['changed']
      or counts['no-metric']
    ):
    return 1
  return 0


if __name__ == '__main__':
  sys.exit(main())
