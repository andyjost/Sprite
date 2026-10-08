import cytest # from ./lib; must be first
import cytest.expression_library
import curry
from curry import inspect
from curry.backends.py.graph.equality import equal
import itertools, operator, unittest

not_equal = lambda *args: not equal(*args)

def raw(arg):
  '''
  raw_expr, with an unboxed marker as its bare value: the equality meets an
  unboxed value as the successor of a primitive.  The builders refuse the
  marker outside a primitive (issue #107).
  '''
  return arg.value if isinstance(arg, curry.unboxed) else curry.raw_expr(arg)

def long_list(n, last=None):
  '''
  Builds the list [1..n] without recursion.  ``last`` replaces the last
  element.
  '''
  interp = curry.getInterpreter()
  prelude = interp.prelude
  make_node = interp.backend.make_node
  tail = make_node(prelude.Nil)
  for i in range(n, 0, -1):
    elem = i if last is None or i < n else last
    tail = make_node(prelude.Cons, make_node(prelude.Int, elem), tail)
  return tail

class TestGraphComparison(cytest.expression_library.ExpressionLibTestCase):
  def negative_cases(self, testexpr, exclude=None):
    exclude = [] if exclude is None else exclude
    exclude.append(testexpr)
    for e in self.everything:
      if inspect.isa_curry_expr(e) and not any(e is x for x in exclude):
        yield not_equal, testexpr, e
        yield not_equal, e, testexpr

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_bool(self):
    yield equal, True, True
    yield not_equal, True, False
    for spec in self.negative_cases(self.true):
      yield spec

  @cytest.check_predicate(mapper=raw)
  def test_equals_int(self):
    yield equal, 1, 1
    yield equal, curry.unboxed(1), curry.unboxed(1)
    yield not_equal, 1, 2
    yield not_equal, 1, curry.unboxed(1)
    yield not_equal, curry.unboxed(1), 1
    for spec in self.negative_cases(self.int, exclude=[self.unboxed_int]):
      yield spec

  @cytest.check_predicate(mapper=raw)
  def test_equals_char(self):
    yield equal, 'a', 'a'
    yield equal, curry.unboxed('a'), curry.unboxed('a')
    yield not_equal, 'a', 'b'
    yield not_equal, 'a', curry.unboxed('a')
    yield not_equal, curry.unboxed('a'), 'a'
    for spec in self.negative_cases(self.char, exclude=[self.unboxed_char]):
      yield spec

  @cytest.check_predicate(mapper=raw)
  def test_equals_float(self):
    yield equal, 1.1, 1.1
    yield equal, curry.unboxed(1.1), curry.unboxed(1.1)
    yield not_equal, 1.1, 1.2
    yield not_equal, 1.1, curry.unboxed(1.1)
    yield not_equal, curry.unboxed(1.1), 1.1
    for spec in self.negative_cases(self.float, exclude=[self.unboxed_float]):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_algebraic(self):
    prelude = curry.import_('Prelude')
    yield equal, [prelude.Just, 5], [prelude.Just, 5]
    yield equal, self.just_nil, self.just_nil
    yield not_equal, [prelude.Just, 5], [prelude.Just, 6]
    yield not_equal, [prelude.Just, 5], prelude.Nothing
    yield not_equal, [prelude.Just, 5], self.just_nil
    for spec in self.negative_cases(self.just_nil):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_io(self):
    prelude = curry.import_('Prelude')
    yield equal, self.io, self.io
    yield equal, [prelude.IO, 5], [prelude.IO, 5]
    yield not_equal, [prelude.IO, 5], [prelude.IO, 6]
    for spec in self.negative_cases(self.io):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_list(self):
    yield equal, [1, 2], [1, 2]
    yield equal, [], []
    yield not_equal, [1, 2], []
    yield equal, [[[]]], [[[]]]
    yield not_equal, [[[]]], []
    yield equal, [1, [2, 3, [4]]], [1, [2, 3, [4]]]
    for spec in self.negative_cases(self.list):
      yield spec
    for spec in self.negative_cases(self.empty_list, exclude=[self.empty_string]):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_tuple(self):
    yield equal, (), ()
    yield equal, (1,2), (1,2)
    yield not_equal, (1,2), (1,2,3)
    yield not_equal, (1,2,3), (1,2)
    yield equal, ((1,2),(3,4)), ((1,2),(3,4))
    for spec in self.negative_cases(self.tuple):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_string(self):
    yield equal, '', ''
    yield equal, 'hello', 'hello'
    yield not_equal, 'hello', 'world'
    yield not_equal, '', 'world'
    yield not_equal, 'hello', ''
    for spec in self.negative_cases(self.string):
      yield spec
    for spec in self.negative_cases(self.empty_string, exclude=[self.empty_list]):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_failure(self):
    yield equal, self.failure, self.failure
    for spec in self.negative_cases(self.failure):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_fwd(self):
    yield equal, self.fwd, self.fwd
    for spec in self.negative_cases(self.fwd):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_var(self):
    yield equal, self.free, self.free
    for spec in self.negative_cases(self.free):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_choice(self):
    yield equal, self.choice, self.choice
    for spec in self.negative_cases(self.choice):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_nonstrict_constraint(self):
    yield equal, self.nonstrict_constraint, self.nonstrict_constraint
    for spec in self.negative_cases(self.nonstrict_constraint):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_setgrd(self):
    yield equal, self.setgrd, self.setgrd
    for spec in self.negative_cases(self.setgrd):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_strict_constraint(self):
    yield equal, self.strict_constraint, self.strict_constraint
    for spec in self.negative_cases(self.strict_constraint):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_value_binding(self):
    yield equal, self.value_binding, self.value_binding
    for spec in self.negative_cases(self.value_binding):
      yield spec

  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_func(self):
    yield equal, self.func, self.func
    for spec in self.negative_cases(self.func):
      yield spec


  @cytest.check_predicate(mapper=curry.raw_expr)
  def test_equals_cyclical(self):
    cons, ref = curry.cons, curry.ref
    # let a=(0:b), b=(1:a) in a
    e0 = curry.raw_expr(ref('a'), a=cons(0, ref('b')), b=cons(1, ref('a')))
    # let a=(0:1:a) in a
    e1 = curry.raw_expr(ref('a'), a=cons(0, 1, ref('a')))
    # let a=(0:1:b), b=(0:1) in a
    e2 = curry.raw_expr(ref('a'), a=cons(0, 1, ref('b')), b=cons(0, 1, ref('a')))
    # let a=(0:1:0:b), b=(1:0:1:a) in a
    e3 = curry.raw_expr(ref('a'), a=cons(0, 1, 0, ref('b')), b=cons(1, 0, 1, ref('a')))
    es = [e0, e1, e2, e3]
    for a,b in itertools.product(es, es):
      yield equal, a, b
    for e in es:
      yield not_equal, e, [0,1]
    onezero = curry.raw_expr(ref('a'), a=cons(1, ref('b')), b=cons(0, ref('a')))
    yield equal, onezero, onezero
    for e in es:
      yield not_equal, e, onezero
      yield not_equal, onezero, e

  def test_equals_long_list(self):
    '''
    A list of 200000 elements.  The comparison recursed once per node, so it
    raised RecursionError at a few hundred elements.  It keeps its own stack
    now.
    '''
    n = 200000
    a, b = long_list(n), long_list(n)
    self.assertTrue(equal(a, a))
    self.assertTrue(equal(a, b))
    self.assertTrue(equal(a, b, skipfwd=True))
    c = long_list(n, last=0)
    self.assertFalse(equal(a, c))
    self.assertFalse(equal(c, a))

  def test_equals_rejects_non_expressions(self):
    one = curry.raw_expr(1)
    self.assertRaises(TypeError, equal, one, object())
    self.assertRaises(TypeError, equal, object(), one)
    self.assertRaises(TypeError, equal, curry.raw_expr([1, 2]), [1, 2])

  @unittest.skipIf(
      curry.flags['backend'] != 'py'
    , 'needs a node with a None placeholder, which only the Python backend builds'
    )
  def test_equals_visits_pairs_in_order(self):
    # The pairs are visited left to right.  A mismatch ends the comparison
    # before a later pair that is not a Curry expression raises TypeError.
    from curry.backends.py.graph import Node
    prelude = curry.import_('Prelude')
    def cons(head):
      return Node(prelude.Cons, Node(prelude.Int, head), None)
    self.assertFalse(equal(cons(1), cons(2)))
    self.assertRaises(TypeError, equal, cons(1), cons(1))


class TestForeignObjects(cytest.TestCase):
  '''
  A node compared with a value that is not a node: == answers False and !=
  answers True, in both directions and through the containment test, as
  Python's data model expects of a comparison the type does not support.
  The C++ bindings raised TypeError (pybind11 refused the argument), and
  the Python backend raised for a value that is not a Curry expression
  (issue #82, found in stage 3).  Both backends answer the same way now.
  '''

  def test_equality_with_a_foreign_object(self):
    node = curry.raw_expr(1)
    same = curry.raw_expr(1)
    self.assertTrue(node == same)
    self.assertFalse(node != same)
    for foreign in [1, True, None, object(), 'a', 1.0, [], (), {}]:
      with self.subTest(foreign=foreign):
        self.assertFalse(node == foreign)
        self.assertTrue(node != foreign)
        self.assertFalse(foreign == node)
        self.assertTrue(foreign != node)
    self.assertNotIn(node, [1, True, None])
    self.assertNotIn(1, [node])
    self.assertIn(node, [1, node])
    self.assertIn(node, [1, same])

  def test_no_order(self):
    '''A node has no order, against a node or a foreign object.'''
    node = curry.raw_expr(1)
    for rhs in [curry.raw_expr(1), 1]:
      for op in [operator.lt, operator.le, operator.gt, operator.ge]:
        with self.subTest(op=op.__name__, rhs=rhs):
          with self.assertRaises(TypeError):
            op(node, rhs)

  def test_hash(self):
    '''
    A node hashes by identity on both backends while equality is
    structural, the rule the owner kept (the entry of 2026-10-08 on issue
    #82): two equal nodes hash differently, a set keyed by nodes keeps
    both, and a dict keyed by one node does not find the other.  A node is
    not meant as a dictionary key; the API page says so.
    '''
    node = curry.raw_expr(1)
    same = curry.raw_expr(1)
    self.assertEqual(hash(node), hash(node))
    self.assertEqual(len({node, node}), 1)
    self.assertTrue(node == same)
    self.assertNotEqual(hash(node), hash(same))
    self.assertEqual(len({node, same}), 2)
    self.assertNotIn(same, {node})
    self.assertIsNone({node: 1}.get(same))
