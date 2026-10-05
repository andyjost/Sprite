'''
Tests for the scheduler counters of the C++ backend (src/cyrt/state/
counters.hpp), which exist in a runtime built with make COUNTERS=1: the steps
taken while the outermost queue held one configuration, the steps inside set
functions, the steps whose redex another configuration created, the largest
queue, and the lifetimes of the configurations.  curry.stats and sprite-exec
--stats report them after the seven fields of every build.

The tests of the counters run on an instrumented runtime only.  On a plain
runtime, and on the Python backend, the tests check that the statistics have
the seven fields alone.  The derivations in Python (the median of a histogram
and the sum over evaluations) are tested on every backend.
'''
import cytest # from ./lib; must be first
from curry.backends.generic.eval import evaluator
from curry.interpreter import stats as statsmod
from curry import config
import curry, re, subprocess, unittest

CXX = curry.flags['backend'] == 'cxx'
if CXX:
  from curry.backends.cxx import cyrtbindings as cyrt
ENABLED = CXX and cyrt.scheduler_counters_enabled()
KEYS = statsmod.KEYS + statsmod.SCHEDULER_KEYS
TIMEOUT = 120

def raw_counters():
  '''The summed counters of the interpreter, as the runtime reports them.'''
  return curry.getInterpreter()._evaluation_totals.scheduler

def plain(stats):
  '''The counts of a Stats object without the clocks and the sizes.'''
  return {key: stats[key] for key in stats
                          if key not in ('wall', 'cpu', 'peak_rss', 'compile'
                                        , 'gc_seconds')}


class TestDerivations(unittest.TestCase):
  '''The Python side: the median of a histogram and the sum of counters.'''

  @staticmethod
  def histogram(exact=(), coarse=()):
    exact = list(exact) + [0] * (1024 - len(exact))
    coarse = list(coarse) + [0] * (64 - len(coarse))
    count = sum(exact) + sum(coarse)
    return {'count': count, 'sum': 0, 'max': 0, 'exact': exact, 'coarse': coarse}

  def test_histogram_median(self):
    median = statsmod.histogram_median
    self.assertEqual(median(self.histogram()), 0)
    self.assertEqual(median(self.histogram([0, 3])), 1)
    self.assertEqual(median(self.histogram([0, 1, 1, 1, 1, 1])), 3)
    # Of an even number of values, the lower middle one counts.
    self.assertEqual(median(self.histogram([0, 1, 1, 0, 0, 1, 1])), 2)
    self.assertEqual(median(self.histogram([0, 1, 1, 0, 0, 1, 1, 1])), 5)
    # A median in a coarse bucket is the lower bound of the bucket: here one
    # value in [1024, 2048) and two in [2048, 4096), then a fourth value, 0,
    # which makes the lower middle one the median.
    coarse = [0] * 10 + [1, 2]
    self.assertEqual(median(self.histogram([], coarse)), 2048)
    self.assertEqual(median(self.histogram([1], coarse)), 1024)
    self.assertEqual(median(self.histogram([], [0] * 20 + [1])), 2 ** 20)
    broken = self.histogram([1])
    broken['count'] = 5
    with self.assertRaises(ValueError):
      median(broken)

  def test_merge_counters(self):
    merge = evaluator.merge_counters
    a = {'n': 1, 'queue_max': 3, 'lst': [1, 2], 'sub': {'max': 4, 'm': 1}}
    b = {'n': 2, 'queue_max': 2, 'lst': [3, 4], 'sub': {'max': 7, 'm': 2}}
    total = merge(None, a)
    self.assertEqual(total, a)
    self.assertIsNot(total, a)
    self.assertIsNot(total['lst'], a['lst'])
    self.assertIsNot(total['sub'], a['sub'])
    total = merge(total, b)
    self.assertEqual(
        total
      , {'n': 3, 'queue_max': 3, 'lst': [4, 6], 'sub': {'max': 7, 'm': 3}}
      )
    self.assertEqual(a['n'], 1)

  def test_scheduler_fields_of_nothing(self):
    '''Without counters every derived field is zero, in the order of the keys.'''
    fields = statsmod.scheduler_fields(None)
    self.assertEqual(tuple(key for key, _ in fields), statsmod.SCHEDULER_KEYS)
    for key, value in fields:
      self.assertEqual(value, 0, key)
      self.assertIsInstance(value, float if key.endswith('_mean') else int)


@unittest.skipIf(ENABLED, 'the runtime has the scheduler counters')
class TestPlainBuild(cytest.TestCase):
  '''A plain runtime, or the Python backend, reports the seven fields only.'''

  def test_no_counters(self):
    goal = curry.expr([curry.symbol('Prelude.not'), curry.choice(True, False)])
    self.assertEqual(sorted(map(str, curry.eval(goal))), ['False', 'True'])
    self.assertEqual(tuple(curry.stats()), statsmod.KEYS)
    self.assertIsNone(raw_counters())
    self.assertFalse(curry.getInterpreter().backend.scheduler_counters_enabled())
    if CXX:
      self.assertFalse(cyrt.scheduler_counters_enabled())


@unittest.skipUnless(ENABLED, 'needs a runtime built with make COUNTERS=1')
class TestCounters(cytest.TestCase):
  '''
  The counters on small programs (data/curry/CxxCounters.curry and
  CxxGc.curry).  Every test starts a fresh interpreter, so the totals are
  those of its own evaluations.
  '''

  @classmethod
  def setUpClass(cls):
    curry.import_('CxxCounters')
    curry.import_('CxxGc')

  def setUp(self):
    curry.reload({'backend': 'cxx'})
    self.M = curry.import_('CxxCounters')
    self.G = curry.import_('CxxGc')

  def evaluate(self, goal, *args):
    return sorted(curry.eval(goal, *args, converter='topython'))

  def check_invariant(self):
    '''
    Every step belongs to one configuration of the outermost queue, which
    ended by a value, a failure, or a fork, or is still in the queue.
    '''
    stats = curry.stats()
    outer = raw_counters()['outer']
    self.assertEqual(
        outer['value_steps'] + outer['failure_steps'] + outer['fork_steps']
            + outer['left_steps']
      , stats['steps']
      )
    self.assertEqual(
        stats['configurations']
      , outer['values'] + outer['failures'] + outer['forked'] + outer['left']
      )
    self.assertEqual(outer['lifetimes']['count'], stats['configurations'] - outer['left'])
    self.assertEqual(stats['forks'], outer['forked'] + raw_counters()['nested']['forked'])
    return stats, outer

  def test_keys(self):
    '''The fourteen keys follow the seven, in the line and in the dict.'''
    stats = curry.stats()
    self.assertEqual(tuple(stats), KEYS)
    self.assertTrue(curry.getInterpreter().backend.scheduler_counters_enabled())
    line = str(stats)
    self.assertRegex(
        line
      , r'^wall=\S+ cpu=\S+ steps=0 forks=0 collections=\d+ peak_rss=\d+'
        r' compile=\S+ gc_seconds=\S+ serial_steps=0 nested_steps=0'
        r' shared_steps=0'
        r' queue_max=0 configurations=0 failures=0 failed_steps=0'
        r' lifetime_median=0 lifetime_mean=0\.000000 lifetime_max=0'
        r' nested_configurations=0 nested_lifetime_median=0'
        r' nested_lifetime_mean=0\.000000 nested_lifetime_max=0$'
      )
    self.assertIsNone(raw_counters())

  def test_deterministic(self):
    '''One configuration: every step is serial, none is shared.'''
    self.assertEqual(self.evaluate(self.M.count, 50), [50])
    stats, outer = self.check_invariant()
    steps = stats['steps']
    self.assertGreater(steps, 100)
    self.assertLess(steps, 1024)
    self.assertEqual(plain(stats), {
        'steps': steps, 'forks': 0, 'collections': stats['collections']
      , 'serial_steps': steps, 'nested_steps': 0, 'shared_steps': 0
      , 'queue_max': 1, 'configurations': 1, 'failures': 0, 'failed_steps': 0
      , 'lifetime_median': steps, 'lifetime_mean': float(steps)
      , 'lifetime_max': steps, 'nested_configurations': 0
      , 'nested_lifetime_median': 0, 'nested_lifetime_mean': 0.0
      , 'nested_lifetime_max': 0
      })
    self.assertEqual(outer['values'], 1)
    self.assertEqual(outer['lifetimes']['exact'][steps], 1)
    # A long life falls in a power-of-two bucket; the median is its lower
    # bound.
    self.assertEqual(self.evaluate(self.G.walk, 50), [50])
    stats = curry.stats()
    self.assertGreater(stats['steps'], 1024 + steps)
    self.assertEqual(stats['configurations'], 2)
    self.assertEqual(stats['lifetime_max'], stats['steps'] - steps)
    self.assertEqual(stats['lifetime_median'], steps)
    histogram = raw_counters()['outer']['lifetimes']
    bucket = (stats['steps'] - steps).bit_length() - 1
    self.assertEqual(histogram['coarse'][bucket], 1)
    self.assertEqual(histogram['count'], 2)

  def test_choice(self):
    '''
    not (True ? False): three steps bring the choice to the root (the
    function, ?, and the pull-tab), the parent forks, and each alternative
    takes one step on the node the parent made.  The second alternative
    runs alone after the first produced its value.
    '''
    self.assertEqual(self.evaluate(self.M.coinNot), [False, True])
    stats, outer = self.check_invariant()
    self.assertEqual(plain(stats), {
        'steps': 5, 'forks': 1, 'collections': stats['collections']
      , 'serial_steps': 4, 'nested_steps': 0, 'shared_steps': 2
      , 'queue_max': 2, 'configurations': 3, 'failures': 0, 'failed_steps': 0
      , 'lifetime_median': 1, 'lifetime_mean': 5 / 3, 'lifetime_max': 3
      , 'nested_configurations': 0, 'nested_lifetime_median': 0
      , 'nested_lifetime_mean': 0.0, 'nested_lifetime_max': 0
      })
    self.assertEqual(
        {k: v for k, v in outer.items() if k != 'lifetimes'}
      , { 'values': 2, 'failures': 0, 'forked': 1, 'left': 0
        , 'value_steps': 2, 'failure_steps': 0, 'fork_steps': 3
        , 'left_steps': 0
        }
      )
    self.assertEqual(outer['lifetimes']['exact'][:4], [0, 2, 0, 1])

  def test_failure(self):
    '''
    not (True ? failed): the failing alternative takes two steps (failed,
    then not forwards to the failure) and is dropped.
    '''
    self.assertEqual(self.evaluate(self.M.oneFails), [False])
    stats, outer = self.check_invariant()
    self.assertEqual(stats['steps'], 6)
    self.assertEqual(stats['forks'], 1)
    self.assertEqual(stats['serial_steps'], 5)
    self.assertEqual(stats['shared_steps'], 3)
    self.assertEqual(stats['configurations'], 3)
    self.assertEqual(stats['failures'], 1)
    self.assertEqual(stats['failed_steps'], 2)
    self.assertEqual(stats['lifetime_median'], 2)
    self.assertEqual(stats['lifetime_mean'], 2.0)
    self.assertEqual(stats['lifetime_max'], 3)
    self.assertEqual(outer['values'], 1)
    self.assertEqual(outer['value_steps'], 1)

  def test_left_in_the_queue(self):
    '''
    A consumer that stops after the first value leaves the other
    alternative in the queue.  It counts as a configuration without a
    lifetime, while the generator runs and after it is closed.
    '''
    values = curry.eval(self.M.twoValues, converter='topython')
    self.assertEqual(next(values), 1)
    stats, outer = self.check_invariant()
    self.assertEqual(stats['steps'], 3)
    self.assertEqual(stats['configurations'], 3)
    self.assertEqual(outer['left'], 1)
    self.assertEqual(outer['left_steps'], 0)
    self.assertEqual(outer['values'], 1)
    self.assertEqual(outer['forked'], 1)
    self.assertEqual(stats['lifetime_mean'], 1.5)
    values.close()
    self.assertEqual(stats, curry.stats() | {
        key: stats[key] for key in ('wall', 'cpu', 'peak_rss')
      })
    self.check_invariant()
    # Both values: nothing is left.
    curry.reload({'backend': 'cxx'})
    M = curry.import_('CxxCounters')
    self.assertEqual(self.evaluate(M.twoValues), [1, 2])
    stats, outer = self.check_invariant()
    self.assertEqual(stats['steps'], 4)
    self.assertEqual(outer['left'], 0)
    self.assertEqual(stats['lifetime_max'], 2)

  def test_set_function(self):
    '''
    A set function runs its alternatives in a nested queue: the outermost
    queue keeps one configuration, so every step is serial, and the nested
    queue sees two forks and three values.
    '''
    self.assertEqual(self.evaluate(self.M.inSet), [[1, 2, 3]])
    stats, outer = self.check_invariant()
    nested = raw_counters()['nested']
    self.assertEqual(stats['forks'], 2)
    self.assertEqual(stats['serial_steps'], stats['steps'])
    self.assertEqual(stats['configurations'], 1)
    self.assertEqual(stats['queue_max'], 1)
    self.assertGreater(stats['nested_steps'], 0)
    self.assertLess(stats['nested_steps'], stats['steps'])
    self.assertGreater(stats['shared_steps'], 0)
    self.assertEqual(stats['nested_configurations'], 5)
    self.assertEqual(
        {k: v for k, v in nested.items() if k != 'lifetimes'}
      , { 'values': 3, 'failures': 0, 'forked': 2, 'left': 0
        , 'value_steps': 3, 'failure_steps': 0, 'fork_steps': 3
        , 'left_steps': 0
        }
      )
    self.assertEqual(
        nested['value_steps'] + nested['fork_steps'], stats['nested_steps']
      )
    self.assertEqual(stats['nested_lifetime_median'], 1)
    self.assertEqual(stats['nested_lifetime_mean'], 1.2)
    self.assertEqual(stats['nested_lifetime_max'], 2)

  def test_search(self):
    '''
    A sort by permutation: a fork per insertion, a failure per unsorted
    prefix, and short lives; the queue grows beyond one configuration.
    '''
    self.assertEqual(self.evaluate(self.G.psort, 4), [[1, 2, 3, 4]])
    stats, outer = self.check_invariant()
    self.assertEqual(stats['forks'], 18)
    self.assertEqual(stats['failures'], 18)
    self.assertEqual(outer['values'], 1)
    self.assertEqual(stats['configurations'], 37)
    self.assertGreater(stats['queue_max'], 2)
    self.assertLess(stats['serial_steps'], stats['steps'])
    self.assertGreater(stats['shared_steps'], 0)
    self.assertLess(stats['shared_steps'], stats['steps'])
    self.assertGreater(stats['failed_steps'], 0)
    self.assertLess(stats['failed_steps'], stats['steps'])
    self.assertLessEqual(stats['lifetime_median'], stats['lifetime_mean'])
    self.assertLess(stats['lifetime_mean'], stats['lifetime_max'])
    self.assertEqual(stats['nested_steps'], 0)
    self.assertEqual(stats['nested_configurations'], 0)
    # The nested search of countQueens: the outermost queue never forks.
    curry.reload({'backend': 'cxx'})
    G = curry.import_('CxxGc')
    self.assertEqual(self.evaluate(G.countQueens, 4), [2])
    stats, outer = self.check_invariant()
    self.assertEqual(stats['configurations'], 1)
    self.assertEqual(stats['serial_steps'], stats['steps'])
    self.assertGreater(stats['forks'], 100)
    nested = raw_counters()['nested']
    self.assertEqual(nested['forked'], stats['forks'])
    self.assertGreater(nested['failures'], 0)
    self.assertGreater(nested['values'], 0)
    self.assertEqual(
        stats['nested_configurations']
      , nested['values'] + nested['failures'] + nested['forked']
      )
    self.assertGreater(stats['nested_lifetime_max'], stats['nested_lifetime_median'])

  def test_single_step(self):
    '''
    A step through evaluator.single_step is a serial step of the one
    configuration of its state, which stays in the queue.
    '''
    expr = curry.expr([curry.symbol('Prelude.not'), True])
    stepped = evaluator.single_step(curry.getInterpreter(), expr)
    stats, outer = self.check_invariant()
    self.assertEqual(stats['steps'], 1)
    self.assertEqual(stats['serial_steps'], 1)
    self.assertEqual(stats['shared_steps'], 0)
    self.assertEqual(stats['configurations'], 1)
    self.assertEqual(outer['left'], 1)
    self.assertEqual(outer['left_steps'], 1)
    self.assertEqual(str(next(curry.eval(stepped))), 'False')

  def test_sum_over_evaluations(self):
    '''The totals of an interpreter sum its evaluations; the maxima do not add.'''
    self.assertEqual(self.evaluate(self.M.coinNot), [False, True])
    self.assertEqual(self.evaluate(self.M.oneFails), [False])
    stats, outer = self.check_invariant()
    self.assertEqual(stats['steps'], 11)
    self.assertEqual(stats['forks'], 2)
    self.assertEqual(stats['serial_steps'], 9)
    self.assertEqual(stats['shared_steps'], 5)
    self.assertEqual(stats['queue_max'], 2)
    self.assertEqual(stats['configurations'], 6)
    self.assertEqual(stats['failures'], 1)
    self.assertEqual(stats['lifetime_max'], 3)
    self.assertEqual(stats['lifetime_median'], 1)
    self.assertEqual(stats['lifetime_mean'], 11 / 6)
    # A soft reset keeps the totals.
    curry.reset()
    self.assertEqual(curry.stats()['configurations'], 6)

  def test_sprite_exec(self):
    '''sprite-exec --stats prints the counters after the seven fields.'''
    cmd = [
        'timeout', str(TIMEOUT), config.sprite_exec(), '--stats', '-m'
      , 'CxxCounters', '-g', 'coinNot'
      ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(sorted(proc.stdout.split()), ['False', 'True'])
    line = proc.stderr.splitlines()[-1]
    fields = dict(item.split('=') for item in line.split())
    self.assertEqual(tuple(fields), KEYS)
    self.assertEqual(fields['steps'], '5')
    self.assertEqual(fields['serial_steps'], '4')
    self.assertEqual(fields['shared_steps'], '2')
    self.assertEqual(fields['configurations'], '3')
    self.assertEqual(fields['lifetime_median'], '1')
    self.assertEqual(fields['lifetime_mean'], '1.666667')
    self.assertEqual(fields['lifetime_max'], '3')
