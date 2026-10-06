'''
Tests for the step budget and the stack-overflow rotation of the Python
backend.

Covers a 2023 report by Michael Hanus: ``length [1..] ? 1 ? length [1..]``
died with RecursionError on the Python backend before ``1`` printed.  The
backend now rotates the work queue when a configuration overflows the Python
stack, and again after a fixed number of rewrite steps (flag ``step_budget``),
so one alternative cannot starve the others.  An alternative that overflows
again without progress is dropped.  Its error waits until the others have
run.

A regression in the rotation makes a test here spin, so every test runs under
``cytest.timeout``.  That decorator goes innermost: the cleanup of
``with_flags`` reloads ``curry``, and the alarm must not fire inside it.  Some
programs are in data/curry/StackGuard.curry.
'''
import cytest # from ./lib; must be first
import curry, unittest

# The tests run under a recursion limit of 16384 frames (the flag
# recursion_limit; the default is 262144), so a short list overflows it.
FLAGS = {'defaultconverter': 'topython', 'recursion_limit': 1 << 14}

@unittest.skipIf(
    curry.flags['backend'] != 'py'
  , 'the step budget and RecursionError rotation belong to the Python backend'
  )
class TestPyFairness(cytest.TestCase):
  # ``length`` nests one evaluation inside another for every list element,
  # about eight frames each, so the list must be long to overflow the limit.
  # The evaluation stops at the overflow depth, so a larger N adds headroom,
  # not much time: a deep test takes about 5 seconds on the Python backend.
  N = 10000
  TIMEOUT = 60

  @classmethod
  def setUpClass(cls):
    curry.import_('StackGuard')

  @cytest.with_flags(**FLAGS)
  @cytest.timeout(TIMEOUT)
  def test_deep_alternatives_do_not_spin(self):
    '''
    Two alternatives that both overflow at a fixed depth must end with an
    error.  An audit finding: the rotation had no progress check, so the two
    configurations took turns forever.  Both are dropped now, and the error
    of the first is reported when the queue is empty.
    '''
    goal = curry.compile(
        'length [1..%d] ? length [1..%d]' % (self.N, self.N), 'expr'
      )
    with self.assertRaises(RecursionError):
      list(curry.eval(goal))

  @cytest.with_flags(**FLAGS)
  @cytest.timeout(TIMEOUT)
  def test_three_deep_alternatives_do_not_spin(self):
    '''
    Three alternatives that overflow at a fixed depth.  The progress check is
    per configuration: a global step count moves while the other two
    configurations run, so it does not show that this one is stuck.
    '''
    goal = curry.compile(
        'length [1..%d] ? length [1..%d] ? length [1..%d]'
            % (self.N, self.N, self.N)
      , 'expr'
      )
    with self.assertRaises(RecursionError):
      list(curry.eval(goal))

  @cytest.with_flags(**FLAGS)
  @cytest.timeout(TIMEOUT)
  def test_deep_alternative_does_not_starve_others(self):
    goal = curry.compile(
        'length [1..%d] ? 1 ? length [1..%d]' % (self.N, self.N), 'expr'
      )
    values = curry.eval(goal)
    self.assertEqual(next(values), 1)
    with self.assertRaises(RecursionError):
      next(values)

  @cytest.with_flags(**FLAGS, step_budget=None)
  @cytest.timeout(TIMEOUT)
  def test_deep_alternative_does_not_starve_others_without_budget(self):
    # The stack-overflow rotation does not depend on the step budget.
    goal = curry.compile(
        'length [1..%d] ? 1 ? length [1..%d]' % (self.N, self.N), 'expr'
      )
    values = curry.eval(goal)
    self.assertEqual(next(values), 1)
    with self.assertRaises(RecursionError):
      next(values)

  @cytest.with_flags(**FLAGS)
  @cytest.timeout(TIMEOUT)
  def test_stuck_alternative_keeps_finite_one(self):
    '''
    An audit finding: the handler raised the RecursionError when the deep
    alternative overflowed twice at the same point, although the finite
    alternative still had work.  The stuck alternative is now dropped, and
    its error waits until the queue is empty.  The C++ backend applies the
    same rule (unit_cxx_stack).
    '''
    M = curry.import_('StackGuard')
    values = curry.eval(M.mixedAlt, self.N, 3000)
    self.assertEqual(next(values), 3000)
    with self.assertRaises(RecursionError):
      next(values)

  @cytest.with_flags(**FLAGS)
  @cytest.timeout(TIMEOUT)
  def test_overflow_inside_setfunction(self):
    '''
    The deep evaluation runs in the nested queue of a set function.  The
    RecursionError passes through the nested scheduler to the enclosing
    queue, which rotates, so the other alternative produces its value first.
    '''
    M = curry.import_('StackGuard')
    values = curry.eval(M.deepSet, self.N)
    self.assertEqual(next(values), 1)
    with self.assertRaises(RecursionError):
      next(values)

  @cytest.with_flags(**FLAGS, step_budget=256)
  @cytest.timeout(TIMEOUT)
  def test_setfunction_keeps_step_budget(self):
    '''
    An audit finding: the step count was keyed on the head of the current
    queue, so a set-function evaluation (a nested queue) reset it, and an
    alternative that calls a set function in every iteration was never
    rotated.
    '''
    SF = curry.compile(
        '''
        import Control.SetFunctions
        loop :: Int
        loop = if isEmpty (set0 (1 ? 2)) then 0 else loop
        main :: Int
        main = loop ? 1
        '''
      , modulename='SF'
      )
    values = curry.eval(SF.main)
    self.assertEqual(next(values), 1)

  @cytest.with_flags(**FLAGS, step_budget=256)
  @cytest.timeout(TIMEOUT)
  def test_diverging_setfunction_does_not_starve_others(self):
    '''
    An audit finding: the budget check looked at the current queue only.  The
    nested queue of a set-function evaluation holds one configuration, so the
    enclosing queue never rotated while the set function diverged.  The
    nested evaluation is now suspended and the enclosing queue rotates.
    '''
    SF = curry.compile(
        '''
        import Control.SetFunctions
        loop :: Int
        loop = loop
        main :: Int
        main = (if isEmpty (set0 loop) then 0 else 1) ? 1
        '''
      , modulename='SF'
      )
    values = curry.eval(SF.main)
    self.assertEqual(next(values), 1)

  @cytest.with_flags(**FLAGS, step_budget=1)
  @cytest.timeout(TIMEOUT)
  def test_nested_queue_rotates_in_place(self):
    '''
    An audit finding: when the budgets of a nested queue and of an enclosing
    queue expired on the same step, only the enclosing queue rotated, and
    the two counters stayed aligned.  The nested queue ``[loop, 2]`` then
    never rotated, and the set function never produced its value.  A budget
    of one step keeps the counters aligned.  The nested queue now rotates in
    place as well.
    '''
    M = curry.import_('StackGuard')
    self.assertEqual(next(curry.eval(M.nestedChoice)), 1)
