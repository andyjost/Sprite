'''Tests for the counters of the collector of the C++ backend.'''
import cytest # from ./lib; must be first
from curry.interpreter import stats as statsmod
import curry, os, re, unittest
from unittest import mock

# The counters of a collection, in the order the bindings report them.
COUNTERS = (
    'roots_seconds', 'trace_seconds', 'sweep_seconds', 'registries_seconds'
  , 'marked', 'marked_old', 'marked_young', 'configurations_pushed'
  , 'queues_destroyed', 'configurations_destroyed', 'old_redexes'
  , 'old_slot_writes', 'old_nodes_written', 'old_blocks'
  )
PHASES = COUNTERS[:4]


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
@cytest.skipUnlessGcBackend(
    'wdgc', 'the counters belong to the collector of the block heap'
  )
class TestCounters(cytest.TestCase):
  '''
  The counters of the collector (src/cyrt/graph/gc/wdgc.cpp): the seconds
  of the phases of a collection, the nodes marked by age, the configurations
  pushed as roots, the queues and the configurations destroyed, and the
  writes into old nodes.  Every test but the one of the toolchain flags runs
  a child under prlimit and timeout, as unit_cxx_gc.py does, with the test
  module data/curry/CxxGc.curry.  The values of the write counters are
  checked on a runtime built with them (make GC_WRITE_COUNTERS=1; see
  tests/README, section 4); the default build checks that they are zero.
  '''
  TIMEOUT = 120

  PREAMBLE = '''
import curry, gc, os, sys
from curry.backends.cxx import cyrtbindings as cyrt
curry.reload({'backend': 'cxx'})
M = curry.import_('CxxGc')
COUNTERS = %r
PHASES = COUNTERS[:4]

def consistent(c):
  """Checks the relations within one record of counters and returns it."""
  assert tuple(c) == COUNTERS, tuple(c)
  for key in COUNTERS:
    assert c[key] >= 0, (key, c)
  assert c['marked'] == c['marked_old'] + c['marked_young'], c
  # A block touched by a write holds a written node; a written node took at
  # least one write.
  assert c['old_blocks'] <= c['old_nodes_written'], c
  assert c['old_nodes_written'] <= c['old_redexes'] + c['old_slot_writes'], c
  return c

def delta(after, before):
  return {key: after[key] - before[key] for key in COUNTERS}

def settle():
  gc.collect()
  cyrt.gc_collect()
''' % (COUNTERS,)

  @classmethod
  def setUpClass(cls):
    # Compile the module here.  The children inherit the address-space cap,
    # and the processes of the Curry compiler do not fit under it.
    curry.import_('CxxGc')

  def run_child(self, code, address_space=2 << 30, status=0, env=None):
    with mock.patch.dict(os.environ, env or {}):
      proc = cytest.run_in_subprocess(
          self.PREAMBLE + code, self.TIMEOUT, address_space=address_space
        )
    self.assertEqual(
        proc.returncode, status
      , 'the child ended with status %s; stdout:\n%s\nstderr:\n%s'
            % (proc.returncode, proc.stdout, proc.stderr)
      )
    return proc

  def test_toolchain_flags(self):
    '''
    The installation names the setting of the write counters, a module is
    compiled with their macro when the installed runtime has them, and the
    ABI stamp tells the two builds apart, so a switch compiles the modules
    again.  The Memory Pool System never gets the flag.
    '''
    from curry import config
    from curry.backends.cxx import cyrtbindings as cyrt, toolchain
    enabled = cyrt.gc_write_counters_enabled()
    self.assertIsInstance(enabled, bool)
    self.assertEqual(config.cxx_gc_write_counters(), enabled)
    self.assertEqual(toolchain.gc_flags('wdgc', write_counters=False), [])
    self.assertEqual(
        toolchain.gc_flags('wdgc', write_counters=True)
      , ['-DSPRITE_GC_WRITE_COUNTERS']
      )
    self.assertEqual(
        toolchain.gc_flags('mps', write_counters=True), ['-DSPRITE_GC_MPS']
      )
    self.assertEqual(toolchain.gc_flags(), toolchain.gc_flags('wdgc', enabled))
    self.assertEqual(
        toolchain.object_digest()
      , toolchain.object_digest(write_counters=enabled)
      )
    self.assertNotEqual(
        toolchain.object_digest(write_counters=False)
      , toolchain.object_digest(write_counters=True)
      )

  def test_keys(self):
    '''
    The bindings, curry.stats, and stats.GC_COUNTERS name the same counters
    in the same order, and the sums of the stats are those of the bindings.
    '''
    self.assertEqual(statsmod.GC_COUNTERS, COUNTERS)
    self.assertEqual(statsmod.GC_KEYS, tuple('gc_' + key for key in COUNTERS))
    self.run_child('''
consistent(cyrt.gc_counters())
consistent(cyrt.gc_last_collection())
cyrt.gc_set_threshold(1 << 14)
assert curry.topython(next(curry.eval(M.walk, 20000))) == 20000
stats = curry.stats()
totals = consistent(cyrt.gc_counters())
for key in COUNTERS:
  assert stats['gc_' + key] == totals[key], (key, stats, totals)
line = str(stats)
assert ' gc_marked=%d ' % totals['marked'] in line, line
assert line.endswith(' gc_old_blocks=%d' % totals['old_blocks']) \\
    or ' gc_old_blocks=%d ' % totals['old_blocks'] in line, line
''')

  def test_phases_and_marks(self):
    '''
    An evaluation that collects adds to every phase, marks nodes, old and
    young, and pushes at least one configuration per collection.  The four
    phases sum to no more than the collector seconds.  The record of the
    last collection is one of those summed.
    '''
    self.run_child('''
cyrt.gc_set_threshold(1 << 14)
before = consistent(cyrt.gc_counters())
seconds0 = cyrt.gc_seconds()
n0 = cyrt.gc_collections()
assert curry.topython(next(curry.eval(M.walk, 100000))) == 100000
after = consistent(cyrt.gc_counters())
last = consistent(cyrt.gc_last_collection())
seconds = cyrt.gc_seconds() - seconds0
collections = cyrt.gc_collections() - n0
d = delta(after, before)
assert collections > 10, collections
assert d['marked'] >= collections, d
assert d['marked_young'] > 0, d
assert d['configurations_pushed'] >= collections, (d, collections)
for key in PHASES:
  assert d[key] >= 0.0, (key, d)
assert d['trace_seconds'] > 0.0, d
assert sum(d[key] for key in PHASES) <= seconds + 1e-3, (d, seconds)
for key in COUNTERS:
  assert last[key] <= after[key], (key, last, after)
assert last['marked'] > 0, last
print('collections', collections, 'marked', d['marked'], 'old', d['marked_old'])
''')

  def test_destroyed_counts_follow_abandoned_queues(self):
    '''
    A set function consumed only in part leaves its queue, with seven
    configurations, to the collector (see partial in CxxGc.curry).  Two
    thousand of them are destroyed by the collections, each with its
    configurations; the configurations a fork or a drop freed are not
    counted.
    '''
    self.run_child('''
cyrt.gc_set_threshold(1 << 14)
before = consistent(cyrt.gc_counters())
def items(n):
  for i in range(n):
    yield i
assert curry.topython(next(curry.eval(M.partial, 3, iter(items(2000))))) == 2000
settle()
after = consistent(cyrt.gc_counters())
d = delta(after, before)
assert d['queues_destroyed'] >= 2000, d
assert 6 * 2000 <= d['configurations_destroyed'] <= 8 * d['queues_destroyed'], d
assert cyrt.gc_queue_count() == 0, cyrt.gc_queue_count()
assert cyrt.gc_configuration_count() == 0, cyrt.gc_configuration_count()
print('destroyed', d['queues_destroyed'], d['configurations_destroyed'])
''')

  def test_old_bitmap_is_the_marks_of_the_last_collection(self):
    '''
    After a collection the old nodes are the nodes it marked, which are the
    nodes alive.  An allocation without a collection adds young nodes and
    no old one.  The next collection marks the value Python kept as old and
    the new value as young, and the verifier accepts the bitmaps.  The child
    runs without the stress mode, which would collect at every step.
    '''
    self.run_child('''
settle()
n0 = cyrt.gc_collections()
first = next(curry.eval(M.table, 300))
cyrt.gc_collect()
last = consistent(cyrt.gc_last_collection())
old = cyrt.gc_old_node_count()
assert old == last['marked'], (old, last)
assert old == cyrt.gc_node_count(), (old, cyrt.gc_node_count())
assert old >= 300, old
# Below the threshold: no collection, the old nodes stay as they are.
assert cyrt.gc_threshold() >= 1 << 20, cyrt.gc_threshold()
assert curry.topython(next(curry.eval(M.walk, 1000))) == 1000
assert cyrt.gc_collections() == n0 + 1, cyrt.gc_collections()
assert cyrt.gc_old_node_count() == old, (cyrt.gc_old_node_count(), old)
assert cyrt.gc_node_count() > old, (cyrt.gc_node_count(), old)
second = next(curry.eval(M.table, 100))
cyrt.gc_collect()
last = consistent(cyrt.gc_last_collection())
assert 300 <= last['marked_old'] <= old, (last, old)
assert last['marked_young'] >= 100, last
assert cyrt.gc_old_node_count() == last['marked'] == cyrt.gc_node_count(), (
    cyrt.gc_old_node_count(), last, cyrt.gc_node_count())
assert cyrt.gc_verify() is None
assert curry.topython(first)[-1] == (300, '300')
assert curry.topython(second)[-1] == (100, '100')
del first, second
settle()
assert cyrt.gc_old_node_count() == cyrt.gc_node_count()
''', env={'SPRITE_GC_STRESS': '0'})

  @cytest.skipIfGcStress('a collection per step over the live thunks is too slow')
  def test_writes_into_old_nodes(self):
    '''
    The thunks of CxxGc.thunks survive collections before they are stepped,
    so most of those steps write an old redex, in several blocks, when the
    runtime counts the writes (make GC_WRITE_COUNTERS=1); every thunk is a
    node of its own, so the distinct old nodes written are at least half of
    them and at most the writes.  The default build reports zeros.  The
    interval in progress joins the sums at the next collection.
    '''
    self.run_child('''
cyrt.gc_set_threshold(1 << 14)
before = consistent(cyrt.gc_counters())
n = 100000
assert curry.topython(next(curry.eval(M.thunks, n))) == n + sum(range(2, n + 2))
settle()
after = consistent(cyrt.gc_counters())
d = delta(after, before)
enabled = cyrt.gc_write_counters_enabled()
print('enabled', enabled, 'old redexes', d['old_redexes']
     , 'old slot writes', d['old_slot_writes'], 'old blocks', d['old_blocks'])
if enabled:
  assert d['old_redexes'] >= n // 2, d
  assert d['old_nodes_written'] >= n // 2, d
  assert d['old_blocks'] >= 2, d
  assert d['old_blocks'] <= d['old_nodes_written'], d
  assert d['old_nodes_written'] <= d['old_redexes'] + d['old_slot_writes'], d
else:
  assert d['old_redexes'] == d['old_slot_writes'] == 0, d
  assert d['old_nodes_written'] == d['old_blocks'] == 0, d
''')

  def test_report(self):
    '''
    SPRITE_GC_REPORT=1 prints one line per collection on stderr with the
    counters of the collection: consistent, and summed to the totals.  The
    value 0 prints nothing; another value prints a warning and nothing.  The
    children run without the stress mode, so the threshold paces the lines.
    '''
    code = '''
cyrt.gc_set_threshold(1 << 14)
n0 = cyrt.gc_collections()
before = consistent(cyrt.gc_counters())
assert curry.topython(next(curry.eval(M.walk, 50000))) == 50000
after = consistent(cyrt.gc_counters())
print('collections', cyrt.gc_collections() - n0)
print('marked', after['marked'] - before['marked'])
'''
    plain = {'SPRITE_GC_STRESS': '0'}
    proc = self.run_child(code, env=dict(plain, SPRITE_GC_REPORT='1'))
    collections = int(re.search(r'collections (\d+)', proc.stdout).group(1))
    marked = int(re.search(r'marked (\d+)', proc.stdout).group(1))
    lines = [line for line in proc.stderr.splitlines()
                  if line.startswith('gc collection=')]
    self.assertEqual(len(lines), collections)
    records = []
    for line in lines:
      fields = dict(item.split('=', 1) for item in line.split()[1:])
      record = {key: float(value) if '.' in value else int(value)
                for key, value in fields.items()}
      for key in COUNTERS + ('collection', 'nested', 'nodes', 'survivors'
                             , 'threshold', 'configurations', 'queues'
                             , 'sets', 'blocks', 'seconds'):
        self.assertIn(key, record, line)
      self.assertEqual(
          record['marked'], record['marked_old'] + record['marked_young'], line
        )
      self.assertLessEqual(record['survivors'], record['nodes'], line)
      self.assertEqual(record['nested'], 0, line)
      records.append(record)
    self.assertEqual(
        [record['collection'] for record in records]
      , list(range(records[0]['collection'], records[0]['collection'] + collections))
      )
    self.assertEqual(sum(record['marked'] for record in records), marked)
    proc = self.run_child(code, env=dict(plain, SPRITE_GC_REPORT='0'))
    self.assertNotIn('gc collection=', proc.stderr)
    proc = self.run_child(code, env=dict(plain, SPRITE_GC_REPORT='yes'))
    self.assertNotIn('gc collection=', proc.stderr)
    self.assertIn('SPRITE_GC_REPORT=yes', proc.stderr)

  def test_stress_mode(self):
    '''
    In stress mode every step collects and the verifier checks the heap,
    the bitmaps of every block included, after every mark phase.  The
    counters stay consistent over forks, set functions, and the thunks, and
    with the write counters nearly every step rewrites an old redex: the
    collection after the step before made it old, and each interval holds
    one step, so the old nodes written are about the old redexes.
    '''
    self.run_child('''
assert cyrt.gc_stress()
before = consistent(cyrt.gc_counters())
steps0 = curry.stats()['steps']
for goal, args, expected in [
    (M.walk, (2000,), 2000), (M.table, (30,), [(i, str(i)) for i in range(1, 31)])
  , (M.spaced, (50,), 156), (M.partial, (3, [1, 2, 3, 4]), 4)
  , (M.thunks, (300,), 300 + sum(range(2, 302)))
  ]:
  value = curry.topython(next(curry.eval(goal, *args)))
  assert value == expected, (goal.name, value, expected)
  consistent(cyrt.gc_counters())
  consistent(cyrt.gc_last_collection())
settle()
after = consistent(cyrt.gc_counters())
steps = curry.stats()['steps'] - steps0
d = delta(after, before)
assert d['marked_old'] > 0, d
assert d['queues_destroyed'] >= 4, d
if cyrt.gc_write_counters_enabled():
  assert d['old_redexes'] >= steps // 2, (d, steps)
  assert d['old_nodes_written'] >= steps // 2, (d, steps)
else:
  assert d['old_redexes'] == d['old_nodes_written'] == 0, d
assert cyrt.gc_verify() is None
assert cyrt.gc_old_node_count() == cyrt.gc_node_count()
print('steps', steps, 'old redexes', d['old_redexes'])
''', env={'SPRITE_GC_STRESS': '1'})

  def test_nested_collection(self):
    '''
    An evaluation started from a Python callback runs nested and collects
    there, at every step in stress mode, with the older blocks as roots.
    The counters stay consistent, the collections inside the callback
    count, and after the outer evaluation the old nodes are the marks of
    the last collection again.
    '''
    self.run_child('''
assert cyrt.gc_stress()
inside = []
def items():
  for i in range(3):
    n0 = cyrt.gc_collections()
    value = curry.topython(next(curry.eval(M.walk, 500)))
    inside.append(cyrt.gc_collections() - n0)
    consistent(cyrt.gc_counters())
    consistent(cyrt.gc_last_collection())
    yield value + i
before = consistent(cyrt.gc_counters())
assert curry.topython(next(curry.eval(M.lastOf, iter(items())))) == 502
after = consistent(cyrt.gc_counters())
assert all(n > 100 for n in inside), inside
assert after['marked'] > before['marked'], (before, after)
assert cyrt.gc_eval_depth() == 0
settle()
assert cyrt.gc_verify() is None
assert cyrt.gc_old_node_count() == cyrt.gc_node_count()
''', env={'SPRITE_GC_STRESS': '1'})
