'''
Tests for the occurs check at the union of two classes of free variables in
a strict equality (the decision of 2026-10-12 on the Fair Scheme).  The
programs are in data/curry/Occurs.curry.  Every test runs on both backends,
in a child under prlimit and timeout; one child per class evaluates the
goals of the class, and one more runs them under the checker.

The rule: when a constraint step unites the class of x with the class of y,
the merged class is tested for a cycle, a member whose generator instance,
as created so far, contains another member of the class.  Such a class has
no finite instance, so the step fails as an inconsistent constraint does,
and the configuration is dropped.  The Lean mechanization of the theory
found that without it the scheme yields a value no instance of the goal
produces: goal below gave True and then dumped core past the stack guard
of the C++ backend (issue #131) or raised a recursion error on the Python
backend (KiCS2 3.5.0 gives True and False); it gives True alone now.  The
checker verifies the invariant (D15 (occurs check)) at every fork,
constraint step and yield.

Two goals of the decision reach the union through the equality step:
goalR, the right alternative alone, and g10, the audit's infinite class.
In both, the step meets a decided variable and a variable that is free in
the configuration, and records the pair (decision D25 of 2026-10-12; see
unit_pairing.py) instead of expanding the decided one and narrowing the
free one against its instance without end, so the union and its check
happen, and both goals give no value.
'''
import cytest # from ./lib; must be first
import curry

ADDRESS_SPACE = 2 << 30
TIMEOUT = 300
# The child of the paired cycles ends at once; a regression to the endless
# narrowing is killed after this.
SHORT_TIMEOUT = 30

# Evaluates goals of the test module and prints one line per goal: its name
# and the sorted values as Curry text, or the name of the error.
CHILD = '''
import curry
curry.reload(%(flags)r)
M = curry.import_('Occurs')
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
    curry.import_('Occurs')
    cls.results = run_child(cls.EXPECTED)

  def check(self, goal):
    self.assertEqual(self.results[goal], self.EXPECTED[goal])


class TestSharedCell(GoalsCase):
  '''The goal of the Lean counterexample and its second type: the right
  alternative meets the shared constraint cell at its root, and the union
  would put a variable inside the instance of its own class.  True alone.'''
  EXPECTED = {'goal': ['True'], 'goalJ': ['True']}

  def test_goal(self): self.check('goal')
  def test_goalJ(self): self.check('goalJ')


class TestControls(GoalsCase):
  '''Unions without a cycle keep their values: a decided class united with
  a free variable, an instance that reaches another decided class, a
  variable united with a leaf of another instance, two narrowed variables
  paired leaf by leaf, and the five-cell goal of Constraints.curry.'''
  EXPECTED = {
      'ctrlShared': ['True', 'True']
    , 'ctrlChain': ['True', 'True']
    , 'ctrlLeaf': ['True', 'True']
    , 'ctrlPair': ['(False, False)', '(True, True)']
    , 'fiveCells': [
          '(False, True, True, True, True)', '(True, True, False, False, False)'
        ]
    }

  def test_shared(self): self.check('ctrlShared')
  def test_chain(self): self.check('ctrlChain')
  def test_leaf(self): self.check('ctrlLeaf')
  def test_pair(self): self.check('ctrlPair')
  def test_five_cells(self): self.check('fiveCells')


class TestPairedCycle(cytest.TestCase):
  '''
  The two goals whose cycle reaches the union through the pairing of the
  equality step (decision D25): goalR (the right alternative of goal
  alone) and g10 (the audit's infinite class).  Both give no value and
  end; before the decision both narrowed without end (see the module
  docstring).
  '''
  @classmethod
  def setUpClass(cls):
    curry.import_('Occurs')

  def test_goalR_and_g10(self):
    results = run_child(['goalR', 'g10'], timeout=SHORT_TIMEOUT)
    self.assertEqual(results, {'goalR': [], 'g10': []})

  def test_under_the_checker(self):
    results = run_child(['goalR', 'g10'], timeout=SHORT_TIMEOUT, checker=True)
    self.assertEqual(results, {'goalR': [], 'g10': []})


class TestChecker(cytest.TestCase):
  '''
  The goals of the shared cell and the controls under the checker: the
  values are the same, and no invariant is reported (the check D15 is in).
  '''
  @classmethod
  def setUpClass(cls):
    curry.import_('Occurs')

  def test_checker(self):
    expected = {}
    for cls in (TestSharedCell, TestControls):
      expected.update(cls.EXPECTED)
    results = run_child(expected, checker=True)
    self.assertEqual(results, expected)
