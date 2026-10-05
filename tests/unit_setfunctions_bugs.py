'''
Tests for three defects of the set functions and the scheduler: issues #61,
#32, and #36.  The programs are in data/curry/SetFunctionsBugs.curry.

Issue #61: a set function over a free variable that a choice bound saw the
binding of the first alternative in every branch.  The application sits
below the pull-tab of the constraint, so the alternatives share it.  The
first alternative to reach it rewrote the shared node into a SetEval whose
nested queue read the bindings of that alternative, and the second found the
values in the shared graph.  A choice the configuration decided before the
set function saw it, in the argument or in the function position, had the
same defect.  The step that creates the SetEval now rewrites through a
private copy of the spine when the application holds a variable that the
configuration bound, narrowed, or grouped, or a choice that it decided, as
the step that puts a binding into an expression does (evalS_step in
currylib/setfunctions.cpp, evalS in backends/py/currylib/setfunctions.py).
The rule covers a variable bound, or a choice decided, before the set
function starts.  A set function that starts before the variable is
narrowed, and is consumed in part on each side of the narrowing, still
shares its queue between the alternatives: a known failure on both backends
(test_narrowed_after_start).

Issue #32: a set function whose values are sub-terms of its guarded argument
put the guard at the root of the nested configuration, where the C++
scheduler asserted.  The set guard at the root (2026-10-04) fixed it; the
three forms of the issue are pinned here on both backends.

Issue #36: a recursion that picks from a shrinking pool with a let did not
end on either backend.  Its rules overlap: the second rule matches n = 0 as
well, and its recursion never ends, because nothing forces anyOf [] once
the pool is empty.  PAKCS does not end on it either.  With a guard the rules
are exclusive, and both backends give the six values and end.

The children run under prlimit and timeout, because a regression can spin
inside C++ (see cytest.run_in_subprocess).
'''
import cytest # from ./lib; must be first
import curry, unittest

ADDRESS_SPACE = 2 << 30
TIMEOUT = 120

# Evaluates goals of the test module and prints one line per goal: its name
# and the sorted values as Curry text, or the name of the error.  A limit
# takes the first values of a goal that does not end.
CHILD = '''
import curry, itertools
curry.reload(%(flags)r)
M = curry.import_('SetFunctionsBugs')
for name, limit in %(goals)r:
  try:
    values = curry.eval(getattr(M, name))
    if limit is not None:
      values = itertools.islice(values, limit)
    print(name, sorted(str(value) for value in values))
  except curry.EvaluationError as exc:
    print(name, 'error', type(exc).__name__, str(exc))
'''

def run_child(testcase, goals, **flags):
  '''
  Evaluates ``goals``, pairs of a goal name and a limit on the number of
  values (None for all of them), in a child on the backend of this test
  process, and returns a dict from the name to the sorted list of values (as
  text) or to the error line.
  '''
  flags.setdefault('backend', curry.flags['backend'])
  code = CHILD % {'flags': flags, 'goals': goals}
  proc = cytest.run_in_subprocess(code, TIMEOUT, address_space=ADDRESS_SPACE)
  testcase.assertEqual(
      proc.returncode, 0
    , 'the child ended with status %s; stdout:\n%s\nstderr:\n%s'
          % (proc.returncode, proc.stdout, proc.stderr)
    )
  results = {}
  for line in proc.stdout.splitlines():
    name, _, rest = line.partition(' ')
    results[name] = eval(rest) if rest.startswith('[') else rest
  return results

def goals(*names):
  return [(name, None) for name in names]


class TestBoundVariable(cytest.TestCase):
  '''
  Issue #61.  A choice binds a free variable, and a set function below the
  pull-tab of the constraint takes the variable as its argument.  Each
  alternative must see its own binding.
  '''
  @classmethod
  def setUpClass(cls):
    # Compile the module here; the children load it from the cache.
    curry.import_('SetFunctionsBugs')

  def test_issue_example(self):
    results = run_child(self, goals('boundVar'))
    self.assertEqual(results, {'boundVar': ['[[A]]', '[[B]]']})

  def test_two_set_functions(self):
    results = run_child(self, goals('twoSets'))
    self.assertEqual(
        results, {'twoSets': ['[([A], [[A, A]])]', '[([B], [[B, B]])]']}
      )

  @unittest.skipIf(
      curry.flags['backend'] != 'cxx'
    , 'the Python backend asserts on a guard of an enclosing set at the root'
    )
  def test_nested_set_function(self):
    results = run_child(self, goals('nestedBound'))
    self.assertEqual(results, {'nestedBound': ['[[[A]]]', '[[[B]]]']})

  @unittest.skipIf(
      curry.flags['backend'] != 'py', 'the known failure of the Python backend'
    )
  @unittest.expectedFailure
  def test_nested_set_function_python(self):
    '''
    On the Python backend a guard of an enclosing set function at the root
    of a nested configuration unwinds to allValues, which expects a choice
    (see TestNestedSetGuardPython in unit_cxx_scheduler.py).
    '''
    results = run_child(self, goals('nestedBound'))
    self.assertEqual(results, {'nestedBound': ['[[[A]]]', '[[[B]]]']})

  def test_forced_argument(self):
    '''
    The variable forced to normal form before the set function sees it: the
    form the examples used before the fix.
    '''
    results = run_child(self, goals('forced', 'forcedStrict'))
    self.assertEqual(results, {
        'forced': ['[[A]]', '[[B]]'], 'forcedStrict': ['[[A]]', '[[B]]']
      })

  @unittest.expectedFailure
  def test_narrowed_after_start(self):
    '''
    The set function starts while the variable is unbound, so the two
    alternatives of the constraint that narrows it afterwards share the
    SetEval node and its queue.  The nested queue reads the fingerprint of
    the alternative that resumes it first, and the shared allValues node
    keeps that value for the other.  Expected [A, A] and [A, B]; both
    backends give [A, A] twice.  The creation-time rule does not cover it.
    A fix needs the escape of rule SF.1 of the dissertation, under which a
    choice in the escape set always leaves the capsule, or a private copy of
    the queue when a nested queue resumes under another configuration.
    '''
    results = run_child(self, goals('narrowedAfterStart'))
    self.assertEqual(
        results, {'narrowedAfterStart': ['[A, A]', '[A, B]']}
      )

  def test_decided_choice(self):
    '''
    A choice, not a variable, decides the argument.  The pull-tab of the
    first component of the pair makes the choice before the set function
    sees it, in the argument (choiceArg) and in the function position
    (choiceCaptured).  Each alternative must see its own side.
    '''
    results = run_child(self, goals('choiceArg', 'choiceCaptured'))
    self.assertEqual(results, {
        'choiceArg': ['(A, [A])', '(B, [B])']
      , 'choiceCaptured': ['(A, [A])', '(B, [B])']
      })

  def test_walk_coverage(self):
    '''
    The walk reaches the bound variable behind a call, behind the forward
    node a forced call leaves, inside a partial application in the function
    position, and inside a data structure.
    '''
    names = ['viaCall', 'viaForward', 'viaPartial', 'viaData']
    results = run_child(self, goals(*names))
    self.assertEqual(results, {name: ['[[A]]', '[[B]]'] for name in names})

  def test_long_argument(self):
    '''
    The walk that looks for private state in the application visits 64
    nodes.  A longer argument counts as private, so a variable behind the
    bound still gets its own binding, and a long argument without a
    variable still gives its value, in a deterministic program (where the
    one configuration skips the walk) and under a decided choice (where the
    walk gives up).
    '''
    results = run_child(self, goals('longArg', 'longPlain', 'longPlainChoice'))
    self.assertEqual(results, {
        'longArg': ['[[A]]', '[[B]]']
      , 'longPlain': ['[A]']
      , 'longPlainChoice': ['(A, [A])', '(B, [A])']
      })


class TestSubtermValues(cytest.TestCase):
  '''
  Issue #32.  The values of the set function are sub-terms of its guarded
  argument.
  '''
  @classmethod
  def setUpClass(cls):
    curry.import_('SetFunctionsBugs')

  def test_three_forms(self):
    results = run_child(self, goals('anyOfSet', 'tailsSet', 'headOrLastSet'))
    self.assertEqual(results, {
        'anyOfSet': ['[1, 2, 3]']
      , 'tailsSet': ['[[[1, 2, 3], [2, 3], [3], []]]']
      , 'headOrLastSet': ['[1, 3]']
      })


class TestShrinkingPool(cytest.TestCase):
  '''
  Issue #36.  Two picks from a pool of three, each pick a let-bound choice
  that the guard of the next pick and the result share.
  '''
  SIX = ['[1, 2]', '[1, 3]', '[2, 1]', '[2, 3]', '[3, 1]', '[3, 2]']

  @classmethod
  def setUpClass(cls):
    curry.import_('SetFunctionsBugs')

  def test_six_values_and_the_end(self):
    results = run_child(self, goals('pick2'))
    self.assertEqual(results, {'pick2': self.SIX})

  def test_overlapping_rules(self):
    '''
    The program of the issue.  Its first six values are the six; the
    evaluation does not end after them, on PAKCS as on Sprite, because the
    second rule also matches n = 0.
    '''
    results = run_child(self, [('pickOverlap', 6)])
    self.assertEqual(results, {'pickOverlap': self.SIX})


if __name__ == '__main__':
  unittest.main()
