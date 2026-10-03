'''Tests for the garbage collector of the C++ backend.'''
import cytest # from ./lib; must be first
import curry, os, unittest
from unittest import mock

@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestCxxGc(cytest.TestCase):
  '''
  The collector of the C++ backend (src/cyrt/graph/gc/wdgc.cpp).  The nodes
  Python holds are roots, the queue of a set function is a root, a nested
  evaluation collects, and a program that allocates many short-lived nodes
  completes under a 1 GiB address-space cap.  Every test runs a child under
  prlimit and timeout, because a missing root ends in a crash.  The programs
  are in data/curry/CxxGc.curry.
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
assert curry.topython(next(curry.eval(M.walk, 100000))) == 100000
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
assert after <= before - 2000, (before, after)
print('collections', collections, 'nodes', before, after)
''')
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

  def test_short_lived_nodes_complete_under_1GiB(self):
    '''
    A walk over a million list cells allocates about 1.5 GB of short-lived
    nodes.  With the collector off (the old threshold of one billion nodes),
    the child runs out of memory under a 1 GiB cap.  With the default
    threshold it completes.
    '''
    self.run_child('''
cyrt.gc_set_threshold(10 ** 9)
try:
  next(curry.eval(M.walk, 1000000))
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
print('depth', cyrt.gc_eval_depth(), 'reclaimed', type(cyrt.gc_collect()).__name__)
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
