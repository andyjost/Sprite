import cytest # from ./lib; must be first
from curry import config
from curry.interpreter import stats as statsmod
import curry, gc, os, re, shutil, subprocess, tempfile, zlib

class ICurryTestCase(cytest.TestCase):
  '''Tests for the API found in module ``curry``.'''

  def test_reload(self):
    curry.reload()
    curry.path.insert(0, 'data/curry/kiel')
    self.assertIn('data/curry/kiel', curry.path)
    curry.import_('rev')
    self.assertIn('rev', curry.modules)

    curry.reload()
    self.assertNotIn('data/curry/kiel', curry.path)
    self.assertNotIn('rev', curry.modules)


class TestStats(cytest.TestCase):
  '''
  ``curry.stats`` and ``sprite-exec --stats``.  Both report the same ten
  fields on both backends: wall and CPU seconds, rewrite steps, forks,
  collections, peak RSS, compile seconds, collector seconds, the functions
  swapped by tiered execution, and the background compiles that failed.  A
  C++ runtime built with the scheduler counters (make COUNTERS=1) appends
  the keys of stats.SCHEDULER_KEYS; unit_cxx_counters.py tests those.
  '''
  KEYS = (
      'wall', 'cpu', 'steps', 'forks', 'collections', 'peak_rss', 'compile'
    , 'gc_seconds', 'swapped', 'failed_compiles'
    )
  TIMEOUT = 120
  # The C++ runtime keeps one entry per module name, so a module built in
  # this process gets a name of its own.
  MODULE = 'StatsApi%d' % os.getpid()

  @staticmethod
  def goal():
    '''A goal with one fork and at least one step; no Curry code is compiled.'''
    return curry.expr([curry.symbol('Prelude.not'), curry.choice(True, False)])

  @staticmethod
  def parse(line):
    '''Parses one line of key=value pairs.  The keys keep their order.'''
    fields = [item.split('=') for item in line.split()]
    return {key: float(value) if '.' in value else int(value)
            for key, value in fields}

  @staticmethod
  def extra_keys():
    '''The keys after the ten: the scheduler counters, when the runtime has them.'''
    if curry.getInterpreter().backend.scheduler_counters_enabled():
      return statsmod.SCHEDULER_KEYS
    return ()

  def test_fields(self):
    '''The ten fields, their types, and the key=value line.'''
    stats = curry.stats()
    self.assertIsInstance(stats, statsmod.Stats)
    self.assertEqual(tuple(stats), self.KEYS + self.extra_keys())
    self.assertEqual(statsmod.KEYS, self.KEYS)
    for key in 'wall', 'cpu', 'compile', 'gc_seconds':
      self.assertIsInstance(stats[key], float, key)
      self.assertGreaterEqual(stats[key], 0.0, key)
    for key in 'steps', 'forks', 'collections', 'peak_rss', 'swapped' \
             , 'failed_compiles':
      self.assertIsInstance(stats[key], int, key)
      self.assertGreaterEqual(stats[key], 0, key)
    self.assertGreater(stats['wall'], 0.0)
    self.assertGreater(stats['cpu'], 0.0)
    self.assertGreater(stats['peak_rss'], 0)
    if curry.flags['backend'] == 'py':
      self.assertEqual(stats['collections'], 0)
      self.assertEqual(stats['gc_seconds'], 0.0)
      self.assertEqual(stats['swapped'], 0)
      self.assertEqual(stats['failed_compiles'], 0)
    line = str(stats)
    self.assertRegex(
        line
      , r'^wall=\d+\.\d{6} cpu=\d+\.\d{6} steps=\d+ forks=\d+ collections=\d+'
        r' peak_rss=\d+ compile=\d+\.\d{6}( \w+=[\d.]+)*$'
      )
    parsed = self.parse(line)
    self.assertEqual(tuple(parsed), self.KEYS + self.extra_keys())
    for key in parsed:
      self.assertAlmostEqual(parsed[key], stats[key], places=6, msg=key)
    self.assertEqual(statsmod.format_stats(stats), line)

  def test_evaluation_counts(self):
    '''An evaluation adds its steps and its forks; the clocks move forward.'''
    before = curry.stats()
    values = sorted(str(value) for value in curry.eval(self.goal()))
    self.assertEqual(values, ['False', 'True'])
    after = curry.stats()
    self.assertGreater(after['steps'], before['steps'])
    self.assertEqual(after['forks'], before['forks'] + 1)
    self.assertGreaterEqual(after['wall'], before['wall'])
    self.assertGreaterEqual(after['cpu'], before['cpu'])
    self.assertGreaterEqual(after['peak_rss'], before['peak_rss'])
    self.assertEqual(after['compile'], before['compile'])

  def test_running_evaluation_is_counted(self):
    '''
    The counts of a running evaluation are part of the totals.  When its
    generator ends or is dropped, the counts are added once.
    '''
    before = curry.stats()
    values = curry.eval(self.goal())
    next(values)
    during = curry.stats()
    self.assertGreater(during['steps'], before['steps'])
    self.assertEqual(during['forks'], before['forks'] + 1)
    list(values)
    after = curry.stats()
    self.assertGreaterEqual(after['steps'], during['steps'])
    self.assertEqual(after['forks'], during['forks'])
    del values
    gc.collect()
    self.assertEqual(curry.stats()['steps'], after['steps'])
    self.assertEqual(curry.stats()['forks'], after['forks'])
    # A generator dropped before it ends is added once as well.
    values = curry.eval(self.goal())
    next(values)
    del values
    gc.collect()
    final = curry.stats()
    self.assertEqual(final['forks'], after['forks'] + 1)
    self.assertGreater(final['steps'], after['steps'])

  def test_single_step_counts(self):
    '''
    A step taken through evaluator.single_step, the entry point behind a
    compiled expression, counts as one rewrite step of the interpreter on
    both backends, as a step of the step loop does.
    '''
    from curry.backends.generic.eval import evaluator
    before = curry.stats()
    expr = curry.expr([curry.symbol('Prelude.not'), True])
    stepped = evaluator.single_step(curry.getInterpreter(), expr)
    after = curry.stats()
    self.assertEqual(after['steps'], before['steps'] + 1)
    self.assertEqual(after['forks'], before['forks'])
    self.assertEqual(str(next(curry.eval(stepped))), 'False')

  @cytest.with_flags(interpret='off')
  def test_compile_time(self):
    '''
    The compile field is the time spent in the steps of the toolchain.  A
    hand-written ICurry-JSON module costs the code generator, and on the C++
    backend the compiler; an import that finds every file current costs
    nothing.  Under the default of the flag ``interpret`` (tiered) the C++
    backend interprets the module and no step runs, so the flag is off.
    '''
    tmpdir = tempfile.mkdtemp(prefix='sprite-stats-')
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    subdir = os.path.join(tmpdir, '.curry', config.intermediate_subdir())
    os.makedirs(subdir)
    with open(os.path.join(subdir, self.MODULE + '.json.z'), 'wb') as stream:
      stream.write(
          zlib.compress(cytest.json_module(self.MODULE, 3).encode('utf-8'))
        )
    before = curry.stats()['compile']
    module = curry.import_(self.MODULE, currypath=[tmpdir] + curry.path)
    after = curry.stats()['compile']
    self.assertGreater(after, before)
    self.assertEqual(list(curry.eval(module.goal, converter='topython')), [3])
    curry.reset()
    self.assertNotIn(self.MODULE, curry.modules)
    module = curry.import_(self.MODULE, currypath=[tmpdir] + curry.path)
    self.assertEqual(curry.stats()['compile'], after)
    self.assertEqual(list(curry.eval(module.goal, converter='topython')), [3])

  def sprite_exec(self, *args, status=0):
    '''
    Runs sprite-exec on the backend of this process and returns the parsed
    statistics line, the last line of stderr, with the output streams.
    '''
    cmd = ['timeout', str(self.TIMEOUT), config.sprite_exec()] + list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    self.assertEqual(
        proc.returncode, status
      , 'sprite-exec ended with status %s; stdout:\n%s\nstderr:\n%s'
            % (proc.returncode, proc.stdout, proc.stderr)
      )
    lines = proc.stderr.splitlines()
    self.assertTrue(lines, 'no statistics line on stderr')
    self.assertRegex(
        lines[-1], r'^wall=.* compile=\d+\.\d{6}( \w+=[\d.]+)*$'
      )
    return self.parse(lines[-1]), proc.stdout, lines[:-1]

  def test_sprite_exec_stats(self):
    '''
    sprite-exec --stats prints the eight fields as the last line of stderr.
    The module has a committed ICurry cache, so no Curry front end runs.
    '''
    stats, stdout, rest = self.sprite_exec('--stats', '-m', 'mynot')
    self.assertEqual(sorted(stdout.split()), ['False', 'True'])
    self.assertEqual(tuple(stats), self.KEYS + self.extra_keys())
    self.assertGreater(stats['wall'], 0.0)
    self.assertGreater(stats['cpu'], 0.0)
    self.assertGreater(stats['steps'], 0)
    self.assertGreaterEqual(stats['forks'], 1)
    self.assertGreaterEqual(stats['collections'], 0)
    self.assertGreater(stats['peak_rss'], 0)
    self.assertGreaterEqual(stats['compile'], 0.0)
    self.assertLessEqual(stats['compile'], stats['wall'])

  def test_sprite_exec_stats_after_an_error(self):
    '''The line follows the error message of a failed run.'''
    stats, stdout, rest = self.sprite_exec(
        '--stats', '-m', 'mynot', '-g', 'nosuchgoal', status=1
      )
    self.assertEqual(stdout, '')
    self.assertTrue(any('nosuchgoal' in line for line in rest), rest)
    self.assertEqual(tuple(stats), self.KEYS + self.extra_keys())
    self.assertEqual(stats['steps'], 0)

  def test_without_stats_option(self):
    '''Without --stats, sprite-exec prints no statistics.'''
    cmd = ['timeout', str(self.TIMEOUT), config.sprite_exec(), '-m', 'mynot']
    proc = subprocess.run(cmd, capture_output=True, text=True)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertNotIn('wall=', proc.stderr)
