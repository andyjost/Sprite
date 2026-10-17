'''
Tests for the two rules of the memo on the Fair Scheme proofs that change
the semantics of the set functions (decisions D1 and D2 of 2026-10-09): the
goals of the probe table of the memo, each a test, on both backends.  The
programs are in data/curry/SetFunctionsSemantics.curry, with the helpers of
the probe modules of the memo.

D2, the captured arguments (issue #117).  The arguments that the function
value of a set function holds, those of a partial application and the
variables of the enclosing context that a lambda closes over (lambda
lifting makes them arguments), are boxed as the value arguments are
(set_step in currylib/setfunctions.cpp; set_ in
backends/py/currylib/setfunctions.py), so their non-determinism escapes the
capsule: ord2 = let x = 0 ? 1 in (sortValues (set1 (\\y -> x + y) 10), x)
gives ([10], 0) and ([11], 1), where it gave ([10, 11], 0) and ([10, 11], 1)
before, values the semantics of weakly encapsulated search does not have.
The whole captured argument is boxed; a pattern match passes the box on to
a component (fst p), and an application of a partial application reached
through a box puts the box on its arguments (apply_step; apply), so a
choice inside a captured data structure or a captured closure escapes too.
captureS stays the explicit capture of an argument.

D1, the failure rule, in its deferred form (Definition 2.94 of the note on
the Fair Scheme; the owner's decision of 2026-10-12, which removed the flag
setfunction_failures and its two values).  A failure that comes from an
argument (a boxed failure) and is demanded inside the capsule drops the
alternative that demands it, and the capsule records it; the set function
fails when its queue empties with no value, no failure of the function's
own and some failure from an argument (record_failure in
state/rts_setfunctions.cpp and eval/rts_setfunctions.py; the verdict in
allValues): sortValues (set1 id failed) has no value.  A failure of the
function's own body drops its alternative, and an argument the function
does not demand fails nothing.  unit_setfunctions_failures.py tests the
rule on the probes of the audit.

Each class runs one child and keeps the results; a test reads the values of
one goal.  The children run under prlimit and timeout, because a regression
can spin inside C++ (see cytest.run_in_subprocess).  Two goals, capNested and nestFail, put a guard
of an enclosing set at the root of a nested configuration, where the Python
backend unwound to allValues before the fix of issue #130; the guard is a
node of the spine like a constructor on both backends now.
'''
import cytest # from ./lib; must be first
import curry, unittest

ADDRESS_SPACE = 2 << 30
TIMEOUT = 120

# Evaluates goals of the test module and prints one line per goal: its name
# and the sorted values as Curry text, or the name of the error.
CHILD = '''
import cytest, curry
curry.reload(%(flags)r)
M = curry.import_('SetFunctionsSemantics')
for name in %(goals)r:
  try:
    values = cytest.raw.values(getattr(M, name))
    print(name, sorted(str(value) for value in values))
  except (curry.EvaluationError, Exception) as exc:
    print(name, 'error', type(exc).__name__, str(exc))
'''

def run_child(goals, **flags):
  '''
  Evaluates ``goals`` in a child on the backend of this test process and
  returns a dict from the name to the sorted list of values (as text) or to
  the error line.
  '''
  flags.setdefault('backend', curry.flags['backend'])
  code = CHILD % {'flags': flags, 'goals': list(goals)}
  proc = cytest.run_in_subprocess(code, TIMEOUT, address_space=ADDRESS_SPACE)
  if proc.returncode != 0:
    raise AssertionError(
        'the child ended with status %s; stdout:\n%s\nstderr:\n%s'
            % (proc.returncode, proc.stdout, proc.stderr)
      )
  results = {}
  for line in proc.stdout.splitlines():
    name, _, rest = line.partition(' ')
    results[name] = eval(rest) if rest.startswith('[') else rest
  return results

def goal_tests(cls):
  '''
  Adds a test per goal of cls.GOALS, which maps a goal to its expected
  values.
  '''
  for goal in cls.GOALS:
    def test(self, goal=goal):
      self.check(goal)
    test.__doc__ = 'The goal %s.' % goal
    setattr(cls, 'test_' + goal, test)
  return cls


class GoalsCase(cytest.TestCase):
  '''One child per class; a test reads the values of one goal.'''
  GOALS = {}

  @classmethod
  def setUpClass(cls):
    # Compile the module here; the children load it from the cache.
    curry.import_('SetFunctionsSemantics')
    cls.results = run_child(cls.GOALS)

  def check(self, goal):
    self.assertEqual(self.results.get(goal), self.GOALS[goal])


@goal_tests
class TestUnchangedGoals(GoalsCase):
  '''
  The goals of the table on which the two rules change nothing: the
  running example of the dissertation (s1), a failing argument the function
  does not demand (s2PL, s3PG), a failure of the function's own body (s3i,
  s4d, s9, s10), the choice or the variable of an argument (s2PG, s6PG,
  s7PG, s7PL, s8PL), nested set functions (s5, nest2), a non-deterministic
  function argument (ho1), the explicit capture (cap1), the captured choice
  decided before the capsule (ord1), and the outside variable as a boxed
  argument (cin2, cin3).  The values are those of the memo's table, and
  those both backends gave before the change.
  '''
  GOALS = {
      's1': ['[(-1), 1]', '[0, 2]']
    , 's2PG': ['([1], 0)', '([2], 1)']
    , 's2PL': ['[1]']
    , 's3PG': ['[1]']
    , 's3i': ['True']
    , 's4d': ['True']
    , 's5': ['[[(-1), 1]]', '[[0, 2]]']
    , 'nest2': ['[[False]]', '[[True]]']
    , 's6PG': ['[False]', '[True]']
    , 's7PG': ['([1], False)', '([2], True)']
    , 's7PL': ['([1], True)', '([2], False)']
    , 's8PL': ['[10]', '[11]']
    , 's9': ['[1]', '[]']
    , 's10': ['[1]', '[]']
    , 'ho1': ['[(-1), 1]', '[0]']
    , 'cap1': ['[(-1), 0, 1, 2]']
    , 'ord1': ['(0, [10])', '(1, [11])']
    , 'cin2': ['([True], True)', '([], False)']
    , 'cin3': ['([_a], _a)']
    }


@goal_tests
class TestCapturedArguments(GoalsCase):
  '''
  Decision D2.  A choice or a free variable that the function value holds
  escapes the capsule.  Before the change both backends gave: s6PL
  [10, 11]; ord2 ([10, 11], 0) and ([10, 11], 1); cin1 ([True], _a); cin1Rev
  (_a, [True]); capNarrow ([False, True], _a); capData and capPartial
  ([10, 11], 0) and ([10, 11], 1); argPartial ([0, 1], 0) and ([0, 1], 1).
  ord2Arg, the reference shape with the choice as an argument of set2, and
  capNested gave their values before as well.  pS and pSCap apply a PartialS
  reached through a box with applyS: the boxes of the arguments it holds
  stay outermost (guard_successors; guard_held), so the inner set function
  gives them its set.  Before the fix of the review the C++ runtime read a
  null set there (a crash) and the Python backend raised KeyError.
  '''
  GOALS = {
      's6PL': ['[10]', '[11]']
    , 'ord2': ['([10], 0)', '([11], 1)']
    , 'ord2Arg': ['([10], 0)', '([11], 1)']
    , 'cin1': ['([True], True)', '([], False)']
    , 'cin1Rev': ['(False, [])', '(True, [True])']
    , 'capNarrow': ['([False], True)', '([True], False)']
    , 'capData': ['([10], 0)', '([11], 1)']
    , 'capPartial': ['([10], 0)', '([11], 1)']
    , 'argPartial': ['([0], 0)', '([1], 1)']
    , 'capNested': ['[[1]]', '[[2]]']
    , 'pS': ['[[1]]', '[[2]]']
    , 'pSCap': ['([[1]], 0)', '([[2]], 1)']
    }


@goal_tests
class TestFailureRule(GoalsCase):
  '''
  Decision D1 in its deferred form.  Every alternative of these set
  functions demands the failing argument, so each capsule fails and the
  goal has no value (the rule of the dissertation gave [] or True, the
  values of both backends before 2026-10-10).  s4a holds the failure in a
  captured argument, which D2 boxes; nestFail demands the argument of the
  outer set function inside the inner one, so the inner capsule fails
  under the guard of the outer set and the outer capsule fails in turn;
  nestFailInner makes the failure inside the outer function and passes it
  to the inner set function, which fails for its own argument, a plain
  failure that drops the alternative of the outer function, so the outer
  set is empty; lazyFirst consumes a value before the failing argument is
  demanded.
  '''
  GOALS = {
      's3': []
    , 's3e': []
    , 's4': []
    , 's4h': []
    , 's4a': []
    , 's4b': []
    , 's4c': []
    , 'nestFail': []
    , 'nestFailInner': ['True']
    , 'lazyFirst': ['True']
    }


if __name__ == '__main__':
  unittest.main()
