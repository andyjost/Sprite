'''
Tests for the guard at the merge of two bound classes (decision D26 of
2026-10-12 on the Fair Scheme).  The programs are in
data/curry/BoundMerge.curry.  Every test runs on both backends, in a child
under prlimit and timeout; one child evaluates the goals, one more runs
them under the checker, and the counts of the guards are read in process.

The rule: the constraint store keeps, per configuration, the classes of
free variables that strict equalities united and the bindings that
non-strict equalities (=:<=) gave them, one binding per class under its
root.  When a union of the constraint step joins two classes that both
carry a binding, and the two binding cells are not one cell, the union
goes ahead, the merged class keeps the binding of the root the union
keeps, and the strict equality of the two bindings, b1 =:= b2, guards the
result of the step: the result becomes (b1 =:= b2) &> result in the
private root of the configuration (the shared constraint cell is left as
it is).  The guard is an ordinary strict equality of the program: its
failure drops the configuration, its success yields True in its place, and
its own pairings proceed as usual.  Several unions in one step (the
pairing of two generators leaf by leaf) each add their guard, nested under
&>.  One cell under both roots is one binding, and a union with one bound
class moves the binding, without a guard.

Before the decision the merge of two distinct cells failed the step
(issue #128), which lost the value of two equal terms not yet evaluated
(eqShapeG18 of unit_constraints.py).  The values are those of KiCS2.
'''
import cytest # from ./lib; must be first
import curry

ADDRESS_SPACE = 2 << 30
TIMEOUT = 300

# Evaluates goals of the test module and prints one line per goal: its name
# and the sorted values as Curry text, or the name of the error.
CHILD = '''
import cytest, curry
curry.reset(**%(flags)r)
M = curry.import_('BoundMerge')
for name in %(goals)r:
  try:
    values = cytest.raw.values(getattr(M, name))
    print(name, sorted(str(value) for value in values))
  except Exception as exc:
    print(name, 'error', type(exc).__name__, str(exc))
'''

# The values of KiCS2 (the harness of the Fair Scheme proofs, 2026-10-12),
# sorted as text, as the child prints them.
EXPECTED = {
    'evalEq': ['(Nothing, Nothing)', '(Just True, Just True)']
  , 'unevalEq': ['(0, 0)', '(2, 2)']
  , 'diffVal': ['(0, 0)']
  , 'sameCell': ['(0, 0)', '(2, 2)']
  , 'leafEq': ['(A, A)', '(B 2, B 2)']
  , 'leafDiff': ['(A, A)']
  , 'three': ['(N, N)', '(P 2 2, P 2 2)']
  , 'threeDiff': ['(N, N)']
  , 'narrowIn': ['(Nothing, Nothing, False)', '(Just True, Just True, True)']
  , 'narrowLeaf': ['(A, A, 0)', '(B 2, B 2, 2)']
  }
EXPECTED = {name: sorted(values) for name, values in EXPECTED.items()}

# The number of guards the constraint step of the second alternative makes,
# as the checker counts them (merge_guards).
GUARDS = {
    'evalEq': 1, 'unevalEq': 1, 'diffVal': 1, 'sameCell': 0
  , 'leafEq': 1, 'leafDiff': 1, 'three': 2, 'threeDiff': 2, 'narrowIn': 1
  , 'narrowLeaf': 1
  }

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


class TestValues(cytest.TestCase):
  '''The values of KiCS2, in one child.'''
  @classmethod
  def setUpClass(cls):
    # Compile the module here; the children load it from the cache.
    curry.import_('BoundMerge')
    cls.results = run_child(EXPECTED)

  def check(self, goal):
    self.assertEqual(self.results[goal], EXPECTED[goal])

  def test_evaluated_equal_bindings(self): self.check('evalEq')
  def test_unevaluated_equal_bindings(self): self.check('unevalEq')
  def test_different_values(self): self.check('diffVal')
  def test_one_cell(self): self.check('sameCell')
  def test_equal_leaves(self): self.check('leafEq')
  def test_different_leaves(self): self.check('leafDiff')
  def test_three_classes(self): self.check('three')
  def test_three_classes_different(self): self.check('threeDiff')
  def test_guard_narrows_a_variable(self): self.check('narrowIn')
  def test_guard_narrows_a_leaf(self): self.check('narrowLeaf')


class TestChecker(cytest.TestCase):
  '''The goals under the checker: the values are the same, and no
  invariant is reported (E11 and D26 are in).'''
  @classmethod
  def setUpClass(cls):
    curry.import_('BoundMerge')

  def test_checker(self):
    self.assertEqual(run_child(EXPECTED, checker=True), EXPECTED)


class TestGuardCounts(cytest.TestCase):
  '''The constraint step makes one guard per union of two bound classes:
  none for one cell under both roots, two when the pairing unites three
  bound classes.  The checker counts the pairs the step reports
  (merge_guards), read in process.'''
  @classmethod
  def setUpClass(cls):
    cls.backend = curry.flags['backend']
    curry.reset(**{'backend': cls.backend, 'checker': True})

  def setUp(self):
    self.M = curry.import_('BoundMerge')

  @classmethod
  def tearDownClass(cls):
    curry.reset(**{'backend': cls.backend, 'checker': False})

  def evaluate(self, goal):
    '''The sorted values of ``goal`` and the counts of the checker.'''
    interp = cytest.raw.interp()
    node = cytest.raw.expr(goal)
    from curry.backends.cxx import curryrtbindings
    rts = curryrtbindings.RuntimeState(interp, node)
    values = sorted(str(v) for v in rts.generate_values())
    counts = curryrtbindings.checker_counts(rts)
    return values, counts

  def test_counts(self):
    for name, expected in sorted(GUARDS.items()):
      with self.subTest(goal=name):
        values, counts = self.evaluate(getattr(self.M, name))
        self.assertEqual(values, EXPECTED[name])
        self.assertEqual(counts.get('merge_guards', 0), expected)
        # No union outside the constraint step at the root (the fork, the
        # pairing of get_generator) merged two distinct binding cells.
        self.assertEqual(counts.get('unguarded_merges', 0), 0)
        self.assertNotIn('violations', counts)
