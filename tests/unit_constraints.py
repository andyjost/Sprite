'''
Tests for the equational constraints (=:=) and (=:<=) over free variables,
from the audit of the implementation against the proved rules of the Fair
Scheme (2026-10-11): issues #127, #128 and #129.  The programs are in
data/curry/Constraints.curry, under the names of the issues.  Every test
runs on both backends, in a child under prlimit and timeout; one child per
class evaluates the goals of the class, and one more runs them under the
checker.

Issue #127: the generator of a decided class was read at the union-find
root alone, and the union by size can make a variable without a generator
the root.  The yield then copied the Unit marker of the variable into the
value (C++) or asserted (Python).  The pairing of a decided class
(_constrain_equal_rec) now finds its pivot among every member and gives the
root a clone, so a decided class has a generator at its root (the checker
verifies it at every fork, constraint step and yield: E5).

Issue #128: at a union of two classes, the binding of the old root was
moved to the new root without a test of the result, so a merge of two
classes bound to different terms kept one binding (C++) or asserted
(Python).  A binding sits under the root of its class now (the checker
verifies it: E11), and the merge of two classes bound to distinct cells
keeps one binding and guards the result of the step with the strict
equality of the two (decision D26 of 2026-10-12; unit_boundmerge.py):
the guard fails for two different terms, so g18, g18t and g5 keep their
values, and succeeds for two equal terms not yet evaluated, which the
first rule after the issue, a failure of the step, lost (eqShapeG18).

Issue #129: the equality steps read "bound" as "has a generator" before
they read the fingerprint, so a variable that another alternative narrowed
was narrowed again instead of bound by its constraint, and (=:<=) evaluated
its right side in each alternative.  The steps take a variable that is
free in the configuration as it is (hnf_or_free with ``free``; the marker
FREE_IN_CONFIGURATION of the C++ steps), and the checker verifies that no
equality step narrows a variable the configuration left free.
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
M = curry.import_('Constraints')
for name in %(goals)r:
  try:
    values = cytest.raw.values(getattr(M, name))
    print(name, sorted(str(value) for value in values))
  except Exception as exc:
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


class GoalsCase(cytest.TestCase):
  '''One child per class; a test reads the values of one goal.'''
  EXPECTED = {}

  @classmethod
  def setUpClass(cls):
    # Compile the module here; the children load it from the cache.
    curry.import_('Constraints')
    cls.results = run_child(cls.EXPECTED)

  def check(self, goal):
    self.assertEqual(self.results[goal], self.EXPECTED[goal])


class TestDecidedClassRoot(GoalsCase):
  '''Issue #127: the values of KiCS2.'''
  EXPECTED = {
      'g14': ['(False, True, True)', '(True, True, False)']
    , 'g16': [
          '(False, True, True, True, True)', '(True, True, False, False, False)'
        ]
    , 'g16b': ['(False, True, True)', '(True, True, False)']
    }

  def test_g14(self): self.check('g14')
  def test_g16(self): self.check('g16')
  def test_g16b(self): self.check('g16b')


class TestMergeOfBoundClasses(GoalsCase):
  '''Issue #128: (A, A) alone, False alone, no value for g5.'''
  EXPECTED = {
      'g5': []
    , 'g18': ['(A, A)']
    , 'g18t': ['False']
    , 'eqJust': ['(Just True, Just True)']
    , 'orphan': ['(True, True)']
    }

  def test_g5(self): self.check('g5')
  def test_g18(self): self.check('g18')
  def test_g18t(self): self.check('g18t')
  def test_equal_bindings(self): self.check('eqJust')
  def test_binding_of_the_old_root(self): self.check('orphan')


class TestMergeOfEqualUnevaluatedTerms(GoalsCase):
  '''
  The case of issue #128 the owner decided (D26): two classes bound to
  equal but unevaluated terms in distinct cells, united by a shared
  constraint cell.  The merge keeps one binding and guards the step with
  the equality (1 + 1) =:= (1 + 1), so the second value stands (KiCS2:
  (0, 0) and (2, 2)).  Before the decision the merge counted the two cells
  as different and failed the step, and (2, 2) was lost.
  '''
  EXPECTED = {'eqShapeG18': ['(0, 0)', '(2, 2)']}

  def test_eqShapeG18(self): self.check('eqShapeG18')


class TestEqualityOfFreeVariable(GoalsCase):
  '''Issue #129: g20 gives the three values of KiCS2; the value set of g15
  stays, in the yield form of KiCS2; g22 stays.'''
  EXPECTED = {
      'g20': ['(False, True)', '(True, False)', '(True, True)']
    , 'g22': ['(True, True)']
    , 'g15': ['(False, True)', '(True, False)', '(_a, _a)']
    , 'strictApp': ['False', 'False', 'False', 'True']
    }

  def test_g20(self): self.check('g20')
  def test_g22(self): self.check('g22')
  def test_g15(self): self.check('g15')
  def test_strict_application(self): self.check('strictApp')


class TestChecker(cytest.TestCase):
  '''
  The goals of the three issues under the checker: the values are the
  same, and no invariant is reported (the checks E5, E11 and Def 2.62 of
  the audit are in).
  '''
  @classmethod
  def setUpClass(cls):
    curry.import_('Constraints')

  def test_checker(self):
    expected = {}
    for cls in (
        TestDecidedClassRoot, TestMergeOfBoundClasses
      , TestMergeOfEqualUnevaluatedTerms, TestEqualityOfFreeVariable
      ):
      expected.update(cls.EXPECTED)
    results = run_child(expected, checker=True)
    self.assertEqual(results, expected)
