'''
Tests for the C-stack guard of the C++ backend and for deep value copies.

Covers a 2023 report by Michael Hanus: ``length [1..] ? 1 ? length [1..]``
crashed the C++ backend with a segmentation fault, because the Prelude's
``length`` nests one evaluation inside another for every list element.  The
backend now unwinds to the scheduler when an evaluation reaches the stack
limit, so the other alternatives run.  A long finite list, an audit finding,
overflowed the stack when the value was copied out of the graph.

A regression in the unwinding can make an evaluation spin or crash, and
SIGALRM does not interrupt the C++ scheduler.  So each test that evaluates at
the limit runs in a subprocess under the ``timeout`` command and under an
address-space cap (see cytest.run_in_subprocess).  The programs are in
data/curry/StackGuard.curry.
'''
import cytest # from ./lib; must be first
from curry.backends.generic.eval import evaluator
import curry, unittest

# The cap on the address space of a child, in bytes.  The C++ backend needs
# about 600 MB at load.  A program that allocates without bound then fails
# with MemoryError within seconds, before it troubles the machine.
ADDRESS_SPACE = 1 << 30

# Each child loads the compiled module from the cache (see setUpClass), so a
# healthy child ends within seconds.
TIMEOUT = 60

# Evaluates a goal on the C++ backend and prints one line per outcome: ``value
# V`` for each of the first ``count`` values, ``end`` when the values run out,
# and ``error MESSAGE`` when the evaluation stops with an EvaluationError.
# ``goal`` lists the arguments of curry.eval in terms of the module ``M``.
CHILD = '''
import curry
curry.reload({
    'backend': 'cxx', 'defaultconverter': 'topython', 'stack_limit': %(limit)r
  })
M = curry.import_('StackGuard')
values = curry.eval(%(goal)s)
try:
  for _ in range(%(count)d):
    print('value', next(values))
except StopIteration:
  print('end')
except curry.EvaluationError as exc:
  print('error', exc)
'''

# Evaluates a long list and prints its length and its last element.
CHILD_LONG_LIST = '''
import curry
curry.reload({'backend': 'cxx', 'defaultconverter': 'topython'})
M = curry.import_('StackGuard')
value, = curry.eval(M.longList, %(n)d)
print(len(value), value[-1])
'''

def run_child(testcase, code):
  '''Runs ``code`` in a child and returns its output lines.'''
  proc = cytest.run_in_subprocess(code, TIMEOUT, address_space=ADDRESS_SPACE)
  testcase.assertEqual(
      proc.returncode, 0
    , 'the child ended with status %s; stderr:\n%s'
          % (proc.returncode, proc.stderr)
    )
  return proc.stdout.splitlines()

@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'the stack guard belongs to the C++ backend'
  )
class TestStackGuard(cytest.TestCase):
  # 64 KiB is far below the nesting that ``length [1..5000]`` needs, so the
  # guard fires early and the tests run fast.
  LIMIT = 1 << 16
  N = 5000
  STACK_ERROR = r'^error stack limit of \d+ bytes exceeded'

  @classmethod
  def setUpClass(cls):
    # Compile the module once here.  The children then load it from the cache.
    curry.import_('StackGuard')

  def evaluate(self, goal, count=1, limit=LIMIT):
    code = CHILD % {'goal': goal, 'count': count, 'limit': limit}
    return run_child(self, code)

  def test_deep_evaluation_raises(self):
    lines = self.evaluate('M.deep, %d' % self.N)
    self.assertEqual(len(lines), 1, lines)
    self.assertRegex(lines[0], self.STACK_ERROR)

  def test_deep_alternative_does_not_starve_others(self):
    lines = self.evaluate('M.deepAlt, %d' % self.N, count=2)
    self.assertEqual(lines[0], 'value 1')
    self.assertRegex(lines[1], self.STACK_ERROR)

  def test_three_deep_alternatives_do_not_spin(self):
    '''
    Three alternatives that each reach the limit must end with an error.  The
    progress check is per configuration: a global step count moves while the
    other two run, so it does not show that this one is stuck.
    '''
    lines = self.evaluate('M.deepThree, %d' % self.N)
    self.assertEqual(len(lines), 1, lines)
    self.assertRegex(lines[0], self.STACK_ERROR)

  def test_stuck_alternative_keeps_finite_one(self):
    '''
    A deep alternative that is stuck at the limit is dropped, and its error
    waits.  The shallow alternative, which needs many steps, still produces
    its value.  The Python backend applies the same rule (unit_py_fairness).
    '''
    lines = self.evaluate('M.mixedAlt, %d, 200000' % self.N, count=2)
    self.assertEqual(lines[0], 'value 200000')
    self.assertRegex(lines[1], self.STACK_ERROR)

  def test_nested_queue_unwinds_to_enclosing_queue(self):
    '''
    An audit finding: a set function evaluates its argument in a nested work
    queue with its own scheduler, which consumed the unwind.  The enclosing
    queue never rotated, so the value 1 never arrived.  The unwind now goes
    to the nearest enclosing queue that can rotate.
    '''
    lines = self.evaluate('M.deepSet, %d' % self.N, count=2)
    self.assertEqual(lines[0], 'value 1')
    self.assertRegex(lines[1], self.STACK_ERROR)

  def test_diverging_setfunction_does_not_starve_others(self):
    '''
    An audit finding: the periodic rotation looked at the current queue only.
    The nested queue of a set function holds one configuration, so the
    enclosing queue never rotated while the set function diverged.  The
    rotation now targets the outermost queue that can rotate.
    '''
    self.assertEqual(self.evaluate('M.divergingSet'), ['value 1'])

  def test_nested_queue_rotates_in_place(self):
    '''
    An audit finding: the periodic rotation named the outermost queue that
    can rotate as its only target, and a nested scheduler handed the request
    outward without rotating its own queue.  While the enclosing queue held
    two configurations, the nested queue ``[loop, 2]`` never rotated, so the
    set function never produced its value.  A nested scheduler now rotates
    its own queue as well.
    '''
    self.assertEqual(self.evaluate('M.nestedChoice'), ['value 1'])

  def test_setfunction_in_every_iteration(self):
    # An alternative that calls a set function in every iteration still gives
    # way to the other one.
    self.assertEqual(self.evaluate('M.setLoopAlt'), ['value 1'])

  @cytest.skipIfGcStress('a deep recursion costs a re-descent per step')
  def test_limit_above_stack_is_clamped(self):
    '''
    An audit finding: a limit larger than the stack of the thread let the
    guard never fire, and the process crashed with a segmentation fault.  The
    limit is now clamped to the stack of the thread less a margin.
    '''
    lines = self.evaluate('M.deep, 100000', limit=1 << 40)
    self.assertEqual(len(lines), 1, lines)
    self.assertRegex(lines[0], self.STACK_ERROR)

  @cytest.with_flags(defaultconverter='topython')
  def test_default_limit_admits_moderate_depth(self):
    goal = curry.compile('length [1..2000]', 'expr')
    self.assertEqual(list(curry.eval(goal)), [2000])

  @cytest.with_flags(defaultconverter='topython', stack_limit=None)
  def test_guard_disabled(self):
    goal = curry.compile('length [1..2000]', 'expr')
    self.assertEqual(list(curry.eval(goal)), [2000])

  @cytest.with_flags(defaultconverter='topython')
  def test_interrupted_steps_are_not_counted(self):
    '''
    An audit finding: a step interrupted by the periodic rotation counted as
    a rewrite step, although the redex was as it was.  The count decides
    whether a configuration at the stack limit made progress.  Two
    alternatives that each need many steps now take as many steps together,
    with the rotations between them, as apart.
    '''
    def steps(goal, *args):
      # The evaluator yields raw values.  curry.eval converts them.
      ev = evaluator.Evaluator(
          curry.getInterpreter(), curry.raw_expr(goal, *args)
        )
      values = [curry.topython(value) for value in ev.evaluate()]
      return values, ev.rts.steps_total
    M = curry.import_('StackGuard')
    n = 200000
    (value,), single = steps(M.lastOfRange, n)
    self.assertEqual(value, n)
    # The steps of the choice itself, measured where no rotation occurs.
    _, small_pair = steps(M.twoLastOf, 10)
    _, small_single = steps(M.lastOfRange, 10)
    overhead = small_pair - 2 * small_single
    values, pair = steps(M.twoLastOf, n)
    self.assertEqual(values, [n, n])
    self.assertEqual(pair, 2 * single + overhead)

@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'too slow on the Python backend'
  )
class TestDeepValue(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    curry.import_('StackGuard')

  @cytest.with_flags(defaultconverter='topython')
  def test_long_list_value(self):
    # Copying the value out of the graph recursed once per list element.  This
    # depth is safe for a recursive copier too.  The deep case runs in a child
    # (see below), because a crash would end the test runner.
    n = 5000
    goal = curry.compile('[1..%d]' % n, 'expr', exprtype='[Int]')
    value, = curry.eval(goal)
    self.assertEqual(len(value), n)
    self.assertEqual(value[-1], n)

  @cytest.skipIfGcStress('a collection per step over 200000 live cells')
  def test_long_list_value_in_child(self):
    '''
    An audit finding: copying a value of 200000 list elements out of the
    graph overflowed the C stack.  The copier keeps its own stack now.
    '''
    n = 200000
    lines = run_child(self, CHILD_LONG_LIST % {'n': n})
    self.assertEqual(lines, ['%d %d' % (n, n)])

  def test_shared_subgraph_copies_once(self):
    '''
    An audit finding: the graph copier read its memo but never filled it, so
    a subgraph reached by several paths was copied once per path.  A node
    with two references to one subgraph, nested ``depth`` times, then copied
    in exponential time.  The copy must keep the sharing.
    '''
    depth = 16
    node = curry.expr(0)
    for _ in range(depth):
      node = curry.expr((node, node))
    self.assertEqual(self.count_nodes(node), depth + 1)
    dup = node.__deepcopy__()
    self.assertNotEqual(dup.id(), node.id())
    self.assertEqual(self.count_nodes(dup), depth + 1)

  def test_cyclic_graph_copies(self):
    '''
    An audit finding: the copier recorded a node in its memo only after its
    successors were copied, so a cycle in the graph made it allocate without
    end.  The copy of a node is now recorded first.  The copy of ``let a =
    [a] in a`` is a cons node that leads back to itself.
    '''
    anchor, ref = curry.expressions.anchor, curry.ref
    node = curry.raw_expr(anchor([ref()]))
    self.assertTrue(self.reaches(node, node.id()))
    dup = node.__deepcopy__()
    self.assertNotEqual(dup.id(), node.id())
    self.assertTrue(self.reaches(dup, dup.id()))
    self.assertFalse(self.reaches(dup, node.id()))
    self.assertEqual(self.count_nodes(dup), self.count_nodes(node))

  @staticmethod
  def node_successors(node):
    return [succ for succ in node.successors if hasattr(succ, 'successors')]

  @classmethod
  def count_nodes(cls, root):
    '''Counts the distinct nodes of a graph.'''
    seen = set()
    pending = [root]
    while pending:
      node = pending.pop()
      if node.id() in seen:
        continue
      seen.add(node.id())
      pending.extend(cls.node_successors(node))
    return len(seen)

  @classmethod
  def reaches(cls, root, target):
    '''
    Tells whether a path of one or more edges leads from ``root`` to the node
    with ID ``target``.
    '''
    seen = set()
    pending = cls.node_successors(root)
    while pending:
      node = pending.pop()
      if node.id() == target:
        return True
      if node.id() in seen:
        continue
      seen.add(node.id())
      pending.extend(cls.node_successors(node))
    return False
