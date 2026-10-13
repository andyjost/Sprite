'''
Tests for the look-ahead of rule N.1 of the Fair Scheme (issue #132).  The
programs are in data/curry/FailSib.curry.  Every test runs on both
backends, in a child under prlimit and timeout; one child per class
evaluates the goals of the class, and one more runs them under the checker.

The rule: before the scan descends into a successor of a constructor cell,
it reads every successor of the cell through forward cells, and it reads
the parent cell of the cursor again at the first descent after a completed
step.  A failure among them means that the configuration has no value, and
the configuration is dropped before any step below the cell (the path a
failure at the cursor takes).  Both backends tested the failure at the
cursor alone: the scan entered a diverging successor first, the rotation
restarted it from the root, and it entered the same successor again, so a
run the Fair Scheme ends did not end.  The checker verifies the rule at
every descent of the scan (N.1 (look-ahead)): a completed step under a
constructor cell one of whose successors is a failure is reported.

The goals that did not end run in their own classes, in a child with a short
timeout: a regression is killed there, and the values of the controls stay
visible.
'''
import cytest # from ./lib; must be first
import curry
import unittest

ADDRESS_SPACE = 2 << 30
TIMEOUT = 300
# The child of the goals that are dropped before the step ends at once; a
# regression to the scan without the look-ahead is killed after this.
SHORT_TIMEOUT = 30

# Evaluates goals of the test module and prints one line per goal: its name
# and the sorted values as Curry text, or the name of the error.
CHILD = '''
import curry
curry.reload(%(flags)r)
M = curry.import_('FailSib')
for name in %(goals)r:
  try:
    values = curry.eval(getattr(M, name))
    print(name, sorted(str(value) for value in values))
  except Exception as exc:
    print(name, 'error', type(exc).__name__, str(exc))
'''

def run_child(goals, timeout=TIMEOUT, **flags):
  '''
  Evaluates ``goals`` in a child on the backend of this test process and
  returns a dict from the name to the sorted list of values (as text) or to
  the error line.  A child that does not end fails the test.
  '''
  flags.setdefault('backend', curry.flags['backend'])
  code = CHILD % {'flags': flags, 'goals': list(goals)}
  proc = cytest.run_in_subprocess(code, timeout, address_space=ADDRESS_SPACE)
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


class TestControls(cytest.TestCase):
  '''The goals that ended before the change keep their values: the control
  of the issue, the operation failed beside a choice, the failure cell
  beside a choice (dropped without a fork now, with a fork before), a
  choice beside a value, and the shared pair of issue #126.'''
  EXPECTED = {
      'goal0': []
    , 'goalChoice': []
    , 'goalOrder': []
    , 'ctrlPair': ['(1, 3)', '(2, 3)']
    , 'ctrlShared': ['(1, 2)']
    }

  @classmethod
  def setUpClass(cls):
    # Compile the module here; the children load it from the cache.
    curry.import_('FailSib')

  def test_values(self):
    self.assertEqual(run_child(self.EXPECTED), self.EXPECTED)

  def test_under_the_checker(self):
    self.assertEqual(run_child(self.EXPECTED, checker=True), self.EXPECTED)


class TestDroppedBeforeTheStep(cytest.TestCase):
  '''The goals the look-ahead ends: the reproducer, the failure one level
  down, the failure a step leaves, the reproducer under an alternative
  with a value, and the two goals whose failure appears after the parent
  cell was read (the read again after a step).  Each child must end within
  the short timeout.'''
  EXPECTED = {
      'goal': []
    , 'goal2': []
    , 'goalFwd': []
    , 'ctrlOuter': ['(5, 5)']
    , 'captureShared': []
    , 'captureStep': []
    }

  @classmethod
  def setUpClass(cls):
    curry.import_('FailSib')

  def test_values(self):
    results = run_child(self.EXPECTED, timeout=SHORT_TIMEOUT)
    self.assertEqual(results, self.EXPECTED)

  def test_under_the_checker(self):
    results = run_child(self.EXPECTED, timeout=SHORT_TIMEOUT, checker=True)
    self.assertEqual(results, self.EXPECTED)


class TestSetFunctions(cytest.TestCase):
  '''The reproducer inside a set function (set0 goal): the failure is the
  function's own, an inside failure of the capsule, so the alternative is
  dropped and the set is empty, [] on both backends.  KiCS2 does not end
  the run, so the test asserts the end of the run alone: the child ends
  within the short timeout, and the goal does not raise.'''
  GOALS = ['goalSet']

  @classmethod
  def setUpClass(cls):
    curry.import_('FailSib')

  def check(self, results):
    self.assertEqual(sorted(results), sorted(self.GOALS))
    for name in self.GOALS:
      self.assertIsInstance(results[name], list, results[name])

  def test_runs_end(self):
    self.check(run_child(self.GOALS, timeout=SHORT_TIMEOUT))

  def test_under_the_checker(self):
    self.check(run_child(self.GOALS, timeout=SHORT_TIMEOUT, checker=True))


class TestBoxedFailureBesideALoop(TestSetFunctions):
  '''A boxed failure beside an alternative that does not end, inside a set
  function (set1 over failed, with the alternatives x ? loop).  The first
  child meets the boxed failure at its cursor; under the failure rule in
  its deferred form the capsule records it as an outside failure and goes
  on with the second child, (loop, guard failed), whose failure sits
  behind a set guard that the look-ahead does not read through, so the run
  does not end, as in KiCS2.  Before that rule the first boxed failure
  failed the whole set function at once under the flag setting 'escape',
  and the run ended.  A read through a set guard is a decision of the
  owner (item 3 of the TODO entry of 2026-10-12 on the look-ahead).  Until
  then the tests are expected failures: the child is killed at the short
  timeout, and a fix ends it at once and shows as an unexpected success.'''
  GOALS = ['goalSetArg']

  @unittest.expectedFailure
  def test_runs_end(self):
    self.check(run_child(self.GOALS, timeout=SHORT_TIMEOUT))

  @unittest.expectedFailure
  def test_under_the_checker(self):
    self.check(run_child(self.GOALS, timeout=SHORT_TIMEOUT, checker=True))
