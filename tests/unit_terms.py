'''The held nodes of terms at the old API boundary.'''
import cytest # from ./lib; must be first
import curry
from curry import inspect
import os, sys

class TestTerms(cytest.TestCase):

  def test_constructor_classes_survive_conversion_and_keep_keys(self):
    M = curry.compile('data Tree = Leaf | Node Tree Int Tree')
    self.assertTrue(issubclass(M.Node, curry.ConstructorClass))
    self.assertTrue(issubclass(curry.info(M).types['Tree'].cls, curry.DataClass))
    value = M.Node(M.Leaf, -1, M.Leaf)
    self.assertIs(M.Leaf.symbol, curry.info(M).symbols['Leaf'])
    self.assertIs(value.symbol, curry.info(M).symbols['Node'])
    self.assertEqual((value._0, value._1, value._2), value.args)
    self.assertIs(type(curry.eval(value).one()), M.Node)
    self.assertEqual({value: 7}[curry.eval(value).one()], 7)
    self.assertEqual(curry.typeof(M.Node), 'Tree -> Int -> Tree -> Tree')
    self.assertEqual(curry.show(M.Node), 'Node')
    self.assertEqual(M.Node, curry.term(M.Node))
    P = curry.import_('Prelude')
    for term in (P.Just(1), P.Left(1), P.Right('x')):
      self.assertIs(type(curry.eval(term).one()), getattr(P, term.symbol.name))

  def test_constructor_application_does_not_evaluate_terms_or_iterators(self):
    M = curry.compile('data Box a = Box a\ncoin = 1 ? 2')
    value = M.Box(M.coin)
    self.assertNotIsInstance(value, curry.Data)
    self.assertEqual([v.args for v in curry.eval(value)], [(1,), (2,)])
    drawn = []
    def items():
      drawn.append(1)
      yield 1
    term = M.Box(items())
    self.assertEqual(drawn, [])
    self.assertEqual(curry.eval(term).one().args, ([1],))
    self.assertEqual(drawn, [1])

  def test_reload_stales_constructor_classes_and_instances(self):
    M = curry.compile('data Named = Named { first :: Int }')
    old, oldtype, value = M.Named, curry.info(M).types['Named'].cls, M.Named(1)
    curry.reload(M, text='data Named = Named { second :: Int }')
    self.assertFalse(isinstance(M.Named(2), old))
    self.assertFalse(isinstance(M.Named(2), oldtype))
    self.assertEqual(M.Named.__match_args__, ('second',))
    self.assertEqual(M.Named(2).second, 2)
    self.assertIs(M.Named.datatype.module, M)
    for use in (lambda: old(1), lambda: curry.term(old), lambda: curry.eval(value).one()):
      with self.assertRaises(curry.StaleError):
        use()

  def test_reset_stales_constructor_classes_and_instances(self):
    P = curry.import_('Prelude')
    old, oldtype, value = P.Just, curry.info(P).types['Maybe'].cls, P.Just(1)
    curry.reset()
    P = curry.import_('Prelude')
    self.assertFalse(isinstance(P.Just(1), old))
    self.assertFalse(isinstance(P.Nothing, oldtype))
    for use in (lambda: old(1), lambda: curry.term(old), lambda: curry.eval(value).one()):
      with self.assertRaises(curry.StaleError):
        use()

  def test_runtime_raw_symbols_do_not_escape_next(self):
    SF = curry.import_('Control.SetFunctions')
    P = curry.import_('Prelude')
    with curry.eval(SF.set0(P.Just(1))) as results:
      self.assertEqual(next(iter(next(results))).args, (1,))
      self.assertTrue(issubclass(P.Just, curry.ConstructorClass))

  def test_constructor_classes_at_internal_node_boundary(self):
    P = curry.import_('Prelude')
    from curry.objects.terms import raw_symbols
    interp = cytest.raw.interp()
    for description in ((P.Just, 1), ([P.Just, 1],)):
      for typed in (False, True):
        node = cytest.raw.expr(*description, typed=typed)
        self.assertEqual(curry.eval(node).one().args, (1,))
    with raw_symbols():
      node = interp.backend.make_node(P.Just, cytest.raw.expr(1))
    self.assertEqual(curry.eval(node).one().args, (1,))
    self.assertTrue(inspect.isa(node, P.Just))
    self.assertTrue(inspect.isa(node, (P.Just,)))
    from curry.typecheck import engine
    for description in ((P.Just, 1), ([P.Just, 1],)):
      node = engine.build(interp, *description)
      self.assertEqual(curry.eval(node).one().args, (1,))

  def test_constructor_values_keep_literal_polymorphism_until_evaluated(self):
    P = curry.import_('Prelude')
    value = P.Just(1)
    self.assertIsInstance(value, P.Just)
    self.assertEqual(curry.typeof(value), 'Num a => Maybe a')
    fixed = curry.eval(curry.term(value, type='Maybe Float')).one()
    self.assertIs(type(fixed.args[0]), float)
    self.assertEqual(curry.typeof(fixed), 'Maybe Float')

  def test_newtype_application_keeps_source_shape_and_runtime_erasure(self):
    M = curry.import_('Data.Functor.Identity')
    value = M.Identity(5)
    self.assertIsInstance(value, M.Identity)
    self.assertEqual(value.args, (5,))
    self.assertEqual(curry.typeof(value, defaulted=True), 'Identity Int')
    self.assertEqual(curry.eval(value).one(), 5)

  def test_iterator_callbacks_see_constructor_classes(self):
    P = curry.import_('Prelude')
    def values():
      self.assertTrue(issubclass(P.Just, curry.ConstructorClass))
      yield curry.eval(P.length('abc')).one()
    self.assertEqual(curry.eval(P.head(values())).one(), 3)

  def test_record_interface_keeps_field_order_and_groups(self):
    M = curry.compile('data Record = Record { x, y :: Int, label :: String }')
    self.assertEqual(M.Record.__match_args__, ('x', 'y', 'label'))
    self.assertEqual(M.Record.symbol.fields, ('x', 'y', 'label'))
    value = M.Record(1, 2, 'r')
    self.assertEqual((value.x, value.y, value.label), (1, 2, 'r'))

  def test_deep_values_convert_and_show(self):
    # The tools convert and print a deep constructor value on both backends.
    M = curry.compile("""
      data Depth = Zero | Next Depth
      depth :: Int -> Depth
      depth 0 = Zero
      depth n | n > 0 = Next (depth (n-1))
    """)
    value = curry.eval(M.depth(1200)).one()
    shown = curry.show(value)
    self.assertEqual(shown, 'Next (' * 1199 + 'Next Zero' + ')' * 1199)
    for _ in range(1200):
      self.assertIsInstance(value, curry.Data)
      value, = value.args
    self.assertEqual(value.symbol.name, 'Zero')

  def test_show_deep_containers(self):
    value = 1
    for _ in range(1200):
      value = [value]
    self.assertEqual(curry.show(value), '[' * 1200 + '1' + ']' * 1200)

  def test_deep_container_conversion(self):
    nested = 1
    for _ in range(500):
      nested = [nested]
    term = curry.term(nested)
    self.assertEqual(curry.typeof(term, defaulted=True)[:20], '[' * 20)

  def test_deep_container_conversion_with_low_recursion_limit(self):
    old = sys.getrecursionlimit()
    try:
      sys.setrecursionlimit(200)
      self.test_deep_container_conversion()
    finally:
      sys.setrecursionlimit(old)

  def test_container_conversion_keeps_scalar_errors(self):
    for value in (b'abc', [b'abc'], (b'abc', 1), (1,)):
      with self.subTest(value=value), self.assertRaises(curry.ConversionError):
        curry.term(value)

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
    self.assertEqual(list(curry.eval(P.take(2, t))), [[0, 1]])
    self.assertEqual(drawn, [0, 1])
    self.assertEqual(list(curry.eval(P.take(2, t))), [[0, 1]])
    self.assertEqual(drawn, [0, 1])

  def test_inspect_sequence_of_terms(self):
    P = curry.import_('Prelude')
    self.assertTrue(inspect.isa(curry.term(1), [P.Int, P.Float]))
    self.assertTrue(inspect.isa(curry.term(1), [curry.info(P).types['Int']]))
    self.assertTrue(inspect.isa(curry.term(1), [P.Int.symbol]))

  def test_internal_builder_accepts_term_heads(self):
    P = curry.import_('Prelude')
    for build in (cytest.raw.expr, lambda *args: cytest.raw.expr(*args, typed=True)):
      node = build(P['not'], True)
      self.assertEqual(list(curry.eval(node)), [False])

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
        self.assertEqual(str(curry.term(value)), str(cytest.raw.expr(value, typed=True)))

  def test_type_constructor_metadata(self):
    constructors = curry.info(curry.import_('Prelude')).types['Bool'].constructors
    self.assertEqual([(c.name, c.arity) for c in constructors],
        [('False', 0), ('True', 0)])


  def test_overloaded_iterator_argument(self):
    P = curry.import_('Prelude')
    goal = P.map(P.show, iter([1]))
    self.assertEqual(curry.typeof(goal), 'Show a => [[Char]]')
    with self.assertRaises(curry.DefaultingError) as caught:
      curry.eval(goal)
    self.assertNotIn('IteratorSource', str(caught.exception))
    typed = curry.term(iter([1]), type='[Int]')
    self.assertEqual(list(curry.eval(P.map(P.show, typed))), [['1']])

  def test_float_in_int_slot_names_operand_and_position(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.ConversionError) as caught:
      P.plusInt(1, 2.5)
    error = caught.exception
    self.assertIn('2.5', str(error))
    self.assertIn('argument 2 of Prelude.plusInt', str(error))
    self.assertIn('write an int', str(error))
    self.assertEqual(error.symbol, 'Prelude.plusInt')

  def test_typeof_python_values_follows_term_conversion(self):
    self.assertEqual(curry.typeof([1, 2.5]), '[Float]')
    self.assertEqual(curry.typeof((1, 2.5)), 'Num a => (a, Float)')
    self.assertEqual(curry.typeof(1), 'Num a => a')
    self.assertEqual(curry.typeof(True), 'Bool')
    self.assertEqual(curry.typeof('a'), '[Char]')
    for value in (None, b'a', {}, set(), (1,)):
      with self.subTest(value=value), self.assertRaises(curry.ConversionError):
        curry.typeof(value)
    with self.assertRaises(curry.IntOverflowError):
      curry.typeof(2 ** 63)

  def test_typeof_internal_markers_retains_node_path(self):
    raw = cytest.raw
    self.assertEqual(raw.interp().typeof(raw.free(exprtype='[Int]')), '[Int]')
    node = raw.expr(True)
    self.assertEqual(raw.interp().typeof(raw.typed(node, 'Bool')), 'Bool')


  def test_bad_operand_keeps_symbol_and_position(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.ConversionError) as caught:
      P.Just(None)
    self.assertIn('None', str(caught.exception))
    self.assertIn('argument 1 of Prelude.Just', str(caught.exception))
    self.assertIn('P.Nothing', str(caught.exception))
    self.assertEqual(caught.exception.symbol, 'Prelude.Just')
    with self.assertRaises(curry.ConversionError) as caught:
      P.plusInt(curry.term(1, type='Int'), 2.5)
    self.assertIn('argument 2 of Prelude.plusInt', str(caught.exception))
    self.assertIn('write an int', str(caught.exception))


  def test_nested_term_mismatch_names_position_and_types(self):
    P = curry.import_('Prelude')
    M = curry.import_('Data.Maybe')
    value = curry.eval(P.Just(1)).one()
    with self.assertRaises(curry.MismatchError) as caught:
      P['+'](1.5, M.fromJust(value))
    message = str(caught.exception)
    self.assertIn('argument 1 of Data.Maybe.fromJust', message)
    self.assertIn('expected Maybe Float, got Maybe Int', message)
    self.assertNotIn('TCons', message)
