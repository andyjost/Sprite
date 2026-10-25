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
import cytest, curry, gc, os, sys
from curry.backends.cxx import curryrtbindings as curryrt
curry.reset(**{'backend': 'cxx'})
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


@cytest.skipUnlessGcBackend(
    'wdgc', 'the block heap'
  )
class TestHeap(ChildTests):
  '''
  The block heap (src/curryrt/graph/gc/blockheap.cpp) through the bindings:
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
    self.run_child('''import cytest

curryrt.gc_collect()
before = curryrt.gc_node_count()
a0 = curryrt.gc_allocation_count()
e = cytest.raw.expr([(1, 'a'), (2, 'b'), (3, 'c')], typed=True)
made = curryrt.gc_allocation_count() - a0
assert made >= 6, made
assert curryrt.gc_node_count() == before + made     , (before, made, curryrt.gc_node_count())
curryrt.gc_collect()
assert curryrt.gc_node_count() == before + made     , (before, made, curryrt.gc_node_count())
assert str(e) == "[(1, 'a'), (2, 'b'), (3, 'c')]", str(e)
heap = curryrt.gc_heap_bytes()
assert heap >= CHUNK_BYTES and heap % BLOCK_BYTES == 0, heap
assert 0 < curryrt.gc_block_count() <= heap // BLOCK_BYTES, curryrt.gc_block_count()
del e
gc.collect()
reclaimed = curryrt.gc_collect()
assert reclaimed == made, (reclaimed, made)
assert curryrt.gc_node_count() == before, (before, curryrt.gc_node_count())
assert curryrt.gc_heap_bytes() == heap, (heap, curryrt.gc_heap_bytes())
assert curryrt.gc_verify() is None
''')

  @cytest.skipIfGcStress('a test of the threshold policy')
  def test_heap_stays_bounded(self):
    '''
    A walk over two million cells allocates about 14 million short-lived
    nodes (7 per cell; 24 before the optimizer inlined the comparison of
    enumFromTo).  The heap holds about one collection cycle of them and
    reuses its blocks: a second walk takes no new memory.
    '''
    proc = self.run_child('''import cytest

assert cytest.raw.interp().topython(next(curry.eval((G.walk)(2000000)))) == 2000000
heap = curryrt.gc_heap_bytes()
collections = curryrt.gc_collections()
assert collections > 10, collections
# The threshold is 2^20 nodes of at most 32 bytes in this program, plus
# the run in progress of each size class and the bitmaps.
assert heap <= 48 * CHUNK_BYTES, heap
assert cytest.raw.interp().topython(next(curry.eval((G.walk)(2000000)))) == 2000000
assert curryrt.gc_heap_bytes() == heap, (heap, curryrt.gc_heap_bytes())
curryrt.gc_collect()
print('heap_mb', heap / 2.0 ** 20, 'blocks', curryrt.gc_block_count()
     , 'collections', curryrt.gc_collections())
''', address_space=1 << 30)
    self.assertIn('heap_mb', proc.stdout)

  def test_large_nodes(self):
    '''
    A node larger than the largest size class lives in a span of its own.
    Such nodes are built, kept through collections, summed, and given back:
    the block count returns to what it was.
    '''
    self.run_child('''import cytest

curryrt.gc_set_threshold(1 << 14)
curryrt.gc_collect()
blocks = curryrt.gc_block_count()
sums = cytest.raw.interp().topython(next(curry.eval((H.sums)(50))))
assert sums == [70 * i for i in range(1, 51)], sums
n0 = curryrt.gc_collections()
assert cytest.raw.interp().topython(next(curry.eval((H.keepWhile)(50, %d)))) == %d + 70 * 1275
assert curryrt.gc_collections() - n0 > 10, curryrt.gc_collections() - n0
value = next(curry.eval((H.keep)(30)))
text = str(value)
assert text.count('Big') == 30, text
assert curryrt.gc_block_count() >= blocks + 30, (blocks, curryrt.gc_block_count())
curryrt.gc_collect()
assert curryrt.gc_block_count() >= blocks + 30, (blocks, curryrt.gc_block_count())
assert str(value) == text
assert curryrt.gc_verify() is None
del value
gc.collect()
curryrt.gc_collect()
assert curryrt.gc_block_count() < blocks + 30, (blocks, curryrt.gc_block_count())
''' % (self.WALK, self.WALK))

  def test_verifier_after_evaluations(self):
    '''
    The verifier finds nothing after evaluations that collect many times:
    a value held by Python, a walk, set functions consumed in part, and an
    evaluation nested in a Python callback.
    '''
    walk = self.WALK
    self.run_child('''import cytest

value = next(curry.eval((G.table)(300)))
curryrt.gc_set_threshold(1 << 14)
assert cytest.raw.interp().topython(next(curry.eval((G.walk)(%d)))) == %d
assert curryrt.gc_verify() is None
assert cytest.raw.interp().topython(next(curry.eval((G.spaced)(%d)))) == %d
assert curryrt.gc_verify() is None
def items():
  for i in range(3):
    yield cytest.raw.interp().topython(next(curry.eval((G.walk)(%d)))) + i
assert cytest.raw.interp().topython(next(curry.eval((G.lastOf)(iter(items()))))) == %d
assert curryrt.gc_verify() is None
assert cytest.raw.interp().topython(value) == [(i, str(i)) for i in range(1, 301)]
assert curryrt.gc_collections() > 20, curryrt.gc_collections()
''' % (walk, walk, walk // 50, 3 * (walk // 50) + 6, walk // 5, walk // 5 + 2))

  def test_verifier_runs_in_stress_mode(self):
    '''
    In the stress mode every collection runs the verifier; the values and
    the counts are as without it, and a request from Python finds nothing.
    '''
    with mock.patch.dict(os.environ, {'SPRITE_GC_STRESS': '1'}):
      self.run_child('''import cytest

assert curryrt.gc_stress()
table = cytest.raw.interp().topython(next(curry.eval((G.table)(50))))
assert table == [(i, str(i)) for i in range(1, 51)], table
assert cytest.raw.interp().topython(next(curry.eval((H.sums)(3)))) == [70, 140, 210]
assert curryrt.gc_collections() > 100, curryrt.gc_collections()
assert curryrt.gc_verify() is None
''')

  def test_verify_refused_inside_an_evaluation(self):
    '''gc_verify runs between evaluations only, like gc_collect.'''
    self.run_child('''
def probe():
  try:
    curryrt.gc_verify()
  except RuntimeError as err:
    raise ValueError('refused: %s' % err)
  yield 1
try:
  next(curry.eval((G.lastOf)(iter(probe()))))
except ValueError as err:
  assert 'refused' in str(err), err
else:
  assert False, 'gc_verify ran inside a callback'
''')


@unittest.skipIf(shutil.which('objdump') is None, 'objdump is not installed')
@unittest.skipUnless(
    config.cxx_flavor() == 'release' and not curry.flags['debug']
  , 'the debug flavor compiles generated code without inlining'
  )
@cytest.skipIfInterpreted('the tests read the compiled object of Tak1')
@cytest.linux_only(
    'reads the disassembly and the symbols of an ELF object with GNU objdump'
  )
class TestInlineAllocation(cytest.TestCase):
  '''
  The allocation fast path is inline in generated code: the step of tak
  calls node_refill and neither node_reserve nor node_commit.  The release
  flavor alone inlines it (make DEBUG=1 compiles at -O0).  Under
  interpret:new and interpret:all no object of Tak1 is made, so the tests
  skip there.
  '''
  BENCHMARKS = os.path.join(HERE, 'data', 'curry', 'benchmarks')

  def tak_disassembly(self):
    '''
    The disassembly of the compiled module Tak1.  The object must carry the
    stamp of the installed runtime: a test process never compiles a stale
    shared module (the prepare pass of the runner does).
    '''
    from curry.backends.cxx import toolchain
    curry.import_('Tak1', path=[self.BENCHMARKS] + curry.path)
    base = os.path.join(
        self.BENCHMARKS, '.curry', config.intermediate_subdir(), 'Tak1'
      )
    self.assertTrue(os.path.exists(base + '.so'), base)
    self.assertEqual(
        toolchain.Cpp2So.read_stamp(base + '.so'), toolchain.object_digest()
      , 'the object of Tak1 is stale; run the prepare pass'
      )
    proc = subprocess.run(
        ['objdump', '-d', '--no-show-raw-insn', base + '.so']
      , capture_output=True, text=True, check=True
      )
    return proc.stdout

  def test_tak_allocates_inline(self):
    refs = set()
    current = False
    for line in self.tak_disassembly().splitlines():
      match = re.match(r'^[0-9a-f]+ <([^>]+)>:$', line)
      if match:
        current = match.group(1) == 'CyF4Tak13tak'
        continue
      if current:
        for match in re.finditer(r'<([^>@+]+)', line):
          refs.add(match.group(1))
    called = sorted(r for r in refs if 'node_' in r)
    self.assertEqual(called, ['_ZN7curryrt11node_refillEm'], refs)

  def test_tak_indexes_inline(self):
    '''
    The indexer (Variable::skip, indexing.hxx) is inline in the module, and
    the counters of writes into old nodes leave no call in a module of the
    default build: without SPRITE_GC_WRITE_COUNTERS they are empty inline
    functions (memory.hpp).  A module of the instrumented build calls them.
    '''
    from curry.backends.cxx import curryrtbindings as curryrt
    symbols = set(re.findall(r'<([^>@+]+)', self.tak_disassembly()))
    hooks = sorted(s for s in symbols if 'gc_count' in s)
    if curryrt.gc_write_counters_enabled():
      self.assertTrue(hooks, symbols)
    else:
      self.assertEqual(hooks, [])
      self.assertEqual(sorted(s for s in symbols if 'Variable4skip' in s), [])


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
          config.cxx_tool(), '-std=c++17', '-O2', '-Wall', '-fno-strict-aliasing'
        , '-I%s' % config.installed_path('include')
        , source, '-o', exe
        , '-L%s' % libdir, '-lcurryrt', '-Wl,-rpath,%s' % libdir
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
        cytest.raw.interp().topython(next(curry.eval((H.sums)(5)))), [70, 140, 210, 280, 350]
      )
    self.assertEqual(
        cytest.raw.interp().topython(next(curry.eval((H.keepWhile)(4, 100)))), 100 + 700
      )
    self.assertEqual(str(next(curry.eval((H.keep)(1)))).count('Big'), 1)
