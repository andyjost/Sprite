'''
Tests for the in-place rewrite of the C++ backend.

A step writes its result into the redex when the result fits the block of the
redex (Node::rewrite in cyrt/graph/node.hxx; vEmit_compileS_IReturn in
backends/cxx/compiler.py), as the Python backend does.  A larger result, a
pinned constructor, and a reference result keep the forward node; a reference
to a primitive value is copied (Node::forward_or_copy).  The periodic rotation
and the collection requests are checked after every completed step (procS),
no longer at the forward nodes.  The programs are in
data/curry/CxxRewrite.curry.
'''
import cytest # from ./lib; must be first
from curry import common, config
from curry.backends.generic.eval import evaluator
from curry.objects.handle import getHandle
import curry, os, shutil, subprocess, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))

# The cap on the address space of a child, in bytes, and the time it may
# take.  A child loads the compiled module from the cache (see setUpClass).
ADDRESS_SPACE = 2 << 30
TIMEOUT = 120

# A child on the C++ backend with the test module imported.
CHILD = '''
import curry
from curry.backends.cxx import cyrtbindings as cyrt
curry.reload({'backend': 'cxx', 'defaultconverter': 'topython'})
M = curry.import_('CxxRewrite')
'''

def step(expr, until=None, limit=64):
  '''
  One rewrite step at the root of a raw expression.  With ``until``, a
  predicate of the expression, steps are taken until it holds.  A step whose
  nested evaluation is interrupted (the collection request of the stress
  mode) leaves the root as it was, so one call is not always one completed
  step; the nested result is in the graph, and the next call goes further.
  '''
  for _ in range(limit):
    evaluator.single_step(curry.getInterpreter(), expr)
    if until is None or until(expr):
      return expr
  raise AssertionError('the root did not change in %d steps' % limit)

class TestValues(cytest.TestCase):
  '''The programs give the same values on both backends.'''
  def values(self, *goal):
    return list(curry.eval(*goal, converter='topython'))

  def test_values(self):
    M = curry.import_('CxxRewrite')
    self.assertEqual(self.values(M.walk, [1, 2, 3]), [0])
    self.assertEqual(self.values(M.first, [7, 8]), [7])
    self.assertEqual(self.values(M.pinned, 1), [True])
    self.assertEqual(self.values(M.lit, 1), [5])
    self.assertEqual(self.values(M.swap, 1, 2), [(2, 1)])
    self.assertEqual(self.values(M.rot, 1, 2, 3, curry.expr(M.nat, 4)), [2])
    self.assertEqual(self.values(M.applyTwice, 5), [7])
    self.assertEqual([str(v) for v in curry.eval(M.just, 1)], ['Just 1'])
    self.assertEqual([str(v) for v in curry.eval(M.three, 1)], ['Three 1 1 1'])
    self.assertEqual([str(v) for v in curry.eval(M.color, 1)], ['Red'])


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestRewrite(cytest.TestCase):
  '''
  One step of each program, taken at the root of a raw expression: the node
  is rewritten in place or forwarded, as the rule says.
  '''
  @classmethod
  def setUpClass(cls):
    cls.M = curry.import_('CxxRewrite')

  def test_tail_call(self):
    e = curry.raw_expr(self.M.walk, [1, 2, 3])
    step(e)
    self.assertEqual(e.info.tag, common.T_FUNC)
    self.assertEqual(e.info.name, 'walk')
    self.assertEqual(str(e), str(curry.raw_expr(self.M.walk, [2, 3])))

  def test_constructor(self):
    e = curry.raw_expr(self.M.just, 1)
    step(e)
    self.assertEqual(e.info.name, 'Just')
    self.assertEqual(str(e), 'Just 1')

  def test_larger_result_is_forwarded(self):
    e = curry.raw_expr(self.M.three, 1)
    step(e)
    self.assertEqual(e.info.tag, common.T_FWD)
    self.assertEqual(str(next(curry.eval(e))), 'Three 1 1 1')

  def test_pinned_result_is_forwarded(self):
    e = curry.raw_expr(self.M.pinned, 1)
    step(e)
    self.assertEqual(e.info.tag, common.T_FWD)
    self.assertEqual(str(next(curry.eval(e))), 'True')

  def test_nullary_constructor(self):
    e = curry.raw_expr(self.M.color, 1)
    step(e)
    self.assertEqual(e.info.name, 'Red')

  def test_literal(self):
    e = curry.raw_expr(self.M.lit, 1)
    step(e)
    self.assertEqual(e.info.name, 'Int')
    self.assertEqual(str(e), '5')

  def test_reference_to_primitive_is_copied(self):
    e = curry.raw_expr(self.M.first, [7, 8])
    step(e)
    self.assertEqual(e.info.name, 'Int')
    self.assertEqual(str(e), '7')

  def test_reference_to_expression_is_forwarded(self):
    e = curry.raw_expr(self.M.first, [curry.raw_expr(self.M.lit, 0)])
    step(e)
    self.assertEqual(e.info.tag, common.T_FWD)
    self.assertEqual(str(next(curry.eval(e))), '5')

  def test_swapped_arguments(self):
    # Both successors are read before the redex is written.
    e = curry.raw_expr(self.M.swap, 1, 2)
    step(e)
    self.assertEqual(e.info.name, '(,)')
    self.assertEqual(str(e), '(2, 1)')

  def test_rotated_arguments(self):
    e = curry.raw_expr(self.M.rot, 1, 2, 3, curry.raw_expr(self.M.nat, 4))
    step(e, until=lambda e: not str(e).startswith('rot 1 2 3 '))
    self.assertEqual(e.info.name, 'rot')
    self.assertRegex(str(e), r'^rot 2 3 1 ')

  def test_apply(self):
    # twice f x = f (f x) is rewritten to the application in place, and the
    # completed partial application is written into the application.
    e = curry.raw_expr(self.M.twice, curry.raw_expr(self.M.plusOne), 5)
    step(e)
    self.assertEqual(e.info.name, 'apply')
    step(e, until=lambda e: e.info.name != 'apply')
    self.assertEqual(e.info.name, 'plus')
    self.assertEqual(curry.topython(next(curry.eval(e))), 7)

  def test_tail_calls_allocate_nothing(self):
    '''
    A walk over a list by tail calls allocates no node per element.  Before
    the in-place rewrite every step allocated the next call.
    '''
    from curry.backends.cxx import cyrtbindings as cyrt
    xs = curry.raw_expr(list(range(100)))
    before = cyrt.gc_allocation_count()
    value = next(curry.eval(self.M.walk, xs, converter='topython'))
    allocated = cyrt.gc_allocation_count() - before
    self.assertEqual(value, 0)
    self.assertLess(allocated, 20)

  def test_rotation_without_forward_nodes(self):
    '''
    The periodic rotation runs on completed steps.  An endless loop of
    in-place steps leaves no forward node, and the alternative beside it
    still gets its turn.
    '''
    proc = cytest.run_in_subprocess(
        CHILD + 'print(next(curry.eval(M.fair)))\n', TIMEOUT
      , address_space=ADDRESS_SPACE
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout.strip(), '42')

  @cytest.skipIfGcStress('a collection runs at every step anyway')
  def test_collections_without_forward_nodes(self):
    '''
    A collection request is honoured on completed steps.  The loop of fair
    allocates two nodes per step and leaves no forward node; its sums stay
    live, so the threshold grows by the growth factor after each collection.
    '''
    proc = cytest.run_in_subprocess(
        CHILD + '''
cyrt.gc_set_threshold(1 << 10)
before = cyrt.gc_collections()
value = next(curry.eval(M.fair))
print(value, cyrt.gc_collections() - before)
''', TIMEOUT, address_space=ADDRESS_SPACE
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    value, collections = proc.stdout.split()
    self.assertEqual(value, '42')
    self.assertGreaterEqual(int(collections), 2)

  def test_generated_code(self):
    '''The generator applies the rule to each shape of result.'''
    shlib = getHandle(self.M).icurry.metadata['cxx.shlib']
    text = cytest.readfile(shlib.sofilename()[:-len('.so')] + '.cpp')
    self.assertRegex(
        text, r'return _0->rewrite\(&CyI10CxxRewrite4walk, _\d+\);'
      )
    self.assertRegex(text, r'return _0->rewrite\(&CyI7Prelude4Just, _\d+\);')
    self.assertRegex(
        text, r'_0->forward_to\(&CyI10CxxRewrite5Three, _\d+, _\d+, _\d+\);'
      )
    self.assertRegex(text, r'return _0->forward_or_copy\(_\d+\);')
    self.assertIn('_0->forward_to(&CyI7Prelude4True);\n', text)
    self.assertIn('return _0->rewrite(&CyI10CxxRewrite3Red);', text)
    self.assertIn('return _0->rewrite(&CyI7Prelude3Int, Arg(5));', text)
    self.assertNotIn('forward_or_copy(int_(', text)


@unittest.skipIf(config.cxx_tool() is None, 'no C++ compiler is installed')
class TestNodeRewrite(cytest.TestCase):
  '''
  Node::rewrite, Node::forward_or_copy, and Node::rewrite_from_partial on
  hand-built nodes.  The checks are a C++ program, data/cxx/rewrite_test.cpp,
  compiled against the installed runtime with its assertions on.
  '''
  def test_program(self):
    source = os.path.join(HERE, 'data', 'cxx', 'rewrite_test.cpp')
    libdir = config.installed_path('lib')
    tmpdir = tempfile.mkdtemp(prefix='sprite-rewrite-')
    try:
      exe = os.path.join(tmpdir, 'rewrite_test')
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
