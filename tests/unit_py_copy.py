'''
Tests for the graph copier of the Python backend.

The copier makes the values that ``curry.eval`` returns, and it serves
``copy.deepcopy``.  It recursed once per node, so a long list value raised
RecursionError and a cyclic expression could not be copied (an entry in
TODO).  It also lost sharing: a subgraph reached by several paths was copied
once per path.  The copier keeps its own stack now, and it records the copy
of a node before it copies the successors.  The C++ backend has the same
tests in unit_cxx_stack.py.
'''
import cytest # from ./lib; must be first
from curry.backends.py.graph import Node
from curry.backends.py.graph.copy import copygraph
from curry.expressions import _setgrd
from curry import inspect
import copy as pycopy
import curry, unittest

def long_list(n):
  '''Builds the list [1..n] without recursion.'''
  prelude = curry.getInterpreter().prelude
  tail = Node(prelude.Nil)
  for i in range(n, 0, -1):
    tail = Node(prelude.Cons, Node(prelude.Int, i), tail)
  return tail

def node_successors(node):
  return [succ for succ in node.successors if isinstance(succ, Node)]

def nodes_of(root):
  '''Generates the distinct nodes of a graph.'''
  seen = set()
  pending = [root]
  while pending:
    node = pending.pop()
    if id(node) in seen:
      continue
    seen.add(id(node))
    yield node
    pending.extend(node_successors(node))

def count_nodes(root):
  return sum(1 for _ in nodes_of(root))

def disjoint(a, b):
  '''Tells whether the graphs at ``a`` and ``b`` share no node.'''
  ids = set(id(node) for node in nodes_of(a))
  return not any(id(node) in ids for node in nodes_of(b))

@unittest.skipIf(
    curry.flags['backend'] != 'py', 'the graph copier belongs to the Python backend'
  )
class TestPyCopy(cytest.TestCase):
  def test_long_list_copy(self):
    '''
    A list of 200000 elements.  The recursive copier raised RecursionError at
    a few thousand elements.
    '''
    n = 200000
    node = long_list(n)
    dup = node.__deepcopy__()
    self.assertIsNot(dup, node)
    value = curry.topython(dup)
    self.assertEqual(len(value), n)
    self.assertEqual(value[-1], n)
    self.assertEqual(count_nodes(dup), 2 * n + 1)
    self.assertTrue(disjoint(dup, node))

  @cytest.with_flags(defaultconverter='topython')
  def test_long_list_value(self):
    '''
    The value of ``[1..n]`` leaves the graph through the copier with
    ``skipfwd`` set.  The recursive copier failed near 4000 elements under
    the raised recursion limit of the evaluator.  The Python backend needs
    about 6 seconds for 10000 elements, so the 200000-element case is
    test_long_list_copy.
    '''
    n = 10000
    M = curry.import_('StackGuard')
    value, = curry.eval(M.longList, n)
    self.assertEqual(len(value), n)
    self.assertEqual(value[-1], n)

  def test_cyclic_graph_copies(self):
    '''
    The copy of ``let a = [a] in a`` is a cons node that leads back to
    itself.  The recursive copier raised RecursionError.
    '''
    anchor, ref = curry.expressions.anchor, curry.ref
    node = curry.raw_expr(anchor([ref()]))
    self.assertIs(node.successors[0], node)
    dup = node.__deepcopy__()
    self.assertIsNot(dup, node)
    self.assertTrue(inspect.isa_cons(dup))
    self.assertIs(dup.successors[0], dup)
    self.assertTrue(disjoint(dup, node))
    self.assertEqual(count_nodes(dup), count_nodes(node))
    self.assertEqual(str(dup), '[...]')

  def test_cycle_of_two_nodes_copies(self):
    # let a=(0:b), b=(1:a) in a
    cons, ref = curry.cons, curry.ref
    node = curry.raw_expr(ref('a'), a=cons(0, ref('b')), b=cons(1, ref('a')))
    dup = node.__deepcopy__()
    self.assertIs(dup.successors[1].successors[1], dup)
    self.assertTrue(disjoint(dup, node))
    self.assertEqual(count_nodes(dup), count_nodes(node))
    self.assertEqual(str(dup), str(node))
    self.assertEqual(dup, node) # logical equality handles cycles

  def test_shared_subgraph_copies_once(self):
    '''
    A node with two references to one subgraph, nested ``depth`` times.  The
    recursive copier copied the subgraph once per path, so the copy had
    ``2 ** depth`` leaves.  The copy must keep the sharing.
    '''
    depth = 16
    node = curry.expr(0)
    for _ in range(depth):
      node = curry.expr((node, node))
    self.assertEqual(count_nodes(node), depth + 1)
    dup = node.__deepcopy__()
    self.assertIsNot(dup, node)
    self.assertEqual(count_nodes(dup), depth + 1)
    self.assertIs(dup.successors[0], dup.successors[1])
    self.assertTrue(disjoint(dup, node))

  def test_unboxed_successor_is_shared(self):
    '''
    An unboxed successor is not copied.  An audit finding: the copier handed
    every successor that is not a node to copy.deepcopy, which rejects a
    memoryview (a string literal) and an iterator (the argument of a
    generator node), so a partial application that held a string literal
    could not leave the graph as a value.
    '''
    from curry.backends.py.currylib.prelude import string
    prelude = curry.getInterpreter().prelude
    literal = string.codepoints('abc')
    items = iter([1, 2])
    node = Node(
        prelude.Cons
      , Node(prelude._biString, literal)
      , Node(prelude._biGenerator, items)
      )
    dup = node.__deepcopy__()
    self.assertIsNot(dup, node)
    self.assertTrue(disjoint(dup, node))
    self.assertIs(dup.successors[0].successors[0], literal)
    self.assertIs(dup.successors[1].successors[0], items)

  def test_skip_fwd(self):
    '''
    ``skipfwd`` removes the forward nodes.  An audit finding: the skipper read
    a name that did not exist, so the option raised NameError on the first
    forward node.
    '''
    fwd = curry.expressions.fwd
    node = curry.raw_expr([fwd(1), fwd(fwd(2))])
    dup = copygraph(node, skipfwd=True)
    self.assertFalse(any(inspect.isa_fwd(x) for x in nodes_of(dup)))
    self.assertEqual(curry.topython(dup), [1, 2])
    kept = copygraph(node)
    self.assertEqual(sum(1 for x in nodes_of(kept) if inspect.isa_fwd(x)), 3)
    self.assertEqual(repr(kept), repr(node))
    self.assertTrue(disjoint(kept, node))

  def test_skip_setguard(self):
    # ``skipgrds`` removes the set guards of the given sets.
    node = curry.raw_expr(_setgrd(7, [1, _setgrd(8, 2)]))
    dup = copygraph(node, skipgrds={7})
    self.assertTrue(inspect.isa_cons(dup))
    self.assertTrue(inspect.isa_setguard(dup.successors[1].successors[0]))
    dup = copygraph(node, skipgrds={7, 8})
    self.assertEqual(curry.topython(dup), [1, 2])
    kept = copygraph(node, skipgrds={9})
    self.assertTrue(inspect.isa_setguard(kept))
    self.assertEqual(repr(kept), repr(node))

  def test_unboxed_values(self):
    # A built-in value and an unboxed successor copy as themselves.
    self.assertEqual(copygraph(5), 5)
    self.assertEqual(copygraph('a'), 'a')
    # A choice holds its id unboxed.  (curry.unboxed stands only under a
    # primitive since issue #107.)
    node = curry.raw_expr(curry.choice(2, 3, 4))
    dup = copygraph(node)
    self.assertEqual(str(dup), '_Choice 2 3 4')
    self.assertEqual(dup.successors[0], 2)
    self.assertIsNot(dup.successors[1], node.successors[1])

  def test_partial_application_copies(self):
    prelude = curry.import_('Prelude')
    node = curry.raw_expr(prelude.Cons, 1) # (1:)
    dup = node.__deepcopy__()
    self.assertEqual(repr(dup), repr(node))
    self.assertTrue(disjoint(dup, node))

  def test_deepcopy_memo(self):
    '''
    ``copy.deepcopy`` passes its memo to the copier.  Two references to one
    node in a Python list lead to one copy.  One memo across several calls
    keeps the sharing as well.
    '''
    node = curry.expr([1, 2])
    a, b = pycopy.deepcopy([node, node])
    self.assertIs(a, b)
    self.assertIsNot(a, node)
    self.assertEqual(curry.topython(a), [1, 2])
    memo = {}
    c = copygraph(node, memo=memo)
    d = copygraph(node, memo=memo)
    self.assertIs(c, d)
    self.assertIsNot(c, node)
