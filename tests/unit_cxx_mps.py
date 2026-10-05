'''
Tests for the Memory Pool System back end of the C++ runtime (make GC=mps;
src/cyrt/graph/gc/mps.cpp), and for the plumbing that selects a collector.
'''
import cytest # from ./lib; must be first
import curry, os, subprocess, sys, unittest
from curry import config

@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestCollectorSelection(cytest.TestCase):
  '''The installed collector is named consistently everywhere.'''

  def test_backend_name(self):
    from curry.backends.cxx import cyrtbindings as cyrt
    self.assertIn(cyrt.gc_backend(), config.CXX_GCS)
    self.assertEqual(cyrt.gc_backend(), config.cxx_gc())
    self.assertEqual(cyrt.gc_backend(), cytest.gc_backend())
    self.assertIsInstance(cyrt.gc_fault_count(), int)
    stats = cyrt.gc_backend_stats()
    self.assertIsInstance(stats, dict)
    if cyrt.gc_backend() == 'wdgc':
      self.assertEqual(stats, {})
      self.assertEqual(cyrt.gc_fault_count(), 0)
    else:
      for key in ['faults', 'fault_seconds', 'fill_seconds', 'collect_seconds'
                 , 'collections', 'starts', 'full_collections'
                 , 'committed_bytes', 'counting_faults', 'nursery_kb']:
        self.assertIn(key, stats)

  def test_toolchain_flags(self):
    '''
    A module is compiled with the macro of the installed collector, and the
    ABI stamp tells the collectors apart.
    '''
    from curry.backends.cxx import toolchain
    self.assertEqual(toolchain.gc_flags('wdgc'), [])
    self.assertEqual(toolchain.gc_flags('mps'), ['-DSPRITE_GC_MPS'])
    self.assertEqual(toolchain.gc_flags(), toolchain.gc_flags(config.cxx_gc()))
    self.assertEqual(
        toolchain.object_digest(), toolchain.object_digest(gc=config.cxx_gc())
      )
    self.assertNotEqual(
        toolchain.object_digest(gc='wdgc'), toolchain.object_digest(gc='mps')
      )


class ChildTests(cytest.TestCase):
  '''
  The base of the MPS tests.  Every test runs a child under prlimit and
  timeout, because a missing root ends in a crash.  The children import the
  bindings and the test modules CxxGc and CxxFreeVars.
  '''
  TIMEOUT = 120

  PREAMBLE = '''
import curry, gc, os, sys, weakref
from curry.backends.cxx import cyrtbindings as cyrt
curry.reload({'backend': 'cxx'})
G = curry.import_('CxxGc')
F = curry.import_('CxxFreeVars')
assert cyrt.gc_backend() == 'mps'
'''

  @classmethod
  def setUpClass(cls):
    # Compile the modules here.  The children inherit the address-space cap,
    # and the processes of the Curry compiler do not fit under it.
    curry.import_('CxxGc')
    curry.import_('CxxFreeVars')

  def run_child(self, code, address_space=2 << 30, status=0, env=None):
    cmd = ['prlimit', '--as=%d' % address_space, 'timeout', str(self.TIMEOUT)]
    cmd += [sys.executable, '-B', '-c', self.PREAMBLE + code]
    environment = dict(os.environ, PYTHONIOENCODING='utf-8')
    if env:
      environment.update(env)
    proc = subprocess.run(cmd, capture_output=True, text=True, env=environment)
    self.assertEqual(
        proc.returncode, status
      , 'the child ended with status %s; stdout:\n%s\nstderr:\n%s'
            % (proc.returncode, proc.stdout, proc.stderr)
      )
    return proc


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
@cytest.skipUnlessGcBackend('mps', 'the Memory Pool System back end')
class TestMps(ChildTests):
  '''
  The MPS back end through the bindings: the values of programs that collect
  many times, the nodes Python holds, the finalizers, the queues of set
  functions, the explicit collection, the fault counter, the stress mode,
  and the signal handler beside Python's faulthandler.
  '''

  def test_values_across_collections(self):
    '''
    Programs that allocate many times the nursery give their values, MPS
    collects on its own, and the heap walks (the in-place rewrites left
    consistent pad objects).
    '''
    proc = self.run_child('''
table = next(curry.eval(G.table, 300))
assert curry.topython(next(curry.eval(G.walk, 300000))) == 300000
assert curry.topython(next(curry.eval(G.psort, 7))) == list(range(1, 8))
assert curry.topython(next(curry.eval(G.countQueens, 6))) == 4
assert curry.topython(next(curry.eval(G.inner, 2000))) == [2000]
assert curry.topython(next(curry.eval(G.lastOf, iter(range(200))))) == 199
text = str(table)
assert text, 'the table lost its text'
collections = cyrt.gc_collections()
assert collections > 0, collections
nodes = cyrt.gc_node_count()
assert nodes > 0, nodes
print('collections', collections, 'nodes', nodes)
print('stats', sorted(cyrt.gc_backend_stats().items()))
''')
    self.assertIn('collections', proc.stdout)

  def test_python_node_is_pinned(self):
    '''
    A node Python holds keeps its address and its content across the
    collections of a long evaluation and an explicit collection.
    '''
    self.run_child('''
e = curry.raw_expr([1, 2, 3, [4, 5], 'ab'])
address = e.id()
text = repr(e)
assert curry.topython(next(curry.eval(G.walk, 300000))) == 300000
cyrt.gc_collect()
assert curry.topython(next(curry.eval(G.walk, 300000))) == 300000
assert e.id() == address, (e.id(), address)
assert repr(e) == text, (repr(e), text)
assert cyrt.gc_collections() > 0
''')

  def test_explicit_collection_reclaims(self):
    '''A value Python drops is reclaimed by gc_collect.'''
    self.run_child('''
table = next(curry.eval(G.table, 3000))
assert str(table), 'the table lost its text'
cyrt.gc_collect()
before = cyrt.gc_node_count()
assert before >= 6000, before
del table
gc.collect()
reclaimed = cyrt.gc_collect()
assert reclaimed >= 6000, reclaimed
after = cyrt.gc_node_count()
assert after < before, (after, before)
''')

  def test_generator_finalizer(self):
    '''
    The iterator of a generator node consumed in part is released by the
    collector; one consumed to the end by the step; one never evaluated is
    kept while Python holds the node.
    '''
    self.run_child('''
def gen(n):
  for i in range(n):
    yield i

g = gen(3)
ref = weakref.ref(g)
assert curry.topython(next(curry.eval(F.total, g))) == 3
del g
gc.collect()
assert ref() is None, 'an exhausted iterator was kept'

g = gen(100)
ref = weakref.ref(g)
assert curry.topython(next(curry.eval(F.firstTwo, g))) == [0, 1]
del g
gc.collect()
cyrt.gc_collect()
cyrt.gc_collect()
assert ref() is None, 'the iterator of a dead node was kept'

g = gen(5)
ref = weakref.ref(g)
e = curry.raw_expr(g)
del g
gc.collect()
cyrt.gc_collect()
assert ref() is not None, 'the iterator of a node Python holds was released'
del e
gc.collect()
cyrt.gc_collect()
cyrt.gc_collect()
assert ref() is None, 'the iterator was kept after the node was dropped'
''')

  def test_set_function_queue_is_freed(self):
    '''
    The queue of a set function is destroyed when its SetEval node dies: the
    node is finalized, and the count of queues returns to its baseline.
    '''
    self.run_child('''
assert curry.topython(next(curry.eval(G.inner, 10))) == [10]
cyrt.gc_collect()
cyrt.gc_collect()
baseline = cyrt.gc_queue_count()
assert curry.topython(next(curry.eval(G.inner, 3000))) == [3000]
assert curry.topython(next(curry.eval(G.psort, 6))) == list(range(1, 7))
grown = cyrt.gc_queue_count()
cyrt.gc_collect()
cyrt.gc_collect()
after = cyrt.gc_queue_count()
assert after <= baseline, (baseline, grown, after)
print('queues', baseline, grown, after)
''')

  def test_nested_evaluation(self):
    '''
    An evaluation nested in a Python callback collects inside the step of
    the enclosing one; the thread root keeps what the suspended step holds.
    '''
    self.run_child('''
def items():
  for i in range(3):
    yield curry.topython(next(curry.eval(G.walk, 100000))) + i
assert curry.topython(next(curry.eval(G.lastOf, iter(items())))) == 100002
assert cyrt.gc_collections() > 0
''')

  def test_threshold_runs_full_collections(self):
    '''
    SPRITE_GC_THRESHOLD, or gc_set_threshold, runs a full collection every
    so many nodes; the values hold across them.
    '''
    self.run_child('''
cyrt.gc_set_threshold(1 << 14)
assert cyrt.gc_threshold() == 1 << 14
table = next(curry.eval(G.table, 300))
assert curry.topython(next(curry.eval(G.walk, 50000))) == 50000
assert curry.topython(next(curry.eval(G.psort, 6))) == list(range(1, 7))
assert str(table), 'the table lost its text'
stats = cyrt.gc_backend_stats()
assert stats['full_collections'] >= 40, stats
print('full', stats['full_collections'])
''')

  def test_fault_counter(self):
    '''
    The fault counter sits on top of the MPS handler and counts the barrier
    faults; the statistics report them.
    '''
    proc = self.run_child('''
table = next(curry.eval(G.table, 300))
assert curry.topython(next(curry.eval(G.walk, 300000))) == 300000
assert curry.topython(next(curry.eval(G.psort, 7))) == list(range(1, 8))
stats = cyrt.gc_backend_stats()
assert stats['counting_faults'] == 1, stats
assert cyrt.gc_fault_count() == stats['faults'], stats
assert stats['fault_seconds'] >= 0 and stats['fill_seconds'] >= 0
print('faults', cyrt.gc_fault_count(), 'collections', stats['collections']
     , 'starts', stats['starts'])
''')
    self.assertIn('faults', proc.stdout)

  def test_stress_mode(self):
    '''A full collection at every safepoint keeps the values right.'''
    self.run_child('''
assert cyrt.gc_stress()
assert curry.topython(next(curry.eval(G.psort, 5))) == list(range(1, 6))
assert curry.topython(next(curry.eval(G.walk, 500))) == 500
assert curry.topython(next(curry.eval(G.inner, 50))) == [50]
stats = cyrt.gc_backend_stats()
assert stats['full_collections'] >= 500, stats
''', env={'SPRITE_GC_STRESS': '1'})

  def test_faulthandler_enabled_at_startup(self):
    '''
    With Python's faulthandler enabled at startup, the MPS handler is
    installed after it and takes the barrier faults; nothing is printed.
    '''
    proc = self.run_child('''
import faulthandler
assert faulthandler.is_enabled()
table = next(curry.eval(G.table, 300))
assert curry.topython(next(curry.eval(G.walk, 300000))) == 300000
assert curry.topython(next(curry.eval(G.psort, 7))) == list(range(1, 8))
print('faults', cyrt.gc_fault_count())
''', env={'PYTHONFAULTHANDLER': '1'})
    self.assertNotIn('Fatal Python error', proc.stderr)
    self.assertIn('faults', proc.stdout)

  def test_faulthandler_enabled_after_allocation(self):
    '''
    faulthandler.enable() after the first allocation puts Python's handler
    in front of the MPS handler.  The program still completes; this test
    records what Python prints on the first barrier fault.
    '''
    proc = self.run_child('''
import faulthandler
table = next(curry.eval(G.table, 300))
faulthandler.enable()
assert curry.topython(next(curry.eval(G.walk, 300000))) == 300000
assert curry.topython(next(curry.eval(G.psort, 8))) == list(range(1, 9))
assert curry.topython(next(curry.eval(G.countQueens, 7))) == 40
print('faults', cyrt.gc_fault_count(), 'enabled', faulthandler.is_enabled())
''')
    self.assertIn('faults', proc.stdout)
    # The observation, for the record of the spike.
    print(
        '\nfaulthandler after the first allocation: %s; stderr has %d bytes%s'
        % (proc.stdout.strip(), len(proc.stderr), ', a fatal-error report'
             if 'Fatal Python error' in proc.stderr else '')
      )
