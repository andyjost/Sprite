'''
Terms: frozen acceptance of Appendix A of python-api-review2.md.

Each row maps a test to the review's lines and the flip lane of
python-api-implementation-plan.md. Section 12 amends metadata access.
  test_term_example: lines 5895-5896; lane 4a.
  test_parse_setup_example: lines 5914; lane 4b.
  test_parse_answer_example: lines 5914-5916; lane 4b.
  test_free_example: lines 5929-5930; lane 4c.
  test_anonymous_example: lines 5940-5941; lane 4c.
  test_choice_example: lines 5953-5954; lane 4c.
  test_let_setup_example: lines 5964; lane 4c.
  test_let_result_example: lines 5964-5966; lane 4c.
  test_symbol_example: lines 5977-5978; lane 4a.
  test_term_sharing_example: lines 5995-5996; lane 4a.
  test_call_example: lines 6019-6020; lane 4a.
  test_infix_example: lines 6074-6075; lane 4c.
  test_var_example: lines 6152-6153; lane 3.
  test_symbol_metadata_example: lines 6198-6199; lane 4a.
  test_datatype_example: lines 6222-6223; 6667-6677; lane 6.
  test_term_identity: lines 5890-5893; lane 4a.
  test_term_type_annotation_unifies: lines 5891-5893; lane 4a.
  test_parse_imports_modules: lines 5901-5903; lane 4b.
  test_parse_imports_names: lines 5901-5903; lane 4b.
  test_parse_type_annotation: lines 5903; lane 4b.
  test_parse_comment_after_free_hides_bindings: lines 5904-5907; lane 4b.
  test_parse_error_position: lines 5908-5909; lane 4b.
  test_parse_overloaded_goal_defaults_at_eval: lines 5909-5910; lane 4b.
  test_free_name_and_anonymous_printing: lines 5921-5924; 6150-6157; lane 4c.
  test_free_type_is_fixed_by_first_goal: lines 5925-5927; lane 4c.
  test_free_explicit_type_guard: lines 5925-5927; lane 4c.
  test_anonymous_occurrences_are_fresh: lines 5934-5945; lane 4c.
  test_choice_is_right_associated: lines 5949-5951; lane 4c.
  test_choices_are_fresh: lines 5949-5951; lane 4c.
  test_choice_type_conversion: lines 5755; lane 4c.
  test_ref_outside_let_is_type_error: lines 5969-5970; lane 4c.
  test_ref_unknown_binding_names_bindings: lines 5969-5970; lane 4c.
  test_qualified_type_imports_on_demand: lines 5981-5982; lane 4a.
  test_evaluation_never_changes_a_term: lines 5990-5991; lane 4d.
  test_structural_equality_and_hash: lines 5991-5992; 6026-6028; lane 4a.
  test_variables_equal_only_by_identity: lines 5992; 6146-6150; lane 3.
  test_term_has_no_truth_value: lines 5993; 6029-6030; lane 4a.
  test_term_root_and_match_args: lines 5999-6008; lane 4a.
  test_free_vars_follow_first_occurrence: lines 6006-6008; lane 4c.
  test_call_typechecks_at_construction: lines 5986-5988; lane 4a.
  test_call_excess_arguments_raises_arity_error: lines 6012-6016; lane 4a.
  test_call_no_arguments_raises_type_error: lines 6015-6017; lane 4a.
  test_choice_dunder: lines 6022-6025; lane 4c.
  test_rchoice_dunder: lines 6022-6025; lane 4c.
  test_shared_subterm_prints_let: lines 6033-6037; lane 4d.
  test_term_repr_includes_type: lines 6039-6040; lane 4a.
  test_add_builds_prelude_term: lines 6042-6062; lane 4c.
  test_add_reflected_builds_prelude_term: lines 6042-6062; lane 4c.
  test_add_foreign_operand_is_not_implemented: lines 6042-6044; lane 4c.
  test_radd_foreign_operand_is_not_implemented: lines 6042-6044; lane 4c.
  test_sub_builds_prelude_term: lines 6042-6062; lane 4c.
  test_sub_reflected_builds_prelude_term: lines 6042-6062; lane 4c.
  test_sub_foreign_operand_is_not_implemented: lines 6042-6044; lane 4c.
  test_rsub_foreign_operand_is_not_implemented: lines 6042-6044; lane 4c.
  test_mul_builds_prelude_term: lines 6042-6062; lane 4c.
  test_mul_reflected_builds_prelude_term: lines 6042-6062; lane 4c.
  test_mul_foreign_operand_is_not_implemented: lines 6042-6044; lane 4c.
  test_rmul_foreign_operand_is_not_implemented: lines 6042-6044; lane 4c.
  test_truediv_builds_prelude_term: lines 6042-6062; lane 4c.
  test_truediv_reflected_builds_prelude_term: lines 6042-6062; lane 4c.
  test_truediv_foreign_operand_is_not_implemented: lines 6042-6044; lane 4c.
  test_rtruediv_foreign_operand_is_not_implemented: lines 6042-6044; lane 4c.
  test_floordiv_builds_prelude_term: lines 6042-6062; lane 4c.
  test_floordiv_reflected_builds_prelude_term: lines 6042-6062; lane 4c.
  test_floordiv_foreign_operand_is_not_implemented: lines 6042-6044; lane 4c.
  test_rfloordiv_foreign_operand_is_not_implemented: lines 6042-6044; lane 4c.
  test_mod_builds_prelude_term: lines 6042-6062; lane 4c.
  test_mod_reflected_builds_prelude_term: lines 6042-6062; lane 4c.
  test_mod_foreign_operand_is_not_implemented: lines 6042-6044; lane 4c.
  test_rmod_foreign_operand_is_not_implemented: lines 6042-6044; lane 4c.
  test_negate_builds_prelude_term: lines 6063-6064; lane 4c.
  test_and_is_concurrent_conjunction: lines 6065-6067; lane 4c.
  test_rand_is_concurrent_conjunction: lines 6065-6067; lane 4c.
  test_and_foreign_operand_is_not_implemented: lines 6042-6044; 6065-6067; lane 4c.
  test_rand_foreign_operand_is_not_implemented: lines 6042-6044; 6065-6067; lane 4c.
  test_comparison_dunders_are_absent: lines 6045-6046; lane 4c.
  test_infix_unknown_operator_is_not_implemented: lines 6068-6072; lane 4c.
  test_reflected_infix: lines 6077; lane 4c.
  test_symbol_metadata_is_not_a_term: lines 6192-6214; lane 4a.
  test_datatype_metadata_and_class: lines 6204-6205; 6217-6231; 6667-6677; lane 6.
  test_var_binding_is_private_to_evaluation: lines 6146-6150; lane 3.
  test_conversion_bool_type: lines 5737-5744; lane 2.
  test_conversion_integer_type: lines 5737-5744; lane 2.
  test_conversion_float_type: lines 5737-5744; lane 2.
  test_conversion_string_type: lines 5737-5744; lane 2.
  test_conversion_char_type: lines 5737-5744; lane 2.
  test_integer_converts_in_float_slot: lines 5738-5740; lane 2.
  test_conversion_rejects_one_tuple: lines 5745-5746; lane 2.
  test_conversion_rejects_sixteen_tuple: lines 5745-5746; lane 2.
  test_tuple_arity_range_and_unit: lines 5745-5746; lane 2.
  test_sequence_converts_to_list: lines 5747-5749; lane 2.
  test_sequence_elements_share_element_type: lines 5747-5749; lane 2.
  test_iterator_is_lazy_and_drawn_once: lines 5750-5752; lane 2.
  test_iterator_bad_element_fails_when_drawn: lines 5750-5752; lane 2.
  test_conversion_rejects_none_with_type_and_spelling: lines 5757-5761; lane 2.
  test_conversion_rejects_bytes_with_type_and_spelling: lines 5757-5761; lane 2.
  test_conversion_rejects_dict_with_type_and_spelling: lines 5757-5761; lane 2.
  test_conversion_rejects_set_with_type_and_spelling: lines 5757-5761; lane 2.
  test_conversion_rejects_function_with_type_and_spelling: lines 5757-5761; lane 2.
  test_conversion_rejects_results_with_list_spelling: lines 5757-5761; lane 2.
  test_bool_does_not_enter_int_slot: lines 5737; lane 2.
  test_float_does_not_enter_int_slot: lines 5742; lane 2.
  test_string_is_data_outside_parse: lines 5909-5912; lane 4b.
  test_symbol_longest_module_prefix: lines 5974-5975; lane 4a.
  test_integer_uses_custom_num_from_int: lines 5738-5740; lane 2.

Examples left out: none. Setup prompts have their own tests; result
tests repeat their setup so they can run independently.
The ChoiceType rule uses the fork's literal spelling inside Python eval.
It remains an expected failure on a Python without that grammar.
'''
import cytest # from ./lib; must be first
import curry
import unittest
import os

FLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'flows')


def setUpModule():
  curry.path.insert(0, FLOW_PATH)


class TestStubTerms(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  def test_term_example(self):
    self.assertEqual(
        (str(curry.term('a')), str(curry.term(curry.Char('a'))), str(curry.term([], type='[Int]')))
      , ('"a"', "'a'", '[]')
      )

  def test_parse_setup_example(self):
    g = curry.parse('xs ++ [3] =:= [1,2,3] where xs free')
    self.assertIsInstance(g, curry.Term)
    self.assertEqual(list(g.free_vars), ['xs'])

  def test_parse_answer_example(self):
    g = curry.parse('xs ++ [3] =:= [1,2,3] where xs free')
    self.assertEqual(str(next(curry.solve(g))), '{xs=[1,2]} True')

  def test_free_example(self):
    P = curry.import_('Prelude')
    x = curry.free('x')
    self.assertEqual(list(curry.eval((P['=:='](x, 1), x, x))), [(True, 1, 1)])

  def test_anonymous_example(self):
    Rule = curry.import_('Rule')
    self.assertEqual(list(curry.eval(Rule.rule('a', curry.anonymous))), ['cmd1', 'cmd2'])

  def test_choice_example(self):
    self.assertEqual(list(curry.eval(curry.choice(1, 2, 3))), [1, 2, 3])

  def test_let_setup_example(self):
    P = curry.import_('Prelude')
    ones = curry.let(curry.ref('a'), a=P[':'](1, curry.ref('a')))
    self.assertIsInstance(ones, curry.Term)

  def test_let_result_example(self):
    P = curry.import_('Prelude')
    ones = curry.let(curry.ref('a'), a=P[':'](1, curry.ref('a')))
    self.assertEqual((str(ones), curry.eval(P.take(3, ones)).one()), ('let a = 1 : a in a', [1, 1, 1]))

  def test_symbol_example(self):
    self.assertEqual(str(curry.symbol('Data.List.nub')), 'nub')

  def test_term_sharing_example(self):
    Coin = curry.import_('Coin')
    t = Coin.coin
    self.assertEqual(
        (list(curry.eval((t, t))), list(curry.eval((Coin.coin, Coin.coin))))
      , ([(0, 0), (1, 1)], [(0, 0), (0, 1), (1, 0), (1, 1)])
      )

  def test_call_example(self):
    P = curry.import_('Prelude')
    Coin = curry.import_('Coin')
    self.assertEqual((str(Coin.inc(1)), str(P.id(Coin.inc, 1))), ('inc 1', 'apply (id inc) 1'))

  def test_infix_example(self):
    self.assertEqual(str(curry.term([1, 2]).__infix__('++', [3])), '[1,2] ++ [3]')

  def test_var_example(self):
    x = curry.free('x')
    self.assertIs(curry.eval(x).one(), x)

  def test_symbol_metadata_example(self):
    Coin = curry.import_('Coin')
    P = curry.import_('Prelude')
    self.assertEqual((Coin.inc.symbol.signature, P['+'].symbol.fixity), ('Int -> Int', 'infixl 6'))

  def test_datatype_example(self):
    Items = curry.import_('Items')
    self.assertEqual([c.name for c in curry.info(Items).types['Item'].constructors], ['A', 'B', 'C'])

  def test_term_identity(self):
    t = curry.term(1)
    self.assertIs(curry.term(t), t)

  def test_term_type_annotation_unifies(self):
    self.assertEqual(curry.typeof(curry.term(1, type='Float')), 'Float')
    with self.assertRaises(curry.CurryTypeError):
      curry.term(True, type='Int')

  def test_parse_imports_modules(self):
    self.assertEqual(curry.eval(curry.parse('Coin.inc 1', imports=[curry.import_('Coin')])).one(), 2)

  def test_parse_imports_names(self):
    self.assertEqual(curry.eval(curry.parse('Coin.inc 1', imports=['Coin'])).one(), 2)

  def test_parse_type_annotation(self):
    g = curry.parse('(read "5") :: Int')
    self.assertEqual(curry.typeof(g), 'Int')
    self.assertEqual(curry.eval(g).one(), 5)

  def test_parse_comment_after_free_hides_bindings(self):
    g = curry.parse('not b where b free -- local declaration')
    self.assertCountEqual([str(a) for a in curry.solve(g)], ['True', 'False'])
    self.assertEqual(dict(g.free_vars), {})

  def test_parse_error_position(self):
    with self.assertRaises(curry.CompileError) as caught:
      curry.parse('1 + )')
    self.assertEqual((caught.exception.line, caught.exception.column), (1, 5))

  def test_parse_overloaded_goal_defaults_at_eval(self):
    g = curry.parse('read "5"')
    with self.assertRaises(curry.DefaultingError):
      curry.eval(g)

  def test_free_name_and_anonymous_printing(self):
    x = curry.free('x')
    a = curry.free()
    b = curry.free()
    self.assertIsInstance(x, curry.Var)
    self.assertEqual(x.name, 'x')
    self.assertIsNone(a.name)
    self.assertEqual(str(curry.term((a, b, x, a))), '(_a,_b,x,_a)')
    self.assertIsNone(x.symbol)
    self.assertEqual(x.args, ())

  def test_free_type_is_fixed_by_first_goal(self):
    P = curry.import_('Prelude')
    x = curry.free('x')
    P.chr(x)
    with self.assertRaises(curry.CurryTypeError):
      P['not'](x)

  def test_free_explicit_type_guard(self):
    P = curry.import_('Prelude')
    x = curry.free('x', type='Int')
    self.assertEqual(curry.typeof(x), 'Int')
    with self.assertRaises(curry.CurryTypeError):
      P['not'](x)

  def test_anonymous_occurrences_are_fresh(self):
    P = curry.import_('Prelude')
    self.assertIsInstance(curry.anonymous, curry.Anonymous)
    g = (P['=:='](curry.anonymous, 1), P['=:='](curry.anonymous, 2))
    self.assertEqual(list(curry.eval(g)), [(True, True)])

  def test_choice_is_right_associated(self):
    t = curry.choice(1, 2, 3)
    self.assertEqual(t, curry.choice(1, curry.choice(2, 3)))

  def test_choices_are_fresh(self):
    self.assertCountEqual(
        list(curry.eval((curry.choice(0, 1), curry.choice(0, 1))))
      , [(0, 0), (0, 1), (1, 0), (1, 1)]
      )

  @unittest.expectedFailure
  def test_choice_type_conversion(self):
    value = eval('1 ? 2')
    self.assertEqual(type(value).__name__, 'ChoiceType')
    self.assertEqual(sorted(curry.eval(curry.term(value))), [1, 2])

  def test_ref_outside_let_is_type_error(self):
    with self.assertRaises(curry.CurryTypeError) as caught:
      curry.term(curry.ref('missing'))
    self.assertIn('missing', str(caught.exception))
    self.assertIn('binding', str(caught.exception))

  def test_ref_unknown_binding_names_bindings(self):
    with self.assertRaises(curry.CurryTypeError) as caught:
      curry.let(curry.ref('missing'), a=1)
    self.assertIn('missing', str(caught.exception))
    self.assertIn('a', str(caught.exception))

  def test_qualified_type_imports_on_demand(self):
    dt = curry.type('Peano.Nat')
    self.assertIsInstance(dt, curry.DataType)
    self.assertIs(dt, curry.info(curry.modules['Peano']).types['Nat'])

  def test_evaluation_never_changes_a_term(self):
    Coin = curry.import_('Coin')
    t = Coin.double(Coin.coin)
    text = str(t)
    self.assertCountEqual(list(curry.eval(t)), [0, 2])
    self.assertEqual(str(t), text)
    self.assertCountEqual(list(curry.eval(t)), [0, 2])
    self.assertEqual(str(t), text)

  def test_structural_equality_and_hash(self):
    Coin = curry.import_('Coin')
    a = Coin.inc(1)
    b = Coin.inc(1)
    self.assertIsNot(a, b)
    self.assertIs(a == b, True)
    self.assertEqual(hash(a), hash(b))
    self.assertIs(a == object(), False)
    self.assertIs(a == 2, False)

  def test_variables_equal_only_by_identity(self):
    x = curry.free('x')
    y = curry.free('x')
    self.assertIs(x == x, True)
    self.assertIs(x == y, False)
    self.assertEqual(len({x, y}), 2)

  def test_term_has_no_truth_value(self):
    with self.assertRaises(TypeError):
      bool(curry.term(True))

  def test_term_root_and_match_args(self):
    Coin = curry.import_('Coin')
    t = Coin.inc(1)
    self.assertEqual(curry.Term.__match_args__, ('symbol', 'args'))
    self.assertIsInstance(t.symbol, curry.Symbol)
    self.assertEqual(t.symbol.name, 'inc')
    self.assertIsInstance(t.args, tuple)
    self.assertTrue(all(isinstance(a, curry.Term) for a in t.args))
    self.assertEqual([str(a) for a in t.args], ['1'])
    self.assertIsNone(curry.term(1).symbol)
    self.assertEqual(len(curry.term([1, 2]).args), 2)

  def test_free_vars_follow_first_occurrence(self):
    x = curry.free('x')
    y = curry.free('y')
    t = curry.term((y, x, y, curry.free()))
    self.assertEqual(list(t.free_vars), ['y', 'x'])
    self.assertIs(t.free_vars['x'], x)
    self.assertIs(t.free_vars['y'], y)

  def test_call_typechecks_at_construction(self):
    Coin = curry.import_('Coin')
    with self.assertRaises(curry.CurryTypeError):
      Coin.inc('a')

  def test_call_excess_arguments_raises_arity_error(self):
    Coin = curry.import_('Coin')
    with self.assertRaises(curry.ArityError):
      Coin.inc(1, 2)

  def test_call_no_arguments_raises_type_error(self):
    Coin = curry.import_('Coin')
    with self.assertRaises(TypeError):
      Coin.coin()

  def test_choice_dunder(self):
    t = curry.term(1)
    self.assertCountEqual(list(curry.eval(t.__choice__(2))), [1, 2])

  def test_rchoice_dunder(self):
    t = curry.term(1)
    self.assertCountEqual(list(curry.eval(t.__rchoice__(2))), [2, 1])

  def test_shared_subterm_prints_let(self):
    Coin = curry.import_('Coin')
    P = curry.import_('Prelude')
    c = Coin.coin
    self.assertEqual(str(P['+'](c, c)), 'let x1 = coin in x1 + x1')
    self.assertEqual(str(P['+'](Coin.coin, Coin.coin)), 'coin + coin')

  def test_term_repr_includes_type(self):
    Coin = curry.import_('Coin')
    self.assertEqual(repr(Coin.inc(1)), '<Term inc 1 :: Int>')

  def test_add_builds_prelude_term(self):
    t = curry.term(7) + 2
    self.assertIsInstance(t, curry.Term)
    self.assertEqual(curry.eval(t).one(), 9)

  def test_add_reflected_builds_prelude_term(self):
    t = 2 + curry.term(7)
    self.assertIsInstance(t, curry.Term)
    self.assertEqual(curry.eval(t).one(), 9)

  def test_add_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(1).__add__(object()), NotImplemented)

  def test_radd_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(1).__radd__(object()), NotImplemented)

  def test_sub_builds_prelude_term(self):
    t = curry.term(7) - 2
    self.assertIsInstance(t, curry.Term)
    self.assertEqual(curry.eval(t).one(), 5)

  def test_sub_reflected_builds_prelude_term(self):
    t = 9 - curry.term(4)
    self.assertIsInstance(t, curry.Term)
    self.assertEqual(curry.eval(t).one(), 5)

  def test_sub_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(1).__sub__(object()), NotImplemented)

  def test_rsub_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(1).__rsub__(object()), NotImplemented)

  def test_mul_builds_prelude_term(self):
    t = curry.term(7) * 2
    self.assertIsInstance(t, curry.Term)
    self.assertEqual(curry.eval(t).one(), 14)

  def test_mul_reflected_builds_prelude_term(self):
    t = 2 * curry.term(7)
    self.assertIsInstance(t, curry.Term)
    self.assertEqual(curry.eval(t).one(), 14)

  def test_mul_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(1).__mul__(object()), NotImplemented)

  def test_rmul_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(1).__rmul__(object()), NotImplemented)

  def test_truediv_builds_prelude_term(self):
    t = curry.term(7.0) / 2
    self.assertIsInstance(t, curry.Term)
    self.assertEqual(curry.eval(t).one(), 3.5)

  def test_truediv_reflected_builds_prelude_term(self):
    t = 7 / curry.term(2.0)
    self.assertIsInstance(t, curry.Term)
    self.assertEqual(curry.eval(t).one(), 3.5)

  def test_truediv_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(1).__truediv__(object()), NotImplemented)

  def test_rtruediv_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(1).__rtruediv__(object()), NotImplemented)

  def test_floordiv_builds_prelude_term(self):
    t = curry.term(-7) // 2
    self.assertIsInstance(t, curry.Term)
    self.assertEqual(curry.eval(t).one(), -4)

  def test_floordiv_reflected_builds_prelude_term(self):
    t = -7 // curry.term(2)
    self.assertIsInstance(t, curry.Term)
    self.assertEqual(curry.eval(t).one(), -4)

  def test_floordiv_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(1).__floordiv__(object()), NotImplemented)

  def test_rfloordiv_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(1).__rfloordiv__(object()), NotImplemented)

  def test_mod_builds_prelude_term(self):
    t = curry.term(-7) % 2
    self.assertIsInstance(t, curry.Term)
    self.assertEqual(curry.eval(t).one(), 1)

  def test_mod_reflected_builds_prelude_term(self):
    t = -7 % curry.term(2)
    self.assertIsInstance(t, curry.Term)
    self.assertEqual(curry.eval(t).one(), 1)

  def test_mod_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(1).__mod__(object()), NotImplemented)

  def test_rmod_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(1).__rmod__(object()), NotImplemented)

  def test_negate_builds_prelude_term(self):
    self.assertEqual(curry.eval(-curry.term(3)).one(), -3)

  def test_and_is_concurrent_conjunction(self):
    self.assertIs(curry.eval(curry.term(True) & False).one(), False)

  def test_rand_is_concurrent_conjunction(self):
    self.assertIs(curry.eval(True & curry.term(False)).one(), False)

  def test_and_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(True).__and__(object()), NotImplemented)

  def test_rand_foreign_operand_is_not_implemented(self):
    self.assertIs(curry.term(True).__rand__(object()), NotImplemented)

  def test_comparison_dunders_are_absent(self):
    with self.assertRaises(TypeError):
      curry.term(1) < curry.term(2)

  def test_infix_unknown_operator_is_not_implemented(self):
    self.assertIs(curry.term(1).__infix__('unknownOperator', 2), NotImplemented)

  def test_reflected_infix(self):
    self.assertEqual(str(curry.term([3]).__rinfix__('++', [1, 2])), '[1,2] ++ [3]')

  def test_symbol_metadata_is_not_a_term(self):
    Coin = curry.import_('Coin')
    sym = Coin.inc.symbol
    self.assertIsInstance(sym, curry.Symbol)
    self.assertNotIsInstance(sym, curry.Term)
    self.assertEqual(
        (sym.name, sym.fullname, sym.kind, sym.arity, sym.signature, sym.public, sym.fixity, sym.fields)
      , ('inc', 'Coin.inc', 'function', 1, 'Int -> Int', True, None, None)
      )
    self.assertIs(sym.module, Coin)
    self.assertEqual(curry.term(sym), Coin.inc)
    self.assertIn('Int -> Int', Coin.inc.__doc__)

  @unittest.expectedFailure
  def test_datatype_metadata_and_class(self):
    Geo = curry.import_('Geo')
    dt = curry.info(Geo).types['Tree']
    self.assertIsInstance(dt, curry.DataType)
    self.assertEqual((dt.name, dt.fullname), ('Tree', 'Geo.Tree'))
    self.assertIs(dt.module, Geo)
    self.assertIsInstance(dt.constructors, tuple)
    self.assertTrue(all(isinstance(c, curry.Symbol) for c in dt.constructors))
    self.assertEqual([c.kind for c in dt.constructors], ['constructor', 'constructor'])
    self.assertTrue(issubclass(dt.cls, curry.Data))
    self.assertIs(Geo.Node.datatype.cls, dt.cls)

  def test_var_binding_is_private_to_evaluation(self):
    P = curry.import_('Prelude')
    x = curry.free('x')
    self.assertEqual(curry.eval((P['=:='](x, 1), x)).one(), (True, 1))
    self.assertIs(curry.eval(x).one(), x)
    self.assertEqual(curry.eval((P['=:='](x, 2), x)).one(), (True, 2))
    self.assertIs(curry.eval([x]).one()[0], x)

  def test_conversion_bool_type(self):
    self.assertEqual(curry.typeof(curry.term(True)), 'Bool')

  def test_conversion_integer_type(self):
    self.assertEqual(curry.typeof(curry.term(1)), 'Num a => a')

  def test_conversion_float_type(self):
    self.assertEqual(curry.typeof(curry.term(1.5)), 'Float')

  def test_conversion_string_type(self):
    self.assertEqual(curry.typeof(curry.term('a')), '[Char]')

  def test_conversion_char_type(self):
    self.assertEqual(curry.typeof(curry.term(curry.Char('a'))), 'Char')

  def test_integer_converts_in_float_slot(self):
    P = curry.import_('Prelude')
    self.assertEqual(curry.eval(P.sqrt(4)).one(), 2.0)

  def test_conversion_rejects_one_tuple(self):
    with self.assertRaises(curry.ConversionError):
      curry.term((1,))

  def test_conversion_rejects_sixteen_tuple(self):
    with self.assertRaises(curry.ConversionError):
      curry.term(tuple(range(16)))

  @unittest.expectedFailure
  def test_tuple_arity_range_and_unit(self):
    self.assertEqual(curry.eval(curry.term(())).one(), ())
    for count in (2, 15):
      value = tuple(range(count))
      self.assertEqual(curry.eval(curry.term(value)).one(), value)

  def test_sequence_converts_to_list(self):
    from collections import UserList
    for value in (range(3), UserList([0, 1, 2])):
      self.assertEqual(curry.eval(curry.term(value)).one(), [0, 1, 2])

  def test_sequence_elements_share_element_type(self):
    with self.assertRaises(curry.CurryTypeError):
      curry.term([1, True])

  def test_iterator_is_lazy_and_drawn_once(self):
    drawn = []
    def items():
      for n in range(3):
        drawn.append(n)
        yield n
    t = curry.term(iter(items()), type='[Int]')
    self.assertEqual(drawn, [])
    P = curry.import_('Prelude')
    self.assertEqual(curry.eval(P.take(2, t)).one(), [0, 1])
    self.assertEqual(drawn, [0, 1])
    self.assertEqual(curry.eval(P.take(2, t)).one(), [0, 1])
    self.assertEqual(drawn, [0, 1])

  @unittest.expectedFailure
  def test_iterator_bad_element_fails_when_drawn(self):
    P = curry.import_('Prelude')
    t = curry.term(iter([1, 'bad']), type='[Int]')
    self.assertEqual(curry.eval(P.take(1, t)).one(), [1])
    with self.assertRaises(curry.ConversionError):
      curry.eval(P.take(2, t)).one()

  def test_conversion_rejects_none_with_type_and_spelling(self):
    with self.assertRaises(curry.ConversionError) as caught:
      curry.term(None)
    self.assertIn('NoneType', str(caught.exception))
    self.assertIn('P.Nothing', str(caught.exception))

  def test_conversion_rejects_bytes_with_type_and_spelling(self):
    with self.assertRaises(curry.ConversionError) as caught:
      curry.term(b'a')
    self.assertIn('bytes', str(caught.exception))
    self.assertIn('decode', str(caught.exception))

  def test_conversion_rejects_dict_with_type_and_spelling(self):
    with self.assertRaises(curry.ConversionError) as caught:
      curry.term({'a': 1})
    self.assertIn('dict', str(caught.exception))
    self.assertIn('list(d.items())', str(caught.exception))

  def test_conversion_rejects_set_with_type_and_spelling(self):
    with self.assertRaises(curry.ConversionError) as caught:
      curry.term({1, 2})
    self.assertIn('set', str(caught.exception))

  def test_conversion_rejects_function_with_type_and_spelling(self):
    with self.assertRaises(curry.ConversionError) as caught:
      curry.term((lambda: 1))
    self.assertIn('function', str(caught.exception))

  def test_conversion_rejects_results_with_list_spelling(self):
    results = curry.eval(1)
    self.addCleanup(results.close)
    with self.assertRaises(curry.ConversionError) as caught:
      curry.term(results)
    self.assertIn('Results', str(caught.exception))
    self.assertIn('list(', str(caught.exception))

  def test_bool_does_not_enter_int_slot(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.CurryTypeError):
      P.chr(True)

  def test_float_does_not_enter_int_slot(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.CurryTypeError):
      P.chr(1.0)

  def test_string_is_data_outside_parse(self):
    self.assertEqual(curry.eval(curry.term('1 + 2')).one(), '1 + 2')

  def test_symbol_longest_module_prefix(self):
    t = curry.symbol('Data.List.nub')
    self.assertEqual(t.symbol.fullname, 'Data.List.nub')
    self.assertIs(t.symbol.module, curry.modules['Data.List'])

  def test_integer_uses_custom_num_from_int(self):
    M = curry.import_('TypeCheck')
    self.assertEqual(curry.eval(M.toInt(3)).one(), 3)


if __name__ == '__main__':
  unittest.main()
