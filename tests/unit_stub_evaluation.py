'''
Evaluation: frozen acceptance of Appendix A of python-api-review2.md.

Each row maps a test to the review's lines and the flip lane of
python-api-implementation-plan.md. Section 12 amends metadata access.
  test_eval_example: lines 6278-6279; lane 3.
  test_solve_example: lines 6292-6294; lane 3.
  test_results_context_setup_example: lines 6307; lane 3.
  test_results_context_result_example: lines 6307-6309; lane 3.
  test_results_one_example: lines 6321-6322; lane 3.
  test_bindings_setup_example: lines 6337; lane 3.
  test_bindings_result_example: lines 6337-6339; lane 3.
  test_answer_setup_example: lines 6353; lane 3.
  test_answer_result_example: lines 6353-6355; lane 3.
  test_stream_primes_example: lines 6378-6379; lane 7.
  test_stream_three_example: lines 6380-6381; lane 7.
  test_eval_is_lazy_and_errors_at_next: lines 6269-6274; lane 3.
  test_eval_error_keeps_prior_values: lines 6273-6276; lane 3.
  test_eval_bare_string_names_parse_and_term: lines 6275-6276; lane 3.
  test_solve_unbound_aliases_preserve_identity: lines 6284-6289; lane 3.
  test_solve_duplicate_variable_names_rejected_at_call: lines 6289-6290; lane 3.
  test_results_is_iterator_without_length: lines 6297-6314; lane 3.
  test_results_break_keeps_search: lines 6301-6303; lane 3.
  test_results_multiple_searches_can_be_open: lines 6303-6304; lane 3.
  test_results_close_ends_search: lines 6324-6325; lane 3.
  test_results_one_no_value: lines 6316-6319; lane 3.
  test_results_one_many_values: lines 6316-6319; lane 3.
  test_bindings_order_mapping_and_hash: lines 6330-6346; lane 3.
  test_empty_bindings_and_answer_tuple: lines 6333-6335; 6348-6351; lane 3.
  test_stream_result_after_end: lines 6363-6367; 6383-6387; lane 7.
  test_stream_close_drops_paused_run: lines 6367; 6383-6387; lane 7.
  test_stream_nondeterminism_raises: lines 6367-6371; lane 7.
  test_stream_is_lazy: lines 6363-6365; lane 7.
  test_next_default_is_none_when_no_value: lines 6300-6301; lane 3.
  test_stream_returns_whole_values_and_action_result: lines 6365-6373; 6383-6387; lane 7.
  test_stream_error_follows_prior_yields: lines 6367-6370; lane 7.
  test_anonymous_variables_are_not_reported: lines 5923-5924; 6284-6286; lane 3.

Examples left out: none. Setup prompts have their own tests; result
tests repeat their setup so they can run independently.
Fixture StubStream adds a whole-list yield with a non-unit result and a
yield before a nondeterministic value. Primes is the existing stream fixture, using Sprite.Stream of lane 7.
The public stream name is read before importing that fixture.
'''
import cytest # from ./lib; must be first
import curry
import unittest
import os
import itertools
from collections.abc import Iterator, Mapping

FLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'flows')


def setUpModule():
  curry.path.insert(0, FLOW_PATH)


class TestStubEvaluation(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  @unittest.expectedFailure
  def test_eval_example(self):
    Coin = curry.import_('Coin')
    P = curry.import_('Prelude')
    self.assertEqual(
        (list(curry.eval(Coin.coin)), list(curry.eval(P.failed)), list(curry.eval((Coin.coin, 'ab'))))
      , ([0, 1], [], [(0, 'ab'), (1, 'ab')])
      )

  @unittest.expectedFailure
  def test_solve_example(self):
    self.assertEqual(
        [str(a) for a in curry.solve(curry.parse('not b where b free'))]
      , ['{b=False} True', '{b=True} False']
      )

  @unittest.expectedFailure
  def test_results_context_setup_example(self):
    Stream = curry.import_('Stream')
    with curry.eval(Stream.three) as r:
      first = next(r)
    self.assertEqual(first, 1)
    self.assertEqual(list(r), [])

  @unittest.expectedFailure
  def test_results_context_result_example(self):
    Stream = curry.import_('Stream')
    with curry.eval(Stream.three) as r:
      first = next(r)
    self.assertEqual((first, list(r)), (1, []))

  @unittest.expectedFailure
  def test_results_one_example(self):
    Coin = curry.import_('Coin')
    self.assertEqual(curry.eval(Coin.inc(41)).one(), 42)

  @unittest.expectedFailure
  def test_bindings_setup_example(self):
    P = curry.import_('Prelude')
    x = curry.free('x')
    a = next(curry.solve(P['=:='](x, 1)))
    self.assertIsInstance(a.bindings, curry.Bindings)

  @unittest.expectedFailure
  def test_bindings_result_example(self):
    P = curry.import_('Prelude')
    x = curry.free('x')
    a = next(curry.solve(P['=:='](x, 1)))
    self.assertEqual((a.bindings['x'], a.bindings[x], str(a.bindings)), (1, 1, '{x=1}'))

  @unittest.expectedFailure
  def test_answer_setup_example(self):
    a = next(curry.solve(curry.parse('xs ++ [3] =:= [1,2,3] where xs free')))
    self.assertIsInstance(a, curry.Answer)

  @unittest.expectedFailure
  def test_answer_result_example(self):
    a = next(curry.solve(curry.parse('xs ++ [3] =:= [1,2,3] where xs free')))
    self.assertEqual((a.value, a.bindings['xs'], str(a)), (True, [1, 2], '{xs=[1,2]} True'))

  @unittest.expectedFailure
  def test_stream_primes_example(self):
    stream = curry.stream
    Primes = curry.import_('Primes')
    r = stream(Primes.primesOut)
    self.addCleanup(r.close)
    self.assertEqual(list(itertools.islice(r, 5)), [2, 3, 5, 7, 11])

  @unittest.expectedFailure
  def test_stream_three_example(self):
    stream = curry.stream
    Primes = curry.import_('Primes')
    self.assertEqual(list(stream(Primes.threeOut)), [1, 2, 3])

  def test_eval_is_lazy_and_errors_at_next(self):
    P = curry.import_('Prelude')
    r = curry.eval(P.error('boom'))
    with self.assertRaises(curry.EvaluationError):
      next(r)
    self.assertEqual(list(r), [])

  @unittest.expectedFailure
  def test_eval_error_keeps_prior_values(self):
    Stream = curry.import_('Stream')
    r = curry.eval(Stream.mixed)
    self.assertEqual(next(r), 1)
    with self.assertRaises(curry.EvaluationError):
      next(r)
    self.assertEqual(list(r), [])

  @unittest.expectedFailure
  def test_eval_bare_string_names_parse_and_term(self):
    with self.assertRaises(curry.ConversionError) as caught:
      curry.eval('1 + 2')
    self.assertIn('parse', str(caught.exception))
    self.assertIn('term', str(caught.exception))

  @unittest.expectedFailure
  def test_solve_unbound_aliases_preserve_identity(self):
    P = curry.import_('Prelude')
    x = curry.free('x')
    y = curry.free('y')
    a = next(curry.solve(P['=:='](x, y)))
    self.assertIs(a.bindings[x], x)
    self.assertIs(a.bindings[y], x)
    self.assertEqual(str(a), '{x=x, y=x} True')

  @unittest.expectedFailure
  def test_solve_duplicate_variable_names_rejected_at_call(self):
    x = curry.free('x')
    other = curry.free('x')
    with self.assertRaises(curry.CurryTypeError):
      curry.solve((x, other))

  @unittest.expectedFailure
  def test_results_is_iterator_without_length(self):
    Coin = curry.import_('Coin')
    r = curry.eval(Coin.coin)
    self.addCleanup(r.close)
    self.assertIsInstance(r, curry.Results)
    self.assertIsInstance(r, Iterator)
    self.assertIs(iter(r), r)
    with self.assertRaises(TypeError):
      len(r)
    self.assertCountEqual([next(r), next(r)], [0, 1])
    with self.assertRaises(StopIteration):
      next(r)

  @unittest.expectedFailure
  def test_results_break_keeps_search(self):
    M = curry.import_('Stream')
    r = curry.eval(M.three)
    for value in r:
      break
    self.assertCountEqual([value] + list(r), [1, 2, 3])

  @unittest.expectedFailure
  def test_results_multiple_searches_can_be_open(self):
    M = curry.import_('Stream')
    a = curry.eval(M.three)
    b = curry.eval(M.three)
    a_first = next(a)
    b_first = next(b)
    self.assertCountEqual([a_first] + list(a), [1, 2, 3])
    self.assertCountEqual([b_first] + list(b), [1, 2, 3])

  def test_results_close_ends_search(self):
    M = curry.import_('Stream')
    r = curry.eval(M.three)
    next(r)
    self.assertIsNone(r.close())
    self.assertEqual(list(r), [])

  @unittest.expectedFailure
  def test_results_one_no_value(self):
    M = curry.import_('Stream')
    with self.assertRaises(curry.NoValueError):
      curry.eval(M.nothing).one()

  @unittest.expectedFailure
  def test_results_one_many_values(self):
    Coin = curry.import_('Coin')
    with self.assertRaises(curry.ManyValuesError):
      curry.eval(Coin.coin).one()

  @unittest.expectedFailure
  def test_bindings_order_mapping_and_hash(self):
    g = curry.parse('(y =:= 2, x =:= 1) where x, y free')
    a = curry.solve(g).one()
    b = curry.solve(g).one()
    self.assertIsInstance(a.bindings, Mapping)
    self.assertEqual(list(a.bindings), ['y', 'x'])
    self.assertEqual(len(a.bindings), 2)
    self.assertEqual(str(a.bindings), '{y=2, x=1}')
    self.assertEqual(hash(a.bindings), hash(b.bindings))
    self.assertEqual(a.bindings, b.bindings)

  @unittest.expectedFailure
  def test_empty_bindings_and_answer_tuple(self):
    a = curry.solve(1).one()
    self.assertIsInstance(a, tuple)
    value, bindings = a
    self.assertEqual(value, 1)
    self.assertIs(bindings, a.bindings)
    self.assertEqual(str(bindings), '{}')
    self.assertEqual(str(a), '1')

  @unittest.expectedFailure
  def test_stream_result_after_end(self):
    stream = curry.stream
    Primes = curry.import_('Primes')
    r = stream(Primes.threeOut)
    self.assertIsInstance(r, curry.Stream)
    self.assertIsInstance(r, Iterator)
    self.assertIs(iter(r), r)
    self.assertIsNone(r.result)
    self.assertEqual(list(r), [1, 2, 3])
    self.assertEqual(r.result, ())
    with self.assertRaises(StopIteration):
      next(r)

  @unittest.expectedFailure
  def test_stream_close_drops_paused_run(self):
    stream = curry.stream
    Primes = curry.import_('Primes')
    r = stream(Primes.primesOut)
    self.assertEqual(next(r), 2)
    self.assertIsNone(r.close())
    self.assertEqual(list(r), [])

  @unittest.expectedFailure
  def test_stream_nondeterminism_raises(self):
    stream = curry.stream
    Primes = curry.import_('Primes')
    r = stream(Primes.ndOut)
    with self.assertRaises(curry.EvaluationError):
      next(r)

  @unittest.expectedFailure
  def test_stream_is_lazy(self):
    P = curry.import_('Prelude')
    r = curry.stream(P.error('boom'))
    with self.assertRaises(curry.EvaluationError):
      next(r)

  def test_next_default_is_none_when_no_value(self):
    P = curry.import_('Prelude')
    self.assertIsNone(next(curry.eval(P.failed), None))

  @unittest.expectedFailure
  def test_stream_returns_whole_values_and_action_result(self):
    stream = curry.stream
    M = curry.import_('StubStream')
    r = stream(M.whole)
    self.assertEqual(next(r), [1, 2])
    self.assertEqual(list(r), [])
    self.assertEqual(r.result, 42)

  @unittest.expectedFailure
  def test_stream_error_follows_prior_yields(self):
    stream = curry.stream
    M = curry.import_('StubStream')
    r = stream(M.priorError)
    self.assertEqual(next(r), 1)
    with self.assertRaises(curry.EvaluationError):
      next(r)

  @unittest.expectedFailure
  def test_anonymous_variables_are_not_reported(self):
    P = curry.import_('Prelude')
    a = curry.solve(P['=:='](curry.free(), 1)).one()
    self.assertEqual(dict(a.bindings), {})


if __name__ == '__main__':
  unittest.main()
