'''
Tests for the pairing of a decided variable with a free one in a strict
equality (decision D25 of 2026-10-12 on the Fair Scheme).  The programs
are in data/curry/Pairing.curry.  Every test runs on both backends, in a
child under prlimit and timeout; one child per class evaluates the goals
of the class, and one more runs them under the checker.

The rule: when a step of =:= meets, on one side, a variable that is free
in the configuration (its group undecided, no binding) and, on the other
side, a variable the configuration decides (its generator was written by
an earlier narrowing, and the fingerprint decides its top choice), the
step records the pair of the two variables, the constraint cell the step
makes for two free variables.  The constraint step then unites the two
classes, with the occurs check, and the free variable reads the instance
of the decided class through the class.  Before, the step expanded the
decided variable to its instance and narrowed the free one against it by
a fork.  The two readings give the same values; the pairing forks less;
and a cyclic pair fails the step where the narrowing ran without end
(goalR and g10 of unit_occurs.py, cycleVar below).  A free variable
against a constructor term narrows as before, and two decided variables
are expanded as before.

After a case on x, the body of the rule reads x as the constructor cell of
the decided branch of its generator, a constructor term to the step, which
narrows a free variable against it by a fork; the equalities below it meet
the variables of the two cells and pair them, so a cycle through such a
cell fails one level down (cycleLeaf).
'''
import cytest # from ./lib; must be first
import curry

ADDRESS_SPACE = 2 << 30
TIMEOUT = 300
# The child of the cycles ends at once; a regression to the endless
# narrowing is killed after this, apart from the value goals.
SHORT_TIMEOUT = 30

# Evaluates goals of the test module and prints one line per goal: its name
# and the sorted values as Curry text, or the name of the error.
CHILD = '''
import curry
curry.reload(%(flags)r)
M = curry.import_('Pairing')
for name in %(goals)r:
  try:
    values = curry.eval(getattr(M, name), converter=None)
    print(name, sorted(str(value) for value in values))
  except Exception as exc:
    print(name, 'error', type(exc).__name__, str(exc))
'''

def run_child(goals, timeout=TIMEOUT, **flags):
  '''
  Evaluates ``goals`` in a child on the backend of this test process and
  returns a dict from the name to the sorted list of values (as text) or to
  the error line.
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


class GoalsCase(cytest.TestCase):
  '''One child per class; a test reads the values of one goal.'''
  EXPECTED = {}

  @classmethod
  def setUpClass(cls):
    # Compile the module here; the children load it from the cache.
    curry.import_('Pairing')
    cls.results = run_child(cls.EXPECTED)

  def check(self, goal):
    self.assertEqual(self.results[goal], self.EXPECTED[goal])


class TestPairing(GoalsCase):
  '''
  The values of the narrowing reading, with their count: a decided variable
  on the left or on the right of a free one, a value per decided branch,
  the free variable read through the merged class, an inner variable
  narrowed after the union, two decided variables, a free variable against
  a constructor term, a decided variable against a constructor term, and
  with no cycle.  The two cycles are in TestPairedCycle.
  '''
  EXPECTED = {
      'leftDecided': ['S _a']
    , 'rightDecided': ['S _a']
    , 'bothBranches': ['S _a', 'Z']
    , 'readThrough': ['(S _a, True)']
    , 'deeper': ['(S Z, S Z)']
    , 'bothDecided': ['(S Z, S Z)']
    , 'againstTerm': ['(S Z, Z)']
    , 'decidedAgainstTerm': ['S Z']
    }

  def test_left_decided(self): self.check('leftDecided')
  def test_right_decided(self): self.check('rightDecided')
  def test_both_branches(self): self.check('bothBranches')
  def test_read_through(self): self.check('readThrough')
  def test_deeper(self): self.check('deeper')
  def test_both_decided(self): self.check('bothDecided')
  def test_against_term(self): self.check('againstTerm')
  def test_decided_against_term(self): self.check('decidedAgainstTerm')


class TestPairedCycle(cytest.TestCase):
  '''
  The two cycles, in the paired form (cycleVar) and through the matched
  argument (cycleLeaf): no value.  They run in their own child with the
  short timeout, so that a regression to the endless narrowing is killed
  after 30 s and does not hide the values of the finite goals.
  '''
  CYCLES = {'cycleVar': [], 'cycleLeaf': []}

  @classmethod
  def setUpClass(cls):
    curry.import_('Pairing')

  def test_cycles(self):
    results = run_child(self.CYCLES, timeout=SHORT_TIMEOUT)
    self.assertEqual(results, self.CYCLES)

  def test_under_the_checker(self):
    results = run_child(self.CYCLES, timeout=SHORT_TIMEOUT, checker=True)
    self.assertEqual(results, self.CYCLES)


class TestChecker(cytest.TestCase):
  '''
  The finite goals of the pairing under the checker: the values are the
  same, and no invariant is reported (the check Def 2.62 reads the rule
  of decision D25).
  '''
  @classmethod
  def setUpClass(cls):
    curry.import_('Pairing')

  def test_checker(self):
    expected = dict(TestPairing.EXPECTED)
    results = run_child(expected, checker=True)
    self.assertEqual(results, expected)
