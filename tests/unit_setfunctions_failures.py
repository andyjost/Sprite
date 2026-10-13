'''
Tests for the failure rule F2 of the set functions in its deferred form
(Definition 2.94 of the note on the Fair Scheme; the owner's decision of
2026-10-12), Sprite's one rule on both backends.  The programs are in
data/curry/SetFunctionsFailures.curry.  Every test runs on both backends,
in a child under prlimit and timeout; one child per class evaluates the
goals of the class, and one more runs them under the checker.

The rule.  (d1) When a configuration of a capsule meets a failure that came
from an argument (a boxed failure: the path from the root of the
configuration to the failure crosses a set guard), the configuration is
dropped, as every failure drops a configuration, and the capsule records an
outside failure with the sets of the enclosing guards the failure crossed,
less its own, and the level at which the failure entered the chain of the
capsules; a failure that crossed no guard is the function's own, and the
capsule records an inside failure.  (d2) When the queue of the capsule is
empty, the capsule is a failure when it produced no value, recorded no
inside failure and recorded some outside failure; its set stands
otherwise, empty or not.  (d3) The failure goes under the guards of the
records at the innermost level (the failures that entered the chain
innermost; deviation 147 of the README of the Lean development), together,
so it escapes to the capsule whose argument it came from; a failure that
crossed the guard of the capsule alone is a plain failure of the enclosing
configuration.  record_failure (state/rts_setfunctions.cpp,
eval/rts_setfunctions.py) makes the record, and allValues
(currylib/setfunctions.cpp, currylib/setfunctions.py) gives the verdict.

Before the change the runtime failed the set function at the first boxed
failure it met: t1, t2, t3, d2a, lazyT, valThenFail and level had no value,
t4 gave False and levelB [], so the value depended on the order of the
alternatives, which the schedule-independence theorem forbids.  The
expected values are those of KiCS2 3.5.0, observed through the harness of
the Fair Scheme proofs on 2026-10-12.
'''
import cytest # from ./lib; must be first
import curry

ADDRESS_SPACE = 2 << 30
TIMEOUT = 300

# Evaluates goals of the test module and prints one line per goal: its name
# and the sorted values as Curry text, or the name of the error.
CHILD = '''
import curry
curry.reload(%(flags)r)
M = curry.import_('SetFunctionsFailures')
for name in %(goals)r:
  try:
    values = curry.eval(getattr(M, name))
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
    curry.import_('SetFunctionsFailures')
    cls.results = run_child(cls.EXPECTED)

  def check(self, goal):
    self.assertEqual(self.results[goal], self.EXPECTED[goal], goal)


class TestOneCapsule(GoalsCase):
  '''
  One capsule.  The example of CHRS13 in both orders (t1, t2) and its
  isEmpty (t3, t4); an inside failure beside the outside one in both
  orders (d2a, d2b: the set is empty); a value produced before the failing
  argument is demanded (lazyT) and one beside a later demand through an
  arithmetic step (valThenFail); an inside failure, an outside failure and
  a value in one capsule (mixed) and without the value (mixedE); the
  failure captured by the function value (t1c); one failing alternative
  of the argument (argFail: one set and no value); and an alternative that
  dies through a failed constraint step at the root, an inside failure
  (cycleInside, cycleInsideS).
  '''
  EXPECTED = {
      't1': ['[True]']
    , 't2': ['[True]']
    , 't3': ['False']
    , 't4': ['False']
    , 'd2a': ['True']
    , 'd2b': ['True']
    , 'lazyT': ['[True]']
    , 'valThenFail': ['[1]']
    , 'mixed': ['[2]']
    , 'mixedE': ['True']
    , 't1c': ['[True]']
    , 'argFail': ['[0]']
    , 'cycleInside': ['True']
    , 'cycleInsideS': ['[]']
    }

  def test_t1(self): self.check('t1')
  def test_t2(self): self.check('t2')
  def test_t3(self): self.check('t3')
  def test_t4(self): self.check('t4')
  def test_d2a(self): self.check('d2a')
  def test_d2b(self): self.check('d2b')
  def test_lazyT(self): self.check('lazyT')
  def test_valThenFail(self): self.check('valThenFail')
  def test_mixed(self): self.check('mixed')
  def test_mixedE(self): self.check('mixedE')
  def test_t1c(self): self.check('t1c')
  def test_argFail(self): self.check('argFail')

  def test_cycle_inside(self):
    '''An alternative that dies through a failed constraint step at the
    root (no failure cell) records an inside failure: the set stands empty
    beside the outside failure.'''
    self.check('cycleInside')
    self.check('cycleInsideS')

  def test_order_independent(self):
    '''The two orders of the alternatives give one value (theorem S3).'''
    self.assertEqual(self.results['t1'], self.results['t2'])
    self.assertEqual(self.results['t3'], self.results['t4'])
    self.assertEqual(self.results['d2a'], self.results['d2b'])


class TestNestedCapsules(GoalsCase):
  '''
  Two capsules.  The level of a failure through both (level, levelB: the
  records at the innermost level decide, so the inner capsule is a plain
  failure and the outer set is empty), the outer argument alone demanded
  inside the inner capsule (levelC: both capsules fail), the inner
  capsule's own argument inside a total outer one (level2), an inside
  failure of the inner function under the box of the outer argument
  (ownflag), and set0, which boxes nothing (set0Inner, set0InnerV).
  '''
  EXPECTED = {
      'level': ['[]']
    , 'levelB': ['[]']
    , 'levelC': []
    , 'level2': ['[]']
    , 'ownflag': ['[0]']
    , 'set0Inner': []
    , 'set0InnerV': ['[[7]]']
    }

  def test_level(self): self.check('level')
  def test_levelB(self): self.check('levelB')
  def test_levelC(self): self.check('levelC')
  def test_level2(self): self.check('level2')
  def test_ownflag(self): self.check('ownflag')
  def test_set0Inner(self): self.check('set0Inner')
  def test_set0InnerV(self): self.check('set0InnerV')

  def test_level_order_independent(self):
    '''The record of a capsule is a set: the two orders of h agree.'''
    self.assertEqual(self.results['level'], self.results['levelB'])


class TestChecker(cytest.TestCase):
  '''
  The goals under the checker: the values are the same, and no invariant
  is reported (the checks F2 (d1), (d2) and (d3) of the record).
  '''
  @classmethod
  def setUpClass(cls):
    curry.import_('SetFunctionsFailures')

  def test_one_capsule(self):
    expected = dict(TestOneCapsule.EXPECTED)
    self.assertEqual(run_child(expected, checker=True), expected)

  def test_nested_capsules(self):
    expected = dict(TestNestedCapsules.EXPECTED)
    self.assertEqual(run_child(expected, checker=True), expected)
