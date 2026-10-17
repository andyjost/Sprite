'''
Values: frozen acceptance of Appendix A of python-api-review2.md.

Each row maps a test to the review's lines and the flip lane of
python-api-implementation-plan.md. Section 12 amends metadata access.
  test_data_point_example: lines 6111-6112; lane 6.
  test_data_tree_setup_example: lines 6113; lane 6.
  test_data_tree_class_example: lines 6113-6115; 6667-6677; lane 6.
  test_data_match_example: lines 6113-6118; lane 6.
  test_function_example: lines 6136-6137; lane 2.
  test_values_example: lines 6170-6171; lane 2.
  test_char_example: lines 6186-6187; lane 2.
  test_data_equality_and_hash: lines 6081-6084; lane 6.
  test_data_without_ord_rejects_ordering: lines 6084-6085; lane 6.
  test_data_with_ord_uses_curry_compare: lines 6084-6085; lane 6.
  test_data_truth_and_no_length: lines 6086-6088; lane 6.
  test_data_round_trip: lines 6087-6088; lane 2.
  test_constructor_type_and_class_relationship: lines 6090-6096; 6667-6677; lane 6.
  test_record_match_uses_field_names: lines 6094-6096; 6212-6214; lane 6.
  test_constructor_values_terms_and_partial_application: lines 6096-6099; lane 6.
  test_constructor_class_in_term_positions: lines 6100-6103; lane 6.
  test_nullary_constructor_is_not_a_class: lines 6103-6106; lane 6.
  test_constructor_shadows_type_name: lines 6106-6109; 6667-6677; lane 6.
  test_builtin_values_are_python_data: lines 5711-5719; 6108-6109; lane 2.
  test_function_is_callable_and_structurally_equal: lines 6129-6140; lane 2.
  test_values_are_a_multiset: lines 6159-6164; lane 2.
  test_empty_values_are_false_and_a_value: lines 6163-6164; lane 2.
  test_values_printing: lines 6164; lane 1.
  test_set0_weak_encapsulation_depends_on_first_owner: lines 6165-6168; lane 2.
  test_set1_keeps_argument_choice_outside: lines 6167-6168; lane 2.
  test_char_is_a_string_with_same_hash: lines 6178-6184; lane 2.
  test_char_rejects_empty_string: lines 6181-6184; lane 2.
  test_char_rejects_long_string: lines 6181-6184; lane 2.
  test_char_slot_requires_char: lines 6183-6184; lane 2.
  test_value_table_bool: lines 5711-5725; lane 2.
  test_value_table_int: lines 5711-5725; lane 2.
  test_value_table_float: lines 5711-5725; lane 2.
  test_value_table_char: lines 5711-5725; lane 2.
  test_value_table_string: lines 5711-5725; lane 2.
  test_value_table_empty_string: lines 5711-5725; lane 2.
  test_value_table_list: lines 5711-5725; lane 2.
  test_value_table_tuple: lines 5711-5725; lane 2.
  test_value_conversion_reaches_nested_positions: lines 5704-5725; lane 2.
  test_io_action_yields_its_converted_result: lines 5721; lane 3.
  test_generic_data_pattern: lines 6095-6096; lane 6.
  test_constructor_class_as_map_argument: lines 6100-6103; lane 6.

Examples left out: none. Setup prompts have their own tests; result
tests repeat their setup so they can run independently.
Fixture StubRecord adds one record field and Ord for the rules at
6084-6085, 6094-6096 and 6212-6214. Geo deliberately has no Ord.
'''
import cytest # from ./lib; must be first
import curry
import unittest
import os
from collections.abc import Collection

FLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'flows')


def setUpModule():
  curry.path.insert(0, FLOW_PATH)


class TestStubValues(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  @unittest.expectedFailure
  def test_data_point_example(self):
    Geo = curry.import_('Geo')
    p = curry.eval(Geo.origin).one()
    self.assertEqual(
        (p.symbol.name, p.args, str(p), p == Geo.Point(0, 0))
      , ('Point', (0, 0), 'Point 0 0', True)
      )

  @unittest.expectedFailure
  def test_data_tree_setup_example(self):
    Geo = curry.import_('Geo')
    t = curry.eval(Geo.Node(Geo.Leaf, -1, Geo.Leaf)).one()
    self.assertIsInstance(t, curry.Data)

  @unittest.expectedFailure
  def test_data_tree_class_example(self):
    Geo = curry.import_('Geo')
    t = curry.eval(Geo.Node(Geo.Leaf, -1, Geo.Leaf)).one()
    self.assertEqual((type(t).__name__, isinstance(t, curry.info(Geo).types['Tree'].cls)), ('Node', True))

  @unittest.expectedFailure
  def test_data_match_example(self):
    Geo = curry.import_('Geo')
    t = curry.eval(Geo.Node(Geo.Leaf, -1, Geo.Leaf)).one()
    match t:
      case Geo.Node(Geo.Leaf, x, Geo.Leaf):
        self.assertEqual(x, -1)
      case _:
        self.fail('Node pattern did not match')

  @unittest.expectedFailure
  def test_function_example(self):
    Coin = curry.import_('Coin')
    f = curry.eval(Coin.inc).one()
    self.assertEqual((str(f), curry.eval(f(41)).one()), ('inc', 42))

  @unittest.expectedFailure
  def test_values_example(self):
    SF = curry.import_('Control.SetFunctions')
    Coin = curry.import_('Coin')
    self.assertEqual(sorted(curry.eval(SF.set0(Coin.coin)).one()), [0, 1])

  @unittest.expectedFailure
  def test_char_example(self):
    P = curry.import_('Prelude')
    c = curry.eval(P.chr(65)).one()
    self.assertEqual((type(c).__name__, c == 'A', curry.show(c)), ('Char', True, "'A'"))

  @unittest.expectedFailure
  def test_data_equality_and_hash(self):
    P = curry.import_('Prelude')
    v = curry.eval(P.Just(5)).one()
    self.assertIsInstance(v, curry.Data)
    self.assertEqual(v, P.Just(5))
    self.assertEqual(hash(v), hash(P.Just(5)))
    self.assertEqual(curry.eval(P.Nothing).one(), P.Nothing)

  @unittest.expectedFailure
  def test_data_without_ord_rejects_ordering(self):
    Geo = curry.import_('Geo')
    a = curry.eval(Geo.Point(0, 0)).one()
    b = curry.eval(Geo.Point(1, 0)).one()
    with self.assertRaises(TypeError):
      a < b

  @unittest.expectedFailure
  def test_data_with_ord_uses_curry_compare(self):
    M = curry.import_('StubRecord')
    a = M.Named(1)
    b = M.Named(2)
    self.assertTrue(a < b)
    self.assertTrue(a <= b)
    self.assertTrue(b > a)
    self.assertTrue(b >= a)

  @unittest.expectedFailure
  def test_data_truth_and_no_length(self):
    P = curry.import_('Prelude')
    v = curry.eval(P.Nothing).one()
    self.assertTrue(bool(v))
    with self.assertRaises(TypeError):
      len(v)

  @unittest.expectedFailure
  def test_data_round_trip(self):
    Geo = curry.import_('Geo')
    v = curry.eval(Geo.Point(2, -3)).one()
    self.assertEqual(curry.eval(Geo.norm1(v)).one(), 5)

  @unittest.expectedFailure
  def test_constructor_type_and_class_relationship(self):
    Geo = curry.import_('Geo')
    tree = curry.info(Geo).types['Tree'].cls
    self.assertTrue(issubclass(tree, curry.Data))
    self.assertTrue(issubclass(Geo.Node, tree))
    self.assertIsInstance(Geo.Leaf, tree)
    self.assertEqual(Geo.Node.__match_args__, ('_0', '_1', '_2'))
    self.assertEqual(curry.Data.__match_args__, ('symbol', 'args'))
    self.assertIs(Geo.Node.datatype.cls, tree)

  @unittest.expectedFailure
  def test_record_match_uses_field_names(self):
    M = curry.import_('StubRecord')
    self.assertEqual(M.Named.__match_args__, ('coordinate',))
    self.assertEqual(M.Named.symbol.fields, ('coordinate',))
    match M.Named(7):
      case M.Named(coordinate=x):
        self.assertEqual(x, 7)
      case _:
        self.fail('record pattern did not match')

  @unittest.expectedFailure
  def test_constructor_values_terms_and_partial_application(self):
    Geo = curry.import_('Geo')
    Coin = curry.import_('Coin')
    self.assertIsInstance(Geo.Point(0, 0), Geo.Point)
    t = Geo.Point(Coin.coin, 0)
    self.assertIsInstance(t, curry.Term)
    self.assertNotIsInstance(t, curry.Data)
    partial = Geo.Point(1)
    self.assertIsInstance(partial, curry.Term)
    self.assertIsInstance(curry.eval(partial).one(), curry.Function)

  @unittest.expectedFailure
  def test_constructor_class_in_term_positions(self):
    P = curry.import_('Prelude')
    Geo = curry.import_('Geo')
    self.assertEqual(str(Geo.Point), 'Point')
    self.assertEqual(curry.term(Geo.Point), Geo.Point)
    self.assertEqual(hash(curry.term(Geo.Point)), hash(Geo.Point))
    self.assertEqual(
        [str(v) for v in curry.eval(P.map(Geo.Point(1), [2, 3])).one()]
      , ['Point 1 2', 'Point 1 3']
      )
    self.assertEqual(len(list(curry.eval(curry.choice(Geo.Point, Geo.Point)))), 2)

  @unittest.expectedFailure
  def test_nullary_constructor_is_not_a_class(self):
    Geo = curry.import_('Geo')
    with self.assertRaises(TypeError):
      isinstance(Geo.Leaf, Geo.Leaf)
    self.assertIsInstance(Geo.Leaf, curry.info(Geo).types['Tree'].cls)

  @unittest.expectedFailure
  def test_constructor_shadows_type_name(self):
    Geo = curry.import_('Geo')
    self.assertIsNot(Geo.Point, curry.info(Geo).types['Point'].cls)
    self.assertTrue(issubclass(Geo.Point, curry.info(Geo).types['Point'].cls))

  @unittest.expectedFailure
  def test_builtin_values_are_python_data(self):
    P = curry.import_('Prelude')
    self.assertIs(type(curry.eval(P['True']).one()), bool)
    self.assertIs(type(curry.eval(curry.term([1, 2])).one()), list)
    self.assertIs(type(curry.eval(curry.term((1, 2))).one()), tuple)

  @unittest.expectedFailure
  def test_function_is_callable_and_structurally_equal(self):
    Coin = curry.import_('Coin')
    f = curry.eval(Coin.inc).one()
    self.assertIsInstance(f, curry.Function)
    self.assertIsInstance(f, curry.Term)
    self.assertTrue(callable(f))
    self.assertEqual(f, Coin.inc)
    self.assertEqual(f.symbol.name, 'inc')
    self.assertEqual(f.args, ())

  @unittest.expectedFailure
  def test_values_are_a_multiset(self):
    SF = curry.import_('Control.SetFunctions')
    v = curry.eval(SF.set0(curry.choice(0, 1, 1))).one()
    w = curry.eval(SF.set0(curry.choice(1, 0, 1))).one()
    self.assertIsInstance(v, curry.Values)
    self.assertIsInstance(v, Collection)
    self.assertEqual(len(v), 3)
    self.assertIn(1, v)
    self.assertNotIn(2, v)
    self.assertEqual(sorted(v), [0, 1, 1])
    self.assertEqual(v, w)
    self.assertNotEqual(v, curry.eval(SF.set0(curry.choice(0, 1))).one())
    self.assertTrue(bool(v))

  @unittest.expectedFailure
  def test_empty_values_are_false_and_a_value(self):
    SF = curry.import_('Control.SetFunctions')
    P = curry.import_('Prelude')
    v = curry.eval(SF.set0(P.failed)).one()
    self.assertIsInstance(v, curry.Values)
    self.assertFalse(bool(v))
    self.assertEqual(len(v), 0)
    self.assertEqual(list(v), [])

  @unittest.expectedFailure
  def test_values_printing(self):
    SF = curry.import_('Control.SetFunctions')
    Coin = curry.import_('Coin')
    self.assertEqual(str(curry.eval(SF.set0(Coin.coin)).one()), 'Values [0,1]')

  @unittest.expectedFailure
  def test_set0_weak_encapsulation_depends_on_first_owner(self):
    Coin = curry.import_('Coin')
    SF = curry.import_('Control.SetFunctions')
    t = Coin.coin
    a = [(sorted(v), n) for v, n in curry.eval((SF.set0(t), t))]
    t = Coin.coin
    b = [(n, sorted(v)) for n, v in curry.eval((t, SF.set0(t)))]
    self.assertCountEqual(a, [([0, 1], 0), ([0, 1], 1)])
    self.assertCountEqual(b, [(0, [0]), (1, [1])])

  @unittest.expectedFailure
  def test_set1_keeps_argument_choice_outside(self):
    Coin = curry.import_('Coin')
    SF = curry.import_('Control.SetFunctions')
    P = curry.import_('Prelude')
    self.assertCountEqual([sorted(v) for v in curry.eval(SF.set1(P.id, Coin.coin))], [[0], [1]])

  @unittest.expectedFailure
  def test_char_is_a_string_with_same_hash(self):
    c = curry.Char('a')
    self.assertIsInstance(c, str)
    self.assertEqual(len(c), 1)
    self.assertEqual(c, 'a')
    self.assertEqual(hash(c), hash('a'))
    self.assertIs(type(curry.eval(curry.term(c)).one()), curry.Char)

  @unittest.expectedFailure
  def test_char_rejects_empty_string(self):
    with self.assertRaises(ValueError):
      curry.Char('')

  @unittest.expectedFailure
  def test_char_rejects_long_string(self):
    with self.assertRaises(ValueError):
      curry.Char('ab')

  @unittest.expectedFailure
  def test_char_slot_requires_char(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.ConversionError):
      P.ord('a')
    self.assertEqual(curry.eval(P.ord(curry.Char('a'))).one(), 97)

  @unittest.expectedFailure
  def test_value_table_bool(self):
    P = curry.import_('Prelude')
    self.assertIs(type(curry.eval(P['True']).one()), bool)

  @unittest.expectedFailure
  def test_value_table_int(self):
    P = curry.import_('Prelude')
    self.assertIs(type(curry.eval(curry.term(1, type='Int')).one()), int)

  @unittest.expectedFailure
  def test_value_table_float(self):
    P = curry.import_('Prelude')
    self.assertIs(type(curry.eval(curry.term(1.5)).one()), float)

  @unittest.expectedFailure
  def test_value_table_char(self):
    P = curry.import_('Prelude')
    self.assertIs(type(curry.eval(P.chr(65)).one()), curry.Char)

  @unittest.expectedFailure
  def test_value_table_string(self):
    P = curry.import_('Prelude')
    self.assertIs(type(curry.eval(curry.term('ab')).one()), str)

  @unittest.expectedFailure
  def test_value_table_empty_string(self):
    P = curry.import_('Prelude')
    self.assertIs(type(curry.eval(curry.term('', type='[Char]')).one()), str)

  @unittest.expectedFailure
  def test_value_table_list(self):
    P = curry.import_('Prelude')
    self.assertIs(type(curry.eval(curry.term([1, 2])).one()), list)

  @unittest.expectedFailure
  def test_value_table_tuple(self):
    P = curry.import_('Prelude')
    self.assertIs(type(curry.eval(curry.term((1, 2))).one()), tuple)

  @unittest.expectedFailure
  def test_value_conversion_reaches_nested_positions(self):
    P = curry.import_('Prelude')
    value = curry.eval(curry.term([(True, 1, P.chr(65), 'ab')])).one()
    self.assertEqual(value, [(True, 1, 'A', 'ab')])
    self.assertIs(type(value[0][0]), bool)
    self.assertIs(type(value[0][2]), curry.Char)
    self.assertIs(type(value[0][3]), str)

  @unittest.expectedFailure
  def test_io_action_yields_its_converted_result(self):
    P = curry.import_('Prelude')
    action = curry.term(P['return'](42), type='IO Int')
    self.assertEqual(curry.eval(action).one(), 42)

  @unittest.expectedFailure
  def test_generic_data_pattern(self):
    Geo = curry.import_('Geo')
    Data = curry.Data
    match Geo.Point(1, 2):
      case Data(sym, args):
        self.assertEqual((sym.name, args), ('Point', (1, 2)))
      case _:
        self.fail('Data pattern did not match')

  @unittest.expectedFailure
  def test_constructor_class_as_map_argument(self):
    P = curry.import_('Prelude')
    Peano = curry.import_('Peano')
    values = curry.eval(P.map(Peano.S, [Peano.O])).one()
    self.assertEqual([str(v) for v in values], ['S O'])


if __name__ == '__main__':
  unittest.main()
