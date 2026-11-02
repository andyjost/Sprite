'''Reuse of typed terms at the Python boundary (including issue #181).'''
import cytest
import curry
from unittest.mock import patch
from curry.objects.terms import Term, _graph_key
from curry.typecheck import engine


class TestBoundaryReuse(cytest.TestCase):
  def setUp(self):
    self.P = curry.import_('Prelude')

  def chain(self, depth):
    value = 1
    for _ in range(depth):
      value = self.P.Just(value)
    return value

  def inference_calls(self, function):
    calls = []
    original = engine.Problem._infer
    def infer(problem):
      calls.append(problem)
      return original(problem)
    with patch.object(engine.Problem, '_infer', infer):
      function()
    return len(calls)

  def test_issue181_one_more_level_types_only_the_new_application(self):
    small, large = self.chain(4), self.chain(64)
    count = self.inference_calls(lambda: self.P.Just(small))
    self.assertLessEqual(count, 1)
    self.assertEqual(self.inference_calls(lambda: self.P.Just(large)), count)

  def test_eval_uses_the_recorded_type(self):
    goal = self.P['+'](1, 2)
    self.assertEqual(self.inference_calls(lambda: curry.eval(goal).one()), 0)
    self.assertEqual(self.inference_calls(lambda: curry.solve(goal).one()), 0)

  def test_stream_uses_the_recorded_type(self):
    action = self.P.returnIO(1)
    def run():
      stream = curry.stream(action)
      self.assertEqual(list(stream), [])
      self.assertEqual(stream.result, 1)
    self.assertEqual(self.inference_calls(run), 0)

  def test_evaluation_copies_the_graph(self):
    goal = self.P['+'](self.P['?'](1, 2), 3)
    before = str(goal)
    graph_before = _graph_key(goal._node)
    self.assertEqual(list(curry.eval(goal)), [4, 5])
    self.assertEqual(str(goal), before)
    self.assertEqual(_graph_key(goal._node), graph_before)
    self.assertEqual(list(curry.eval(goal)), [4, 5])

  def test_solve_keeps_named_unnamed_and_anonymous_variables(self):
    x, y = curry.free('x'), curry.free(None)
    goal = curry.term((self.P['=:='](x, 1), self.P['=:='](y, 2), curry.anonymous))
    for _ in range(2):
      answer = curry.solve(goal).one()
      self.assertEqual(answer.bindings[x], 1)
      self.assertEqual(answer.bindings['x'], 1)
      self.assertEqual(answer.bindings[y], 2)
      self.assertEqual(sorted(answer.bindings.values()), [1, 2])
      self.assertEqual(answer.bindings[str(y)], 2)

  def test_success_does_not_format_the_goal(self):
    goal = self.P['+'](1, 2)
    with patch.object(Term, '__str__', side_effect=AssertionError('formatted goal')):
      self.assertEqual(curry.eval(goal).one(), 3)

  def test_failure_messages_keep_the_goal(self):
    goal = self.P.failed
    expected = 'No value found: %s' % goal
    with self.assertRaises(curry.NoValueError) as caught:
      curry.eval(goal).one()
    self.assertEqual(str(caught.exception), expected)

  def test_internal_goal_failure_keeps_its_original_name(self):
    from curry.typecheck.goals import Goal
    node = cytest.raw.interp().expr(self.P.failed)
    expected = 'No value found: %s' % node.info.name
    with self.assertRaises(curry.NoValueError) as caught:
      cytest.raw.interp().eval(Goal(node)).one()
    self.assertEqual(str(caught.exception), expected)

  def test_context_can_specialize_a_previously_defaulted_literal(self):
    value = self.P.Just(self.P.Just(1))
    result = curry.eval(curry.term(value, type='Maybe (Maybe Float)')).one()
    self.assertEqual(result.args[0].args, (1.0,))
    self.assertIs(type(result.args[0].args[0]), float)

  def test_unary_wrappers_keep_free_variable_types_and_bindings(self):
    x = curry.free('x')
    goal = self.P.Just(self.P.Just(self.P.id(x)))
    self.assertEqual(curry.typeof(goal), 'Data a => Maybe (Maybe a)')
    answer = curry.solve(goal).one()
    self.assertIs(answer.bindings[x], x)
    self.assertIs(answer.value.args[0].args[0], x)

  def test_iterator_source_is_consumed_once_across_evaluations(self):
    consumed = []
    def source():
      for item in range(3):
        consumed.append(item)
        yield item
    goal = curry.term(source(), type='[Int]')
    self.assertEqual(curry.eval(goal).one(), [0, 1, 2])
    self.assertEqual(curry.eval(goal).one(), [0, 1, 2])
    self.assertEqual(consumed, [0, 1, 2])

  def test_held_iterator_keeps_its_defaulting_environment(self):
    raw = self.P.map(self.P.show, iter([1, 2]))
    held = self.P.map(self.P.show, curry.term(iter([1, 2])))
    errors = []
    for goal in (raw, held):
      with self.assertRaises(curry.CurryTypeError) as caught:
        curry.eval(goal)
      errors.append(str(caught.exception))
    self.assertEqual(errors[0], errors[1])
    self.assertIn('state the type', errors[1])
    errors = []
    for value in (iter([1, 2]), curry.term(iter([1, 2]))):
      with self.assertRaises(curry.CurryTypeError) as caught:
        cytest.raw.interp().eval(self.P.map, self.P.show, value)
      errors.append(str(caught.exception))
    self.assertEqual(errors[0], errors[1])
    self.assertIn('the element type of an iterator', errors[1])

  def test_symbol_term_is_cached(self):
    first = self.P.id
    with patch.object(Term, '__init__', side_effect=AssertionError('rebuilt symbol term')):
      second = self.P.id
    self.assertIsNot(first, second)
    self.assertIs(first.symbol, second.symbol)
    self.assertEqual(first._node.id(), second._node.id())
    self.assertFalse(self.P.Just == list)
    self.assertFalse(self.P.Just == tuple)

  def test_constructor_equality_keeps_false_for_unrelated_objects(self):
    class ReverseEquality:
      def __eq__(self, other):
        raise AssertionError('reverse equality was called')
    self.assertIs(self.P.Just == ReverseEquality(), False)

  def test_nullary_function_occurrences_keep_independent_choices(self):
    module = curry.compile('coin :: Int\ncoin = 0 ? 1')
    held = module.coin
    self.assertEqual(sorted(curry.eval(held + held)), [0, 2])
    self.assertEqual(sorted(set(curry.eval(module.coin + module.coin))), [0, 1, 2])

  def test_nullary_function_template_keeps_defaulted_dictionaries(self):
    module = curry.compile('coin = 1 ? 2')
    goal = module.coin
    self.assertEqual(list(curry.eval(goal)), [1, 2])
    self.assertEqual(list(curry.eval(goal)), [1, 2])
    self.assertEqual(list(curry.eval(curry.term(goal, type='Float'))), [1.0, 2.0])
