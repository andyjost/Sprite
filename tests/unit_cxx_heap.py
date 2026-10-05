'''Tests for the block heap of the C++ runtime.'''
import cytest # from ./lib; must be first
from curry import config
import curry, os, re, shutil, subprocess, tempfile, unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 120
BLOCK_BYTES = 64 << 10
CHUNK_BYTES = 1 << 20


class ChildTests(cytest.TestCase):
  '''
  The base of the test classes below.  Every test runs a child under prlimit
  and timeout.  The children import the bindings and the test modules,
  data/curry/CxxHeap.curry and data/curry/CxxGc.curry.  No test of its own.
  '''
  PREAMBLE = '''
import curry, gc, os, sys
from curry.backends.cxx import cyrtbindings as cyrt
curry.reload({'backend': 'cxx'})
H = curry.import_('CxxHeap')
G = curry.import_('CxxGc')
BLOCK_BYTES = %d
CHUNK_BYTES = %d
''' % (BLOCK_BYTES, CHUNK_BYTES)

  @classmethod
  def setUpClass(cls):
    # Compile the modules here.  The children inherit the address-space
    # cap, and the processes of the Curry compiler do not fit under it.
    curry.import_('CxxHeap')
    curry.import_('CxxGc')

  def run_child(self, code, address_space=2 << 30, status=0):
    proc = cytest.run_in_subprocess(
        self.PREAMBLE + code, TIMEOUT, address_space=address_space
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
    'wdgc', 'the block heap'
  )
class TestHeap(ChildTests):
  '''
  The block heap (src/cyrt/graph/gc/blockheap.cpp) through the bindings:
  the counts, the memory it holds, the spans of large nodes, and the
  verifier.
  '''

  # The cells walked beside live data.  In stress mode every step marks the
  # live data, so the walks are shorter there.
  WALK = 5000 if cytest.GC_STRESS else 100000

  def test_counts_are_exact(self):
    '''
    The node count follows the allocations exactly, although the allocator
    counts runs of slots: an expression built from Python adds its nodes,
    and a collection after Python drops it takes them away again.  The heap
    holds whole chunks and spans.
    '''
    self.run_child('''
cyrt.gc_collect()
before = cyrt.gc_node_count()
a0 = cyrt.gc_allocation_count()
e = curry.expr([(1, 'a'), (2, 'b'), (3, 'c')])
made = cyrt.gc_allocation_count() - a0
assert made >= 6, made
assert cyrt.gc_node_count() == before + made \
    , (before, made, cyrt.gc_node_count())
cyrt.gc_collect()
assert cyrt.gc_node_count() == before + made \
    , (before, made, cyrt.gc_node_count())
assert str(e) == "[(1, 'a'), (2, 'b'), (3, 'c')]", str(e)
heap = cyrt.gc_heap_bytes()
assert heap >= CHUNK_BYTES and heap % BLOCK_BYTES == 0, heap
assert 0 < cyrt.gc_block_count() <= heap // BLOCK_BYTES, cyrt.gc_block_count()
del e
gc.collect()
reclaimed = cyrt.gc_collect()
assert reclaimed == made, (reclaimed, made)
assert cyrt.gc_node_count() == before, (before, cyrt.gc_node_count())
assert cyrt.gc_heap_bytes() == heap, (heap, cyrt.gc_heap_bytes())
assert cyrt.gc_verify() is None
''')

  @cytest.skipIfGcStress('a test of the threshold policy')
  def test_heap_stays_bounded(self):
    '''
    A walk over a million cells allocates about 24 million short-lived
    nodes.  The heap holds about one collection cycle of them and reuses
    its blocks: a second walk takes no new memory.
    '''
    proc = self.run_child('''
assert curry.topython(next(curry.eval(G.walk, 1000000))) == 1000000
heap = cyrt.gc_heap_bytes()
collections = cyrt.gc_collections()
assert collections > 10, collections
# The threshold is 2^20 nodes of at most 32 bytes in this program, plus
# the run in progress of each size class and the bitmaps.
assert heap <= 48 * CHUNK_BYTES, heap
assert curry.topython(next(curry.eval(G.walk, 1000000))) == 1000000
assert cyrt.gc_heap_bytes() == heap, (heap, cyrt.gc_heap_bytes())
cyrt.gc_collect()
print('heap_mb', heap / 2.0 ** 20, 'blocks', cyrt.gc_block_count()
     , 'collections', cyrt.gc_collections())
''', address_space=1 << 30)
    self.assertIn('heap_mb', proc.stdout)

  def test_large_nodes(self):
    '''
    A node larger than the largest size class lives in a span of its own.
    Such nodes are built, kept through collections, summed, and given back:
    the block count returns to what it was.
    '''
    self.run_child('''
cyrt.gc_set_threshold(1 << 14)
cyrt.gc_collect()
blocks = cyrt.gc_block_count()
sums = curry.topython(next(curry.eval(H.sums, 50)))
assert sums == [70 * i for i in range(1, 51)], sums
n0 = cyrt.gc_collections()
assert curry.topython(next(curry.eval(H.keepWhile, 50, %d))) == %d + 70 * 1275
assert cyrt.gc_collections() - n0 > 10, cyrt.gc_collections() - n0
value = next(curry.eval(H.keep, 30))
text = str(value)
assert text.count('Big') == 30, text
assert cyrt.gc_block_count() >= blocks + 30, (blocks, cyrt.gc_block_count())
cyrt.gc_collect()
assert cyrt.gc_block_count() >= blocks + 30, (blocks, cyrt.gc_block_count())
assert str(value) == text
assert cyrt.gc_verify() is None
del value
gc.collect()
cyrt.gc_collect()
assert cyrt.gc_block_count() < blocks + 30, (blocks, cyrt.gc_block_count())
''' % (self.WALK, self.WALK))

  def test_verifier_after_evaluations(self):
    '''
    The verifier finds nothing after evaluations that collect many times:
    a value held by Python, a walk, set functions consumed in part, and an
    evaluation nested in a Python callback.
    '''
    walk = self.WALK
    self.run_child('''
value = next(curry.eval(G.table, 300))
cyrt.gc_set_threshold(1 << 14)
assert curry.topython(next(curry.eval(G.walk, %d))) == %d
assert cyrt.gc_verify() is None
assert curry.topython(next(curry.eval(G.spaced, %d))) == %d
assert cyrt.gc_verify() is None
def items():
  for i in range(3):
    yield curry.topython(next(curry.eval(G.walk, %d))) + i
assert curry.topython(next(curry.eval(G.lastOf, iter(items())))) == %d
assert cyrt.gc_verify() is None
assert curry.topython(value) == [(i, str(i)) for i in range(1, 301)]
assert cyrt.gc_collections() > 20, cyrt.gc_collections()
''' % (walk, walk, walk // 50, 3 * (walk // 50) + 6, walk // 5, walk // 5 + 2))

  def test_verifier_runs_in_stress_mode(self):
    '''
    In the stress mode every collection runs the verifier; the values and
    the counts are as without it, and a request from Python finds nothing.
    '''
    with mock.patch.dict(os.environ, {'SPRITE_GC_STRESS': '1'}):
      self.run_child('''
assert cyrt.gc_stress()
table = curry.topython(next(curry.eval(G.table, 50)))
assert table == [(i, str(i)) for i in range(1, 51)], table
assert curry.topython(next(curry.eval(H.sums, 3))) == [70, 140, 210]
assert cyrt.gc_collections() > 100, cyrt.gc_collections()
assert cyrt.gc_verify() is None
''')

  def test_verify_refused_inside_an_evaluation(self):
    '''gc_verify runs between evaluations only, like gc_collect.'''
    self.run_child('''
def probe():
  try:
    cyrt.gc_verify()
  except RuntimeError as err:
    raise ValueError('refused: %s' % err)
  yield 1
try:
  next(curry.eval(G.lastOf, iter(probe())))
except ValueError as err:
  assert 'refused' in str(err), err
else:
  assert False, 'gc_verify ran inside a callback'
''')


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
@unittest.skipIf(shutil.which('objdump') is None, 'objdump is not installed')
@unittest.skipUnless(
    config.cxx_flavor() == 'release' and not curry.flags['debug']
  , 'the debug flavor compiles generated code without inlining'
  )
class TestInlineAllocation(cytest.TestCase):
  '''
  The allocation fast path is inline in generated code: the step of tak
  calls node_refill and neither node_reserve nor node_commit.  The release
  flavor alone inlines it (make DEBUG=1 compiles at -O0).
  '''
  BENCHMARKS = os.path.join(HERE, 'data', 'curry', 'benchmarks')

  def test_tak_allocates_inline(self):
    curry.import_('Tak1', currypath=[self.BENCHMARKS] + curry.path)
    base = os.path.join(
        self.BENCHMARKS, '.curry', config.intermediate_subdir(), 'Tak1'
      )
    self.assertTrue(os.path.exists(base + '.so'), base)
    proc = subprocess.run(
        ['objdump', '-d', '--no-show-raw-insn', base + '.so']
      , capture_output=True, text=True, check=True
      )
    refs = set()
    current = False
    for line in proc.stdout.splitlines():
      match = re.match(r'^[0-9a-f]+ <([^>]+)>:$', line)
      if match:
        current = match.group(1) == 'CyF4Tak13tak'
        continue
      if current:
        for match in re.finditer(r'<([^>@+]+)', line):
          refs.add(match.group(1))
    called = sorted(r for r in refs if 'node_' in r)
    self.assertEqual(called, ['_ZN4cyrt11node_refillEm'], refs)


@unittest.skipIf(config.cxx_tool() is None, 'no C++ compiler is installed')
@cytest.skipUnlessGcBackend(
    'wdgc', 'the block heap'
  )
class TestHeapProgram(cytest.TestCase):
  '''
  The heap through its C++ interface: data/cxx/heap_test.cpp, compiled
  against the installed runtime with its assertions on.
  '''
  def test_program(self):
    source = os.path.join(HERE, 'data', 'cxx', 'heap_test.cpp')
    libdir = config.installed_path('lib')
    tmpdir = tempfile.mkdtemp(prefix='sprite-heap-')
    try:
      exe = os.path.join(tmpdir, 'heap_test')
      cmd = [
          config.cxx_tool(), '-std=c++17', '-O2', '-Wall'
        , '-I%s' % config.installed_path('include')
        , source, '-o', exe
        , '-L%s' % libdir, '-lcyrt', '-Wl,-rpath,%s' % libdir
        ]
      proc = subprocess.run(cmd, capture_output=True, text=True)
      self.assertEqual(proc.returncode, 0, proc.stderr)
      self.assertEqual(proc.stderr, '', 'the compiler warned')
      proc = subprocess.run(
          ['timeout', str(TIMEOUT), exe], capture_output=True, text=True
        )
      self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
      self.assertEqual(proc.stdout, 'ok\n')
    finally:
      shutil.rmtree(tmpdir, ignore_errors=True)


class TestValues(cytest.TestCase):
  '''The programs of CxxHeap.curry give the same values on both backends.'''

  def test_values(self):
    H = curry.import_('CxxHeap')
    self.assertEqual(
        curry.topython(next(curry.eval(H.sums, 5))), [70, 140, 210, 280, 350]
      )
    self.assertEqual(
        curry.topython(next(curry.eval(H.keepWhile, 4, 100))), 100 + 700
      )
    self.assertEqual(str(next(curry.eval(H.keep, 1))).count('Big'), 1)
