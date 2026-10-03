'''
The compare command: joins two record files and shows the change per item.

Items are matched on suite, program, backend, and variant; the last record of
an item in a file counts.  The ratio is NEW over OLD of one metric (CPU
seconds by default).  A ratio within the noise threshold of 1 is the same.
The exact counters, steps and forks, must agree; a change in them means a
change in the program or the compiler, not in the machine.
'''

import argparse, sys
from . import records

__all__ = ['COUNTERS', 'METRICS', 'VERDICTS', 'compare', 'main', 'parse_args']

METRICS = ('wall', 'cpu', 'eval_wall', 'eval_cpu', 'peak_rss', 'compile')
COUNTERS = ('steps', 'forks')
VERDICTS = (
    'same', 'faster', 'slower', 'fail', 'no-metric', 'only-old', 'only-new'
  )
COLUMNS = '%-10s %-16s %-7s %-13s %10s %10s %6s  %-9s %s'
HEADINGS = (
    'suite', 'program', 'backend', 'variant', 'old', 'new', 'ratio', 'verdict'
  , 'counters'
  )


def parse_args(argv):
  parser = argparse.ArgumentParser(
      prog='run_benchmarks compare'
    , description='Compare two record files of the benchmark harness.  The '
                  'ratio is NEW over OLD of the chosen metric; a ratio within '
                  'the noise threshold of 1 counts as the same.  The exact '
                  'counters, steps and forks, must agree.'
    )
  parser.add_argument(
      'old', metavar='OLD', help='the record file of the baseline'
    )
  parser.add_argument('new', metavar='NEW', help='the record file to compare')
  parser.add_argument(
      '-m', '--metric', choices=METRICS, default='cpu'
    , help='the metric to compare [default: cpu]'
    )
  parser.add_argument(
      '-t', '--threshold', type=float, default=0.10, metavar='FRACTION'
    , help='noise threshold: a ratio within 1 +/- FRACTION is the same '
           '[default: 0.10]'
    )
  parser.add_argument(
      '--strict', action='store_true'
    , help='exit with status 1 when an item is slower, a counter changed, or '
           'a run failed'
    )
  args = parser.parse_args(argv)
  if args.threshold < 0:
    parser.error('--threshold must not be negative')
  return args


def latest(recs):
  '''The last record of each item, keyed, in the order of first appearance.'''
  out = {}
  for record in recs:
    out[records.key(record)] = record
  return out


def compare(old, new, metric, threshold):
  '''
  The row of one item: the two values of the metric, their ratio, the
  verdict, and the counters that changed.  Either record may be None.
  '''
  row = {
      'key': records.key(old or new), 'old': None, 'new': None, 'ratio': None
    , 'verdict': None, 'counters': []
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
  row['old'], row['new'] = old[metric], new[metric]
  if row['old'] is None or row['new'] is None:
    row['verdict'] = 'no-metric'
  elif row['old'] == 0:
    row['ratio'] = 1.0 if row['new'] == 0 else float('inf')
    row['verdict'] = 'same' if row['new'] == 0 else 'slower'
  else:
    row['ratio'] = row['new'] / row['old']
    if row['ratio'] > 1 + threshold:
      row['verdict'] = 'slower'
    elif row['ratio'] < 1 - threshold:
      row['verdict'] = 'faster'
    else:
      row['verdict'] = 'same'
  for name in COUNTERS:
    if None not in (old[name], new[name]) and old[name] != new[name]:
      row['counters'].append('%s %s->%s' % (name, old[name], new[name]))
  return row


def number(value, metric):
  if value is None:
    return '-'
  if metric == 'peak_rss':
    return '%.1fM' % (value / 1048576.0)
  return '%.4f' % value


def write_row(stream, row, metric):
  suite, program, backend, variant = row['key']
  if row['counters']:
    counters = ', '.join(row['counters'])
  elif row['verdict'] in ('only-old', 'only-new', 'fail'):
    counters = '-'
  else:
    counters = 'equal'
  ratio = '-' if row['ratio'] is None else '%.2f' % row['ratio']
  stream.write(COLUMNS % (
      suite, program[:16], backend, variant or '-', number(row['old'], metric)
    , number(row['new'], metric), ratio, row['verdict'], counters
    ) + '\n')


def main(argv=None):
  args = parse_args(sys.argv[1:] if argv is None else argv)
  try:
    old = latest(records.read(args.old))
    new = latest(records.read(args.new))
  except (OSError, ValueError) as exc:
    sys.exit('compare: %s' % exc)
  keys = list(old) + [k for k in new if k not in old]
  rows = [
      compare(old.get(k), new.get(k), args.metric, args.threshold)
          for k in keys
    ]
  out = sys.stdout
  out.write(COLUMNS % HEADINGS + '\n')
  for row in rows:
    write_row(out, row, args.metric)
  counts = {verdict: 0 for verdict in VERDICTS}
  for row in rows:
    counts[row['verdict']] += 1
  changed = sum(1 for row in rows if row['counters'])
  out.write(
      '%d items: %d same, %d faster, %d slower, %d failed, %d without the '
      'metric, %d only in one file; %d with changed counters '
      '(metric %s, threshold %d%%)\n' % (
          len(rows), counts['same'], counts['faster'], counts['slower']
        , counts['fail'], counts['no-metric']
        , counts['only-old'] + counts['only-new'], changed, args.metric
        , round(args.threshold * 100)
        )
    )
  out.flush()
  if args.strict and (counts['slower'] or counts['fail'] or changed):
    return 1
  return 0


if __name__ == '__main__':
  sys.exit(main())
