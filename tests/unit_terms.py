'''The held nodes of terms at the old API boundary.'''
import cytest # from ./lib; must be first
import curry
from curry import inspect
import os

class TestTerms(cytest.TestCase):

  def test_data_ordering_calls_curry_compare(self):
    path = os.path.join(os.path.dirname(__file__), 'data', 'curry', 'flows')
    curry.path.insert(0, path)
    try:
      M = curry.import_('StubRecord')
    finally:
      curry.path.remove(path)
    a, b = [curry.eval(M.Named(n)).one() for n in (1, 2)]
    self.assertTrue(a < b)
    self.assertTrue(a <= b)
    self.assertTrue(b > a)
    self.assertTrue(b >= a)
    self.assertFalse(b < a)
    self.assertEqual(curry.eval(curry.import_('Prelude').compare(a, b)).one().symbol.name, 'LT')

  def test_data_equality_ignores_constructor_sharing(self):
    P = curry.import_('Prelude')
    inner = P.Just(0)
    first = curry.eval(P.Just((inner, inner))).one()
    second = P.Just((P.Just(0), P.Just(0)))
    self.assertEqual(first, second)
    self.assertEqual(hash(first), hash(second))
    self.assertEqual(curry.term(first), first)

  def test_conversion_reaches_user_fields_and_variables(self):
    P = curry.import_('Prelude')
    x = curry.free('x', type='Char')
    value = curry.eval(P.Just((x, '', [P.Just('')]))).one()
    self.assertIsInstance(value, curry.Data)
    self.assertIs(value.args[0][0], x)
    self.assertIs(type(value.args[0][1]), str)
    self.assertIs(type(value.args[0][2][0].args[0]), str)
    self.assertEqual(value.args[0][2][0].args, ('',))
    self.assertEqual(curry.typeof(value), 'Maybe (Char, [Char], [Maybe [Char]])')

  def test_values_nested_conversion_and_round_trip(self):
    P = curry.import_('Prelude')
    SF = curry.import_('Control.SetFunctions')
    value = curry.eval(SF.set0(P.Just((curry.Char('a'), '')))).one()
    self.assertIsInstance(value, curry.Values)
    self.assertIs(type(next(iter(value)).args[0][0]), curry.Char)
    self.assertEqual(next(iter(value)).args[0][1], '')
    self.assertEqual(curry.eval(SF.values2list(value)).one(), list(value))
    self.assertEqual(curry.eval(value).one(), value)
    chars = curry.eval(SF.set0(curry.Char('a'))).one()
    self.assertIs(type(next(iter(chars))), curry.Char)
    self.assertEqual(curry.eval(chars).one(), chars)

  def test_iterator_cached_prefix_and_deferred_errors(self):
    P = curry.import_('Prelude')
    drawn = []
    def items():
      for item in (1, None):
        drawn.append(item)
        yield item
    t = curry.term(items(), type='[Int]')
    self.assertEqual(curry.eval(P.take(1, t)).one(), [1])
    self.assertEqual(curry.eval(P.take(1, t)).one(), [1])
    self.assertEqual(drawn, [1])
    with self.assertRaises(curry.ConversionError):
      curry.eval(P.take(2, t)).one()
    self.assertEqual(drawn, [1, None])

  def test_iterator_char_slot_keeps_string_boundary(self):
    P = curry.import_('Prelude')
    self.assertEqual(curry.eval(curry.term(iter([curry.Char('a')]), type='[Char]')).one(), 'a')
    for value in ('a', None, True):
      with self.subTest(value=value), self.assertRaises(curry.ConversionError):
        curry.eval(curry.term(iter([value]), type='[Char]')).one()

  def test_char_is_a_value_goal(self):
    value = curry.eval(curry.Char('a')).one()
    self.assertIs(type(value), curry.Char)
    self.assertEqual(hash(value), hash('a'))

  def test_parsed_functions_are_callable_values(self):
    for text in ('\\x -> x + 1', '(+) 1'):
      with self.subTest(text=text):
        f = curry.eval(curry.parse(text)).one()
        self.assertIsInstance(f, curry.Function)
        self.assertEqual(curry.typeof(f), 'Int -> Int')
        before = hash(f), str(f), repr(f)
        self.assertEqual(curry.eval(f(2)).one(), 3)
        self.assertEqual(curry.eval(f(2)).one(), 3)
        self.assertEqual((hash(f), str(f), repr(f)), before)

  def test_function_captured_iterator_replays_without_mutation(self):
    P = curry.import_('Prelude')
    drawn = []
    def items():
      for item in range(3):
        drawn.append(item)
        yield item
    f = curry.eval(P['flip'](P.take, items())).one()
    before = hash(f), str(f)
    for count in (1, 2, 1):
      self.assertEqual(curry.eval(f(count)).one(), list(range(count)))
    self.assertEqual(drawn, [0, 1])
    self.assertEqual((hash(f), str(f)), before)

  def test_iterator_element_type_reaches_nested_positions(self):
    P = curry.import_('Prelude')
    for values in ([[1], ['a']], [[], [1], [True]]):
      with self.subTest(values=values), self.assertRaises(curry.ConversionError):
        curry.eval(P.take(3, iter(values))).one()

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
