'''
The counters command: tabulates the scheduler counters of a record file.

A C++ runtime built with the scheduler counters (make COUNTERS=1) appends
fields to the line of ``sprite-exec --stats``: the steps taken while the
outermost queue held one configuration, the steps inside set functions, the
steps whose redex another configuration created, the largest queue, and the
lifetimes of the configurations.  The harness keeps the whole line in
``extra.stats`` of every sample.  This command prints one row per item of a
record file, with the fractions the parallel-evaluation gate asks for:

    serial    serial_steps / steps: the share of the work during which a
              thread pool over the queue would have nothing else to run.
    nested    nested_steps / steps: the share of the work inside set
              functions.
    shared    shared_steps / steps: the share of the steps on a redex that
              another configuration created.
    failed    failed_steps / steps: the share of the work spent in
              configurations that failed.

The lifetimes are in steps: the median (exact below 1024, else the lower
bound of a power-of-two bucket), the mean, and the largest.  The counters
come from the first successful repetition.  An item without the counters
shows dashes.  An item with a variant (the memory and the split suites) is
named program:variant.
'''

import argparse, sys
from . import records

__all__ = ['FIELDS', 'HEADINGS', 'counters_of', 'main', 'parse_args', 'row']

# The fields of the stats line that the row needs.
FIELDS = (
    'steps', 'forks', 'serial_steps', 'nested_steps', 'shared_steps'
  , 'queue_max', 'configurations', 'failed_steps', 'lifetime_median'
  , 'lifetime_mean', 'lifetime_max', 'nested_configurations'
  , 'nested_lifetime_median'
  )
HEADINGS = (
    'program', 'steps', 'forks', 'serial', 'nested', 'shared', 'failed'
  , 'qmax', 'configs', 'median', 'mean', 'max', 'nconfigs', 'nmedian'
  )
COLUMNS = '%-16s %11s %9s %6s %6s %6s %6s %6s %9s %7s %9s %9s %9s %7s'


def parse_args(argv):
  parser = argparse.ArgumentParser(
      prog='run_benchmarks counters'
    , description='Tabulate the scheduler counters of a record file of the '
                  'benchmark harness.  The runtime must have been built with '
                  'make COUNTERS=1; an item without the counters shows '
                  'dashes.  The fractions are over the steps of the run.'
    )
  parser.add_argument('file', metavar='FILE', help='a record file')
  parser.add_argument(
      '-b', '--backend', default=None
    , help='show the records of this backend only [default: all]'
    )
  parser.add_argument(
      '--csv', action='store_true'
    , help='write comma-separated values instead of a table'
    )
  return parser.parse_args(argv)


def counters_of(record):
  '''
  The stats fields of the first successful sample of ``record`` that carries
  the scheduler counters, or None.
  '''
  for sample in record['samples']:
    if sample['status'] != 'ok':
      continue
    stats = (sample.get('extra') or {}).get('stats') or {}
    if all(name in stats for name in FIELDS):
      return stats
  return None


def fraction(part, whole):
  return None if not whole else part / whole


def row(record):
  '''
  The row of one record: a dict keyed by HEADINGS.  The fractions are None
  when the run took no step; every value is None without the counters.
  '''
  stats = counters_of(record)
  out = dict.fromkeys(HEADINGS)
  out['program'] = record['program']
  if record['variant']:
    out['program'] += ':' + record['variant']
  if stats is None:
    return out
  steps = stats['steps']
  out.update(
      steps=steps, forks=stats['forks']
    , serial=fraction(stats['serial_steps'], steps)
    , nested=fraction(stats['nested_steps'], steps)
    , shared=fraction(stats['shared_steps'], steps)
    , failed=fraction(stats['failed_steps'], steps)
    , qmax=stats['queue_max'], configs=stats['configurations']
    , median=stats['lifetime_median'], mean=stats['lifetime_mean']
    , max=stats['lifetime_max'], nconfigs=stats['nested_configurations']
    , nmedian=stats['nested_lifetime_median']
    )
  return out


def text(value, heading):
  if value is None:
    return '-'
  if heading in ('serial', 'nested', 'shared', 'failed'):
    return '%.3f' % value
  if heading == 'mean':
    return '%.1f' % value
  return str(value)


def write_table(stream, rows, csv=False):
  if csv:
    stream.write(','.join(HEADINGS) + '\n')
    for r in rows:
      stream.write(','.join(text(r[h], h) for h in HEADINGS) + '\n')
  else:
    stream.write(COLUMNS % HEADINGS + '\n')
    for r in rows:
      values = [text(r[h], h) for h in HEADINGS]
      values[0] = values[0][:16]
      stream.write(COLUMNS % tuple(values) + '\n')
  stream.flush()


def main(argv=None):
  args = parse_args(sys.argv[1:] if argv is None else argv)
  try:
    recs = records.read(args.file)
  except (OSError, ValueError) as exc:
    sys.exit('counters: %s' % exc)
  if args.backend:
    recs = [r for r in recs if r['backend'] == args.backend]
  rows = [row(r) for r in recs]
  write_table(sys.stdout, rows, csv=args.csv)
  return 0 if any(r['steps'] is not None for r in rows) else 1


if __name__ == '__main__':
  sys.exit(main())
