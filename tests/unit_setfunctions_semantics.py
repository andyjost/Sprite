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

D1, the failure rule, behind the flag setfunction_failures (the default
'encapsulate').  Under 'escape' a failure that comes from an argument (a
boxed failure) and is demanded inside the capsule fails the set function
(failure_escapes and fail_capsule in state/rts_setfunctions.cpp;
boxed_failure in eval/rts_setfunctions.py): sortValues (set1 id failed) has
no value, where it gives [] by default.  A failure of the function's own
body drops its alternative under both settings, and an argument the
function does not demand fails nothing.

Each class runs one child per setting of the flag and keeps the results;
a test reads the values of one goal under both settings.  The children run
under prlimit and timeout, because a regression can spin inside C++ (see
cytest.run_in_subprocess).  Two goals put a guard of an enclosing set at
the root of a nested configuration, the known failure of the Python
backend (TestNestedSetGuardPython in unit_cxx_scheduler.py).
'''
import cytest # from ./lib; must be first
import curry, unittest

ADDRESS_SPACE = 2 << 30
TIMEOUT = 120
SETTINGS = ('encapsulate', 'escape')

# Evaluates goals of the test module and prints one line per goal: its name
# and the sorted values as Curry text, or the name of the error.
CHILD = '''
import curry
curry.reload(%(flags)r)
M = curry.import_('SetFunctionsSemantics')
for name in %(goals)r:
  try:
    values = curry.eval(getattr(M, name))
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

def same(values):
  '''The expected values of a goal that the flag does not change.'''
  return (values, values)

# The goals of the Python backend that put a guard of an enclosing set at
# the root of a nested configuration: its known failure.
PY_KNOWN_FAILURES = {'capNested', 'nestFail'}

def goal_tests(cls):
  '''
  Adds a test per goal of cls.GOALS, which maps a goal to its expected
  values under 'encapsulate' and under 'escape'.
  '''
  for goal in cls.GOALS:
    def test(self, goal=goal):
      self.check(goal)
    test.__doc__ = 'The goal %s under both settings of the flag.' % goal
    if goal in PY_KNOWN_FAILURES and curry.flags['backend'] == 'py':
      test = unittest.expectedFailure(test)
    setattr(cls, 'test_' + goal, test)
  return cls


class GoalsCase(cytest.TestCase):
  '''
  One child per setting of the flag setfunction_failures, run once per
  class; a test compares the values of one goal under both settings.
  '''
  GOALS = {}

  @classmethod
  def setUpClass(cls):
    # Compile the module here; the children load it from the cache.
    curry.import_('SetFunctionsSemantics')
    cls.results = {
        setting: run_child(cls.GOALS, setfunction_failures=setting)
            for setting in SETTINGS
      }

  def check(self, goal):
    for setting, expected in zip(SETTINGS, self.GOALS[goal]):
      with self.subTest(setfunction_failures=setting):
        self.assertEqual(self.results[setting].get(goal), expected)


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
      's1': same(['[(-1), 1]', '[0, 2]'])
    , 's2PG': same(['([1], 0)', '([2], 1)'])
    , 's2PL': same(['[1]'])
    , 's3PG': same(['[1]'])
    , 's3i': same(['True'])
    , 's4d': same(['True'])
    , 's5': same(['[[(-1), 1]]', '[[0, 2]]'])
    , 'nest2': same(['[[False]]', '[[True]]'])
    , 's6PG': same(['[False]', '[True]'])
    , 's7PG': same(['([1], False)', '([2], True)'])
    , 's7PL': same(['([1], True)', '([2], False)'])
    , 's8PL': same(['[10]', '[11]'])
    , 's9': same(['[1]', '[]'])
    , 's10': same(['[1]', '[]'])
    , 'ho1': same(['[(-1), 1]', '[0]'])
    , 'cap1': same(['[(-1), 0, 1, 2]'])
    , 'ord1': same(['(0, [10])', '(1, [11])'])
    , 'cin2': same(['([True], True)', '([], False)'])
    , 'cin3': same(['([_a], _a)'])
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
      's6PL': same(['[10]', '[11]'])
    , 'ord2': same(['([10], 0)', '([11], 1)'])
    , 'ord2Arg': same(['([10], 0)', '([11], 1)'])
    , 'cin1': same(['([True], True)', '([], False)'])
    , 'cin1Rev': same(['(False, [])', '(True, [True])'])
    , 'capNarrow': same(['([False], True)', '([True], False)'])
    , 'capData': same(['([10], 0)', '([11], 1)'])
    , 'capPartial': same(['([10], 0)', '([11], 1)'])
    , 'argPartial': same(['([0], 0)', '([1], 1)'])
    , 'capNested': same(['[[1]]', '[[2]]'])
    , 'pS': same(['[[1]]', '[[2]]'])
    , 'pSCap': same(['([[1]], 0)', '([[2]], 1)'])
    }


@goal_tests
class TestFailureRule(GoalsCase):
  '''
  Decision D1.  A boxed failure demanded inside the capsule drops its
  alternative under 'encapsulate' (the values of both backends before the
  change) and fails the set function under 'escape' (no value).  s4a holds
  the failure in a captured argument, which D2 boxes; nestFail demands the
  argument of the outer set function inside the inner one, so both fail;
  nestFailInner makes the failure inside the outer function and passes it
  to the inner set function, which fails and drops the alternative of the
  outer function, so the outer set is empty; lazyFirst consumes a value
  before the failing argument is demanded.
  '''
  GOALS = {
      's3': (['[]'], [])
    , 's3e': (['True'], [])
    , 's4': (['[]'], [])
    , 's4h': (['[]'], [])
    , 's4a': (['True'], [])
    , 's4b': (['True'], [])
    , 's4c': (['True'], [])
    , 'nestFail': (['False'], [])
    , 'nestFailInner': (['False'], ['True'])
    , 'lazyFirst': same(['True'])
    }


if __name__ == '__main__':
  unittest.main()
