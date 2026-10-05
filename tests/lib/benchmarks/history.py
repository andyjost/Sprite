'''
The history command: the records of the nightly job and the points of the
chart page.

A history is a directory, the working tree of the branch that the nightly
performance job writes (perf-history; see the README of the tests, section
9).  It holds:

    README.md             What the files are.  Written once.
    records/SUITE.jsonl   Every record of the suite, in the order of
                          arrival: a record file of the harness, which the
                          compare command reads as it is.
    points.json           The points of the chart page: one compact object
                          per record (POINT_FIELDS: the item, the date, the
                          commit, the status, the medians, and the exact
                          counters) without the samples and the machine
                          facts.  Derived from the record files, so it can
                          be written again at any time.

``history DIR FILE...`` reads the records of each FILE, prints each against
the previous record of its item in the history (the rows and the summary of
the compare command: the ratio of one metric and the counters that
changed), appends the records to records/SUITE.jsonl, and writes
points.json again from every record file.  ``history DIR`` writes
points.json (and a missing README) and nothing else.  A timing never fails
the command; a file it cannot read does.
'''

import argparse, glob, json, os, sys
from . import SUITES
from . import records
from .compare import COLUMNS, HEADINGS, METRICS, compare, latest, summary
from .compare import write_row

__all__ = [
    'POINTS_SCHEMA', 'POINT_FIELDS', 'README', 'append', 'main', 'parse_args'
  , 'point', 'points', 'read_history', 'record_file', 'report'
  , 'write_points', 'write_readme'
  ]

POINTS_SCHEMA = 1
POINTS_FILE = 'points.json'
RECORDS_DIR = 'records'
POINT_FIELDS = (
    'suite', 'program', 'backend', 'variant', 'date', 'commit', 'label'
  , 'status', 'error', 'wall', 'cpu', 'eval_wall', 'compile', 'peak_rss'
  , 'steps', 'forks'
  )
README = '''\
# Performance history

The nightly performance job of Sprite writes this branch, perf-history.
It is not meant to be edited by hand.

- `records/SUITE.jsonl`: every record of the suite, one JSON object per
  line, in the order of arrival.  The fields are documented in
  `tests/lib/benchmarks/records.py` of the main branch, and
  `tests/run_benchmarks compare` reads these files as they are.
- `points.json`: the points of the chart page: one compact object per
  record, derived from the record files by `tests/run_benchmarks history`.

The page `perf/index.html` of the documentation reads `points.json` from
this branch.  Timings from shared runners are advisory; the exact counters
(steps, forks) tell a change in the program from a change in the machine.
'''


def parse_args(argv):
  parser = argparse.ArgumentParser(
      prog='run_benchmarks history'
    , description='Append record files to the history of the nightly job '
                  'and write the points of the chart page.  Each new record '
                  'is printed against the previous record of its item: the '
                  'ratio of one metric with a noise threshold, and the '
                  'counters that changed.  Without a FILE only the points '
                  'are written again.'
    )
  parser.add_argument(
      'dir', metavar='DIR'
    , help='the history directory (records/SUITE.jsonl and points.json)'
    )
  parser.add_argument(
      'files', nargs='*', metavar='FILE', help='a record file to append'
    )
  parser.add_argument(
      '-m', '--metric', choices=METRICS, default='cpu'
    , help='the metric of the comparison [default: cpu]'
    )
  parser.add_argument(
      '-t', '--threshold', type=float, default=0.10, metavar='FRACTION'
    , help='noise threshold: a ratio within 1 +/- FRACTION is the same '
           '[default: 0.10]'
    )
  args = parser.parse_args(argv)
  if args.threshold < 0:
    parser.error('--threshold must not be negative')
  return args


def record_file(directory, suite):
  '''The record file of ``suite`` in the history.'''
  return os.path.join(directory, RECORDS_DIR, suite + '.jsonl')


def read_history(directory):
  '''
  The records of the history: the record files in the order of the suites,
  each in file order.  An empty list for a directory without records.
  '''
  pattern = os.path.join(directory, RECORDS_DIR, '*.jsonl')
  files = sorted(glob.glob(pattern))
  files.sort(key=lambda f: _suite_order(os.path.basename(f)[:-len('.jsonl')]))
  recs = []
  for filename in files:
    recs.extend(records.read(filename))
  return recs


def _suite_order(suite):
  return (SUITES.index(suite) if suite in SUITES else len(SUITES), suite)


def point(record):
  '''The point of a record: POINT_FIELDS and nothing else.'''
  return {name: record[name] for name in POINT_FIELDS}


def points(recs):
  '''
  The points of ``recs``, sorted by suite (in the order of SUITES),
  program, backend, variant, and date, so that a series is contiguous and
  in time order.
  '''
  def order(p):
    return (
        _suite_order(p['suite']), p['program'], p['backend']
      , p['variant'] or '', p['date']
      )
  return sorted((point(r) for r in recs), key=order)


def write_points(directory, pts):
  '''
  Writes points.json: a JSON object with the schema, the time, and the
  points, one per line.  Returns the file name.
  '''
  filename = os.path.join(directory, POINTS_FILE)
  with open(filename, 'w') as stream:
    stream.write(
        '{"schema": %d, "generated": "%s", "points": [\n'
        % (POINTS_SCHEMA, records.now())
      )
    stream.write(',\n'.join(json.dumps(p, separators=(',', ':')) for p in pts))
    stream.write('\n]}\n')
  return filename


def write_readme(directory):
  '''Writes README.md unless the history has one.  Returns the file name.'''
  filename = os.path.join(directory, 'README.md')
  if not os.path.exists(filename):
    with open(filename, 'w') as stream:
      stream.write(README)
  return filename


def append(directory, recs):
  '''
  Appends ``recs`` to the record files of their suites, in order.  Returns
  the files written.
  '''
  os.makedirs(os.path.join(directory, RECORDS_DIR), exist_ok=True)
  streams = {}
  try:
    for record in recs:
      suite = record['suite']
      if suite not in streams:
        streams[suite] = open(record_file(directory, suite), 'a')
      records.write(streams[suite], record)
  finally:
    for stream in streams.values():
      stream.close()
  return [record_file(directory, suite) for suite in streams]


def report(stream, previous, recs, title, metric, threshold):
  '''
  Writes the rows of ``recs`` against ``previous`` (the last record of
  each item, as compare.latest gives it) and the summary line, under a
  heading that names ``title``.  Returns the counts of the summary.
  '''
  rows = [
      compare(previous.get(records.key(r)), r, metric, threshold)
          for r in recs
    ]
  stream.write(
      '%s: %d records against the previous run\n' % (title, len(recs))
    )
  stream.write(COLUMNS % HEADINGS + '\n')
  for row in rows:
    write_row(stream, row, metric)
  counts, line = summary(rows, metric, threshold)
  stream.write(line + '\n')
  stream.flush()
  return counts


def main(argv=None):
  args = parse_args(sys.argv[1:] if argv is None else argv)
  try:
    os.makedirs(args.dir, exist_ok=True)
    history = read_history(args.dir)
    previous = latest(history)
    for filename in args.files:
      recs = records.read(filename)
      report(
          sys.stdout, previous, recs, os.path.basename(filename), args.metric
        , args.threshold
        )
      append(args.dir, recs)
      history.extend(recs)
      # A later file compares with the records of an earlier one.
      previous.update(latest(recs))
    write_readme(args.dir)
    write_points(args.dir, points(history))
  except (OSError, ValueError) as exc:
    sys.exit('history: %s' % exc)
  return 0


if __name__ == '__main__':
  sys.exit(main())
