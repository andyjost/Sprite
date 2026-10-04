'''
The run command: runs the items of a suite and writes one record per item.

The records go to standard output, or to the file of -o (appended); the
progress table goes to standard error.  When perf is available, every item
whose measured repetitions succeeded gets one more repetition under perf,
which counts the instructions (see measure.py); --no-perf leaves it out.
'''

import argparse, os, shutil, sys, tempfile
from . import BACKENDS, CURRYDIR, DEFAULT_SPRITE_HOME, ROOTDIR, SUITES
from . import measure, records, suites

__all__ = ['main', 'parse_args', 'parse_cap']

COLUMNS = '%-10s %-16s %-7s %-13s %9s %9s %9s %8s %10s %9s  %s'
HEADINGS = (
    'suite', 'program', 'backend', 'variant', 'wall', 'cpu', 'eval', 'rss_mb'
  , 'steps', 'instr_m', 'status'
  )
EPILOG = '''
Other commands: "compare OLD NEW" compares two record files (see
"compare -h"); "list" lists the programs of a suite.  Records are JSON
Lines; the fields are documented in benchmarks/records.py.  The column
instr_m of the table is the instructions in millions.
'''


def parse_cap(text):
  '''A size in bytes with an optional suffix K, M, or G (binary).'''
  units = {'k': 1024, 'm': 1024 ** 2, 'g': 1024 ** 3}
  text = text.strip().lower()
  factor = units.get(text[-1:], 1)
  digits = text[:-1] if text[-1:] in units else text
  try:
    value = int(digits) * factor
  except ValueError:
    raise argparse.ArgumentTypeError('not a size: %r' % text)
  if value < 0:
    raise argparse.ArgumentTypeError('a size is not negative: %r' % text)
  return value


def parse_env(text):
  '''A NAME=VALUE pair.'''
  name, sep, value = text.partition('=')
  if not sep or not name:
    raise argparse.ArgumentTypeError('not NAME=VALUE: %r' % text)
  return name, value


def parse_args(argv):
  parser = argparse.ArgumentParser(
      prog='run_benchmarks', epilog=EPILOG
    , description='Run a suite of the benchmark harness and write one JSON '
                  'record per program and backend.  Times are in seconds.'
    )
  parser.add_argument(
      'program', nargs='*', metavar='PROGRAM'
    , help='program or item to run (shell-style patterns allowed) '
           '[default: the dissertation programs, or every item of the suite]'
    )
  parser.add_argument(
      '-s', '--suite', choices=SUITES, default='throughput'
    , help='the suite to run [default: throughput]'
    )
  parser.add_argument(
      '-b', '--backend', action='append', choices=BACKENDS, default=None
    , help='backend to measure; repeat for several [default: cxx]'
    )
  parser.add_argument(
      '--variant', action='append', default=None, metavar='NAME'
    , help='run the items of this variant only (cold, warm, collector=on, '
           'collector=off); repeat for several'
    )
  parser.add_argument(
      '-r', '--repeat', type=int, default=None, metavar='N'
    , help='measured repetitions per item [default: throughput 5, compile 3, '
           'import 5, memory 1]'
    )
  parser.add_argument(
      '-w', '--warmup', type=int, default=1, metavar='N'
    , help='runs before the measured ones, not recorded [default: 1]'
    )
  parser.add_argument(
      '--timeout', type=float, default=600, metavar='SEC'
    , help='kill a run after SEC seconds and record a timeout [default: 600]'
    )
  parser.add_argument(
      '--cap', type=parse_cap, default='6G', metavar='SIZE'
    , help='cap on the address space of a run; suffixes K, M, G; 0 for no '
           'cap [default: 6G]'
    )
  parser.add_argument(
      '--no-perf', action='store_true'
    , help='do not count the instructions: skip the repetition under perf '
           'that follows the measured ones'
    )
  parser.add_argument(
      '--pakcs', metavar='EXE', default=None
    , help='PAKCS executable [default: tools/pakcs of the installation]'
    )
  parser.add_argument(
      '--sprite-home', metavar='DIR', default=None
    , help='Sprite installation [default: $SPRITE_HOME or the staged install/]'
    )
  parser.add_argument(
      '--label', default='', metavar='TEXT'
    , help='a label for the machine or the run, stored in every record'
    )
  parser.add_argument(
      '-e', '--env', action='append', type=parse_env, default=[]
    , metavar='NAME=VALUE'
    , help='set a variable in the environment of every run; repeatable'
    )
  parser.add_argument(
      '-o', '--output', metavar='FILE', default=None
    , help='append the records to FILE [default: standard output]'
    )
  parser.add_argument(
      '-l', '--list', action='store_true'
    , help='list the programs of the suite and exit'
    )
  args = parser.parse_args(argv)
  if args.backend is None:
    args.backend = ['cxx']
  if args.repeat is None:
    args.repeat = suites.DEFAULT_REPEAT[args.suite]
  if args.repeat < 1:
    parser.error('--repeat must be at least 1')
  if args.warmup < 0:
    parser.error('--warmup must not be negative')
  if args.timeout <= 0:
    parser.error('--timeout must be positive')
  return args


def default_pakcs(home):
  '''The PAKCS of the installation, or None.'''
  pakcs = os.path.join(home, 'tools', 'pakcs')
  return pakcs if os.access(pakcs, os.X_OK) else None


def seconds(value):
  return '-' if value is None else '%.3f' % value


def megabytes(value):
  return '-' if value is None else '%.1f' % (value / 1048576.0)


def millions(value):
  return '-' if value is None else '%.1f' % (value / 1e6)


def count(value):
  return '-' if value is None else str(value)


def write_row(stream, record):
  stream.write(COLUMNS % (
      record['suite'], record['program'][:16], record['backend']
    , record['variant'] or '-', seconds(record['wall']), seconds(record['cpu'])
    , seconds(record['eval_wall']), megabytes(record['peak_rss'])
    , count(record['steps']), millions(record['instructions'])
    , record['status']
    ) + '\n')
  for warning in record['warnings']:
    stream.write('    warning: %s\n' % warning)
  if record['error']:
    stream.write('    %s\n' % record['error'])
  stream.flush()


def measure_item(item, repeat, perf):
  '''
  The samples of one item: the warm-up runs (not returned), the measured
  repetitions, and, with ``perf`` and when every measured repetition
  succeeded, one repetition under perf.
  '''
  for _ in range(item.warmup()):
    item.measure()
  samples = [item.measure() for _ in range(repeat)]
  if perf and all(s['status'] == 'ok' for s in samples):
    samples.append(item.measure(perf=True))
  return samples


def main(argv=None):
  args = parse_args(sys.argv[1:] if argv is None else argv)
  try:
    programs = suites.select(args.suite, args.program)
  except ValueError as exc:
    sys.exit('run_benchmarks: %s' % exc)
  if args.list:
    print('\n'.join(programs))
    return 0
  home = args.sprite_home or os.environ.get('SPRITE_HOME') \
                          or DEFAULT_SPRITE_HOME
  if args.no_perf:
    perf, source = None, 'not measured: --no-perf'
  else:
    perf, source = measure.perf(), measure.instructions_source()
  settings = suites.Settings(
      home, pakcs=args.pakcs or default_pakcs(home), timeout=args.timeout
    , cap=args.cap or None, env=dict(args.env), label=args.label
    , warmup=args.warmup, perf=perf, instructions_source=source
    )
  if not os.access(settings.sprite_exec, os.X_OK):
    sys.exit(
        'run_benchmarks: sprite-exec not found at %s' % settings.sprite_exec
      )
  workdir = tempfile.mkdtemp(prefix='sprite-benchmarks-')
  try:
    try:
      items = suites.build(
          args.suite, programs, args.backend, settings, workdir
        )
    except ValueError as exc:
      sys.exit('run_benchmarks: %s' % exc)
    if args.variant:
      items = [item for item in items if item.variant in args.variant]
      if not items:
        sys.exit('run_benchmarks: no item of the %s suite has a variant in %s'
                 % (args.suite, args.variant))
    meta = settings.metadata()
    commit = records.commit(ROOTDIR)
    out = open(args.output, 'a') if args.output else sys.stdout
    log = sys.stderr
    log.write('programs: %s\n' % CURRYDIR)
    log.write('commit: %s\n' % (commit or 'unknown'))
    log.write('machine: %s, %s cores, %s GiB%s\n' % (
        meta['cpu_model'] or 'unknown processor', meta['cores'] or '?'
      , meta['mem_gb'] if meta['mem_gb'] is not None else '?'
      , ', label %r' % args.label if args.label else ''
      ))
    log.write('instructions: %s%s\n' % (
        source, ', in one repetition after the measured ones' if perf else ''
      ))
    log.write('records: %s\n' % (args.output or 'standard output'))
    log.write(COLUMNS % HEADINGS + '\n')
    failures = 0
    try:
      for item in items:
        samples = measure_item(item, args.repeat, perf)
        record = records.summarize(
            item.suite, item.program, item.backend, item.variant, samples
          , meta, label=settings.label, warmup=item.warmup(), commit=commit
          )
        records.write(out, record)
        out.flush()
        write_row(log, record)
        failures += record['status'] != 'ok'
    finally:
      if out is not sys.stdout:
        out.close()
  finally:
    shutil.rmtree(workdir, ignore_errors=True)
  return 1 if failures else 0


if __name__ == '__main__':
  sys.exit(main())
