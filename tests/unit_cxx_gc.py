'''Tests for the garbage collector of the C++ backend.'''
import cytest # from ./lib; must be first
import ast, curry, os, unittest
from unittest import mock

class ChildTests(cytest.TestCase):
  '''
  The base of the test classes below.  Every test runs a child under prlimit
  and timeout, because a missing root ends in a crash.  The children import
  the bindings and the test module, data/curry/CxxGc.curry.  No test of its
  own.
  '''
  TIMEOUT = 120

  # The children import the bindings and the test module.
  PREAMBLE = '''
import curry, gc, os, sys
from curry.backends.cxx import cyrtbindings as cyrt
curry.reload({'backend': 'cxx'})
M = curry.import_('CxxGc')
'''

  @classmethod
  def setUpClass(cls):
    # Compile the module here.  The children inherit the address-space cap,
    # and the processes of the Curry compiler do not fit under it.
    curry.import_('CxxGc')

  def run_child(self, code, address_space=2 << 30, status=0):
    proc = cytest.run_in_subprocess(
        self.PREAMBLE + code, self.TIMEOUT, address_space=address_space
      )
    self.assertEqual(
        proc.returncode, status
      , 'the child ended with status %s; stdout:\n%s\nstderr:\n%s'
            % (proc.returncode, proc.stdout, proc.stderr)
      )
    return proc


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestCxxGc(ChildTests):
  '''
  The collector of the C++ backend (src/cyrt/graph/gc/wdgc.cpp).  The nodes
  Python holds are roots, the queue of a set function is a root, a nested
  evaluation collects, and a program that allocates many short-lived nodes
  completes under a 1 GiB address-space cap.
  '''

  # The cells walked beside a live table of 300 pairs.  In stress mode every
  # step marks the table, so the walk is shorter there.
  WALK = 10000 if cytest.GC_STRESS else 100000

  def test_value_survives_collections(self):
    '''
    A value handed to Python stays correct across collections, and its nodes
    are reclaimed after Python drops it.
    '''
    proc = self.run_child('''
value = next(curry.eval(M.table, 300))
text = str(value)
expected = [(i, str(i)) for i in range(1, 301)]
assert curry.topython(value) == expected
cyrt.gc_set_threshold(1 << 14)
n0 = cyrt.gc_collections()
assert curry.topython(next(curry.eval(M.walk, %d))) == %d
collections = cyrt.gc_collections() - n0
assert collections > 10, collections
cyrt.gc_collect()
assert str(value) == text, str(value)
assert curry.topython(value) == expected
before = cyrt.gc_node_count()
del value
gc.collect()
cyrt.gc_collect()
after = cyrt.gc_node_count()
# Each entry is a pair, a list cell, and a cons cell per character of the
# shown number.  The Int and the Char nodes are the shared literal nodes
# of the runtime, which stay (see unit_cxx_literals.py).
assert after <= before - 1200, (before, after)
print('collections', collections, 'nodes', before, after)
''' % (self.WALK, self.WALK))
    self.assertIn('collections', proc.stdout)

  def test_expression_survives_collections(self):
    '''
    An expression built with curry.expr, evaluated or not, stays correct
    across collections.
    '''
    self.run_child('''
value = curry.expr([(1, 'a'), (2, 'b')])
goal = curry.expr(M.walk, 25)
text, goaltext = str(value), str(goal)
cyrt.gc_set_threshold(1 << 14)
n0 = cyrt.gc_collections()
assert curry.topython(next(curry.eval(M.walk, 100000))) == 100000
assert cyrt.gc_collections() > n0
cyrt.gc_collect()
assert str(value) == text, str(value)
assert str(goal) == goaltext, str(goal)
assert curry.topython(next(curry.eval(value))) == [(1, 'a'), (2, 'b')]
assert curry.topython(next(curry.eval(goal))) == 25
''')

  def test_copy_of_a_pinned_constructor(self):
    '''
    A pinned nullary constructor ([], (), True, False) has one node, the
    static object, which the collector neither marks nor sweeps.  A copy of
    it is the node itself, so the copy survives collections and a reuse of
    the heap while Python holds it.  A heap copy with the same info table
    was freed under its holder, and the verifier did not see it, because it
    checks the marked nodes.
    '''
    self.run_child('''
import copy
raw = lambda e: getattr(e, 'raw_expr', e)
copies = []
for value in [[], (), True, False]:
  node = raw(curry.raw_expr(value))
  text = repr(node)
  copies.append((node.copy(), text))
  copies.append((copy.copy(node), text))
  copies.append((node.__deepcopy__(), text))
  for c, _ in copies[-3:]:
    assert c.id() == node.id(), (repr(c), text)
    assert cyrt.gc_root_count(c) >= 1
before = cyrt.gc_node_count()
cyrt.gc_collect()
assert cyrt.gc_node_count() == before, (before, cyrt.gc_node_count())
# Fill the slots a freed copy would have left behind.
junk = [curry.raw_expr(i) for i in range(1000, 4000)]
assert curry.topython(next(curry.eval(M.walk, 3000))) == 3000
cyrt.gc_collect()
for c, text in copies:
  assert repr(c) == text, (repr(c), text)
assert cyrt.gc_verify() is None
assert curry.topython(next(curry.eval(copies[0][0]))) == []
assert curry.topython(next(curry.eval(copies[6][0]))) is True
''')

  def test_roots_follow_wrappers(self):
    '''
    A node is a root while a Python wrapper of it exists.  Wrappers come and
    go with curry.expr and with the successors of a node.
    '''
    self.run_child('''
raw = lambda e: getattr(e, 'raw_expr', e)
r0 = cyrt.gc_num_roots()
e = curry.expr(7)
assert cyrt.gc_num_roots() == r0 + 1, (r0, cyrt.gc_num_roots())
assert cyrt.gc_root_count(raw(e)) == 1
lst = curry.expr([1, 2, 3])
assert cyrt.gc_num_roots() == r0 + 2
succ = raw(lst).successors
assert len(succ) == 2
assert cyrt.gc_num_roots() == r0 + 4
del succ
assert cyrt.gc_num_roots() == r0 + 2
del e, lst
gc.collect()
assert cyrt.gc_num_roots() == r0, (r0, cyrt.gc_num_roots())
assert cyrt.gc_root_count(None) == 0
''')

  @cytest.skipIfGcStress('the collector runs whatever the threshold says')
  @cytest.skipUnlessGcBackend(
      'wdgc', 'the threshold policy of the block heap'
    )
  def test_short_lived_nodes_complete_under_1GiB(self):
    '''
    A walk over list cells allocates about 24 short-lived nodes per cell,
    about 1.6 GB for three million cells in the block heap.  With the
    collector off (the old threshold of one billion nodes), the child runs
    out of memory under a 1 GiB cap.  With the default threshold a walk
    over a million cells completes under the cap.
    '''
    self.run_child('''
cyrt.gc_set_threshold(10 ** 9)
try:
  next(curry.eval(M.walk, 3000000))
except MemoryError:
  os._exit(42)
os._exit(1)
''', address_space=1 << 30, status=42)
    proc = self.run_child('''
assert curry.topython(next(curry.eval(M.walk, 1000000))) == 1000000
print('collections', cyrt.gc_collections(), 'seconds', cyrt.gc_seconds())
assert cyrt.gc_collections() > 0
''', address_space=1 << 30)
    self.assertIn('collections', proc.stdout)

  def test_nested_evaluation_collects(self):
    '''
    The same walk inside a set function runs in a nested evaluation.  A
    collection there reclaims the nodes allocated since the nested
    evaluation began.
    '''
    self.run_child('''
assert curry.topython(next(curry.eval(M.inner, 1000000))) == [1000000]
assert cyrt.gc_collections() > 0
assert cyrt.gc_eval_depth() == 0
''', address_space=1 << 30)

  def test_set_function_queue_is_a_root(self):
    '''
    The alternatives a lazy set function has not produced yet wait in a
    queue that only the SetEval node reaches.  Collections between two
    values must keep them.
    '''
    self.run_child('''
cyrt.gc_set_threshold(1 << 14)
assert curry.topython(next(curry.eval(M.spaced, 20000))) == 60006
assert cyrt.gc_collections() > 10
''')

  def test_callback_evaluation(self):
    '''
    A Python iterator feeds a Curry list.  Its items come from evaluations
    that run inside a step of the enclosing evaluation; the collector runs
    there as a nested collection.  gc_collect refuses to run inside the
    callback, because the steps of the enclosing evaluation are on the C
    stack.
    '''
    self.run_child('''
cyrt.gc_set_threshold(1 << 14)
depths = []
def items():
  for i in range(3):
    depths.append(cyrt.gc_eval_depth())
    yield curry.topython(next(curry.eval(M.walk, 50000))) + i
assert curry.topython(next(curry.eval(M.lastOf, iter(items())))) == 50002
assert depths == [1, 1, 1], depths
assert cyrt.gc_collections() > 0
def refuse():
  try:
    cyrt.gc_collect()
  except RuntimeError as err:
    raise ValueError('refused: %s' % err)
  yield 1
try:
  next(curry.eval(M.lastOf, iter(refuse())))
except ValueError as err:
  assert 'refused' in str(err), err
else:
  assert False, 'gc_collect ran inside a callback'
assert cyrt.gc_eval_depth() == 0
''')

  @cytest.skipIfGcStress('a test of the threshold policy; 3000 pairs live')
  @cytest.skipUnlessGcBackend(
      'wdgc', 'the threshold policy of the block heap'
    )
  def test_threshold_follows_the_survivors(self):
    '''
    After a collection the threshold is eight times the survivors, but not
    less than the configured value (GC_GROWTH in wdgc.cpp).  So the heap
    stays within eight times the live nodes, and the threshold falls back
    to the configured value when the live nodes go.
    '''
    self.run_child('''
floor = 1 << 14
cyrt.gc_set_threshold(floor)
value = next(curry.eval(M.table, 3000))
cyrt.gc_collect()
live = cyrt.gc_node_count()
assert live > floor, live
assert cyrt.gc_threshold() == 8 * live, (cyrt.gc_threshold(), live)
del value
gc.collect()
cyrt.gc_collect()
assert 8 * cyrt.gc_node_count() < floor, cyrt.gc_node_count()
assert cyrt.gc_threshold() == floor, cyrt.gc_threshold()
''')

  def test_stats_report_collections(self):
    '''
    curry.stats reports the collections of the process and their seconds,
    the steps of the evaluations, and the peak RSS.  The collections field
    follows gc_collections, and gc_seconds follows gc_seconds, before and
    after an evaluation that collects.
    '''
    proc = self.run_child('''
cyrt.gc_set_threshold(1 << 14)
before = curry.stats()
assert before['collections'] == cyrt.gc_collections(), before
assert curry.topython(next(curry.eval(M.walk, 100000))) == 100000
after = curry.stats()
collections = cyrt.gc_collections()
assert after['collections'] == collections, (after, collections)
assert after['collections'] > before['collections'] + 10, (before, after)
assert after['steps'] >= before['steps'] + 100000, (before, after)
assert after['forks'] == before['forks'], (before, after)
assert after['peak_rss'] >= before['peak_rss'] > 0, (before, after)
assert after['cpu'] > before['cpu'], (before, after)
assert after['gc_seconds'] > before['gc_seconds'] >= 0.0, (before, after)
assert after['gc_seconds'] == cyrt.gc_seconds(), (after, cyrt.gc_seconds())
print(after)
''')
    self.assertIn('collections', proc.stdout)

  @cytest.skipIfGcStress('a test of the growth policy; 3000 pairs live')
  @cytest.skipUnlessGcBackend(
      'wdgc', 'the threshold policy of the block heap'
    )
  def test_growth(self):
    '''
    SPRITE_GC_GROWTH sets the growth factor when the runtime loads: after a
    collection the threshold is that many times the survivors.  A bad value
    falls back to the default with a warning.
    '''
    code = '''
print('growth', cyrt.gc_growth())
cyrt.gc_set_threshold(1 << 14)
value = next(curry.eval(M.table, 3000))
cyrt.gc_collect()
live = cyrt.gc_node_count()
assert live > 1 << 14, live
print('threshold', cyrt.gc_threshold() // live)
'''
    with mock.patch.dict(os.environ, {'SPRITE_GC_GROWTH': '3'}):
      proc = self.run_child(code)
    self.assertEqual(proc.stdout.splitlines(), ['growth 3', 'threshold 3'])
    with mock.patch.dict(os.environ, {'SPRITE_GC_GROWTH': '1'}):
      proc = self.run_child(code)
    self.assertEqual(proc.stdout.splitlines(), ['growth 8', 'threshold 8'])
    self.assertIn('SPRITE_GC_GROWTH=1', proc.stderr)

  @cytest.skipUnlessGcBackend(
      'wdgc', 'the threshold policy of the block heap'
    )
  def test_threshold(self):
    '''
    SPRITE_GC_THRESHOLD sets the threshold when the runtime loads.  A bad
    value falls back to the default with a warning.  gc_set_threshold
    rejects zero.
    '''
    code = '''
print('threshold', cyrt.gc_threshold())
try:
  cyrt.gc_set_threshold(0)
except ValueError:
  print('zero rejected')
cyrt.gc_set_threshold(5000)
print('threshold', cyrt.gc_threshold())
print('depth', cyrt.gc_eval_depth()
     , 'reclaimed', type(cyrt.gc_collect()).__name__)
'''
    with mock.patch.dict(os.environ, {'SPRITE_GC_THRESHOLD': '12345'}):
      proc = self.run_child(code)
    self.assertEqual(
        proc.stdout.splitlines()
      , ['threshold 12345', 'zero rejected', 'threshold 5000'
        , 'depth 0 reclaimed int']
      )
    with mock.patch.dict(os.environ, {'SPRITE_GC_THRESHOLD': 'abc'}):
      proc = self.run_child(code)
    self.assertEqual(proc.stdout.splitlines()[0], 'threshold 1048576')
    self.assertIn('SPRITE_GC_THRESHOLD=abc', proc.stderr)


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
@cytest.skipUnlessGcBackend(
    'wdgc', 'the counts of queues and sets are exact for the block heap'
  )
class TestOwnership(ChildTests):
  '''
  The ownership of configurations, queues, and sets (src/cyrt/state/queue.hpp
  and gc/wdgc.cpp).  A queue owns its configurations, so a fork and a drop
  free them at once; the queue and the set of a set function go when no
  SetEval node reaches them; and the counters of the bindings report what is
  alive.
  '''

  # Reads the counters and checks their relations: the live configurations
  # are those in the queues (a configuration shared by two queues after a
  # split counts in both), and a queue of a set function has a set.
  COUNTS = '''
def counts():
  lengths = cyrt.gc_queue_lengths()
  configurations = cyrt.gc_configuration_count()
  assert len(lengths) == cyrt.gc_queue_count(), (lengths, cyrt.gc_queue_count())
  assert configurations <= sum(lengths), (configurations, lengths)
  return configurations, cyrt.gc_queue_count(), cyrt.gc_set_count()

def settled():
  # Nothing of an evaluation survives its runtime state and a collection.
  gc.collect()
  cyrt.gc_collect()
  return counts()
'''

  def test_fork_and_drop_free_configurations(self):
    '''
    A sort by permutation forks once per element inserted and drops every
    unsorted prefix.  The parent of a fork and a dropped configuration are
    freed at once, so the live count follows the queue, and nothing is left
    when the evaluation ends.
    '''
    proc = self.run_child(self.COUNTS + '''
base = settled()
assert base == (0, 0, 0), base
values = list(curry.eval(M.psort, 7))
assert curry.topython(values[0]) == list(range(1, 8)), values
assert len(values) == 1, values
assert settled() == (0, 0, 0), counts()
stats = curry.stats()
assert stats['forks'] > 100, stats
print('forks', stats['forks'])
''')
    self.assertIn('forks', proc.stdout)

  def test_set_function_queues_are_freed(self):
    '''
    A set function consumed only in part leaves its queue, with the
    alternatives not produced yet, to the collector.  The items come from a
    Python iterator, which reads the counters between them: the queues and
    the configurations of finished set functions go at each collection, so
    the counts stay far below the number of set functions run.
    '''
    proc = self.run_child(self.COUNTS + '''
cyrt.gc_set_threshold(1 << 14)
seen = []
def items(n):
  for i in range(n):
    seen.append(counts())
    yield i
n0 = cyrt.gc_collections()
assert curry.topython(next(curry.eval(M.partial, 3, iter(items(2000))))) == 2000
collections = cyrt.gc_collections() - n0
assert collections > 0, collections
peak_queues = max(q for c, q, s in seen)
peak_sets = max(s for c, q, s in seen)
peak_configurations = max(c for c, q, s in seen)
# Each item leaves 7 configurations in a queue with a set of its own.
assert peak_queues < 2000, peak_queues
assert peak_sets < 2000, peak_sets
assert peak_configurations < 7 * 2000, peak_configurations
assert settled() == (0, 0, 0), counts()
print('collections', collections
     , 'peak', peak_configurations, peak_queues, peak_sets)
''')
    self.assertIn('collections', proc.stdout)

  def test_configurations_request_a_collection(self):
    '''
    The configurations alive request a collection when they reach one
    eighth of the node threshold.  A wide choice tree inside a set function
    consumed only in part leaves 63 configurations per item and allocates
    few nodes, so without this rule the dead queues would pile up until the
    nodes reached the threshold.
    '''
    proc = self.run_child(self.COUNTS + '''
cyrt.gc_set_threshold(1 << 16)
seen = []
def items(n):
  for i in range(n):
    seen.append(counts() + (cyrt.gc_node_count(),))
    yield i
n0 = cyrt.gc_collections()
assert curry.topython(next(curry.eval(M.partial, 6, iter(items(600))))) == 600
collections = cyrt.gc_collections() - n0
peak_configurations = max(c for c, q, s, n in seen)
peak_nodes = max(n for c, q, s, n in seen)
assert collections > 0, collections
# The configuration threshold is 8192.  Without the rule the first
# collection would come at 65536 nodes, with many more configurations.
assert peak_configurations < 3 * 8192, peak_configurations
print('collections', collections, 'peak', peak_configurations, peak_nodes)
''')
    self.assertIn('collections', proc.stdout)

  def test_nested_set_functions_settle(self):
    '''
    The queens of a small board through nested set functions: the outer set
    function forks on the permutation, each permutation runs a set function
    of its own, and most of them are consumed only in part.  The values are
    right, and nothing is left afterwards.
    '''
    self.run_child(self.COUNTS + '''
cyrt.gc_set_threshold(1 << 14)
assert curry.topython(next(curry.eval(M.countQueens, 5))) == 10
assert cyrt.gc_eval_depth() == 0
assert settled() == (0, 0, 0), counts()
''')

  def test_error_in_a_set_function(self):
    '''
    An error inside a set function leaves the nested evaluation.  The queue
    of the set function comes off the stack of queues on the way out, so the
    state is consistent afterwards: the depth is zero, a collection runs,
    and nothing is left once the evaluation is dropped.
    '''
    self.run_child(self.COUNTS + '''
try:
  next(curry.eval(M.boomSet))
except curry.exceptions.EvaluationError as err:
  assert 'boom' in str(err), err
else:
  assert False, 'no error'
assert cyrt.gc_eval_depth() == 0
assert settled() == (0, 0, 0), counts()
assert curry.topython(next(curry.eval(M.psort, 4))) == [1, 2, 3, 4]
assert settled() == (0, 0, 0), counts()
''')

  def test_escaped_choice_splits_the_queue(self):
    '''
    A choice of the argument escapes a set function while its queue holds
    two configurations.  Both queues of the split hold the configurations
    that have not made the choice, and each queue clones one before it
    steps it, so neither sees the steps of the other.  The two sets are
    {1,2} and {2,3}.
    '''
    self.run_child(self.COUNTS + '''
values = sorted(curry.topython(v) for v in curry.eval(M.escaped))
assert values == [[1, 2], [2, 3]], values
assert settled() == (0, 0, 0), counts()
''')


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
@cytest.skipUnlessGcBackend(
    'wdgc', 'the counts of queues and sets are exact for the block heap'
  )
class TestStress(ChildTests):
  '''
  The stress mode of the collector: with SPRITE_GC_STRESS=1 the collector
  runs at every safepoint of the scheduler, after every rewrite step (see
  gc/wdgc.cpp).  The children run with the variable set, whatever the
  environment of the test process says, and one child runs without it for
  comparison.
  '''

  def run_stress_child(self, code, **kwds):
    with mock.patch.dict(os.environ, {'SPRITE_GC_STRESS': '1'}):
      return self.run_child(code, **kwds)

  def test_collects_at_every_step(self):
    '''
    The collections of an evaluation in stress mode are at least its rewrite
    steps, the values are right, curry.stats reports the collections, and
    nothing is left afterwards.
    '''
    proc = self.run_stress_child(TestOwnership.COUNTS + '''
assert cyrt.gc_stress()
table = [(i, str(i)) for i in range(1, 51)]
for goal, args, expected in [
    (M.walk, (2000,), 2000), (M.table, (50,), table), (M.spaced, (50,), 156)
  ]:
  before = curry.stats()
  value = curry.topython(next(curry.eval(goal, *args)))
  after = curry.stats()
  assert value == expected, (value, expected)
  steps = after['steps'] - before['steps']
  collections = after['collections'] - before['collections']
  assert collections == cyrt.gc_collections() - before['collections']
  assert steps > 100, steps
  assert collections >= steps, (collections, steps)
  print(goal.name, 'steps', steps, 'collections', collections)
assert settled() == (0, 0, 0), counts()
''')
    self.assertIn('walk steps', proc.stdout)

  def test_same_values_and_steps_as_without(self):
    '''
    Forks, free variables, constraints, set functions (nested schedulers,
    which hand the request outward), a split queue, and an error inside a
    set function give the same values, in the same order and with the same
    step counts, with and without the stress mode: a collection changes
    nothing in the schedule.  Two defects of the runtime showed up here as
    false suspensions: hnf_or_free left the residual of its probe of a free
    variable behind (fairscheme.cpp), and applygnf reported the free
    variables of an interrupted normalization, or of a constraint lifted to
    the root, as residuals (apply.cpp).
    '''
    code = TestOwnership.COUNTS + '''
results = []
for goal, args in [
    (M.psort, (5,)), (M.escaped, ()), (M.countQueens, (4,)), (M.queens, (4,))
  , (M.partial, (3, [1, 2, 3, 4])), (M.groundOwn, ())
  ]:
  before = curry.stats()
  values = [curry.topython(v) for v in curry.eval(goal, *args)]
  results.append((values, curry.stats()['steps'] - before['steps']))
try:
  next(curry.eval(M.boomSet))
except curry.exceptions.EvaluationError as err:
  assert 'boom' in str(err), err
else:
  assert False, 'no error'
assert cyrt.gc_eval_depth() == 0
assert settled() == (0, 0, 0), counts()
print(results)
'''
    stressed = self.run_stress_child(code)
    with mock.patch.dict(os.environ, {'SPRITE_GC_STRESS': '0'}):
      plain = self.run_child(code)
    self.assertEqual(stressed.stdout, plain.stdout)
    results = ast.literal_eval(stressed.stdout)
    self.assertEqual(
        [values for values, steps in results]
      , [ [[1, 2, 3, 4, 5]], [[1, 2], [2, 3]], [2], [[3, 1, 4, 2], [2, 4, 1, 3]]
        , [4], [1]
        ]
      )
    self.assertTrue(all(steps > 0 for values, steps in results), results)

  def test_nested_callback_evaluation(self):
    '''
    An evaluation started from a Python callback runs nested and collects
    there, with the older nodes as roots, at every step.
    '''
    self.run_stress_child('''
depths = []
def items():
  for i in range(3):
    depths.append(cyrt.gc_eval_depth())
    yield curry.topython(next(curry.eval(M.walk, 500))) + i
assert curry.topython(next(curry.eval(M.lastOf, iter(items())))) == 502
assert depths == [1, 1, 1], depths
assert cyrt.gc_eval_depth() == 0
''')

  def test_off_unless_asked(self):
    '''
    Without the variable, or with the value 0, the mode is off and an
    evaluation below the threshold runs no collection.  Another value turns
    the mode off with a warning.
    '''
    code = '''
print('stress', cyrt.gc_stress())
before = cyrt.gc_collections()
assert curry.topython(next(curry.eval(M.walk, 1000))) == 1000
print('collections', cyrt.gc_collections() - before)
'''
    expected = ['stress False', 'collections 0']
    environment = {
        key: value for key, value in os.environ.items()
        if key != 'SPRITE_GC_STRESS'
      }
    with mock.patch.dict(os.environ, environment, clear=True):
      proc = self.run_child(code)
    self.assertEqual(proc.stdout.splitlines(), expected)
    with mock.patch.dict(os.environ, {'SPRITE_GC_STRESS': '0'}):
      proc = self.run_child(code)
    self.assertEqual(proc.stdout.splitlines(), expected)
    with mock.patch.dict(os.environ, {'SPRITE_GC_STRESS': 'yes'}):
      proc = self.run_child(code)
    self.assertEqual(proc.stdout.splitlines(), expected)
    self.assertIn('SPRITE_GC_STRESS=yes', proc.stderr)


class TestSplitValues(cytest.TestCase):
  '''The values of the split of a set function's queue, on both backends.'''

  def test_escaped_choice(self):
    M = curry.import_('CxxGc')
    values = sorted(curry.topython(v) for v in curry.eval(M.escaped))
    self.assertEqual(values, [[1, 2], [2, 3]])
