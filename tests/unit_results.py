'''Evaluation ownership, the legacy converter and stale provenance.'''
import cytest # from ./lib; must be first
import curry
from curry import backends
from curry.objects.handle import getHandle
from curry.typecheck.goals import Goal
from unittest import mock


class TestResults(cytest.TestCase):
  def test_start_is_deferred_and_close_drops_the_run(self):
    original = Goal.evaluate
    with mock.patch.object(Goal, 'evaluate', autospec=True, side_effect=original) as start:
      results = curry.eval(curry.term(1))
      self.assertEqual(start.call_count, 0)
      self.assertEqual(next(results), 1)
      self.assertEqual(start.call_count, 1)
      self.assertEqual(len(cytest.raw.interp()._evaluation_totals._running), 1)
      results.close()
      self.assertEqual(len(cytest.raw.interp()._evaluation_totals._running), 0)

  def test_close_before_start(self):
    with mock.patch.object(Goal, 'evaluate') as start:
      results = curry.eval(1)
      results.close()
      self.assertEqual(list(results), [])
      start.assert_not_called()

  def test_raw_and_converted_values(self):
    P = curry.import_('Prelude')
    node = cytest.raw.values(P.id(1)).one()
    self.assertIsInstance(node, backends.Node)
    self.assertEqual(curry.eval(P.id(1)).one(), 1)


  def test_many_values_closes_the_run(self):
    results = curry.eval(curry.choice(1, 2))
    with self.assertRaises(curry.ManyValuesError):
      results.one()
    self.assertEqual(list(results), [])
    self.assertEqual(len(cytest.raw.interp()._evaluation_totals._running), 0)

  def test_stale_nested_term_and_prelude_module(self):
    P = curry.import_('Prelude')
    old = curry.term((P.id(1), [curry.free('x')]))
    curry.reset()
    for value in (old, [old], P):
      with self.assertRaises(curry.StaleError):
        curry.eval(value)
    with self.assertRaises(curry.StaleError):
      P.id
    self.assertEqual(curry.eval(curry.import_('Prelude').id(2)).one(), 2)

  def test_retired_module_stales_held_applications(self):
    module = curry.compile('f :: Int -> Int\nf x = x', modulename='ResultsRetired')
    old = module.f(1)
    getHandle(module).unlink(cytest.raw.interp())
    with self.assertRaisesRegex(curry.StaleError, 'reload.*build it again from ResultsRetired'):
      curry.eval(old)

  def test_bindings_beyond_tuple_limit_and_hash_order(self):
    variables = [curry.free('x%d' % i) for i in range(16)]
    answer = curry.solve(variables).one()
    self.assertEqual(list(answer.bindings), [v.name for v in variables])
    for value, var in zip(answer.value, variables):
      self.assertIs(value, var)
      self.assertIs(answer.bindings[var], var)
    a = curry.Bindings([('x', [1, 2]), ('y', True)])
    b = curry.Bindings([('y', True), ('x', [1, 2])])
    self.assertEqual(a, b)
    self.assertEqual(hash(a), hash(b))

  def test_io_solve_converts_the_payload_and_bindings(self):
    answer = curry.solve(curry.parse('return (x =:= 1) where x free')).one()
    self.assertIs(answer.value, True)
    self.assertEqual(dict(answer.bindings), {'x': 1})
    answer = curry.solve(curry.parse('return (x =:= 1, "") where x free')).one()
    self.assertEqual(answer.value, (True, ''))

  def test_module_version_survives_rebinding_the_wrapper(self):
    module = curry.compile('f :: Int\nf = 1', modulename='ResultsVersion')
    old = module.f
    setattr(module, '.version', object())
    with self.assertRaisesRegex(curry.StaleError, 'reload.*build it again from ResultsVersion'):
      curry.eval(old)

  def test_lists_remain_values_when_they_hold_variables(self):
    P = curry.import_('Prelude')
    x = curry.free('x')
    with self.assertRaises(curry.CurryTypeError):
      curry.eval([P.id, x])
    self.assertEqual(curry.eval((P.id)(3)).one(), 3)

  def test_stale_iterator_item_and_internal_builders(self):
    old = curry.term(1)
    symbol = curry.import_('Prelude').id
    curry.reset()
    for build in (cytest.raw.expr, lambda *args, **kwds: cytest.raw.expr(*args, typed=True, **kwds)):
      with self.assertRaises(curry.StaleError):
        build(old)
      with self.assertRaises(curry.StaleError):
        build(symbol, 1)
    results = curry.eval(curry.term(iter([old]), type='[Int]'))
    with self.assertRaises(curry.StaleError):
      next(results)
    self.assertEqual(list(results), [])

  def test_bindings_hash_with_user_nodes(self):
    P = curry.import_('Prelude')
    x = curry.free('x')
    goal = P['=:='](x, P.Just(1))
    a, b = curry.solve(goal).one(), curry.solve(goal).one()
    self.assertEqual(a.bindings, b.bindings)
    self.assertEqual(hash(a.bindings), hash(b.bindings))

  def test_goal_keyword(self):
    self.assertEqual(curry.eval(goal=1).one(), 1)
    self.assertEqual(curry.solve(goal=1).one(), curry.Answer(1, curry.Bindings()))
