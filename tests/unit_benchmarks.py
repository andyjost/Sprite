'''
Tests for the benchmark harness under lib/benchmarks: the child runner, the
parsers, the records, the suites, and the run, compare, counters, split, and
history commands.

The smoke tests run the harness on Hello, whose outputs the warm-up run
builds (or finds in the local cache), on the backend of this process, and
they compile Hello and the expression of the compile suite with a warm cache.
In a fresh checkout the file costs three calls of the Curry front end: Hello
in the first warm-up, and Hello and the expression in the compile suite.
'''
import cytest # from ./lib; must be first
from benchmarks import CURRYDIR, DISSERTATION, NIGHTLY, ROOTDIR, SPLITDIR
from benchmarks import SUITES
from benchmarks import compare, counters, history, measure, records, run
from benchmarks import split, suites
from curry import config
import contextlib, curry, io, json, os, shutil, signal, socket, sys, tempfile
import unittest

BACKEND = curry.flags['backend']
PYTHON = sys.executable
CAP = 2 * 1024 ** 3
TIMEOUT = 120
STATS_LINE = (
    'wall=0.124318 cpu=0.116882 steps=7 forks=2 collections=3 '
    'peak_rss=36528128 compile=0.500000'
  )
# The line of a runtime built with the scheduler counters (make COUNTERS=1).
COUNTERS_LINE = STATS_LINE + (
    ' serial_steps=5 nested_steps=0 shared_steps=4 queue_max=4'
    ' configurations=6 failures=1 failed_steps=2 lifetime_median=1'
    ' lifetime_mean=1.166667 lifetime_max=3 nested_configurations=0'
    ' nested_lifetime_median=0 nested_lifetime_mean=0.000000'
    ' nested_lifetime_max=0'
  )
# The output of perf stat -e instructions:u -x, true, captured on a machine
# where perf works: the line on stderr, and the file that -o writes.
PERF_LINE = '226934,,instructions:u,660021,100.00,,\n'
PERF_FILE = (
    '# started on Sun Oct  4 12:53:06 2026\n\n'
    '226935,,instructions:u,759911,100.00,,\n'
  )
BASELINES = os.path.join(CURRYDIR, 'results', 'baseline-2026-10-03-%s.jsonl')
# A million: the compare tables print the instructions in millions.
M = 10 ** 6


class FakeRun:
  '''Stands in for measure.Run.'''
  def __init__(
      self, status='ok', wall=1.0, cpu=0.5, peak_rss=1000, stdout='', stderr=''
    , instructions=None, perf=False
    ):
    self.status = status
    self.returncode = 0 if status == 'ok' else 1
    self.error = None if status == 'ok' else 'boom'
    self.wall = wall
    self.cpu = cpu
    self.peak_rss = peak_rss
    self.stdout = stdout
    self.stderr = stderr
    self.instructions = instructions
    self.perf = perf


def make_record(
    program, cpu, steps=5, forks=1, status='ok', suite='throughput'
  , backend='cxx', variant=None, collections=None, instructions=None
  , meta=None, label=''
  ):
  '''
  A record with one measured sample and, with ``instructions``, one sample
  under perf.
  '''
  fields = {'steps': steps, 'forks': forks, 'collections': collections}
  run = FakeRun(status=status, wall=cpu * 2, cpu=cpu, peak_rss=int(cpu * 1000))
  samples = [records.sample(run, fields)]
  if instructions is not None:
    run = FakeRun(
        status=status, wall=cpu * 3, cpu=cpu * 2, peak_rss=int(cpu * 1000)
      , instructions=instructions, perf=True
      )
    samples.append(records.sample(run, fields))
  return records.summarize(
      suite, program, backend, variant, samples, meta or {}, commit='abc'
    , label=label
    )


def schema_1(record, meta=None):
  '''
  The record as the harness of schema 1 wrote it: no instructions, and the
  machine named cpu and cpus in meta.
  '''
  old = dict(record, schema=1, meta=meta or {'cpu': 'Model', 'cpus': 4})
  del old['instructions']
  old['samples'] = [dict(s) for s in record['samples'] if not s['perf']]
  for sample in old['samples']:
    del sample['instructions'], sample['perf']
  return old


class TestMeasure(unittest.TestCase):
  '''The child runner: wall, CPU, peak RSS, status, output.'''

  def run_python(self, code, **kwds):
    kwds.setdefault('timeout', TIMEOUT)
    kwds.setdefault('cap', CAP)
    return measure.run_command([PYTHON, '-c', code], **kwds)

  def test_run(self):
    run = self.run_python('import sys; print(1); sys.stderr.write("two\\n")')
    self.assertEqual(run.status, 'ok')
    self.assertEqual(run.returncode, 0)
    self.assertIsNone(run.error)
    self.assertFalse(run.timed_out)
    self.assertEqual(run.stdout, '1\n')
    self.assertEqual(run.stderr, 'two\n')
    self.assertGreater(run.wall, 0)
    self.assertGreater(run.cpu, 0)
    self.assertGreater(run.peak_rss, 1024 * 1024)
    self.assertEqual(run.cmd[0], 'timeout')
    self.assertIn('--as=%d' % CAP, run.cmd)
    self.assertFalse(run.perf)
    self.assertIsNone(run.instructions)

  def test_failure(self):
    run = self.run_python('import sys; sys.exit("bad")')
    self.assertEqual(run.status, 'fail')
    self.assertEqual(run.returncode, 1)
    self.assertEqual(run.error, 'exit status 1: bad')

  def test_timeout(self):
    run = self.run_python('import time; time.sleep(60)', timeout=1)
    self.assertEqual(run.status, 'timeout')
    self.assertTrue(run.timed_out)
    self.assertEqual(run.returncode, measure.TIMEOUT_STATUS)
    self.assertEqual(run.error, 'timed out')
    self.assertLess(run.wall, 30)

  def test_cap(self):
    '''An allocation above the cap fails the run.'''
    run = self.run_python('x = b"x" * %d' % (3 * 1024 ** 3), cap=1024 ** 3)
    self.assertEqual(run.status, 'fail')
    self.assertIn('MemoryError', run.error)

  def test_peak_rss_from_a_fat_parent(self):
    '''
    Linux starts the memory high-water mark of a child at the resident set
    of its parent.  With GNU time in the wrapper chain the peak of a small
    child stays small, although this process is big.
    '''
    ballast = b'x' * (64 * 1024 ** 2)
    run = self.run_python('pass')
    self.assertEqual(run.status, 'ok')
    if measure.gnu_time() is None:
      self.assertFalse(run.peak_rss_exact)
      self.assertIn('wait4', measure.rss_source())
      self.skipTest('GNU time is not installed')
    self.assertTrue(run.peak_rss_exact)
    self.assertEqual(measure.rss_source(), 'GNU time')
    self.assertLess(run.peak_rss, len(ballast))
    self.assertGreater(run.peak_rss, 1024 ** 2)
    self.assertIn(measure.gnu_time(), run.cmd)
    del ballast

  def test_descendants_are_counted(self):
    '''The CPU time and the memory of a grandchild are part of the run.'''
    inner = "t = 0\nfor i in range(4000000): t += i\nx = b'x' * %d" \
          % (200 * 1024 ** 2)
    code = 'import subprocess, sys; ' \
           'subprocess.run([sys.executable, "-c", %r])' % inner
    run = self.run_python(code)
    self.assertEqual(run.status, 'ok', run.stderr)
    self.assertGreater(run.cpu, 0.1)
    self.assertGreater(run.peak_rss, 150 * 1024 ** 2)
    self.assertEqual(run.peak_rss_exact, measure.gnu_time() is not None)

  def test_parsers(self):
    stats = measure.parse_stats('** some error **\n' + STATS_LINE + '\n')
    self.assertEqual(stats, {
        'wall': 0.124318, 'cpu': 0.116882, 'steps': 7, 'forks': 2
      , 'collections': 3, 'peak_rss': 36528128, 'compile': 0.5
      })
    self.assertIsNone(measure.parse_stats('no statistics\n'))
    self.assertIsNone(measure.parse_stats('wall=1 cpu=2\n'))
    # The scheduler counters follow the seven fields and are kept.
    stats = measure.parse_stats(COUNTERS_LINE + '\n')
    self.assertEqual(stats['steps'], 7)
    self.assertEqual(stats['serial_steps'], 5)
    self.assertEqual(stats['lifetime_mean'], 1.166667)
    self.assertEqual(stats['nested_lifetime_max'], 0)
    self.assertEqual(len(stats), 7 + 14)
    self.assertIsNone(measure.parse_stats(STATS_LINE + ' trailing\n'))
    # -t prints the seconds without a newline.
    self.assertEqual(measure.parse_time('0.001'), 0.001)
    self.assertEqual(measure.parse_time('True\n0.250\n'), 0.25)
    self.assertIsNone(measure.parse_time(''))
    self.assertIsNone(measure.parse_time('abc'))
    output = 'Result: 42\nExecution time: 12 msec. / elapsed: 15 msec.\n'
    self.assertEqual(measure.parse_pakcs(output), (0.012, 0.015))
    self.assertIsNone(measure.parse_pakcs('Result: 42\n'))
    self.assertEqual(measure.parse_json('noise\n{"a": 1}\n'), {'a': 1})
    self.assertIsNone(measure.parse_json('[1]\n'))
    self.assertIsNone(measure.parse_json('not json\n'))
    self.assertIsNone(measure.parse_json(''))

  def test_parse_perf(self):
    '''The CSV of perf stat -x, from captured samples.'''
    self.assertEqual(measure.parse_perf(PERF_LINE), 226934)
    # The file of -o starts with a comment and an empty line.
    self.assertEqual(measure.parse_perf(PERF_FILE), 226935)
    # A hybrid processor reports one line per kind of core; the sum counts.
    hybrid = (
        '1000,,cpu_core/instructions:u/,500,100.00,,\n'
        '234,,cpu_atom/instructions:u/,500,100.00,,\n'
      )
    self.assertEqual(measure.parse_perf(hybrid), 1234)
    # Other events do not count; the event alone, without the rest, does.
    self.assertEqual(
        measure.parse_perf('12,,cycles:u,1,100.00,,\n7,,instructions:u\n'), 7
      )
    for text in (
        '<not counted>,,instructions:u,0,100.00,,\n'
      , '<not supported>,,instructions:u,0,100.00,,\n'
      , '12,,cycles:u,1,100.00,,\n', 'Error:\n', ''
      ):
      self.assertIsNone(measure.parse_perf(text), text)

  def test_perf_detection(self):
    '''perf is detected once; the source says how, or why not.'''
    path = measure.perf()
    source = measure.instructions_source()
    self.assertIs(measure.perf(), path)
    self.assertEqual(measure.instructions_source(), source)
    self.assertEqual(measure.PERF_EVENT, 'instructions:u')
    if path is None:
      self.assertTrue(source.startswith('not measured: '), source)
    else:
      self.assertTrue(os.access(path, os.X_OK))
      self.assertTrue(
          source.startswith('perf stat -e instructions:u ('), source
        )

  def test_run_under_perf(self):
    '''
    A run under perf counts the instructions of the command and its
    descendants and keeps the exit status, also after a signal death, which
    perf alone reports as text: the shell between perf and the command
    turns it into a status.
    '''
    # The status read-back needs no perf.
    self.assertEqual(measure.perf_status(0), 0)
    self.assertEqual(measure.perf_status(3), 3)
    self.assertEqual(measure.perf_status(128), 128)
    self.assertEqual(measure.perf_status(137), -9)
    self.assertEqual(measure.perf_status(130), -2)
    self.assertEqual(measure.perf_status(measure.TIMEOUT_STATUS), 124)
    # Only a status that names a signal of this machine reads as one: 255
    # (a C program that returns -1) stays 255.
    self.assertEqual(measure.perf_status(129), -1)
    top = max(signal.valid_signals())
    self.assertEqual(measure.perf_status(128 + top), -top)
    self.assertEqual(measure.perf_status(129 + top), 129 + top)
    self.assertEqual(measure.perf_status(255), 255)
    self.assertEqual(measure.PERF_SHIM[:2], ['sh', '-c'])
    perf = measure.perf()
    if perf is None:
      self.skipTest(measure.instructions_source())
    tmp = tempfile.gettempdir()
    def perffiles():
      return [name for name in os.listdir(tmp) if name.startswith('perf-')]
    before = perffiles()
    one = self.run_python('pass', perf=perf)
    self.assertEqual(one.status, 'ok', one.stderr)
    self.assertTrue(one.perf)
    self.assertGreater(one.instructions, 10 ** 6)
    self.assertEqual(perffiles(), before)
    # perf wraps the shell and the command, inside the cap.
    at = one.cmd.index(perf)
    self.assertGreater(at, one.cmd.index('prlimit'))
    self.assertEqual(
        one.cmd[at + 1:at + 5], ['stat', '-e', 'instructions:u', '-x,']
      )
    self.assertEqual(one.cmd[at + 5], '-o')
    self.assertEqual(
        one.cmd[at + 7:], ['--'] + measure.PERF_SHIM + [PYTHON, '-c', 'pass']
      )
    # A grandchild is counted.
    code = 'import subprocess, sys; ' \
           'subprocess.run([sys.executable, "-c", "pass"])'
    two = self.run_python(code, perf=perf)
    self.assertEqual(two.status, 'ok', two.stderr)
    self.assertGreater(two.instructions, 1.5 * one.instructions)
    # The exit status of the command is the status of the run.
    run = self.run_python('import sys; sys.exit(3)', perf=perf)
    self.assertEqual(run.status, 'fail')
    self.assertEqual(run.returncode, 3)
    self.assertIsNotNone(run.instructions)
    # A signal death: perf exits with 0 after one; the shell exits with 128
    # plus the signal, and the harness reads it back.  The command is a
    # shell that kills itself, so the killed process is the command, not
    # the shell of the harness.
    run = measure.run_command(
        ['sh', '-c', 'kill -9 $$'], timeout=TIMEOUT, cap=CAP, perf=perf
      )
    self.assertEqual(run.status, 'fail')
    self.assertEqual(run.returncode, -9)
    self.assertTrue(run.error.startswith('killed by signal 9'), run.error)
    # A command that exits above 128 by itself reads as a signal, as in
    # every shell.
    run = self.run_python('import sys; sys.exit(130)', perf=perf)
    self.assertEqual(run.returncode, -2)
    run = self.run_python('import sys; sys.exit(255)', perf=perf)
    self.assertEqual(run.status, 'fail')
    self.assertEqual(run.returncode, 255)
    # A timeout is a timeout under perf as well.
    run = self.run_python('import time; time.sleep(60)', timeout=1, perf=perf)
    self.assertEqual(run.status, 'timeout')
    self.assertEqual(perffiles(), before)

class TestRecords(unittest.TestCase):
  '''The record format.'''

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-benchmarks-test-')
    self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

  def test_median(self):
    self.assertEqual(records.median([3]), 3)
    self.assertEqual(records.median([3, 1, 2]), 2)
    self.assertEqual(records.median([4, 1, 3, 2]), 2.5)
    self.assertRaises(ValueError, records.median, [])

  def test_committed_records(self):
    '''
    The record files under data/curry/benchmarks/results read and validate.
    Each is named LABEL-SUITE.jsonl after the label and the suite of its
    records, the README of the directory has a section for every label, and
    no record names a path of the machine.
    '''
    results = os.path.join(CURRYDIR, 'results')
    with open(os.path.join(results, 'README.md')) as stream:
      readme = stream.read()
    names = sorted(n for n in os.listdir(results) if n.endswith('.jsonl'))
    self.assertTrue(names)
    labels = set()
    for name in names:
      recs = records.read(os.path.join(results, name))
      self.assertTrue(recs, name)
      for rec in recs:
        records.validate(rec)
        self.assertEqual(name, '%s-%s.jsonl' % (rec['label'], rec['suite']))
        self.assertNotIn('"/', json.dumps(rec), name)
        labels.add(rec['label'])
    for label in sorted(labels):
      self.assertIn('\n## %s\n' % label, readme)

  @staticmethod
  def sample(wall, steps=5, status='ok', **fields):
    run = FakeRun(
        status=status, wall=wall, cpu=wall / 2, peak_rss=int(wall * 1000)
      )
    fields.setdefault('steps', steps)
    fields.setdefault('forks', 1)
    return records.sample(run, fields)

  def test_summarize(self):
    samples = [self.sample(3.0), self.sample(1.0), self.sample(2.0)]
    record = records.summarize(
        'throughput', 'Fib', 'cxx', None, samples, {'cpus': 1}, label='lab'
      , warmup=1, commit='abc'
      )
    records.validate(record)
    self.assertEqual([name for name, _ in records.FIELDS], list(record))
    self.assertEqual(record['status'], 'ok')
    self.assertIsNone(record['error'])
    self.assertEqual(record['wall'], 2.0)
    self.assertEqual(record['cpu'], 1.0)
    self.assertEqual(record['peak_rss'], 2000)
    self.assertEqual(record['steps'], 5)
    self.assertEqual(record['forks'], 1)
    self.assertIsNone(record['collections'])
    self.assertIsNone(record['instructions'])
    self.assertIsNone(record['eval_wall'])
    self.assertIsNone(record['compile'])
    self.assertEqual(record['repeat'], 3)
    self.assertEqual(record['schema'], 2)
    self.assertFalse(samples[0]['perf'])
    self.assertIsNone(samples[0]['instructions'])
    self.assertEqual(record['warmup'], 1)
    self.assertEqual(record['commit'], 'abc')
    self.assertEqual(record['label'], 'lab')
    self.assertEqual(record['warnings'], [])
    self.assertEqual(record['meta'], {'cpus': 1})
    self.assertEqual(record['samples'], samples)
    self.assertRegex(record['date'], r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')
    self.assertEqual(records.key(record), ('throughput', 'Fib', 'cxx', None))
    self.assertRaises(
        ValueError, records.summarize, 'throughput', 'Fib', 'cxx', None, [], {}
      )

  def test_counters_that_differ(self):
    samples = [self.sample(1.0, steps=5), self.sample(1.0, steps=6)]
    record = records.summarize('throughput', 'Fib', 'cxx', None, samples, {})
    self.assertIsNone(record['steps'])
    self.assertEqual(record['forks'], 1)
    self.assertEqual(
        record['warnings'], ['steps differs between repetitions: [5, 6]']
      )

  @staticmethod
  def perf_sample(instructions, steps=5, status='ok'):
    '''A sample of the repetition under perf, with large seconds.'''
    run = FakeRun(
        status=status, wall=9.0, cpu=9.0, peak_rss=9000
      , instructions=instructions, perf=True
      )
    return records.sample(run, {'steps': steps, 'forks': 1})

  def test_instructions(self):
    '''
    The repetition under perf gives the instructions; its seconds stay out
    of the medians; its counters must agree with the measured ones.
    '''
    measured = [self.sample(1.0), self.sample(3.0)]
    def summarize(*extra):
      return records.summarize(
          'throughput', 'Fib', 'cxx', None, measured + list(extra), {}
        )
    record = summarize(self.perf_sample(1000))
    records.validate(record)
    self.assertEqual(record['instructions'], 1000)
    self.assertEqual(record['repeat'], 2)
    self.assertEqual(record['wall'], 2.0)
    self.assertEqual(record['cpu'], 1.0)
    self.assertEqual(record['peak_rss'], 2000)
    self.assertEqual(record['steps'], 5)
    self.assertEqual(record['warnings'], [])
    self.assertEqual(len(record['samples']), 3)
    self.assertTrue(record['samples'][-1]['perf'])
    self.assertEqual(record['samples'][-1]['instructions'], 1000)
    # Several repetitions under perf: the median.
    record = summarize(
        self.perf_sample(1000), self.perf_sample(1300), self.perf_sample(1100)
      )
    self.assertEqual(record['instructions'], 1100)
    self.assertEqual(record['repeat'], 2)
    # A failed repetition under perf: no instructions, a warning, and the
    # status of the measured repetitions.
    record = summarize(self.perf_sample(1000, status='fail'))
    self.assertIsNone(record['instructions'])
    self.assertEqual(record['status'], 'ok')
    self.assertEqual(
        record['warnings']
      , ['instructions: the repetition under perf failed: boom']
      )
    record = summarize(self.perf_sample(None))
    self.assertIsNone(record['instructions'])
    self.assertEqual(
        record['warnings'], ['instructions: perf reported no count']
      )
    # Other counters than the measured ones: the count is not comparable.
    record = summarize(self.perf_sample(1000, steps=6))
    self.assertIsNone(record['instructions'])
    self.assertIsNone(record['steps'])
    self.assertEqual(record['warnings'], [
        'steps differs between repetitions: [5, 5, 6]'
      , 'instructions: the repetition under perf has other counters than '
        'the measured ones: steps 6 (measured 5)'
      ])
    # A command that died before its statistics has no counters.
    truncated = self.perf_sample(1000)
    truncated['steps'] = None
    record = summarize(truncated)
    self.assertIsNone(record['instructions'])
    self.assertEqual(record['steps'], 5)
    self.assertIn('steps None (measured 5)', record['warnings'][0])
    # Without a successful measured repetition there is nothing to agree
    # with; the count stands.
    record = records.summarize(
        'throughput', 'Fib', 'cxx', None
      , [self.sample(1.0, status='fail'), self.perf_sample(7)], {}
      )
    self.assertEqual(record['instructions'], 7)
    self.assertEqual(record['status'], 'fail')
    # A record needs a measured sample.
    with self.assertRaisesRegex(ValueError, 'measured sample'):
      records.summarize(
          'throughput', 'Fib', 'cxx', None, [self.perf_sample(1)], {}
        )

  def test_failed_repetition(self):
    '''A failure sets the status; the medians cover the successful runs.'''
    samples = [
        self.sample(1.0), self.sample(9.0, status='fail'), self.sample(3.0)
      ]
    record = records.summarize('throughput', 'Fib', 'cxx', None, samples, {})
    self.assertEqual(record['status'], 'fail')
    self.assertEqual(record['error'], 'boom')
    self.assertEqual(record['wall'], 2.0)
    self.assertEqual(record['steps'], 5)
    samples = [self.sample(1.0, status='fail')]
    record = records.summarize('throughput', 'Fib', 'cxx', None, samples, {})
    self.assertEqual(record['status'], 'fail')
    self.assertIsNone(record['wall'])
    self.assertIsNone(record['steps'])
    records.validate(record)

  def test_write_and_read(self):
    filename = os.path.join(self.tmpdir, 'records.jsonl')
    first = make_record('Fib', 1.0)
    second = make_record('Tak1', 2.0, backend='py')
    with open(filename, 'w') as stream:
      records.write(stream, first)
      stream.write('\n')
      records.write(stream, second)
    with open(filename) as stream:
      self.assertEqual(len(stream.read().strip().splitlines()), 3)
    self.assertEqual(records.read(filename), [first, second])
    with open(filename, 'a') as stream:
      stream.write('{"schema": 1}\n')
    with self.assertRaisesRegex(
        ValueError, r"line 4: field 'suite' is missing"
      ):
      records.read(filename)
    with open(filename, 'w') as stream:
      stream.write('not json\n')
    self.assertRaisesRegex(ValueError, 'line 1', records.read, filename)

  def test_validate(self):
    record = make_record('Fib', 1.0)
    records.validate(record)
    for name, value, message in [
        ('schema', 3, r'schema 3 is not in \[1, 2\]')
      , ('schema', True, 'schema True is not in')
      , ('suite', 'speed', "field 'suite' has a bad value")
      , ('backend', 'c', "field 'backend' has a bad value")
      , ('status', 'done', "field 'status' has a bad value")
      , ('steps', 1.5, "field 'steps' has a bad value")
      , ('steps', True, "field 'steps' has a bad value")
      , ('instructions', 1.5, "field 'instructions' has a bad value")
      , ('wall', '1', "field 'wall' has a bad value")
      , ('samples', [1], 'samples are JSON objects')
      ]:
      bad = dict(record, **{name: value})
      with self.assertRaisesRegex(ValueError, message):
        records.validate(bad)
    bad = dict(record)
    del bad['meta']
    self.assertRaisesRegex(
        ValueError, "field 'meta' is missing", records.validate, bad
      )
    self.assertRaisesRegex(ValueError, 'JSON object', records.validate, [])
    stream = io.StringIO()
    self.assertRaises(ValueError, records.write, stream, bad)
    self.assertEqual(stream.getvalue(), '')

  def test_commit(self):
    value = records.commit(ROOTDIR)
    if value is not None:
      self.assertRegex(value, r'^[0-9a-f]{12}(-dirty)?$')
    self.assertIsNone(records.commit(os.path.join(self.tmpdir, 'missing')))

  def test_machine_facts(self):
    model = records.cpu_model()
    self.assertTrue(model is None or isinstance(model, str))
    memory = records.memory_gb()
    self.assertTrue(memory is None or isinstance(memory, float))
    if memory is not None:
      self.assertGreater(memory, 0)
      self.assertEqual(memory, round(memory, 1))

  def test_schema_1(self):
    '''
    Records of schema 1 lack the instructions and name the machine cpu and
    cpus.  They validate, load with the instructions None, and tell their
    machine; a record of schema 2 must have the field.
    '''
    record = make_record('Fib', 1.0, instructions=10)
    old = schema_1(record)
    records.validate(old)
    self.assertEqual(
        records.machine(old)
      , {'cpu_model': 'Model', 'cores': 4, 'mem_gb': None}
      )
    self.assertEqual(
        records.machine(record)
      , {'cpu_model': None, 'cores': None, 'mem_gb': None}
      )
    new = dict(record, meta={'cpu_model': 'M2', 'cores': 8, 'mem_gb': 15.5})
    self.assertEqual(
        records.machine(new), {'cpu_model': 'M2', 'cores': 8, 'mem_gb': 15.5}
      )
    bad = dict(record)
    del bad['instructions']
    self.assertRaisesRegex(
        ValueError, "field 'instructions' is missing", records.validate, bad
      )
    self.assertEqual(
        records.upgrade({'schema': 1}), {'schema': 1, 'instructions': None}
      )
    filename = os.path.join(self.tmpdir, 'mixed.jsonl')
    with open(filename, 'w') as stream:
      stream.write(json.dumps(old) + '\n')
      records.write(stream, record)
    loaded = records.read(filename)
    self.assertEqual(loaded[0]['schema'], 1)
    self.assertIsNone(loaded[0]['instructions'])
    self.assertEqual(loaded[0]['steps'], 5)
    self.assertEqual(loaded[1], record)
    self.assertEqual(loaded[1]['instructions'], 10)
    # The committed baseline is schema 1 and loads.
    for suite in 'import', 'throughput':
      recs = records.read(BASELINES % suite)
      self.assertTrue(recs)
      for r in recs:
        self.assertEqual(r['schema'], 1)
        self.assertIsNone(r['instructions'])
        self.assertEqual(r['label'], 'baseline-2026-10-03')
        m = records.machine(r)
        self.assertIsInstance(m['cpu_model'], str)
        self.assertIsInstance(m['cores'], int)
        self.assertIsNone(m['mem_gb'])


class TestSuites(unittest.TestCase):
  '''The selection of programs and the items of the suites.'''

  def setUp(self):
    self.settings = suites.Settings(
        '/nonexistent/home', pakcs='/nonexistent/pakcs', timeout=7, cap=123
      , env={'HARNESS_VAR': '1'}, label='l', warmup=2
      )
    self.workdir = tempfile.mkdtemp(prefix='sprite-benchmarks-test-')
    self.addCleanup(shutil.rmtree, self.workdir, ignore_errors=True)

  def build(self, suite, programs, backends, settings=None):
    return suites.build(
        suite, programs, backends, settings or self.settings, self.workdir
      )

  def test_dissertation_programs(self):
    programs = suites.all_programs()
    self.assertEqual(len(DISSERTATION), 30)
    self.assertEqual(len(set(DISSERTATION)), 30)
    for name in DISSERTATION:
      self.assertIn(name, programs)
      self.assertTrue(os.path.isfile(os.path.join(CURRYDIR, name + '.curry')))
    self.assertEqual(suites.select('throughput', []), list(DISSERTATION))
    self.assertEqual(suites.select('memory', []), list(DISSERTATION))
    self.assertEqual(
        suites.select('compile', []), list(DISSERTATION) + ['expression']
      )
    self.assertEqual(suites.select('import', []), list(suites.IMPORT_ITEMS))

  def test_split_programs(self):
    '''The programs with a split module, and the variants of the suite.'''
    programs = suites.split_programs()
    self.assertEqual(programs, ['PermSort', 'QueensSet', 'SearchQueens'])
    for name in programs:
      self.assertIn(name, DISSERTATION)
      self.assertTrue(
          os.path.isfile(os.path.join(SPLITDIR, name + 'Split.curry'))
        )
    self.assertEqual(suites.select('split', []), programs)
    self.assertEqual(suites.select('split', ['Q*']), ['QueensSet'])
    self.assertEqual(suites.SPLIT_PARTS, (2, 4, 8))
    variants = suites.split_variants()
    self.assertEqual(len(variants), 15)
    self.assertEqual(variants[:4], ['whole', '2/0', '2/1', '4/0'])
    self.assertEqual(variants[-1], '8/7')
    # The split modules are not programs of the other suites.
    self.assertNotIn('QueensSetSplit', suites.all_programs())

  def test_nightly_items(self):
    '''The fixed set of the nightly job, and --nightly.'''
    self.assertEqual(len(NIGHTLY), 10)
    self.assertEqual(len(set(NIGHTLY)), 10)
    programs = suites.all_programs()
    for name in NIGHTLY:
      self.assertIn(name, programs)
    self.assertEqual(suites.nightly_items('throughput'), list(NIGHTLY))
    self.assertEqual(suites.nightly_items('memory'), list(NIGHTLY))
    self.assertEqual(
        suites.nightly_items('compile'), list(NIGHTLY) + ['expression']
      )
    self.assertEqual(suites.nightly_items('import'), list(suites.IMPORT_ITEMS))
    self.assertEqual(suites.nightly_items('split'), suites.split_programs())
    self.assertEqual(
        suites.select('throughput', [], nightly=True), list(NIGHTLY)
      )
    self.assertEqual(
        suites.select('compile', ['Q*'], nightly=True)
      , ['Queens10', 'QueensSet', 'QueensSet9']
      )
    self.assertEqual(
        suites.select('import', ['h*'], nightly=True), ['hello']
      )
    with self.assertRaisesRegex(
        ValueError, "no program of the throughput suite matches 'Hello'"
      ):
      suites.select('throughput', ['Hello'], nightly=True)
    # Without the flag nothing changes.
    self.assertEqual(suites.select('throughput', []), list(DISSERTATION))

  def test_select(self):
    self.assertEqual(
        suites.select('throughput', ['Tak*'])
      , ['Tak0', 'Tak1', 'Tak2', 'TakPeano']
      )
    self.assertEqual(
        suites.select('throughput', ['Fib', 'Tak1', 'Fib']), ['Fib', 'Tak1']
      )
    self.assertEqual(suites.select('compile', ['expr*']), ['expression'])
    self.assertEqual(suites.select('import', ['p*']), ['python', 'prelude'])
    with self.assertRaisesRegex(
        ValueError, "no program of the throughput suite matches 'Nope'"
      ):
      suites.select('throughput', ['Nope'])
    with self.assertRaisesRegex(
        ValueError, "no program of the import suite matches 'Fib'"
      ):
      suites.select('import', ['Fib'])
    self.assertRaises(ValueError, suites.select, 'nosuite', [])

  def test_backend_flag(self):
    self.assertEqual(suites.set_backend_flag(None, 'cxx'), 'backend:cxx')
    self.assertEqual(suites.set_backend_flag('', 'py'), 'backend:py')
    self.assertEqual(
        suites.set_backend_flag('backend:py,debug:1', 'cxx')
      , 'backend:cxx,debug:1'
      )

  def test_environment(self):
    env = self.settings.environment('cxx', CURRYPATH='here')
    self.assertEqual(env['SPRITE_HOME'], '/nonexistent/home')
    self.assertEqual(env['HARNESS_VAR'], '1')
    self.assertEqual(env['CURRYPATH'], 'here')
    self.assertEqual(env['PYTHONIOENCODING'], 'utf-8')
    self.assertTrue(env['SPRITE_INTERPRETER_FLAGS'].startswith('backend:cxx'))
    self.assertEqual(env['PATH'], os.environ['PATH'])
    env = self.settings.environment('pakcs')
    self.assertEqual(
        env.get('SPRITE_INTERPRETER_FLAGS')
      , os.environ.get('SPRITE_INTERPRETER_FLAGS')
      )
    self.assertEqual(
        self.settings.sprite_exec, '/nonexistent/home/bin/sprite-exec'
      )
    self.assertEqual(self.settings.python, '/nonexistent/home/bin/python')

  def test_throughput_items(self):
    items = self.build('throughput', ['Fib', 'Tak1'], ['cxx', 'py', 'pakcs'])
    self.assertEqual([item.key for item in items], [
        ('throughput', program, backend, None)
            for program in ['Fib', 'Tak1']
            for backend in ['cxx', 'py', 'pakcs']
      ])
    cmd, env, cwd = items[0].command()
    self.assertEqual(
        cmd, [self.settings.sprite_exec, '-t', '--stats', '-m', 'Fib']
      )
    self.assertEqual(cwd, CURRYDIR)
    self.assertEqual(env['CURRYPATH'], CURRYDIR)
    self.assertEqual(items[0].warmup(), 2)
    cmd, env, cwd = items[2].command()
    self.assertEqual(
        cmd
      , [ '/nonexistent/pakcs', ':set', '+time', ':l', 'Fib', ':eval', 'main'
        , ':q'
        ]
      )
    self.assertEqual(cwd, CURRYDIR)
    self.assertEqual(env['CURRYPATH'], CURRYDIR)

  def test_memory_items(self):
    items = self.build('memory', ['Fib'], ['cxx', 'py'])
    self.assertEqual([item.key for item in items], [
        ('memory', 'Fib', 'cxx', 'collector=on')
      , ('memory', 'Fib', 'cxx', 'collector=off')
      , ('memory', 'Fib', 'py', 'collector=on')
      ])
    env = items[0].command()[1]
    self.assertEqual(
        env.get('SPRITE_GC_THRESHOLD'), os.environ.get('SPRITE_GC_THRESHOLD')
      )
    env = items[1].command()[1]
    self.assertEqual(env['SPRITE_GC_THRESHOLD'], suites.COLLECTOR_OFF)
    self.assertEqual(items[1].command()[0][1:], ['-t', '--stats', '-m', 'Fib'])

  def test_split_items(self):
    '''
    The whole runs the command of the throughput suite; a part runs the
    goal of the split module with the split directory on CURRYPATH.
    '''
    items = self.build('split', ['QueensSet'], ['cxx', 'py'])
    self.assertEqual([item.key for item in items], [
        ('split', 'QueensSet', backend, variant)
            for backend in ['cxx', 'py']
            for variant in suites.split_variants()
      ])
    whole = items[0]
    self.assertIsNone(whole.part)
    cmd, env, cwd = whole.command()
    reference = suites.SpriteExecItem('QueensSet', 'cxx', self.settings)
    self.assertEqual((cmd, env, cwd), reference.command())
    part = items[5]
    self.assertEqual(part.variant, '4/2')
    self.assertEqual(part.part, (4, 2))
    self.assertEqual(part.module, 'QueensSetSplit')
    cmd, env, cwd = part.command()
    self.assertEqual(cmd, [
        self.settings.sprite_exec, '-t', '--stats', '-m', 'QueensSetSplit'
      , '-g', 'part4_2'
      ])
    self.assertEqual(env['CURRYPATH'], SPLITDIR + os.pathsep + CURRYDIR)
    self.assertTrue(env['SPRITE_INTERPRETER_FLAGS'].startswith('backend:cxx'))
    self.assertEqual(cwd, CURRYDIR)
    self.assertEqual(items[-1].command()[0][-2:], ['-g', 'part8_7'])
    self.assertEqual(items[5].warmup(), 2)
    with self.assertRaisesRegex(ValueError, 'throughput suite only'):
      self.build('split', ['QueensSet'], ['pakcs'])

  def test_compile_items(self):
    items = self.build('compile', ['Fib', 'expression'], ['py'])
    self.assertEqual([item.key for item in items], [
        ('compile', 'Fib', 'py', 'cold'), ('compile', 'Fib', 'py', 'warm')
      , ('compile', 'expression', 'py', 'cold')
      , ('compile', 'expression', 'py', 'warm')
      ])
    cold, warm = items[:2]
    # A cold item needs no warm-up; a warm item needs one to fill the cache.
    self.assertEqual(cold.warmup(), 0)
    self.assertEqual(warm.warmup(), 2)
    settings = suites.Settings('/nonexistent/home', warmup=0)
    self.assertEqual(
        self.build('compile', ['Fib'], ['py'], settings)[1].warmup(), 1
      )
    cmd, env, cwd = cold.command()
    self.assertEqual(
        cmd, [self.settings.sprite_exec, '--stats', '-g', '', 'Fib.curry']
      )
    self.assertEqual(env['SPRITE_CACHE_FILE'], '')
    self.assertEqual(os.path.dirname(cwd), self.workdir)
    self.assertEqual(os.listdir(cwd), ['Fib.curry'])
    cold.cleanup()
    self.assertFalse(os.path.exists(cwd))
    cmd, env, cwd = warm.command()
    self.assertEqual(
        env['SPRITE_CACHE_FILE'], os.path.join(self.workdir, 'icurry.db')
      )
    self.assertNotEqual(cwd, self.workdir)
    warm.cleanup()
    cmd, env, cwd = items[3].command()
    self.assertEqual(cmd, [self.settings.python, suites.PROBE, '1+2', 'Int'])
    self.assertTrue(os.path.isfile(suites.PROBE))
    self.assertEqual(
        env['SPRITE_CACHE_FILE'], os.path.join(self.workdir, 'icurry.db')
      )
    items[3].cleanup()
    self.assertEqual(os.listdir(self.workdir), [])

  def test_import_items(self):
    items = self.build('import', list(suites.IMPORT_ITEMS), ['py'])
    self.assertEqual(
        [item.program for item in items], list(suites.IMPORT_ITEMS)
      )
    self.assertEqual([item.suite for item in items], ['import'] * 4)
    self.assertEqual(
        items[0].command()[0], [self.settings.python, '-c', 'pass']
      )
    self.assertEqual(
        items[1].command()[0], [self.settings.python, '-c', 'import curry']
      )
    self.assertIn('Prelude', items[2].command()[0][2])
    self.assertEqual(
        items[3].command()[0][1:], ['-t', '--stats', '-m', 'Hello']
      )

  def test_refused(self):
    with self.assertRaisesRegex(ValueError, 'throughput suite only'):
      self.build('compile', ['Hello'], ['pakcs'])
    settings = suites.Settings('/nonexistent/home')
    with self.assertRaisesRegex(ValueError, 'needs a PAKCS executable'):
      self.build('throughput', ['Hello'], ['pakcs'], settings)
    self.assertRaisesRegex(
        ValueError, 'no backend', self.build, 'throughput', ['Hello'], ['c']
      )
    self.assertRaisesRegex(
        ValueError, 'no suite', self.build, 'speed', ['Hello'], ['cxx']
      )

  def test_parse(self):
    '''The items read their numbers from hand-made output.'''
    item = suites.SpriteExecItem('Fib', 'cxx', self.settings)
    fields = item.parse(
        FakeRun(stdout='0.250', stderr='noise\n' + STATS_LINE + '\n')
      )
    self.assertEqual(fields['eval_wall'], 0.25)
    self.assertEqual(fields['steps'], 7)
    self.assertEqual(fields['forks'], 2)
    self.assertEqual(fields['collections'], 3)
    self.assertEqual(fields['compile'], 0.5)
    self.assertEqual(fields['extra']['stats']['peak_rss'], 36528128)
    self.assertEqual(item.parse(FakeRun()), {'eval_wall': None})
    item = suites.PakcsItem('Fib', 'pakcs', self.settings)
    output = '42\nExecution time: 12 msec. / elapsed: 15 msec.\n'
    self.assertEqual(
        item.parse(FakeRun(stdout=output))
      , {'eval_cpu': 0.012, 'eval_wall': 0.015}
      )
    self.assertEqual(item.parse(FakeRun()), {})
    item = suites.ModuleCompileItem(
        'Fib', 'cxx', self.settings, 'cold', self.workdir
      )
    self.assertEqual(item.parse(FakeRun(stderr=STATS_LINE))['compile'], 0.5)
    self.assertEqual(item.parse(FakeRun()), {})
    item = suites.ExpressionItem(
        'expression', 'py', self.settings, 'warm', self.workdir
      )
    probe = {
        'import': 0.05, 'prelude': 0.03, 'compile': 0.9, 'first_value': 0.001
      , 'value': '3', 'stats': {'steps': 2, 'forks': 0, 'collections': 0}
      }
    fields = item.parse(FakeRun(stdout=json.dumps(probe) + '\n'))
    self.assertEqual(fields['compile'], 0.9)
    self.assertEqual(fields['eval_wall'], 0.001)
    self.assertEqual(fields['steps'], 2)
    self.assertEqual(fields['extra'], {'probe': probe})
    self.assertEqual(item.parse(FakeRun(stdout='no json\n')), {})

  def test_perf_repetition(self):
    '''measure(perf=True) runs under the perf of the settings, if any.'''
    calls = []
    def fake(cmd, env=None, cwd=None, timeout=600, cap=None, perf=None):
      calls.append((cmd[0], timeout, cap, perf))
      return FakeRun(perf=perf is not None, instructions=5 if perf else None)
    original = suites.measure.run_command
    suites.measure.run_command = fake
    try:
      settings = suites.Settings(
          '/nonexistent/home', timeout=7, cap=123, perf='/nonexistent/perf'
        )
      item = suites.CommandItem('python', 'py', settings)
      plain, under_perf = item.measure(), item.measure(perf=True)
      without = suites.Settings('/nonexistent/home')
      suites.CommandItem('python', 'py', without).measure(perf=True)
    finally:
      suites.measure.run_command = original
    self.assertEqual(calls, [
        (settings.python, 7, 123, None)
      , (settings.python, 7, 123, '/nonexistent/perf')
      , (settings.python, 600, None, None)
      ])
    self.assertFalse(plain['perf'])
    self.assertIsNone(plain['instructions'])
    self.assertTrue(under_perf['perf'])
    self.assertEqual(under_perf['instructions'], 5)
    self.assertEqual(
        settings.instructions_source, 'perf stat -e instructions:u'
      )
    self.assertEqual(without.instructions_source, 'not measured')
    told = suites.Settings('/nonexistent/home', instructions_source='why')
    self.assertEqual(told.instructions_source, 'why')

  def test_metadata(self):
    '''The machine context names no host and no path.'''
    meta = suites.Settings('/nonexistent/home').metadata()
    self.assertEqual(
        records.machine({'meta': meta})
      , { 'cpu_model': meta['cpu_model'], 'cores': meta['cores']
        , 'mem_gb': meta['mem_gb']
        }
      )
    self.assertEqual(meta['cpu_model'], records.cpu_model())
    self.assertEqual(meta['cores'], os.cpu_count())
    self.assertEqual(meta['mem_gb'], records.memory_gb())
    self.assertEqual(meta['instructions_source'], 'not measured')
    self.assertEqual(meta['rss_source'], measure.rss_source())
    self.assertNotIn('cpu', meta)
    self.assertNotIn('cpus', meta)
    self.assertIsNone(meta['python'])
    text = json.dumps(meta)
    self.assertNotIn(os.path.expanduser('~'), text)
    hostname = socket.gethostname()
    if len(hostname) > 3:
      self.assertNotIn(hostname, text)
    meta = suites.Settings(
        '/nonexistent/home', perf='/nonexistent/perf'
      , instructions_source='perf stat -e instructions:u (perf version 1)'
      ).metadata()
    self.assertEqual(
        meta['instructions_source']
      , 'perf stat -e instructions:u (perf version 1)'
      )


class TestRunOptions(unittest.TestCase):
  '''The command line of the run command.'''

  def test_parse_cap(self):
    self.assertEqual(run.parse_cap('6G'), 6 * 1024 ** 3)
    self.assertEqual(run.parse_cap('512m'), 512 * 1024 ** 2)
    self.assertEqual(run.parse_cap('1k'), 1024)
    self.assertEqual(run.parse_cap('2147483648'), 2147483648)
    self.assertEqual(run.parse_cap('0'), 0)
    for bad in 'x', '-1', '1x', '':
      self.assertRaises(run.argparse.ArgumentTypeError, run.parse_cap, bad)

  def test_parse_args(self):
    args = run.parse_args([])
    self.assertEqual(args.suite, 'throughput')
    self.assertEqual(args.backend, ['cxx'])
    self.assertEqual(args.repeat, 5)
    self.assertEqual(args.warmup, 1)
    self.assertEqual(args.cap, 6 * 1024 ** 3)
    self.assertEqual(args.timeout, 600)
    self.assertEqual(args.env, [])
    self.assertFalse(args.no_perf)
    self.assertTrue(run.parse_args(['--no-perf']).no_perf)
    args = run.parse_args([
        '-s', 'memory', '-b', 'py', '-b', 'cxx', '-e', 'A=1', '-e', 'B=x=y'
      , 'Fib'
      ])
    self.assertEqual(args.repeat, 1)
    self.assertEqual(args.backend, ['py', 'cxx'])
    self.assertEqual(run.parse_args(['-s', 'split']).repeat, 3)
    self.assertEqual(args.env, [('A', '1'), ('B', 'x=y')])
    self.assertEqual(args.program, ['Fib'])
    self.assertFalse(args.nightly)
    self.assertTrue(run.parse_args(['--nightly']).nightly)
    bad_options = [
        ['-r', '0'], ['-w', '-1'], ['--timeout', '0'], ['-e', 'novalue']
      , ['-b', 'c']
      ]
    for bad in bad_options:
      with contextlib.redirect_stderr(io.StringIO()):
        self.assertRaises(SystemExit, run.parse_args, bad)

  def test_measure_item(self):
    '''
    The warm-up runs, the measured repetitions, and the repetition under
    perf, which follows the measured ones when they all succeeded.
    '''
    class Item:
      def __init__(self, statuses, warmups=1):
        self.calls = []
        self.statuses = list(statuses)
        self.warmups = warmups
      def warmup(self):
        return self.warmups
      def measure(self, perf=False):
        self.calls.append(perf)
        status = self.statuses.pop(0) if self.statuses else 'ok'
        return records.sample(FakeRun(
            status=status, perf=perf, instructions=42 if perf else None
          ))
    item = Item([])
    samples = run.measure_item(item, 2, '/nonexistent/perf')
    self.assertEqual(item.calls, [False, False, False, True])
    self.assertEqual([s['perf'] for s in samples], [False, False, True])
    self.assertEqual(samples[-1]['instructions'], 42)
    item = Item([])
    self.assertEqual(len(run.measure_item(item, 2, None)), 2)
    self.assertEqual(item.calls, [False] * 3)
    # A failed measured repetition: no repetition under perf.
    item = Item(['ok', 'ok', 'fail'])
    self.assertEqual(len(run.measure_item(item, 2, '/p')), 2)
    self.assertEqual(item.calls, [False] * 3)
    item = Item([], warmups=0)
    run.measure_item(item, 1, '/p')
    self.assertEqual(item.calls, [False, True])

  def test_list_and_errors(self):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(run.main(['--list', '-s', 'import']), 0)
    self.assertEqual(out.getvalue().split(), list(suites.IMPORT_ITEMS))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(run.main(['-l', 'Tak?']), 0)
    self.assertEqual(out.getvalue().split(), ['Tak0', 'Tak1', 'Tak2'])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(run.main(['--list', '--nightly', '-s', 'compile']), 0)
    self.assertEqual(out.getvalue().split(), list(NIGHTLY) + ['expression'])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(run.main(['-l', '--nightly', 'Tak?']), 0)
    self.assertEqual(out.getvalue().split(), ['Tak1'])
    with self.assertRaisesRegex(
        SystemExit, "no program of the throughput suite matches 'Nope'"
      ):
      run.main(['Nope'])
    with self.assertRaisesRegex(
        SystemExit, "no program of the throughput suite matches 'Tak0'"
      ):
      run.main(['--nightly', 'Tak0'])
    with self.assertRaisesRegex(SystemExit, 'throughput suite only'):
      run.main(['-s', 'compile', '-b', 'pakcs', 'Hello'])
    with self.assertRaisesRegex(
        SystemExit, 'no item of the import suite has a variant'
      ):
      run.main(['-s', 'import', '--variant', 'warm'])
    with self.assertRaisesRegex(SystemExit, 'sprite-exec not found'):
      run.main(['--sprite-home', '/nonexistent/home', 'Hello'])


class TestCompare(unittest.TestCase):
  '''The compare command on hand-made records.'''

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-benchmarks-test-')
    self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
    # A to G and Z exercise the verdicts; H and I move the collections
    # within and beyond the tolerance of one percent; J has no instructions
    # on the old side.
    self.old = [
        make_record('A', 1.0, instructions=1000 * M)
      , make_record('B', 1.0, instructions=1000 * M)
      , make_record('C', 1.0, instructions=1000 * M)
      , make_record('D', 1.0, steps=5, instructions=1000 * M)
      , make_record('E', 1.0), make_record('F', 1.0, status='fail')
      , make_record('Z', 0.0)
      , make_record('H', 1.0, collections=100, instructions=1000 * M)
      , make_record('I', 1.0, collections=100, instructions=1000 * M)
      , make_record('J', 1.0)
      ]
    self.new = [
        make_record('A', 1.05, instructions=1005 * M)
      , make_record('B', 1.5, instructions=1020 * M)
      , make_record('C', 0.5, instructions=980 * M)
      , make_record('D', 1.0, steps=6, instructions=1000 * M)
      , make_record('F', 1.0), make_record('G', 1.0), make_record('Z', 0.0)
      , make_record('H', 1.0, collections=101, instructions=1000 * M)
      , make_record('I', 1.0, collections=120, instructions=1000 * M)
      , make_record('J', 1.0, instructions=1000 * M)
      ]

  def write(self, name, recs):
    filename = os.path.join(self.tmpdir, name)
    with open(filename, 'w') as stream:
      for record in recs:
        if 'instructions' in record:
          records.write(stream, record)
        else:
          stream.write(json.dumps(record) + '\n')
    return filename

  @staticmethod
  def key(program):
    return ('throughput', program, 'cxx', None)

  def rows(
      self, metric='cpu', threshold=0.10, counters=compare.COUNTERS
    , tolerance=0.0
    ):
    '''A function from a program to its row of the comparison.'''
    old = compare.latest(self.old)
    new = compare.latest(self.new)
    def row(program):
      k = self.key(program)
      return compare.compare(
          old.get(k), new.get(k), metric, threshold, counters, tolerance
        )
    return row

  @staticmethod
  def run_main(argv):
    '''The status of compare.main and its output as lines.'''
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      status = compare.main(argv)
    return status, out.getvalue().splitlines()

  @staticmethod
  def table(lines):
    '''The rows of a table, by program, as lists of words.'''
    rows = [line.split() for line in lines if line.split()[0] in SUITES]
    return {row[1]: row for row in rows}

  @staticmethod
  def summary(lines):
    return next(line for line in lines if ' items: ' in line)

  def test_verdicts(self):
    row = self.rows()
    self.assertEqual(row('A')['verdict'], 'same')
    self.assertAlmostEqual(row('A')['ratio'], 1.05)
    self.assertAlmostEqual(row('A')['ratios']['instructions'], 1.005)
    self.assertAlmostEqual(row('A')['ratios']['cpu'], 1.05)
    self.assertAlmostEqual(row('A')['ratios']['wall'], 1.05)
    self.assertEqual(row('B')['verdict'], 'slower')
    self.assertEqual(self.rows(threshold=0.6)('B')['verdict'], 'same')
    self.assertEqual(self.rows(threshold=0.0)('B')['verdict'], 'slower')
    self.assertEqual(row('C')['verdict'], 'faster')
    self.assertEqual(row('D')['verdict'], 'same')
    self.assertEqual(row('D')['counters'], ['steps 5->6 (+20.0%)'])
    self.assertEqual(row('E')['verdict'], 'only-old')
    self.assertEqual(row('E')['ratios'], {})
    self.assertEqual(row('F')['verdict'], 'fail')
    self.assertEqual(row('G')['verdict'], 'only-new')
    self.assertEqual(row('Z')['verdict'], 'same')
    self.assertEqual(row('Z')['ratio'], 1.0)
    # The collections are not among the exact counters of the default mode.
    self.assertEqual(row('I')['counters'], [])
    self.assertEqual(row('I')['within'], [])
    self.assertEqual(row('J')['verdict'], 'same')
    self.assertIsNone(row('J')['ratios']['instructions'])
    self.assertEqual(
        self.rows(metric='eval_wall')('A')['verdict'], 'no-metric'
      )
    zero = compare.compare(
        make_record('Z', 0.0), make_record('Z', 0.5), 'cpu', 0.1
      )
    self.assertEqual(zero['verdict'], 'slower')
    self.assertEqual(zero['ratio'], float('inf'))
    self.assertIsNone(compare.ratio(None, 1))
    self.assertIsNone(compare.ratio(1, None))
    self.assertEqual(compare.ratio(0, 0), 1.0)
    self.assertEqual(compare.ratio(2, 1), 0.5)
    self.assertEqual(compare.change('steps', 0, 3), 'steps 0->3')
    self.assertEqual(compare.change('steps', 4, 3), 'steps 4->3 (-25.0%)')
    # The last record of an item counts.
    latest = compare.latest([make_record('A', 1.0), make_record('A', 2.0)])
    self.assertEqual(latest[self.key('A')]['cpu'], 2.0)
    # The summary counts the verdicts and the changed counters.
    rows = [row(p) for p in 'ABCDEFGZ']
    counts, line = compare.summary(rows, 'cpu', 0.1)
    self.assertEqual(counts['same'], 3)
    self.assertEqual(counts['slower'], 1)
    self.assertEqual(counts['changed'], 1)
    self.assertTrue(line.startswith('8 items: 3 same, 1 faster, 1 slower'))
    self.assertTrue(line.endswith('(metric cpu, threshold 10%)'))

  def test_deterministic_verdicts(self):
    '''The instructions decide; the counters get the same tolerance.'''
    row = self.rows(
        'instructions', 0.01, compare.DETERMINISTIC_COUNTERS, 0.01
      )
    self.assertEqual(row('A')['verdict'], 'same')
    self.assertAlmostEqual(row('A')['ratio'], 1.005)
    self.assertEqual(
        (row('A')['old'], row('A')['new']), (1000 * M, 1005 * M)
      )
    self.assertEqual(row('B')['verdict'], 'slower')
    self.assertEqual(row('C')['verdict'], 'faster')
    self.assertEqual(row('D')['verdict'], 'same')
    self.assertEqual(row('D')['counters'], ['steps 5->6 (+20.0%)'])
    self.assertEqual(row('H')['verdict'], 'same')
    self.assertEqual(row('H')['counters'], [])
    self.assertEqual(row('H')['within'], ['collections'])
    self.assertEqual(row('I')['counters'], ['collections 100->120 (+20.0%)'])
    self.assertEqual(row('J')['verdict'], 'no-metric')
    self.assertAlmostEqual(row('J')['ratios']['cpu'], 1.0)
    self.assertEqual(row('F')['verdict'], 'fail')
    self.assertEqual(row('Z')['verdict'], 'no-metric')
    wide = self.rows(
        'instructions', 0.05, compare.DETERMINISTIC_COUNTERS, 0.05
      )
    self.assertEqual(wide('B')['verdict'], 'same')
    self.assertEqual(wide('I')['counters'], ['collections 100->120 (+20.0%)'])

  def test_main(self):
    old = self.write('old.jsonl', self.old)
    new = self.write('new.jsonl', self.new)
    status, lines = self.run_main([old, new])
    self.assertEqual(status, 0)
    self.assertEqual(lines[0], 'old: commit abc, unknown processor')
    self.assertEqual(lines[1], 'new: commit abc, unknown processor')
    self.assertEqual(
        lines[2].split()
      , [ 'suite', 'program', 'backend', 'variant', 'old', 'new', 'ratio'
        , 'instr', 'verdict', 'counters'
        ]
      )
    table = self.table(lines)
    self.assertEqual(len(table), 11)
    self.assertEqual(table['A'][4:7], ['1.0000', '1.0500', '1.05'])
    self.assertIn(table['A'][7], ('1.00', '1.01'))
    self.assertEqual(table['A'][8:], ['same', 'equal'])
    self.assertEqual(table['B'][7:], ['1.02', 'slower', 'equal'])
    self.assertEqual(table['C'][7:], ['0.98', 'faster', 'equal'])
    self.assertEqual(
        table['D'][8:], ['same', 'steps', '5->6', '(+20.0%)']
      )
    self.assertEqual(table['E'][4:], ['-', '-', '-', '-', 'only-old', '-'])
    self.assertEqual(table['F'][8:], ['fail', '-'])
    self.assertEqual(table['G'][8:], ['only-new', '-'])
    self.assertEqual(table['Z'][6:], ['1.00', '-', 'same', 'equal'])
    self.assertEqual(table['H'][8:], ['same', 'equal'])
    self.assertEqual(table['I'][8:], ['same', 'equal'])
    self.assertEqual(table['J'][7:], ['-', 'same', 'equal'])
    self.assertEqual(
        self.summary(lines)
      , '11 items: 6 same, 1 faster, 1 slower, 1 failed, 0 without the '
        'metric, 2 only in one file; 1 with changed counters '
        '(metric cpu, threshold 10%)'
      )
    self.assertEqual(
        lines[-1]
      , 'instructions: missing in OLD for 3 items and in NEW for 3 items '
        '(records written without perf, or by an older harness)'
      )
    good = self.write(
        'good.jsonl', [make_record('A', 1.0, instructions=10 * M)]
      )
    with contextlib.redirect_stdout(io.StringIO()):
      self.assertEqual(compare.main(['--strict', old, new]), 1)
      self.assertEqual(compare.main(['--strict', old, old]), 1) # F failed
      # D and F
      self.assertEqual(compare.main(['--strict', '-t', '0.6', old, new]), 1)
      self.assertEqual(compare.main(['--strict', good, good]), 0)
      self.assertEqual(compare.main(['-m', 'peak_rss', old, new]), 0)
    status, lines = self.run_main(['--strict', good, good])
    self.assertEqual(status, 0)
    self.assertNotIn('instructions: missing', lines[-1])
    status, lines = self.run_main(['-m', 'eval_wall', good, good])
    self.assertEqual(status, 0)
    self.assertIn('no-metric', self.table(lines)['A'])
    # The instructions as the metric of the default mode.
    status, lines = self.run_main(
        ['-m', 'instructions', '-t', '0.3', old, new]
      )
    self.assertEqual(status, 0)
    table = self.table(lines)
    self.assertEqual(table['A'][4:6], ['1000.0M', '1005.0M'])
    self.assertEqual(table['B'][8], 'same')
    self.assertEqual(table['J'][8], 'no-metric')
    self.assertIn('(metric instructions, threshold 30%)', self.summary(lines))
    with self.assertRaisesRegex(SystemExit, 'compare: '):
      compare.main([old, os.path.join(self.tmpdir, 'missing.jsonl')])
    bad = os.path.join(self.tmpdir, 'bad.jsonl')
    with open(bad, 'w') as stream:
      stream.write('{}\n')
    with self.assertRaisesRegex(SystemExit, 'line 1'):
      compare.main([old, bad])

  def test_deterministic_main(self):
    '''The table of --deterministic: instructions, advisory seconds.'''
    old = self.write('old.jsonl', self.old)
    new = self.write('new.jsonl', self.new)
    status, lines = self.run_main(['--deterministic', old, new])
    self.assertEqual(status, 0)
    self.assertEqual(
        lines[2]
      , 'deterministic: the instructions decide (tolerance 1%); counters '
        'lists steps, forks, and collections beyond it; ~cpu and ~wall are '
        'advisory'
      )
    self.assertEqual(
        lines[3].split()
      , [ 'suite', 'program', 'backend', 'variant', 'old', 'new', 'ratio'
        , '~cpu', '~wall', 'verdict', 'counters'
        ]
      )
    table = self.table(lines)
    self.assertEqual(table['A'][4:6], ['1000.0M', '1005.0M'])
    self.assertEqual(table['A'][7:], ['1.05', '1.05', 'same', 'equal'])
    self.assertEqual(
        table['B'][6:], ['1.02', '1.50', '1.50', 'slower', 'equal']
      )
    self.assertEqual(table['C'][9:], ['faster', 'equal'])
    self.assertEqual(
        table['D'][9:], ['same', 'steps', '5->6', '(+20.0%)']
      )
    self.assertEqual(table['H'][9:], ['same', 'within'])
    self.assertEqual(
        table['I'][9:], ['same', 'collections', '100->120', '(+20.0%)']
      )
    # J has the count on the new side only.
    self.assertEqual(
        table['J'][4:]
      , ['-', '1000.0M', '-', '1.00', '1.00', 'no-metric', 'equal']
      )
    self.assertEqual(table['E'][9:], ['only-old', '-'])
    self.assertEqual(table['F'][9:], ['fail', '-'])
    self.assertEqual(
        self.summary(lines)
      , '11 items: 4 same, 1 faster, 1 slower, 1 failed, 2 without the '
        'metric, 2 only in one file; 2 with changed counters '
        '(deterministic: metric instructions, tolerance 1%; wall and CPU '
        'seconds advisory)'
      )
    self.assertTrue(
        lines[-1].startswith('instructions: missing in OLD for 3')
      )
    with contextlib.redirect_stdout(io.StringIO()):
      self.assertEqual(
          compare.main(['--deterministic', '--strict', old, new]), 1
        )
      # B is within five percent; D and I are not.
      self.assertEqual(
          compare.main(
              ['--deterministic', '-t', '0.05', '--strict', old, new]
            )
        , 1
        )
    status, lines = self.run_main(
        ['--deterministic', '-t', '0.05', old, new]
      )
    self.assertEqual(self.table(lines)['B'][9], 'same')
    self.assertIn('tolerance 5%', lines[2])
    # Five times the CPU seconds pass: the seconds are advisory.
    before = self.write(
        'before.jsonl', [make_record('A', 1.0, instructions=1000 * M)]
      )
    after = self.write(
        'after.jsonl', [make_record('A', 5.0, instructions=1005 * M)]
      )
    status, lines = self.run_main(
        ['--deterministic', '--strict', before, after]
      )
    self.assertEqual(status, 0)
    self.assertEqual(
        self.table(lines)['A'][7:], ['5.00', '5.00', 'same', 'equal']
      )
    with contextlib.redirect_stdout(io.StringIO()):
      self.assertEqual(compare.main(['--strict', before, after]), 1)
    # -m conflicts with --deterministic, except for the instructions.
    with contextlib.redirect_stderr(io.StringIO()):
      self.assertRaises(
          SystemExit, compare.parse_args
        , ['-m', 'cpu', '--deterministic', 'a', 'b']
        )
    args = compare.parse_args(
        ['--deterministic', '-m', 'instructions', 'a', 'b']
      )
    self.assertEqual((args.metric, args.threshold), ('instructions', 0.01))
    args = compare.parse_args(['a', 'b'])
    self.assertEqual((args.metric, args.threshold), ('cpu', 0.10))

  def test_machines(self):
    '''The machine of each file, and the warning when they differ.'''
    alpha = {'cpu_model': 'Alpha', 'cores': 4, 'mem_gb': 7.5}
    beta = {'cpu_model': 'Beta', 'cores': 8, 'mem_gb': 15.0}
    one = self.write('one.jsonl', [
        make_record('A', 1.0, meta=alpha, label='A')
      , make_record('B', 1.0, meta=alpha, label='A')
      ])
    two = self.write(
        'two.jsonl', [make_record('A', 1.0, meta=beta, label='B')]
      )
    status, lines = self.run_main([one, two])
    self.assertEqual(
        lines[0], "old: label 'A', commit abc, Alpha, 4 cores, 7.5 GiB"
      )
    self.assertEqual(
        lines[1], "new: label 'B', commit abc, Beta, 8 cores, 15.0 GiB"
      )
    self.assertEqual(
        lines[2]
      , 'warning: the machines differ; wall and CPU seconds do not compare '
        'across machines; use --deterministic'
      )
    self.assertTrue(lines[3].startswith('suite '))
    status, lines = self.run_main(['--deterministic', one, two])
    self.assertEqual(
        lines[2]
      , 'note: the machines differ; the deterministic columns compare, the '
        'advisory columns ~cpu and ~wall do not'
      )
    status, lines = self.run_main([one, one])
    self.assertTrue(lines[2].startswith('suite '))
    # Schema 1 named the machine cpu and cpus and did not know the memory;
    # such a record agrees with a record of the same processor and cores.
    legacy = schema_1(
        make_record('A', 1.0), meta={'cpu': 'Alpha', 'cpus': 4}
      )
    three = self.write('three.jsonl', [legacy])
    status, lines = self.run_main([three, one])
    self.assertEqual(status, 0)
    self.assertEqual(lines[0], 'old: commit abc, Alpha, 4 cores')
    self.assertTrue(lines[2].startswith('suite '))
    self.assertTrue(compare.machines_differ([legacy], records.read(two)))
    self.assertFalse(compare.machines_differ([legacy], records.read(one)))
    # Several machines and labels in one file.
    both = self.write('both.jsonl', records.read(one) + records.read(two))
    self.assertEqual(
        compare.describe(records.read(both))
      , "label 'A' or 'B', commit abc, Alpha, 4 cores, 7.5 GiB or Beta, 8 "
        "cores, 15.0 GiB"
      )
    self.assertEqual(compare.describe([]), 'no records')
    self.assertEqual(
        compare.machine_text(
            {'cpu_model': None, 'cores': None, 'mem_gb': None}
          )
      , 'unknown processor'
      )

  def test_schema_1_file(self):
    '''A file of schema 1 compares with a file of schema 2.'''
    old = self.write('old.jsonl', [schema_1(make_record('A', 1.0))])
    new = self.write(
        'new.jsonl', [make_record('A', 1.0, instructions=1000 * M)]
      )
    status, lines = self.run_main([old, new])
    self.assertEqual(status, 0)
    self.assertEqual(
        self.table(lines)['A'][6:], ['1.00', '-', 'same', 'equal']
      )
    self.assertEqual(
        lines[-1]
      , 'instructions: missing in OLD for 1 items and in NEW for 0 items '
        '(records written without perf, or by an older harness)'
      )
    # A strict gate that could not measure has not passed.
    status, lines = self.run_main(['--deterministic', old, new])
    self.assertEqual(status, 0)
    self.assertEqual(self.table(lines)['A'][9], 'no-metric')
    status, lines = self.run_main(['--deterministic', '--strict', old, new])
    self.assertEqual(status, 1)
    self.assertEqual(self.table(lines)['A'][9], 'no-metric')
    status, lines = self.run_main([old, old])
    self.assertEqual(status, 0)
    self.assertTrue(lines[-1].startswith(
        'instructions: missing in OLD for 1 items and in NEW for 1'
      ))
    # The committed baseline against itself: the CPU seconds compare, the
    # instructions are missing, so the deterministic gate fails.
    baseline = BASELINES % 'import'
    status, lines = self.run_main(['--strict', baseline, baseline])
    self.assertEqual(status, 0)
    self.assertEqual(len(self.table(lines)), 4)
    self.assertIn("label 'baseline-2026-10-03'", lines[0])
    self.assertTrue(lines[-1].startswith('instructions: missing in OLD for 8'))
    status, lines = self.run_main(
        ['--deterministic', '--strict', baseline, baseline]
      )
    self.assertEqual(status, 1)
    self.assertIn('8 without the metric', self.summary(lines))


class TestCounters(unittest.TestCase):
  '''The counters command on hand-made records.'''

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-benchmarks-test-')
    self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

  @staticmethod
  def record(program, line, status='ok', backend='cxx', variant=None):
    '''A record of one sample whose stderr holds the stats line.'''
    run = FakeRun(status=status, stdout='0.25', stderr=line + '\n')
    item = suites.SpriteExecItem(program, backend, None)
    sample = records.sample(run, item.parse(run))
    suite = 'throughput' if variant is None else 'split'
    return records.summarize(
        suite, program, backend, variant, [sample], {}, commit='abc'
      )

  def test_row(self):
    '''The fractions and the lifetimes of one record.'''
    row = counters.row(self.record('A', COUNTERS_LINE))
    self.assertEqual(tuple(row), counters.HEADINGS)
    self.assertEqual(row['program'], 'A')
    self.assertEqual(row['steps'], 7)
    self.assertEqual(row['forks'], 2)
    self.assertAlmostEqual(row['serial'], 5 / 7)
    self.assertEqual(row['nested'], 0.0)
    self.assertAlmostEqual(row['shared'], 4 / 7)
    self.assertAlmostEqual(row['failed'], 2 / 7)
    self.assertEqual(row['qmax'], 4)
    self.assertEqual(row['configs'], 6)
    self.assertEqual(row['median'], 1)
    self.assertEqual(row['mean'], 1.166667)
    self.assertEqual(row['max'], 3)
    self.assertEqual(row['nconfigs'], 0)
    self.assertEqual(row['nmedian'], 0)
    # A plain runtime reports no counters; a failed sample does not count;
    # a run without steps has no fractions.
    for record in (
        self.record('B', STATS_LINE), self.record('C', COUNTERS_LINE, 'fail')
      ):
      row = counters.row(record)
      self.assertEqual(row['program'], record['program'])
      self.assertTrue(all(row[h] is None for h in counters.HEADINGS[1:]))
    idle = self.record('D', COUNTERS_LINE.replace('steps=7', 'steps=0'))
    row = counters.row(idle)
    self.assertEqual(row['steps'], 0)
    self.assertIsNone(row['serial'])
    self.assertEqual(row['configs'], 6)
    # An item with a variant is named program:variant.
    row = counters.row(self.record('E', COUNTERS_LINE, variant='4/1'))
    self.assertEqual(row['program'], 'E:4/1')
    self.assertEqual(row['steps'], 7)

  def test_main(self):
    '''The table, the CSV form, the backend filter, and the errors.'''
    filename = os.path.join(self.tmpdir, 'counters.jsonl')
    with open(filename, 'w') as stream:
      records.write(stream, self.record('A', COUNTERS_LINE))
      records.write(stream, self.record('B', STATS_LINE))
      records.write(stream, self.record('C', COUNTERS_LINE, backend='py'))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(counters.main([filename]), 0)
    lines = out.getvalue().splitlines()
    self.assertEqual(tuple(lines[0].split()), counters.HEADINGS)
    self.assertEqual(
        lines[1].split()
      , [ 'A', '7', '2', '0.714', '0.000', '0.571', '0.286', '4', '6', '1'
        , '1.2', '3', '0', '0'
        ]
      )
    self.assertEqual(lines[2].split(), ['B'] + ['-'] * 13)
    self.assertEqual(lines[3].split()[:2], ['C', '7'])
    self.assertEqual(len(lines), 4)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(counters.main(['--csv', '-b', 'py', filename]), 0)
    lines = out.getvalue().splitlines()
    self.assertEqual(lines[0], ','.join(counters.HEADINGS))
    self.assertEqual(lines[1].split(',')[:4], ['C', '7', '2', '0.714'])
    self.assertEqual(len(lines), 2)
    # No record with the counters: status 1.
    with contextlib.redirect_stdout(io.StringIO()):
      self.assertEqual(counters.main(['-b', 'pakcs', filename]), 1)
    with self.assertRaisesRegex(SystemExit, 'counters: '):
      counters.main([os.path.join(self.tmpdir, 'missing.jsonl')])


class TestSplit(unittest.TestCase):
  '''The split command on hand-made records.'''

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-benchmarks-test-')
    self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

  @staticmethod
  def record(program, variant, cpu, steps, forks, status='ok', backend='cxx'):
    return make_record(
        program, cpu, steps=steps, forks=forks, status=status, suite='split'
      , backend=backend, variant=variant
      )

  def records(self):
    '''
    A: a complete split into two (bound 10/6, duplicated work 11/10), four
    parts with one missing, and eight parts with one failed.  B on the
    Python backend: a complete split into two.  A throughput record of A
    is ignored.
    '''
    recs = [
        self.record('A', 'whole', 10.0, 1000, 100)
      , self.record('A', '2/0', 6.0, 700, 60)
      , self.record('A', '2/1', 5.0, 500, 50)
      , self.record('A', '4/0', 3.0, 300, 30)
      , self.record('A', '4/1', 3.0, 300, 30)
      , self.record('A', '4/2', 3.0, 300, 30)
      ]
    recs += [self.record('A', '8/%d' % i, 2.0, 200, 20) for i in range(7)]
    recs.append(self.record('A', '8/7', 2.0, 200, 20, status='fail'))
    recs += [
        self.record('B', 'whole', 4.0, 400, 40, backend='py')
      , self.record('B', '2/0', 4.0, 400, 40, backend='py')
      , self.record('B', '2/1', 1.0, 100, 10, backend='py')
      , make_record('A', 1.0)
      ]
    return recs

  def test_part_of(self):
    self.assertIsNone(split.part_of('whole'))
    self.assertIsNone(split.part_of(None))
    self.assertEqual(split.part_of('2/0'), (2, 0))
    self.assertEqual(split.part_of('8/7'), (8, 7))

  def test_rows(self):
    '''The bound and the duplicated work of each split.'''
    table = split.rows(self.records())
    self.assertEqual(
        [(r['program'], r['backend'], r['parts'], r['ok']) for r in table]
      , [ ('A', 'cxx', 2, '2/2'), ('A', 'cxx', 4, '3/4')
        , ('A', 'cxx', 8, '7/8'), ('B', 'py', 2, '2/2')
        ]
      )
    two = table[0]
    self.assertEqual(tuple(two)[:len(split.HEADINGS)], split.HEADINGS)
    self.assertEqual(two['whole'], 10.0)
    self.assertEqual(two['longest'], 6.0)
    self.assertEqual(two['part'], '2/0')
    self.assertAlmostEqual(two['bound'], 10 / 6)
    self.assertAlmostEqual(two['dup'], 1.1)
    self.assertEqual(two['whole_steps'], 1000)
    self.assertAlmostEqual(two['bound_steps'], 1000 / 700)
    self.assertAlmostEqual(two['dup_steps'], 1.2)
    self.assertAlmostEqual(two['dup_forks'], 1.1)
    self.assertEqual([v for v, _ in two['records']], ['2/0', '2/1'])
    # A part missing or failed: the counts and dashes.
    for row in table[1:3]:
      self.assertTrue(all(row[h] is None for h in split.HEADINGS[4:]), row)
    self.assertEqual([v for v, r in table[1]['records'] if r is None], ['4/3'])
    self.assertEqual(table[2]['records'][7][1]['status'], 'fail')
    b = table[3]
    self.assertEqual(b['part'], '2/0')
    self.assertEqual(b['bound'], 1.0)
    self.assertAlmostEqual(b['dup'], 1.25)
    # Another metric: the wall of make_record is twice the CPU, so the
    # ratios are the same.  Without the metric the step columns stay.
    table = split.rows(self.records(), 'wall')
    self.assertEqual(table[0]['whole'], 20.0)
    self.assertAlmostEqual(table[0]['bound'], 10 / 6)
    table = split.rows(self.records(), 'eval_wall')
    self.assertIsNone(table[0]['bound'])
    self.assertIsNone(table[0]['dup'])
    self.assertAlmostEqual(table[0]['bound_steps'], 1000 / 700)
    # A whole that failed, or is missing: no aggregate.
    recs = [
        self.record('C', 'whole', 1.0, 10, 1, status='timeout')
      , self.record('C', '2/0', 1.0, 5, 1), self.record('C', '2/1', 1.0, 5, 1)
      ]
    row, = split.rows(recs)
    self.assertEqual(row['ok'], '2/2')
    self.assertIsNone(row['bound'])
    self.assertIsNone(row['dup_steps'])
    row, = split.rows(recs[1:])
    self.assertIsNone(row['bound'])
    # The last record of an item counts.
    recs = [
        self.record('D', 'whole', 1.0, 10, 1)
      , self.record('D', '2/0', 1.0, 5, 1), self.record('D', '2/1', 1.0, 5, 1)
      , self.record('D', 'whole', 2.0, 20, 2)
      ]
    row, = split.rows(recs)
    self.assertEqual(row['whole'], 2.0)
    self.assertEqual(row['bound'], 2.0)
    self.assertEqual(row['dup_steps'], 0.5)
    self.assertEqual(split.rows([]), [])

  def test_main(self):
    '''The table, the parts, the backend filter, the CSV form, the errors.'''
    filename = os.path.join(self.tmpdir, 'split.jsonl')
    with open(filename, 'w') as stream:
      for record in self.records():
        records.write(stream, record)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(split.main([filename]), 0)
    lines = out.getvalue().splitlines()
    self.assertEqual(tuple(lines[0].split()), split.HEADINGS)
    self.assertEqual(
        lines[1].split()
      , [ 'A', 'cxx', '2', '2/2', '10.000', '6.000', '2/0', '1.67', '1.10'
        , '1000', '1.43', '1.20', '1.10'
        ]
      )
    self.assertEqual(lines[2].split(), ['A', 'cxx', '4', '3/4'] + ['-'] * 9)
    self.assertEqual(lines[3].split()[:4], ['A', 'cxx', '8', '7/8'])
    self.assertEqual(lines[4].split()[:4], ['B', 'py', '2', '2/2'])
    self.assertEqual(len(lines), 5)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(split.main(['--parts', '-b', 'cxx', filename]), 0)
    lines = out.getvalue().splitlines()
    self.assertEqual(lines[2].split(), ['2/0', '6.000', '700', '60', 'ok'])
    self.assertEqual(lines[3].split(), ['2/1', '5.000', '500', '50', 'ok'])
    self.assertEqual(lines[4].split()[:4], ['A', 'cxx', '4', '3/4'])
    self.assertEqual(lines[8].split(), ['4/3', '-', '-', '-', 'missing'])
    self.assertEqual(lines[-1].split(), ['8/7', '-', '-', '-', 'fail'])
    self.assertEqual(len(lines), 1 + 3 + 5 + 9)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(
          split.main(['--csv', '-m', 'wall', '-b', 'py', filename]), 0
        )
    lines = out.getvalue().splitlines()
    self.assertEqual(lines[0], ','.join(split.HEADINGS))
    self.assertEqual(
        lines[1], 'B,py,2,2/2,8.000,8.000,2/0,1.00,1.25,400,1.00,1.25,1.25'
      )
    self.assertEqual(len(lines), 2)
    # No complete split: status 1.
    with contextlib.redirect_stdout(io.StringIO()):
      self.assertEqual(split.main(['-b', 'pakcs', filename]), 1)
    with self.assertRaisesRegex(SystemExit, 'split: '):
      split.main([os.path.join(self.tmpdir, 'missing.jsonl')])
    with contextlib.redirect_stderr(io.StringIO()):
      self.assertRaises(SystemExit, split.parse_args, ['-m', 'rss', filename])


class TestHistory(unittest.TestCase):
  '''The history command on hand-made records.'''

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-benchmarks-test-')
    self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
    self.first = [make_record('A', 1.0), make_record('B', 1.0, suite='import')]
    self.second = [
        make_record('A', 1.5, steps=6), make_record('B', 1.0, suite='import')
      , make_record('C', 1.0)
      ]

  def write(self, name, recs):
    filename = os.path.join(self.tmpdir, name)
    with open(filename, 'w') as stream:
      for record in recs:
        records.write(stream, record)
    return filename

  def main(self, argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      status = history.main(argv)
    return status, out.getvalue().splitlines()

  @staticmethod
  def table(lines):
    '''The rows of the last block of a report, by program.'''
    return {line.split()[1]: line.split() for line in lines}

  def test_points(self):
    '''A point has the fields of the page and nothing else.'''
    record = make_record('Fib', 1.0)
    point = history.point(record)
    self.assertEqual(tuple(point), history.POINT_FIELDS)
    self.assertEqual(point['cpu'], 1.0)
    self.assertEqual(point['status'], 'ok')
    self.assertEqual(point['steps'], 5)
    self.assertNotIn('samples', point)
    self.assertNotIn('meta', point)
    # Sorted by suite (in the order of the suites), program, backend,
    # variant, and date.
    recs = [
        make_record('B', 1.0, suite='import')
      , make_record('A', 2.0, backend='py')
      , make_record('A', 1.0, suite='memory', variant='collector=on')
      , make_record('A', 1.0)
      ]
    pts = history.points(recs)
    self.assertEqual(
        [(p['suite'], p['program'], p['backend'], p['variant']) for p in pts]
      , [ ('throughput', 'A', 'cxx', None), ('throughput', 'A', 'py', None)
        , ('import', 'B', 'cxx', None), ('memory', 'A', 'cxx', 'collector=on')
        ]
      )

  def test_main(self):
    '''Two runs: the files of the history, and the second against the first.'''
    d = os.path.join(self.tmpdir, 'history')
    first = self.write('first.jsonl', self.first)
    second = self.write('second.jsonl', self.second)
    status, lines = self.main([d, first])
    self.assertEqual(status, 0)
    self.assertEqual(
        lines[0], 'first.jsonl: 2 records against the previous run'
      )
    self.assertEqual(
        lines[1].split()[:4], ['suite', 'program', 'backend', 'variant']
      )
    # The column instr is '-' for records without instructions.
    self.assertEqual(self.table(lines[2:4])['A'][7:], ['-', 'only-new', '-'])
    self.assertEqual(self.table(lines[2:4])['B'][7:], ['-', 'only-new', '-'])
    self.assertTrue(lines[-1].startswith(
        '2 items: 0 same, 0 faster, 0 slower, 0 failed, 0 without the metric, '
        '2 only in one file; 0 with changed counters'
      ))
    self.assertEqual(len(lines), 5)
    self.assertEqual(
        sorted(os.listdir(d)), ['README.md', 'points.json', 'records']
      )
    self.assertEqual(
        sorted(os.listdir(os.path.join(d, 'records')))
      , ['import.jsonl', 'throughput.jsonl']
      )
    self.assertEqual(
        records.read(history.record_file(d, 'throughput')), [self.first[0]]
      )
    self.assertEqual(
        records.read(history.record_file(d, 'import')), [self.first[1]]
      )
    readme = os.path.join(d, 'README.md')
    with open(readme) as stream:
      self.assertEqual(stream.read(), history.README)
    points = os.path.join(d, 'points.json')
    with open(points) as stream:
      data = json.load(stream)
    self.assertEqual(sorted(data), ['generated', 'points', 'schema'])
    self.assertEqual(data['schema'], history.POINTS_SCHEMA)
    self.assertRegex(data['generated'], r'^\d{4}-\d\d-\d\dT')
    self.assertEqual(data['points'], history.points(self.first))
    # The second run: A slower with changed steps, B the same, C new.
    status, lines = self.main([d, second])
    self.assertEqual(status, 0)
    self.assertEqual(
        lines[0], 'second.jsonl: 3 records against the previous run'
      )
    table = self.table(lines[2:5])
    self.assertEqual(
        table['A'][4:]
      , ['1.0000', '1.5000', '1.50', '-', 'slower', 'steps', '5->6', '(+20.0%)']
      )
    self.assertEqual(
        table['B'][4:], ['1.0000', '1.0000', '1.00', '-', 'same', 'equal']
      )
    self.assertEqual(table['C'][7:], ['-', 'only-new', '-'])
    self.assertTrue(lines[-1].startswith(
        '3 items: 1 same, 0 faster, 1 slower, 0 failed, 0 without the metric, '
        '1 only in one file; 1 with changed counters'
      ))
    self.assertEqual(
        records.read(history.record_file(d, 'throughput'))
      , [self.first[0], self.second[0], self.second[2]]
      )
    with open(points) as stream:
      data = json.load(stream)
    self.assertEqual(
        [(p['program'], p['cpu']) for p in data['points']]
      , [('A', 1.0), ('A', 1.5), ('C', 1.0), ('B', 1.0), ('B', 1.0)]
      )
    # Without a file the points are written again and the README is kept.
    os.unlink(points)
    with open(readme, 'w') as stream:
      stream.write('kept\n')
    status, lines = self.main([d])
    self.assertEqual((status, lines), (0, []))
    with open(points) as stream:
      self.assertEqual(len(json.load(stream)['points']), 5)
    with open(readme) as stream:
      self.assertEqual(stream.read(), 'kept\n')

  def test_options_and_errors(self):
    '''Two files in one call, the metric and the threshold, the errors.'''
    d = os.path.join(self.tmpdir, 'history')
    first = self.write('first.jsonl', self.first)
    second = self.write('second.jsonl', self.second)
    # The wall of make_record is twice the CPU; A's ratio of 1.5 is the same
    # at a threshold of 0.6.  The second file compares with the first.
    status, lines = self.main(['-m', 'wall', '-t', '0.6', d, first, second])
    self.assertEqual(status, 0)
    self.assertEqual(
        lines[0], 'first.jsonl: 2 records against the previous run'
      )
    start = lines.index('second.jsonl: 3 records against the previous run')
    table = self.table(lines[start + 2:-1])
    self.assertEqual(table['A'][4:9], ['2.0000', '3.0000', '1.50', '-', 'same'])
    self.assertTrue(lines[-1].endswith('(metric wall, threshold 60%)'))
    self.assertEqual(
        len(records.read(history.record_file(d, 'throughput'))), 3
      )
    # Errors: a missing file, a bad file, a bad threshold.
    missing = os.path.join(self.tmpdir, 'missing.jsonl')
    with self.assertRaisesRegex(SystemExit, 'history: '):
      history.main([d, missing])
    bad = os.path.join(self.tmpdir, 'bad.jsonl')
    with open(bad, 'w') as stream:
      stream.write('{}\n')
    with self.assertRaisesRegex(SystemExit, 'line 1'):
      history.main([d, bad])
    with contextlib.redirect_stderr(io.StringIO()):
      self.assertRaises(SystemExit, history.parse_args, ['-t', '-1', d])
      self.assertRaises(SystemExit, history.parse_args, [])
    # A history whose record file is bad fails before anything is written.
    with open(history.record_file(d, 'import'), 'a') as stream:
      stream.write('broken\n')
    with self.assertRaisesRegex(SystemExit, 'import.jsonl, line 3'):
      history.main([d, first])
    self.assertEqual(
        len(records.read(history.record_file(d, 'throughput'))), 3
      )


class TestSmoke(cytest.TestCase):
  '''
  The run command end to end on the backend of this process: Hello in the
  throughput, import, and memory suites; Hello and the expression in the
  compile suite with a warm cache.
  '''

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-benchmarks-test-')
    self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

  def harness(self, *args):
    '''
    Runs the run command under the limits of this test; returns its status
    and its table.
    '''
    log = io.StringIO()
    argv = [
        '-b', BACKEND, '-r', '1', '--timeout', str(TIMEOUT), '--cap', str(CAP)
      , '--sprite-home', config.prefix()
      ] + list(args)
    with contextlib.redirect_stderr(log):
      status = run.main(argv)
    return status, log.getvalue()

  def filename(self, name):
    return os.path.join(self.tmpdir, name)

  def workdirs(self):
    '''The working directories of the harness that exist now.'''
    tmp = tempfile.gettempdir()
    return [
        name for name in os.listdir(tmp)
             if name.startswith('sprite-benchmarks-')
                and not name.startswith('sprite-benchmarks-test-')
      ]

  def test_throughput_records_agree(self):
    '''
    Two runs of Hello write valid records with the same counters and, with
    perf, nearly the same instructions.
    '''
    files = [self.filename(name) for name in ('a.jsonl', 'b.jsonl')]
    logs = []
    for filename in files:
      status, log = self.harness('Hello', '-o', filename)
      self.assertEqual(status, 0, log)
      self.assertIn('Hello', log)
      self.assertIn('  ok', log)
      with open(filename) as stream:
        self.assertEqual(len(stream.readlines()), 1)
      logs.append(log)
    first, second = [records.read(filename)[0] for filename in files]
    self.assertEqual(records.key(first), ('throughput', 'Hello', BACKEND, None))
    self.assertEqual(first['status'], 'ok')
    self.assertIsNone(first['error'])
    self.assertEqual(first['repeat'], 1)
    self.assertEqual(first['warmup'], 1)
    self.assertEqual(first['steps'], 1)
    self.assertEqual(first['forks'], 0)
    self.assertGreaterEqual(first['collections'], 0)
    self.assertEqual(first['compile'], 0.0)
    self.assertGreaterEqual(first['eval_wall'], 0.0)
    self.assertIsNone(first['eval_cpu'])
    self.assertGreater(first['wall'], 0.0)
    self.assertGreater(first['cpu'], 0.0)
    self.assertGreater(first['peak_rss'], 10 * 1024 ** 2)
    measured = first['samples'][0]
    self.assertEqual(measured['steps'], 1)
    self.assertEqual(measured['extra']['stats']['steps'], 1)
    self.assertFalse(measured['perf'])
    self.assertIsNone(measured['instructions'])
    self.assertEqual(first['warnings'], [])
    self.assertEqual(first['label'], '')
    meta = first['meta']
    self.assertRegex(meta['python'], r'^\d+\.\d+')
    self.assertRegex(meta['frontend'], r'^pakcs-\d')
    self.assertEqual(records.machine(first), {
        'cpu_model': records.cpu_model(), 'cores': os.cpu_count()
      , 'mem_gb': records.memory_gb()
      })
    self.assertGreaterEqual(meta['cores'], 1)
    self.assertNotIn('cpus', meta)
    self.assertEqual(meta['cap'], CAP)
    self.assertEqual(meta['timeout'], TIMEOUT)
    self.assertEqual(meta['env'], {})
    self.assertEqual(meta['rss_source'], measure.rss_source())
    self.assertEqual(
        meta['instructions_source'], measure.instructions_source()
      )
    if config.cxx_tool():
      self.assertTrue(meta['compiler'])
    self.assertEqual(first['commit'], records.commit(ROOTDIR))
    self.assertIn('machine: ', logs[0])
    self.assertIn('instructions: ' + measure.instructions_source(), logs[0])
    # The exact counters agree between the two runs.
    for name in records.COUNTERS:
      self.assertEqual(first[name], second[name], name)
    perf = measure.perf()
    if perf:
      # The repetition under perf comes last and gives the instructions.
      self.assertEqual(len(first['samples']), 2)
      under_perf = first['samples'][1]
      self.assertTrue(under_perf['perf'])
      self.assertEqual(under_perf['steps'], 1)
      self.assertGreater(under_perf['instructions'], 10 ** 6)
      self.assertEqual(first['instructions'], under_perf['instructions'])
      self.assertIn('in one repetition after the measured ones', logs[0])
      # Two runs of Hello retire nearly the same instructions.
      self.assertAlmostEqual(
          second['instructions'] / first['instructions'], 1.0, delta=0.05
        )
    else:
      self.assertEqual(len(first['samples']), 1)
      self.assertIsNone(first['instructions'])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(compare.main(files), 0)
    text = out.getvalue()
    self.assertIn('Hello', text)
    self.assertIn('equal', text)
    self.assertIn('0 with changed counters', text)
    self.assertNotIn('machines differ', text)
    # With a threshold wide enough for a shared machine, strict mode passes
    # on the counters alone.
    with contextlib.redirect_stdout(io.StringIO()):
      self.assertEqual(compare.main(['--strict', '-t', '100'] + files), 0)
    # The deterministic columns compare without a quiet machine.
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      status = compare.main(
          ['--deterministic', '--strict', '-t', '0.05'] + files
        )
    text = out.getvalue()
    self.assertIn('~cpu', text)
    if perf:
      self.assertEqual(status, 0, text)
      self.assertNotIn('instructions: missing', text)
    else:
      self.assertIn('no-metric', text)
      self.assertIn('instructions: missing in OLD for 1 items', text)
    # --no-perf leaves the repetition under perf out.
    filename = self.filename('c.jsonl')
    status, log = self.harness('Hello', '--no-perf', '-o', filename)
    self.assertEqual(status, 0, log)
    self.assertIn('instructions: not measured: --no-perf', log)
    record = records.read(filename)[0]
    self.assertIsNone(record['instructions'])
    self.assertEqual(len(record['samples']), 1)
    self.assertEqual(
        record['meta']['instructions_source'], 'not measured: --no-perf'
      )

  def test_import_suite(self):
    filename = self.filename('import.jsonl')
    status, log = self.harness(
        '-s', 'import', 'python', 'import', '-o', filename
      )
    self.assertEqual(status, 0, log)
    recs = records.read(filename)
    self.assertEqual([r['program'] for r in recs], ['python', 'import'])
    for record in recs:
      self.assertEqual(record['suite'], 'import')
      self.assertEqual(record['status'], 'ok', record['error'])
      self.assertGreater(record['wall'], 0.0)
      self.assertGreater(record['cpu'], 0.0)
      self.assertIsNone(record['steps'])
    if measure.gnu_time():
      # import curry costs memory; without GNU time both peaks sit at the
      # floor set by this process.
      self.assertGreater(recs[1]['peak_rss'], recs[0]['peak_rss'])

  def test_memory_suite(self):
    filename = self.filename('memory.jsonl')
    status, log = self.harness('-s', 'memory', 'Hello', '-o', filename)
    self.assertEqual(status, 0, log)
    recs = records.read(filename)
    variants = ['collector=on']
    if BACKEND == 'cxx':
      variants.append('collector=off')
    self.assertEqual([r['variant'] for r in recs], variants)
    for record in recs:
      self.assertEqual(record['suite'], 'memory')
      self.assertEqual(record['status'], 'ok', record['error'])
      self.assertEqual(record['steps'], 1)
      self.assertGreater(record['peak_rss'], 10 * 1024 ** 2)

  def test_compile_suite(self):
    '''
    The warm variant of Hello and of the expression: the warm-up run calls
    the Curry front end and fills the cache of the harness; the measured run
    hits it and pays the rest of the toolchain.
    '''
    before = self.workdirs()
    filename = self.filename('compile.jsonl')
    status, log = self.harness(
        '-s', 'compile', '--variant', 'warm', 'Hello', 'expression'
      , '-o', filename
      )
    self.assertEqual(status, 0, log)
    hello, expression = records.read(filename)
    self.assertEqual(records.key(hello), ('compile', 'Hello', BACKEND, 'warm'))
    self.assertEqual(hello['status'], 'ok', hello['error'])
    self.assertEqual(hello['warmup'], 1)
    self.assertGreater(hello['compile'], 0.0)
    self.assertLess(hello['compile'], hello['wall'])
    self.assertEqual(hello['steps'], 0)
    self.assertIsNone(hello['eval_wall'])
    self.assertEqual(
        records.key(expression), ('compile', 'expression', BACKEND, 'warm')
      )
    self.assertEqual(expression['status'], 'ok', expression['error'])
    self.assertGreater(expression['compile'], 0.0)
    self.assertGreater(expression['eval_wall'], 0.0)
    self.assertGreaterEqual(expression['steps'], 1)
    probe = expression['samples'][0]['extra']['probe']
    self.assertEqual(probe['value'], '3')
    self.assertEqual(
        sorted(probe)
      , ['compile', 'first_value', 'import', 'prelude', 'stats', 'value']
      )
    self.assertEqual(probe['stats']['steps'], expression['steps'])
    # The working directory of the harness is gone.
    self.assertEqual(self.workdirs(), before)

  @unittest.skipUnless(
      BACKEND == 'cxx', 'QueensSet takes a minute on the Python backend'
    )
  def test_split_suite(self):
    '''QueensSet whole and in two parts, and the split command on them.'''
    filename = self.filename('split.jsonl')
    status, log = self.harness(
        '-s', 'split', 'QueensSet', '--variant', 'whole', '--variant', '2/0'
      , '--variant', '2/1', '-o', filename
      )
    self.assertEqual(status, 0, log)
    recs = records.read(filename)
    self.assertEqual(
        [records.key(r) for r in recs]
      , [('split', 'QueensSet', BACKEND, v) for v in ('whole', '2/0', '2/1')]
      )
    for record in recs:
      self.assertEqual(record['status'], 'ok', record['error'])
      self.assertGreater(record['steps'], 0)
      self.assertGreater(record['forks'], 0)
      self.assertGreater(record['eval_wall'], 0.0)
    row, = split.rows(recs)
    self.assertEqual(row['ok'], '2/2')
    # Each part is a proper part of the search: fewer steps than the whole.
    self.assertGreater(row['bound_steps'], 1.0)
    self.assertGreater(row['bound'], 0.0)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(split.main(['--parts', filename]), 0)
    lines = out.getvalue().splitlines()
    self.assertEqual(lines[1].split()[:4], ['QueensSet', BACKEND, '2', '2/2'])
    self.assertEqual(len(lines[1].split()), len(split.HEADINGS))
    self.assertEqual(lines[2].split()[0], '2/0')
    self.assertEqual(lines[3].split()[0], '2/1')
    self.assertEqual(len(lines), 4)
