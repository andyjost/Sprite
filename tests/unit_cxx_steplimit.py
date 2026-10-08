'''
Tests for the step limit of an evaluation: the limit of the stepper of the
test library (cytest.step, Evaluator.set_global_step_limit).  The generic
evaluator sets it through ``rts.stepcounter``.  The Python RuntimeState
counts in its StepCounter; the C++ RuntimeState has the field
``step_limit`` (cyrt/state/rts.hpp), after which its scheduler stops with
the status E_TERMINATE, and the adapter cyrtbindings.StepCounter presents it
as ``rts.stepcounter``.  The file runs on both backends, so that the limit
leaves the same graph on both.
'''
import cytest # from ./lib; must be first
from curry.backends.generic.eval import control, evaluator
import curry, cytest.step, unittest

IS_CXX = curry.flags['backend'] == 'cxx'


class TestStepLimit(cytest.TestCase):
  def setUp(self):
    super().setUp()
    self.interp = curry.getInterpreter()

  def expr(self, text, **kwds):
    return self.interp.compile(text, mode='expr', **kwds)

  def steps_of(self, text, **kwds):
    '''The values and the rewrite steps of one evaluation of ``text``.'''
    e = self.expr(text, **kwds)
    before = curry.stats()['steps']
    values = list(curry.eval(e, converter='topython'))
    return values, curry.stats()['steps'] - before

  def limited(self, e, limit):
    '''The values of ``e`` under ``limit`` steps, as Python objects.'''
    return [
        self.interp.topython(v)
          for v in evaluator.evaluate(self.interp, e, steplimit=limit)
      ]

  def test_limit_ends_the_evaluation(self):
    '''
    Below or at the step count of a value, the limit ends the evaluation
    with E_TERMINATE after exactly that many steps, which the totals count;
    the expression then evaluates to its value from where it stopped.  One
    step above the count the value comes.
    '''
    text = '1 + (2 + 3)'
    values, n = self.steps_of(text)
    self.assertEqual(values, [6])
    self.assertGreater(n, 2)
    for limit in range(1, n + 1):
      e = self.expr(text)
      before = curry.stats()['steps']
      with self.assertRaises(control.E_TERMINATE):
        self.limited(e, limit)
      self.assertEqual(curry.stats()['steps'] - before, limit, limit)
      self.assertEqual(list(curry.eval(e, converter='topython')), [6], limit)
    e = self.expr(text)
    self.assertEqual(self.limited(e, n + 1), [6])

  @cytest.with_flags(inline_budget=0)
  def test_stepper(self):
    '''
    cytest.step takes the given number of steps and leaves the expression
    as the steps left it; the same states on both backends.  The inliner
    is off, so that the steps are those of the text.
    '''
    self.interp = curry.getInterpreter()
    code = self.interp.compile(
        '''
        f :: Int -> Int
        f x = x + 1
        g :: Int -> Int
        g 0 = 10
        goal :: Int
        goal = f (g 0)
        after1 :: Int
        after1 = f (g 0)
        after2 :: Int
        after2 = (g 0) + 1
        after3 :: Int
        after3 = 10 + 1
        '''
      )
    goal = self.interp.raw_expr(code.goal)
    expected = {}
    for n, name in (1, 'after1'), (2, 'after2'), (3, 'after3'):
      expected[n] = self.interp.raw_expr(getattr(code, name))
      cytest.step.step(self.interp, expected[n])
    # The nullary goal costs the first step; f builds the addition without
    # a look at its argument (the second); the addition needs g 0 (the
    # third); the fourth adds.
    cytest.step.step(self.interp, goal)
    self.assertEqual(goal, expected[1])
    cytest.step.step(self.interp, goal)
    self.assertEqual(goal, expected[2])
    cytest.step.step(self.interp, goal)
    self.assertEqual(goal, expected[3])
    self.assertEqual(list(curry.eval(goal, converter='topython')), [11])

  def test_counter_interface(self):
    '''The interface of the step counter the generic evaluator reads.'''
    e = self.expr('1 + 1')
    ev = evaluator.Evaluator(self.interp, e)
    counter = ev.rts.stepcounter
    self.assertEqual(counter.global_count, 0)
    self.assertEqual(counter.global_limit, float('inf'))
    ev.set_global_step_limit(5)
    self.assertEqual(counter.global_limit, 5)
    ev.set_global_step_limit(None)
    self.assertEqual(counter.global_limit, float('inf'))
    # A limit at or below the count raises at once.
    with self.assertRaises(control.E_TERMINATE):
      ev.set_global_step_limit(0)
    if IS_CXX:
      from curry.backends.cxx import cyrtbindings as cyrt
      self.assertEqual(ev.rts.step_limit, cyrt.NOLIMIT)
      ev.set_global_step_limit(7)
      self.assertEqual(ev.rts.step_limit, 7)
      ev.set_global_step_limit(None)
      self.assertEqual(ev.rts.step_limit, cyrt.NOLIMIT)
    # The steps taken count from the reset.
    ev.set_global_step_limit(1)
    with self.assertRaises(control.E_TERMINATE):
      list(ev.evaluate())
    self.assertEqual(counter.global_count, 1)
    self.assertEqual(ev.rts.steps_total, 1)

  @unittest.skipUnless(IS_CXX, 'the counter of the C++ state is a view')
  def test_counter_keeps_no_cycle(self):
    '''
    The counter holds the state, never the other way round, so a state goes
    with its last reference and not with the cyclic collector: a live state
    is a root of the C++ collector (evaluator.single_step makes one per
    compiled expression; test_repl_eval_under_stress of unit_goals.py).
    '''
    import gc, weakref
    e = self.expr('1 + 1')
    ev = evaluator.Evaluator(self.interp, e)
    ev.set_global_step_limit(5)
    self.assertEqual(ev.rts.stepcounter.global_limit, 5)
    ref = weakref.ref(ev.rts)
    gc.disable()
    try:
      del ev
      self.assertIsNone(ref())
    finally:
      gc.enable()

  def test_limit_inside_a_set_function(self):
    '''
    A limit reached inside the nested evaluation of a set function ends
    the whole evaluation: the nested scheduler hands the status out.
    '''
    # The choice is inside the function: the set function captures it.
    text = 'sortValues (set1 (\\x -> x ? x + 1) 1)'
    imports = [curry.import_('Control.SetFunctions')]
    values, n = self.steps_of(text, imports=imports)
    self.assertEqual(values, [[1, 2]])
    self.assertGreater(n, 5)
    for limit in range(1, n + 1):
      e = self.expr(text, imports=imports)
      before = curry.stats()['steps']
      with self.assertRaises(control.E_TERMINATE):
        self.limited(e, limit)
      self.assertEqual(curry.stats()['steps'] - before, limit, limit)
    e = self.expr(text, imports=imports)
    self.assertEqual(self.limited(e, n + 1), [[1, 2]])

  def test_limit_in_a_search(self):
    '''A limit inside a search with several alternatives.'''
    text = '(1 ? 2) + (10 ? 20)'
    values, n = self.steps_of(text)
    self.assertEqual(sorted(values), [11, 12, 21, 22])
    seen = []
    for limit in range(1, n + 1):
      e = self.expr(text)
      produced = []
      gen = evaluator.evaluate(self.interp, e, steplimit=limit)
      with self.assertRaises(control.E_TERMINATE):
        for v in gen:
          produced.append(self.interp.topython(v))
      seen.append(len(produced))
    # The values come out as the steps allow; none is lost or repeated.
    self.assertEqual(seen[0], 0)
    self.assertEqual(seen, sorted(seen))
    self.assertLessEqual(seen[-1], 4)
    e = self.expr(text)
    self.assertEqual(sorted(self.limited(e, n + 1)), [11, 12, 21, 22])


if __name__ == '__main__':
  unittest.main()
