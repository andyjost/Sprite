'''The held nodes of terms at the old API boundary.'''
import cytest # from ./lib; must be first
import curry
from curry import inspect

class TestTerms(cytest.TestCase):

  def test_iterator_is_held_across_calls(self):
    drawn = []
    def items():
      for value in range(3):
        drawn.append(value)
        yield value
    t = curry.term(items(), type='[Int]')
    P = curry.import_('Prelude')
    self.assertEqual(drawn, [])
    self.assertEqual(list(curry.eval(P.take(2, t), converter='topython')), [[0, 1]])
    self.assertEqual(drawn, [0, 1])
    self.assertEqual(list(curry.eval(P.take(2, t), converter='topython')), [[0, 1]])
    self.assertEqual(drawn, [0, 1])

  def test_inspect_sequence_of_terms(self):
    P = curry.import_('Prelude')
    self.assertTrue(inspect.isa(curry.term(1), [P.Int, P.Float]))
    self.assertTrue(inspect.isa(curry.term(1), [curry.type('Prelude.Int')]))
    self.assertTrue(inspect.isa(curry.term(1), [P.Int.symbol]))

  def test_old_builders_accept_term_heads(self):
    P = curry.import_('Prelude')
    for build in (curry.expr, curry.raw_expr):
      node = build(P['not'], True)
      self.assertEqual(list(curry.eval(node, converter='topython')), [False])

  def test_call_type_error_is_a_conversion(self):
    P = curry.import_('Prelude')
    with self.assertRaises((curry.ConversionError, curry.MismatchError)):
      P.ord('a')

  def test_deep_graph_keys(self):
    first = curry.term(range(2000), type='[Int]')
    second = curry.term(range(2000), type='[Int]')
    self.assertEqual(first, second)
    self.assertEqual(hash(first), hash(second))

  def test_float_text_uses_the_node_printer(self):
    for value in (1.5, 1.0e15, 1.0e-5, -0.0, float('inf'),
        -float('inf'), float('nan')):
      with self.subTest(value=value):
        self.assertEqual(str(curry.term(value)), str(curry.expr(value)))

  def test_type_constructors_keep_the_old_info_field(self):
    constructors = curry.type('Prelude.Bool').constructors
    self.assertEqual([(c.name, c.info.arity) for c in constructors],
        [('False', 0), ('True', 0)])
