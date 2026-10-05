'''
The split command: tabulates the records of the split suite.

The split suite runs a search program whole and in parts: its search space
split by hand into 2, 4, and 8 independent subproblems (the modules under
data/curry/benchmarks/split), each part in a process of its own.  For a
program and a part count, this command computes what a design that runs the
parts on separate workers could gain:

    bound        The speedup bound: the whole over the longest part, in CPU
                 seconds by default (-m picks wall or eval_wall, the time
                 of the evaluation alone).
    dup          The duplicated work: the sum of the parts over the whole,
                 by the same metric; 1.0 means the parts cost the whole.
    bound_steps  The whole's rewrite steps over the steps of the longest
                 part.  Steps are exact, so this bound does not move with
                 the load of the machine.
    dup_steps    The sum of the parts' steps over the whole's.
    dup_forks    The sum of the parts' forks over the whole's.

A row needs the whole and every part of the split, each with status ok; a
row with a part missing or failed shows the count of parts it has and
dashes.  With --parts, the parts follow their row: the variant, the metric,
the steps, the forks, and the status.  The last record of an item in the
file counts.
'''

import argparse, sys
from . import records
from .compare import latest
from .suites import SPLIT_PARTS

__all__ = [
    'HEADINGS', 'METRICS', 'PART_HEADINGS', 'main', 'parse_args', 'part_of'
  , 'rows'
  ]

METRICS = ('cpu', 'wall', 'eval_wall')
HEADINGS = (
    'program', 'backend', 'parts', 'ok', 'whole', 'longest', 'part', 'bound'
  , 'dup', 'whole_steps', 'bound_steps', 'dup_steps', 'dup_forks'
  )
PART_HEADINGS = ('variant', 'metric', 'steps', 'forks', 'status')
COLUMNS = '%-13s %-7s %5s %5s %9s %9s %-5s %6s %6s %12s %11s %9s %9s'
PART_COLUMNS = '    %-13s %9s %12s %9s %s'


def parse_args(argv):
  parser = argparse.ArgumentParser(
      prog='run_benchmarks split'
    , description='Tabulate the records of the split suite: the speedup '
                  'bound (the whole over the longest part) and the '
                  'duplicated work (the sum of the parts over the whole) '
                  'of a search program split by hand into 2, 4, and 8 '
                  'parts.'
    )
  parser.add_argument('file', metavar='FILE', help='a record file')
  parser.add_argument(
      '-b', '--backend', default=None
    , help='show the records of this backend only [default: all]'
    )
  parser.add_argument(
      '-m', '--metric', choices=METRICS, default='cpu'
    , help='the time of the whole and the parts [default: cpu]'
    )
  parser.add_argument(
      '--parts', action='store_true'
    , help='list the parts below the row of their split'
    )
  parser.add_argument(
      '--csv', action='store_true'
    , help='write comma-separated values instead of a table'
    )
  return parser.parse_args(argv)


def part_of(variant):
  '''
  The part count and the index named by the variant of a split record, or
  None for the whole.
  '''
  if variant is None or variant == 'whole':
    return None
  k, _, i = variant.partition('/')
  return int(k), int(i)


def ratio(numerator, denominator):
  if numerator is None or not denominator:
    return None
  return numerator / denominator


def rows(recs, metric='cpu'):
  '''
  The rows of a record file: one per program, backend, and part count, in
  the order of the programs in the file and of the part counts.  A row is a
  dict keyed by HEADINGS, with the records of its parts under 'records':
  a list of (variant, record or None) in the order of the parts.
  '''
  groups = {}
  for record in latest(recs).values():
    if record['suite'] != 'split':
      continue
    group = groups.setdefault((record['program'], record['backend']), {})
    group[record['variant']] = record
  out = []
  for (program, backend), group in groups.items():
    counts = sorted(set(
        part_of(v)[0] for v in group if part_of(v) is not None
      ))
    for k in counts:
      whole = group.get('whole')
      parts = [(v, group.get(v)) for v in ('%d/%d' % (k, i) for i in range(k))]
      good = [r for _, r in parts if r is not None and r['status'] == 'ok']
      row = dict.fromkeys(HEADINGS)
      row.update(
          program=program, backend=backend, parts=k
        , ok='%d/%d' % (len(good), k), records=parts
        )
      complete = len(good) == k and whole is not None \
                 and whole['status'] == 'ok'
      if complete:
        times = [(r[metric], v) for v, r in parts if r[metric] is not None]
        if len(times) == k and whole[metric] is not None:
          longest, variant = max(times)
          row.update(
              whole=whole[metric], longest=longest, part=variant
            , bound=ratio(whole[metric], longest)
            , dup=ratio(sum(t for t, _ in times), whole[metric])
            )
        steps = [r['steps'] for r in good]
        if None not in steps and whole['steps'] is not None:
          row.update(
              whole_steps=whole['steps']
            , bound_steps=ratio(whole['steps'], max(steps))
            , dup_steps=ratio(sum(steps), whole['steps'])
            )
        forks = [r['forks'] for r in good]
        if None not in forks and whole['forks'] is not None:
          row['dup_forks'] = ratio(sum(forks), whole['forks'])
      out.append(row)
  return out


def text(value, heading):
  if value is None:
    return '-'
  if heading in ('whole', 'longest', 'metric'):
    return '%.3f' % value
  if heading in ('bound', 'dup', 'bound_steps', 'dup_steps', 'dup_forks'):
    return '%.2f' % value
  return str(value)


def part_row(variant, record, metric):
  '''The row of one part, a dict keyed by PART_HEADINGS.'''
  if record is None:
    return dict(zip(PART_HEADINGS, (variant, None, None, None, 'missing')))
  return dict(zip(
      PART_HEADINGS
    , (variant, record[metric], record['steps'], record['forks']
      , record['status'])
    ))


def write_table(stream, table, metric, parts=False, csv=False):
  if csv:
    stream.write(','.join(HEADINGS) + '\n')
    for row in table:
      stream.write(','.join(text(row[h], h) for h in HEADINGS) + '\n')
      if parts:
        for variant, record in row['records']:
          r = part_row(variant, record, metric)
          stream.write(
              ',' + ','.join(text(r[h], h) for h in PART_HEADINGS) + '\n'
            )
  else:
    stream.write(COLUMNS % HEADINGS + '\n')
    for row in table:
      values = [text(row[h], h) for h in HEADINGS]
      values[0] = values[0][:13]
      stream.write(COLUMNS % tuple(values) + '\n')
      if parts:
        for variant, record in row['records']:
          r = part_row(variant, record, metric)
          stream.write(
              PART_COLUMNS % tuple(text(r[h], h) for h in PART_HEADINGS)
              + '\n'
            )
  stream.flush()


def main(argv=None):
  args = parse_args(sys.argv[1:] if argv is None else argv)
  try:
    recs = records.read(args.file)
  except (OSError, ValueError) as exc:
    sys.exit('split: %s' % exc)
  if args.backend:
    recs = [r for r in recs if r['backend'] == args.backend]
  table = rows(recs, args.metric)
  write_table(sys.stdout, table, args.metric, parts=args.parts, csv=args.csv)
  return 0 if any(row['bound'] is not None for row in table) else 1


if __name__ == '__main__':
  sys.exit(main())
