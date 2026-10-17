'''
Tests for rule N.1 of the Fair Scheme read at the cursor of the scan
(decision D27 of 2026-10-12; issues #132 and #136).  The programs are in
data/curry/FailSib.curry.  Every test runs on both backends, in a child
under prlimit and timeout; one child evaluates the goals, and one more runs
them under the checker.

The rule: the scan of a constructor-rooted configuration reads a failure at
its cursor alone, as KiCS2 does, not over every successor of a constructor
cell before the descent, as the thesis states rule N.1.  The look-ahead of
2026-10-12 read the whole cell; decision D27 removed it: no value depends
on it, since a configuration with a failure under its constructor spine has
no value under either reading and a step at the sibling of a failure is a
step at a needed position, and the theorems of safety and optimality hold
under both.  The difference is in termination alone: the goal
let t = failed in (t ? loop, t) ends under the eager reading and does not
end under the cursor reading, as in KiCS2.  FailSib.curry keeps those goals
as records; no test runs them.

The tests here are the goals that end under the cursor reading, with their
values.  TestCapturedFailure holds the three capture goals of FailSib.curry,
which the set0 lift of decision D28 (2026-10-12) made end: the compiler
lifts set0 (t + 1) over the captured t into set1 L t, so t is boxed at the
entry of the capsule, its failure is an outside failure of the set
function, which fails, and length fails at the cursor before the scan
reaches loop.  Before the lift the failure was the function's own, the set
was empty, and the scan then stepped loop without end.
'''
import cytest # from ./lib; must be first
import curry

ADDRESS_SPACE = 2 << 30
TIMEOUT = 300

# Evaluates goals of the test module and prints one line per goal: its name
# and the sorted values as Curry text, or the name of the error.
CHILD = '''
import curry
curry.reset(**%(flags)r)
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


class TestCursorReading(cytest.TestCase):
  '''The goals that end under the cursor reading keep their values: the
  control of issue #132 (a failure beside a choice without a diverging
  alternative), the operation failed beside a choice, the failure cell
  beside a choice (a fork, then both children drop), a choice beside a
  value, and the shared pair of issue #126.'''
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


class TestCapturedFailure(cytest.TestCase):
  '''The captured variable t of set0 fails beside loop (decision D28): the
  lifted set function fails on the boxed failure, length fails at the
  cursor, and the run ends with no value, whether the failing cell is a
  successor of the root (captureShared), under a step at the cursor
  (captureStep), or one level down (captureDeep).'''
  EXPECTED = {
      'captureShared': []
    , 'captureStep': []
    , 'captureDeep': []
    }

  @classmethod
  def setUpClass(cls):
    curry.import_('FailSib')

  def test_values(self):
    self.assertEqual(run_child(self.EXPECTED), self.EXPECTED)

  def test_under_the_checker(self):
    self.assertEqual(run_child(self.EXPECTED, checker=True), self.EXPECTED)
