'''
Tests for the benchmark harness under lib/benchmarks: the child runner, the
parsers, the records, the suites, and the run and compare commands.

The smoke tests run the harness on Hello, whose outputs the warm-up run
builds (or finds in the local cache), on the backend of this process, and
they compile Hello and the expression of the compile suite with a warm cache.
In a fresh checkout the file costs three calls of the Curry front end: Hello
in the first warm-up, and Hello and the expression in the compile suite.
'''
import cytest # from ./lib; must be first
from benchmarks import CURRYDIR, DISSERTATION, ROOTDIR
from benchmarks import compare, measure, records, run, suites
from curry import config
import contextlib, curry, io, json, os, shutil, sys, tempfile, unittest

BACKEND = curry.flags['backend']
PYTHON = sys.executable
CAP = 2 * 1024 ** 3
TIMEOUT = 120
STATS_LINE = (
    'wall=0.124318 cpu=0.116882 steps=7 forks=2 collections=3 '
    'peak_rss=36528128 compile=0.500000'
  )


class FakeRun:
  '''Stands in for measure.Run.'''
  def __init__(
      self, status='ok', wall=1.0, cpu=0.5, peak_rss=1000, stdout='', stderr=''
    ):
    self.status = status
    self.returncode = 0 if status == 'ok' else 1
    self.error = None if status == 'ok' else 'boom'
    self.wall = wall
    self.cpu = cpu
    self.peak_rss = peak_rss
    self.stdout = stdout
    self.stderr = stderr


def make_record(
    program, cpu, steps=5, forks=1, status='ok', suite='throughput'
  , backend='cxx', variant=None
  ):
  '''A record with one sample.'''
  run = FakeRun(status=status, wall=cpu * 2, cpu=cpu, peak_rss=int(cpu * 1000))
  sample = records.sample(run, {'steps': steps, 'forks': forks})
  return records.summarize(
      suite, program, backend, variant, [sample], {}, commit='abc'
    )


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
    self.assertIsNone(record['eval_wall'])
    self.assertIsNone(record['compile'])
    self.assertEqual(record['repeat'], 3)
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
        ('schema', 2, 'schema 2 is not 1')
      , ('suite', 'speed', "field 'suite' has a bad value")
      , ('backend', 'c', "field 'backend' has a bad value")
      , ('status', 'done', "field 'status' has a bad value")
      , ('steps', 1.5, "field 'steps' has a bad value")
      , ('steps', True, "field 'steps' has a bad value")
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

  def test_cpu_model(self):
    model = records.cpu_model()
    self.assertTrue(model is None or isinstance(model, str))


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
    args = run.parse_args([
        '-s', 'memory', '-b', 'py', '-b', 'cxx', '-e', 'A=1', '-e', 'B=x=y'
      , 'Fib'
      ])
    self.assertEqual(args.repeat, 1)
    self.assertEqual(args.backend, ['py', 'cxx'])
    self.assertEqual(args.env, [('A', '1'), ('B', 'x=y')])
    self.assertEqual(args.program, ['Fib'])
    bad_options = [
        ['-r', '0'], ['-w', '-1'], ['--timeout', '0'], ['-e', 'novalue']
      , ['-b', 'c']
      ]
    for bad in bad_options:
      with contextlib.redirect_stderr(io.StringIO()):
        self.assertRaises(SystemExit, run.parse_args, bad)

  def test_list_and_errors(self):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(run.main(['--list', '-s', 'import']), 0)
    self.assertEqual(out.getvalue().split(), list(suites.IMPORT_ITEMS))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(run.main(['-l', 'Tak?']), 0)
    self.assertEqual(out.getvalue().split(), ['Tak0', 'Tak1', 'Tak2'])
    with self.assertRaisesRegex(
        SystemExit, "no program of the throughput suite matches 'Nope'"
      ):
      run.main(['Nope'])
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
    self.old = [
        make_record('A', 1.0), make_record('B', 1.0), make_record('C', 1.0)
      , make_record('D', 1.0, steps=5), make_record('E', 1.0)
      , make_record('F', 1.0, status='fail'), make_record('Z', 0.0)
      ]
    self.new = [
        make_record('A', 1.05), make_record('B', 1.5), make_record('C', 0.5)
      , make_record('D', 1.0, steps=6), make_record('F', 1.0)
      , make_record('G', 1.0), make_record('Z', 0.0)
      ]

  def write(self, name, recs):
    filename = os.path.join(self.tmpdir, name)
    with open(filename, 'w') as stream:
      for record in recs:
        records.write(stream, record)
    return filename

  @staticmethod
  def key(program):
    return ('throughput', program, 'cxx', None)

  def test_verdicts(self):
    old = compare.latest(self.old)
    new = compare.latest(self.new)
    def row(program, metric='cpu', threshold=0.10):
      k = self.key(program)
      return compare.compare(old.get(k), new.get(k), metric, threshold)
    self.assertEqual(row('A')['verdict'], 'same')
    self.assertAlmostEqual(row('A')['ratio'], 1.05)
    self.assertEqual(row('B')['verdict'], 'slower')
    self.assertEqual(row('B', threshold=0.6)['verdict'], 'same')
    self.assertEqual(row('B', threshold=0.0)['verdict'], 'slower')
    self.assertEqual(row('C')['verdict'], 'faster')
    self.assertEqual(row('D')['verdict'], 'same')
    self.assertEqual(row('D')['counters'], ['steps 5->6'])
    self.assertEqual(row('E')['verdict'], 'only-old')
    self.assertEqual(row('F')['verdict'], 'fail')
    self.assertEqual(row('G')['verdict'], 'only-new')
    self.assertEqual(row('Z')['verdict'], 'same')
    self.assertEqual(row('Z')['ratio'], 1.0)
    self.assertEqual(row('A', metric='eval_wall')['verdict'], 'no-metric')
    zero = compare.compare(
        make_record('Z', 0.0), make_record('Z', 0.5), 'cpu', 0.1
      )
    self.assertEqual(zero['verdict'], 'slower')
    # The last record of an item counts.
    latest = compare.latest([make_record('A', 1.0), make_record('A', 2.0)])
    self.assertEqual(latest[self.key('A')]['cpu'], 2.0)

  def test_main(self):
    old = self.write('old.jsonl', self.old)
    new = self.write('new.jsonl', self.new)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(compare.main([old, new]), 0)
    lines = out.getvalue().splitlines()
    self.assertEqual(
        lines[0].split()
      , [ 'suite', 'program', 'backend', 'variant', 'old', 'new', 'ratio'
        , 'verdict', 'counters'
        ]
      )
    table = {line.split()[1]: line.split() for line in lines[1:-1]}
    self.assertEqual(table['A'][7:], ['same', 'equal'])
    self.assertEqual(table['B'][7:], ['slower', 'equal'])
    self.assertEqual(table['C'][7:], ['faster', 'equal'])
    self.assertEqual(table['D'][7:], ['same', 'steps', '5->6'])
    self.assertEqual(table['E'][7:], ['only-old', '-'])
    self.assertEqual(table['F'][7:], ['fail', '-'])
    self.assertEqual(table['G'][7:], ['only-new', '-'])
    self.assertEqual(table['Z'][7:], ['same', 'equal'])
    self.assertEqual(
        lines[-1]
      , '8 items: 3 same, 1 faster, 1 slower, 1 failed, 0 without the metric, '
        '2 only in one file; 1 with changed counters '
        '(metric cpu, threshold 10%)'
      )
    good = self.write('good.jsonl', [make_record('A', 1.0)])
    with contextlib.redirect_stdout(io.StringIO()):
      self.assertEqual(compare.main(['--strict', old, new]), 1)
      self.assertEqual(compare.main(['--strict', old, old]), 1) # F failed
      # D and F
      self.assertEqual(compare.main(['--strict', '-t', '0.6', old, new]), 1)
      self.assertEqual(compare.main(['--strict', good, good]), 0)
      self.assertEqual(compare.main(['-m', 'peak_rss', old, new]), 0)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(compare.main(['-m', 'eval_wall', good, good]), 0)
    self.assertIn('no-metric', out.getvalue())
    with self.assertRaisesRegex(SystemExit, 'compare: '):
      compare.main([old, os.path.join(self.tmpdir, 'missing.jsonl')])
    bad = os.path.join(self.tmpdir, 'bad.jsonl')
    with open(bad, 'w') as stream:
      stream.write('{}\n')
    with self.assertRaisesRegex(SystemExit, 'line 1'):
      compare.main([old, bad])


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
    '''Two runs of Hello write valid records with the same counters.'''
    files = [self.filename(name) for name in ('a.jsonl', 'b.jsonl')]
    for filename in files:
      status, log = self.harness('Hello', '-o', filename)
      self.assertEqual(status, 0, log)
      self.assertIn('Hello', log)
      self.assertIn('  ok', log)
      with open(filename) as stream:
        self.assertEqual(len(stream.readlines()), 1)
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
    self.assertEqual(len(first['samples']), 1)
    self.assertEqual(first['samples'][0]['steps'], 1)
    self.assertEqual(first['samples'][0]['extra']['stats']['steps'], 1)
    self.assertEqual(first['warnings'], [])
    self.assertEqual(first['label'], '')
    meta = first['meta']
    self.assertRegex(meta['python'], r'^\d+\.\d+')
    self.assertRegex(meta['frontend'], r'^pakcs-\d')
    self.assertGreaterEqual(meta['cpus'], 1)
    self.assertEqual(meta['cap'], CAP)
    self.assertEqual(meta['timeout'], TIMEOUT)
    self.assertEqual(meta['env'], {})
    self.assertEqual(meta['rss_source'], measure.rss_source())
    if config.cxx_tool():
      self.assertTrue(meta['compiler'])
    self.assertEqual(first['commit'], records.commit(ROOTDIR))
    # The exact counters agree between the two runs.
    for name in records.COUNTERS:
      self.assertEqual(first[name], second[name], name)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      self.assertEqual(compare.main(files), 0)
    text = out.getvalue()
    self.assertIn('Hello', text)
    self.assertIn('equal', text)
    self.assertIn('0 with changed counters', text)
    # With a threshold wide enough for a shared machine, strict mode passes
    # on the counters alone.
    with contextlib.redirect_stdout(io.StringIO()):
      self.assertEqual(compare.main(['--strict', '-t', '100'] + files), 0)

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
