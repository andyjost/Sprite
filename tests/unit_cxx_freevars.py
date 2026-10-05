'''
Tests for the free-variable table and the finalizers of the C++ backend.
'''
import cytest # from ./lib; must be first
import ast, curry, os, unittest
from unittest import mock

class ChildTests(cytest.TestCase):
  '''
  The base of the test classes below.  Every test runs a child under prlimit
  and timeout, because a missing root ends in a crash.  The children import
  the bindings and the test module, data/curry/CxxFreeVars.curry.  No test
  of its own.
  '''
  TIMEOUT = 300

  PREAMBLE = '''
import curry, gc, os, resource, sys, weakref
from curry.backends.cxx import cyrtbindings as cyrt
curry.reload({'backend': 'cxx'})
M = curry.import_('CxxFreeVars')
'''

  @classmethod
  def setUpClass(cls):
    # Compile the module here.  The children inherit the address-space cap,
    # and the processes of the Curry compiler do not fit under it.
    curry.import_('CxxFreeVars')

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
@cytest.skipUnlessGcBackend(
    'wdgc', 'the free-variable table is a strong root under MPS'
  )
class TestWeakTable(ChildTests):
  '''
  The free-variable table (InterpreterState::vtable, state/rts.hpp) is weak:
  the collector drops the entry of a variable no live configuration can ask
  for (gc/wdgc.cpp).  So a program that narrows many variables in sequence
  runs in bounded memory, and a variable a value handed to Python holds
  stays in the table while Python holds it.
  '''

  def test_million_narrowings_run_flat(self):
    '''
    A program that narrows a million variables in sequence runs under a
    1 GiB cap, and leaves as few nodes and table entries behind as one that
    narrows a hundred thousand.
    '''
    proc = self.run_child('''
def live(n):
  value = curry.topython(next(curry.eval(M.narrowMany, n)))
  assert value == n, (value, n)
  gc.collect()
  cyrt.gc_collect()
  return cyrt.gc_node_count(), cyrt.gc_freevar_count()
small = live(100000)
big = live(1000000)
assert big[0] <= small[0] + 100, (small, big)
assert big[1] <= 100, (small, big)
stats = curry.stats()
assert stats['collections'] > 10, stats
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
print('live', small, big, 'peak_rss_mb', peak
     , 'gc_seconds', stats['gc_seconds'])
''', address_space=1 << 30)
    self.assertIn('live', proc.stdout)

  def test_table_shrinks_at_a_collection(self):
    '''
    The table follows the collections: between two runs that narrow 5000
    variables each it holds the variables allocated since the last
    collection, not every variable of the process.
    '''
    proc = self.run_child('''
cyrt.gc_set_threshold(1 << 14)
seen = []
def items(n, k):
  for i in range(n):
    seen.append((cyrt.gc_freevar_count(), cyrt.gc_node_count()))
    yield k
value = curry.topython(next(curry.eval(M.narrowEach, iter(items(40, 5000)))))
assert value == 200000, value
peak = max(entries for entries, nodes in seen)
# The threshold is 16384 nodes, and a narrowing allocates several nodes
# per variable, so the table holds a few thousand entries at most.
assert peak < 16384, seen
assert cyrt.gc_collections() > 40, cyrt.gc_collections()
gc.collect()
cyrt.gc_collect()
assert cyrt.gc_freevar_count() == 0, cyrt.gc_freevar_count()
print('peak', peak)
''')
    self.assertIn('peak', proc.stdout)

  def test_shared_variable_in_a_value(self):
    '''
    A free variable in a value handed to Python is the node of the table,
    not a copy: both occurrences are one node, a copy of it is the node
    itself, the entry stays while Python holds the value, and an evaluation
    of the value narrows the one variable (2 and 4, not 2, 3, 3, 4).  Before
    the table was weak, that evaluation crashed in a new runtime state.
    '''
    self.run_child('''
value = next(curry.eval(M.pairFree))
a, b = value.successors
assert a.info.name == '_Free', repr(value)
assert a.id() == b.id(), repr(value)
assert a.copy().id() == a.id()
assert a.__deepcopy__().id() == a.id()
gc.collect()
cyrt.gc_collect()
assert cyrt.gc_freevar_count() == 1, cyrt.gc_freevar_count()
values = sorted(curry.topython(x) for x in curry.eval(M.both, value))
assert values == [2, 4], values
del value, a, b
gc.collect()
cyrt.gc_collect()
assert cyrt.gc_freevar_count() == 0, cyrt.gc_freevar_count()
''')

  def test_same_values_and_steps_in_stress_mode(self):
    '''
    In the stress mode of the collector a collection runs after every step,
    so a variable that no root names is dropped at once.  Narrowing, binding,
    and unification in sequence, a group whose root leaves the expression
    (groupRoot, wakeInGroup, triple), a configuration that wakes on a
    variable another one narrowed, and a functional pattern give the same
    values, in the same order and with the same steps, as without the mode.
    triple needs the root of its group after the expression dropped it: a
    table that lost the root narrows x and z apart.
    '''
    code = '''
results = []
for goal, args in [
    (M.narrowMany, (2000,)), (M.bindMany, (2000,)), (M.uniteMany, (300,))
  , (M.groupRoot, ()), (M.wakeByNarrowing, ()), (M.wakeInGroup, ())
  , (M.triple, ()), (M.lasts, (15,))
  ]:
  before = curry.stats()['steps']
  values = [repr(v) for v in curry.eval(goal, *args)]
  results.append((goal.name, values, curry.stats()['steps'] - before))
gc.collect()
cyrt.gc_collect()
results.append(('freevars', cyrt.gc_freevar_count()))
print(results)
'''
    with mock.patch.dict(os.environ, {'SPRITE_GC_STRESS': '1'}):
      stressed = self.run_child(code)
    with mock.patch.dict(os.environ, {'SPRITE_GC_STRESS': '0'}):
      plain = self.run_child(code)
    self.assertEqual(stressed.stdout, plain.stdout)
    results = dict(
        (item[0], item[1:]) for item in ast.literal_eval(plain.stdout)
      )
    self.assertEqual(results['narrowMany'][0], ['<Int 2000>'])
    self.assertEqual(results['bindMany'][0], ['<Int 2000>'])
    self.assertEqual(results['uniteMany'][0], ['<Int 300>'])
    self.assertRegex(results['groupRoot'][0][0], r'^<_Free \d+ <\(\)>>$')
    bits = ['<O>', '<I>', '<O>', '<I>']
    self.assertEqual(results['wakeByNarrowing'][0], bits)
    self.assertEqual(results['wakeInGroup'][0], bits)
    self.assertEqual(
        sorted(results['triple'][0])
      , ['<(,) <Int %d> <Int %d>>' % (i, i) for i in (1, 2, 3)]
      )
    self.assertEqual(len(results['lasts'][0]), 1)
    self.assertEqual(results['freevars'], (0,))
    self.assertTrue(all(
        steps > 0 for name, values, steps in ast.literal_eval(plain.stdout)[:-1]
      ))


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestNarrowing(ChildTests):
  '''
  The narrowing of a variable of a constructor type with fields
  (Node::create_flat in graph/node.cpp) makes one fresh variable per field.
  Every allocation may collect under the MPS back end, so the node is
  written before the first variable is made and each variable goes into its
  slot at once; a pointer kept outside the node would go stale when the
  collector moves its variable.  On every collector, the values are right
  across many collections and the verifier finds nothing.
  '''

  def test_list_variables_across_collections(self):
    '''
    The functional pattern of lastOf narrows a list variable once per cell;
    with a small threshold the collector runs many times during it.
    '''
    proc = self.run_child('''
cyrt.gc_set_threshold(1 << 13)
n0 = cyrt.gc_collections()
assert curry.topython(next(curry.eval(M.lasts, 60))) == list(range(1, 61))
collections = cyrt.gc_collections() - n0
assert collections > 10, collections
assert cyrt.gc_verify() is None
print('collections', collections)
''')
    self.assertIn('collections', proc.stdout)


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestFinalizers(ChildTests):
  '''
  A generator node owns a reference to its Python iterator (biGeneratorNode
  in builtins.hpp).  The step releases it when the iterator is exhausted,
  and the collector releases it when the node dies before that.  A copy of
  the node owns a reference of its own.
  '''

  def test_iterator_is_released(self):
    self.run_child('''
def gen(n):
  for i in range(n):
    yield i

# Consumed to the end: the step releases the iterator at the last item.
g = gen(3)
ref = weakref.ref(g)
assert curry.topython(next(curry.eval(M.total, g))) == 3
del g
gc.collect()
assert ref() is None, 'an exhausted iterator was kept'

# Consumed in part: the node of the rest dies with the evaluation, and the
# collector releases the iterator.  In stress mode a collection ran as soon
# as take dropped the rest, before the evaluation ended.
g = gen(100)
ref = weakref.ref(g)
assert curry.topython(next(curry.eval(M.firstTwo, g))) == [0, 1]
del g
gc.collect()
if not cyrt.gc_stress():
  assert ref() is not None, 'released before the node died'
cyrt.gc_collect()
assert ref() is None, 'the iterator of a dead node was kept'

# Never evaluated: the node Python holds keeps the iterator.
g = gen(5)
ref = weakref.ref(g)
e = curry.raw_expr(g)
del g
gc.collect()
cyrt.gc_collect()
assert ref() is not None, 'released while a node held it'
del e
gc.collect()
cyrt.gc_collect()
assert ref() is None, 'the iterator of a dropped node was kept'

# A copy of the node owns a reference of its own.
g = gen(5)
ref = weakref.ref(g)
e = curry.raw_expr(g)
c = e.copy()
d = e.__deepcopy__()
del g, e
gc.collect()
cyrt.gc_collect()
assert ref() is not None, 'released while a copy held it'
del c
gc.collect()
cyrt.gc_collect()
assert ref() is not None, 'released while a deep copy held it'
del d
gc.collect()
cyrt.gc_collect()
assert ref() is None, 'the iterator of the copies was kept'
print('released')
''')


class TestValues(cytest.TestCase):
  '''The values of the test programs, on both backends.'''

  def test_values(self):
    M = curry.import_('CxxFreeVars')
    self.assertEqual(curry.topython(next(curry.eval(M.narrowMany, 500))), 500)
    self.assertEqual(curry.topython(next(curry.eval(M.bindMany, 500))), 500)
    self.assertEqual(curry.topython(next(curry.eval(M.uniteMany, 100))), 100)
    self.assertEqual(
        sorted(curry.topython(v) for v in curry.eval(M.triple))
      , [(1, 1), (2, 2), (3, 3)]
      )
    self.assertEqual(
        sorted(str(v) for v in curry.eval(M.wakeByNarrowing))
      , ['I', 'I', 'O', 'O']
      )
    self.assertEqual(
        curry.topython(next(curry.eval(M.lasts, 10))), list(range(1, 11))
      )
