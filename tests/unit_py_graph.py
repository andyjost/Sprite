'''Tests for the node, variable, and spine-copy code of the Python backend.'''
import cytest # from ./lib; must be first
from curry.backends.py.eval.rts import RuntimeState
from curry.backends.py.graph import Node, utility, walk
from curry.common import T_CTOR
from curry.expressions import fwd, _setgrd
import curry, unittest

@unittest.skipIf(
    curry.flags['backend'] != 'py', 'drives the Python-backend graph classes directly'
  )
class TestPyGraph(cytest.TestCase):
  def setUp(self):
    self.interp = curry.getInterpreter()
    self.P = self.interp.prelude

  def test_node_slots(self):
    '''A node holds its info and its successors, nothing else.'''
    node = curry.raw_expr([self.P.Just, 1])
    self.assertFalse(hasattr(node, '__dict__'))
    self.assertRaises(AttributeError, setattr, node, 'extra', 1)
    self.assertIs(node.info, self.P.Just.info)
    self.assertEqual(len(node.successors), 1)
    self.assertEqual(curry.topython(node.successors[0]), 1)

  def test_node_construction(self):
    '''Checks the forms of info and the keywords accepted by Node.'''
    Int = self.P.Int
    one = Node(Int.info, 1)                   # an InfoTable
    self.assertEqual(curry.topython(one), 1)
    two = Node(Int, 2)                        # a CurryNodeInfo
    self.assertEqual(curry.topython(two), 2)
    three = Node([Int.info, 3])               # a sequence
    self.assertEqual(curry.topython(three), 3)
    four = Node(x for x in [Int.info, 4])     # a generator
    self.assertEqual(curry.topython(four), 4)
    # The target is rewritten in place.  It may be a variable.
    Node(Int.info, 5, target=one)
    self.assertEqual(curry.topython(one), 5)
    rts = RuntimeState(self.interp, two)
    Node(Int.info, 6, target=rts.variable(two))
    self.assertEqual(curry.topython(two), 6)
    Node((x for x in [Int.info, 7]), target=one)
    self.assertEqual(curry.topython(one), 7)
    # A variable as a successor stands for its target.
    just = Node(self.P.Just.info, rts.variable(two))
    self.assertIs(just.successors[0], two)
    # The number of successors must match the arity.
    self.assertRaisesRegex(
        TypeError, r"cannot construct 'Int' \(arity=1\), with 0 args"
      , lambda: Node(Int.info)
      )
    self.assertRaisesRegex(
        TypeError, r"cannot curry 'Int' \(arity=1\), with 1 arg"
      , lambda: Node(Int.info, 1, partial=True)
      )
    # Partial applications.
    cons = Node(self.P.Cons.info, 1, partial=True)
    self.assertIs(cons.info, self.P.Cons.info)
    self.assertEqual(len(cons.successors), 1)
    papp = Node(self.P.Cons.info, 1, partial_info=rts.PartApplic)
    self.assertIs(papp.info, rts.PartApplic)
    self.assertEqual(papp.successors[0], 1)
    self.assertIs(papp.successors[1].info, self.P.Cons.info)

  def test_variable(self):
    '''Checks the path and the guards of variables made by indexing.'''
    P = self.P
    inner = curry.raw_expr([P.id, True])
    e = curry.raw_expr([P.id, fwd(_setgrd(0, inner))])
    rts = RuntimeState(self.interp, e)
    _0 = rts.variable(e)
    self.assertFalse(hasattr(_0, '__dict__'))
    self.assertTrue(_0.is_root)
    self.assertIs(_0.target, e)
    self.assertIsNone(_0.realpath)
    self.assertEqual(_0.guards, set())
    # The forward node is spliced out, and the set guard is crossed.
    _1 = _0[0]
    self.assertIs(_1.root, e)
    self.assertIs(_1.target, inner)
    self.assertEqual(_1.realpath, [0, 1])
    self.assertEqual(_1.guards, set([0]))
    self.assertIs(e.successors[0].info, rts.SetGuard)
    # The path and the guards of the parent are inherited.
    _2 = _1[0]
    self.assertIs(_2.target, inner.successors[0])
    self.assertEqual(_2.realpath, [0, 1, 0])
    self.assertEqual(_2.guards, set([0]))
    self.assertIsNot(_2.guards, _1.guards)
    self.assertIs(_2.info, P.True_.info)
    self.assertEqual(_2.tag, P.True_.info.tag)
    self.assertTrue(_2.is_boxed)
    # A tuple path gives the same variable.
    _2b = _0[0, 0]
    self.assertIs(_2b.target, _2.target)
    self.assertEqual(_2b.realpath, [0, 1, 0])
    self.assertEqual(_2b.guards, set([0]))
    # None gives the root variable.
    self.assertTrue(_2[None].is_root)
    # The rvalue inserts the guards that were crossed.
    rvalue = _2.rvalue
    self.assertIs(rvalue.info, rts.SetGuard)
    self.assertEqual(rvalue.successors[0], 0)
    self.assertIs(rvalue.successors[1], _2.target)
    # A variable over an unboxed value.
    one = curry.raw_expr(1)
    _3 = rts.variable(one, 0)
    self.assertEqual(_3.target, 1)
    self.assertEqual(_3.realpath, [0])
    self.assertEqual(_3.tag, T_CTOR)
    self.assertIsNone(_3.info)
    self.assertFalse(_3.is_boxed)
    self.assertEqual(_3.unboxed_value, 1)
    # A bad path.
    self.assertRaises(curry.CurryIndexError, lambda: _0[2])
    self.assertRaises(curry.CurryIndexError, lambda: _0['x'])

  def test_copy_spine(self):
    '''copy_spine copies the nodes along a path and shares the rest.'''
    P = self.P
    just1 = curry.raw_expr([P.Just, 1])
    e = curry.raw_expr([P.id, [P.Just, just1]])
    two = curry.raw_expr(2)
    # A new root.
    r = utility.copy_spine(e, [0, 0], end=two)
    self.assertIsNot(r, e)
    self.assertIs(r.info, e.info)
    self.assertIsNot(r.successors[0], e.successors[0])
    self.assertIs(r.successors[0].info, P.Just.info)
    self.assertIs(r.successors[0].successors[0], two)
    self.assertIs(e.successors[0].successors[0], just1)
    # Without an end, the original node ends the copied spine.
    r = utility.copy_spine(e, (0,))
    self.assertIsNot(r, e)
    self.assertIs(r.successors[0], e.successors[0])
    # An empty path returns the end or the root.  Nothing is rewritten.
    self.assertIs(utility.copy_spine(e, [], end=two), two)
    self.assertIs(utility.copy_spine(e, []), e)
    self.assertIs(utility.copy_spine(e, (), end=two, rewrite=e), two)
    self.assertIs(e.successors[0].successors[0], just1)
    # The root is rewritten in place.
    inner = e.successors[0]
    utility.copy_spine(e, (0, 0), end=two, rewrite=e)
    self.assertIs(e.info, P.id.info)
    self.assertIsNot(e.successors[0], inner)
    self.assertIs(e.successors[0].successors[0], two)
    self.assertIs(inner.successors[0], just1)
    # The rewrite target and the end may be variables.
    rts = RuntimeState(self.interp, e)
    three = curry.raw_expr(3)
    utility.copy_spine(e, [0, 0], end=rts.variable(three), rewrite=rts.variable(e))
    self.assertIs(e.successors[0].successors[0], three)
    # Only a function node can be rewritten.
    self.assertRaises(
        AssertionError
      , lambda: utility.copy_spine(e, [0], end=two, rewrite=just1)
      )

  def test_walk_push(self):
    '''walk pushes the successors of a node and nothing for a literal.'''
    e = curry.raw_expr([self.P.Just, 1])
    state = walk(e)
    self.assertIs(state.cursor, e)
    state.push()
    self.assertEqual(len(state.stack[-1]), 1)
    self.assertTrue(state.advance())
    self.assertIs(state.cursor, e.successors[0])
    self.assertEqual(state.realpath, [0])
    state.push()
    self.assertEqual(state.stack[-1], [(0, 1)])
    self.assertTrue(state.advance())
    self.assertEqual(state.cursor, 1)
    self.assertEqual(state.realpath, [0, 0])
    state.push()
    self.assertEqual(state.stack[-1], [])
    self.assertFalse(state.advance())
    # The memoryview of a string literal is a literal as well.
    s = Node(self.P._biString.info, memoryview(b'ab'))
    state = walk(s)
    state.push()
    self.assertTrue(state.advance())
    self.assertIsInstance(state.cursor, memoryview)
    state.push()
    self.assertEqual(state.stack[-1], [])
