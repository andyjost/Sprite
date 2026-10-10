'''
Tests for the C++ mirror of the checker mode of the Fair Scheme proofs
program: the interpreter flag ``checker`` on the C++ backend and the checker
of the runtime (src/cyrt/checker.hpp), section 6.5 of the memo on the Fair
Scheme proofs.  The checker of the Python backend and its tests
(unit_py_checker.py) are the model.

Two kinds of tests.  The known-good programs of the suite (the set-function,
functional-pattern and free-variable programs) run under the checker without
a report, with the values and the counters they have without it, compiled
and under interpret:all.  And one constructed violation per check, provoked
through the debug entry points of the bindings (cyrtbindings.checker_debug_*),
which corrupt one configuration of a runtime state on purpose or run one
check on constructed nodes; the entries work only while the flag is on.

The checker drives the C++ runtime, so the white-box tests skip on the
Python backend.
'''
import cytest # from ./lib; must be first
from curry.common import LEFT, RIGHT, T_FUNC
import curry, unittest

CXX = curry.flags['backend'] == 'cxx'
LEFT, RIGHT = int(LEFT), int(RIGHT)

def _cb():
  from curry.backends.cxx import cyrtbindings
  return cyrtbindings

def _state(goal):
  '''A runtime state of the global interpreter over the node ``goal``.'''
  return _cb().RuntimeState(curry.getInterpreter(), goal)

def _values(module, name, *args):
  return sorted(str(v) for v in curry.eval(getattr(module, name), *args))

def _goals(module):
  '''The nullary functions of a module, by name.'''
  from curry import inspect
  return sorted(
      name for name, sym in inspect.symbols(module).items()
          if sym.info.tag == T_FUNC and sym.info.arity == 0
    )

def _node(*args):
  return curry.raw_expr(*args)

def _choice(cid, lhs, rhs):
  return curry.raw_expr(curry.choice(cid, lhs, rhs))

def _make(info, *args):
  return _cb().make_node(getattr(info, 'info', info), *args)

def _just(node):
  return _make(curry.getInterpreter().prelude.Just, node)

def _vid(x):
  '''The id of a free variable node.'''
  return x.successor(0)

def _totals():
  t = curry.getInterpreter()._evaluation_totals
  return t.steps, t.forks

# A name a functional pattern produced, read many times (the shape of
# unit_funcpat_narrowed.py), a residuation that another alternative releases,
# a narrowing and a pairing.
PROGRAMS = '''
import Control.SetFunctions

source :: String -> String
source (stem ++ ".o") = stem ++ ".c"

sourceS :: String -> String
sourceS t = case sortValues (set1 source t) of [s] -> s

many :: (String -> String) -> Int
many f = length [() | _ <- [1 .. 20], s == "ab.c"]
  where s = f "ab.o"

distinct :: (String -> String) -> Int
distinct f = length (nubList (map f [[x, y] ++ ".o" | x <- "ab", y <- "ab"]))

nubList :: [String] -> [String]
nubList [] = []
nubList (x:xs) = x : nubList (filter (/= x) xs)

manySource :: Int
manySource = many source

manySourceS :: Int
manySourceS = many sourceS

distinctSource :: Int
distinctSource = distinct source

released :: Int
released = (x =:= (3 ? 4)) &> (x + 1) where x free

data T3 = P | Q | R
  deriving (Eq, Ord, Show)

pick :: T3 -> Int
pick P = 1
pick Q = 2
pick R = 3

narrowed :: Int
narrowed = pick y where y free

paired :: (T3, T3)
paired = (x =:= y) &> (pick x =:= 2) &> (x, y) where x, y free
'''

# The goals of unit_setfunctions_bugs.py whose evaluation ends (pickOverlap
# does not end, by the program of its issue: the test takes its first six
# values).
BUGS_GOALS = [
    'anyOfSet', 'tailsSet', 'headOrLastSet', 'argAfterStart', 'boundVar'
  , 'capturedChoiceAfterStart', 'capturedThenGuarded', 'capturedVarAfterStart'
  , 'choiceAfterStart', 'choiceArg', 'choiceCaptured', 'escapeUndecided'
  , 'forced', 'forcedStrict', 'longArg', 'longPlain', 'longPlainChoice'
  , 'longPlainList', 'narrowedAfterStart', 'narrowedInData', 'nestedAfterStart'
  , 'nestedAlive', 'nestedAliveChoice', 'nestedBound', 'pick2', 'twoCapsules'
  , 'twoSets', 'viaCall', 'viaData', 'viaForward', 'viaPartial'
  ]

# The program of the defect the Python checker found: a captured choice
# reached through a forward node in front of its box.  The C++ backend gives
# the values of weakly encapsulated search.
DROPPED_BOX = '''
import Control.SetFunctions

data T = A | B
  deriving (Eq, Ord, Show)

constT :: T -> Int -> T
constT t _ = t

pickOne :: T -> (Int -> T) -> [T]
pickOne z f = [z] ? [f 0]

oneCaptured :: (Int, T)
oneCaptured = let x = A ? B in
  let vs = sortValues (set2 pickOne A (constT x)) in (length vs, x)
'''

# The program of the false alarm of both checkers fixed on 2026-10-09 (see
# TestSharedArgument): a boxed argument whose evaluation outside the box,
# after the capsule started, creates a choice.  The capsule yields 0 without
# demanding the argument; the enclosing configuration steps g2 at the
# flagged cell and then `?`.  The `?` cell is made under the result of the
# step of g2, so it inherits the flags of the redex, and the choice it
# creates is argument-derived for the box; the second alternative of the
# capsule pulls the choice across the box.  The runtime gives the values of
# weakly encapsulated search.  g2 cases on an argument computed at run
# time, so the front end does not inline it.
SHARED_ARGUMENT = '''
import Control.SetFunctions

data T = A | B
  deriving (Eq, Ord, Show)

g2 :: Int -> Maybe T
g2 n = case n of { 1 -> Just (A ? B); _ -> Nothing }

fromJust' :: Maybe T -> T
fromJust' (Just y) = y

f2 :: Maybe T -> Int
f2 x = 0 ? (case x of Just y -> case y of { A -> 1; B -> 2 })

lazyThenOutside2 :: (Int, T, [Int])
lazyThenOutside2 = let a = g2 (length [()]) in
  let vs = valuesOf (set1 f2 a) in
  (head vs, fromJust' a, vs)

h2 :: Maybe T -> Int
h2 x = case x of Just y -> case y of { A -> 10; B -> 20 }

twoCapsulesChoice2 :: (Int, Int, T, [Int], [Int])
twoCapsulesChoice2 = let a = g2 (length [()]) in
  let vs = valuesOf (set1 f2 a) in
  let ws = valuesOf (set1 f2 a) in
  (head vs, head ws, fromJust' a, vs, ws)

capturedThenShared2 :: (Int, T, [Int], [Int])
capturedThenShared2 = let a = g2 (length [()]) in
  let vs = valuesOf (set1 f2 a) in
  let ws = valuesOf (set1 h2 a) in
  (head vs, fromJust' a, vs, ws)
'''

# The shape of lazyThenOutside2 with a step that builds more cells than the
# budget of one propagation walk (1024): the step of gBig at the flagged
# argument builds about 2300 cells.  The walk flags the cells near the
# result and runs out before the first element, so the choice e 1 creates
# outside the box carries no tag.  The sets of the flags become unbounded
# at that point, so the pull-tab across the box is not reported.
BIG_STEP = '''
import Control.SetFunctions

e :: Int -> Int
e i = i ? (i + 1)

gBig :: Int -> [Int]
gBig n = case n of { 1 -> [%s]; _ -> [] }

fFirst :: [Int] -> Int
fFirst x = 0 ? (x !! 0)

bigThenOutside :: (Int, Int, [Int])
bigThenOutside = let a = gBig (length [()]) in
  let vs = valuesOf (set1 fFirst a) in
  (head vs, a !! 0, vs)
''' % ', '.join('e (%s)' % ('(' * 10 + str(i) + ' + 0)' * 10) for i in range(1, 101))


@unittest.skipIf(not CXX, 'the checker of the C++ runtime')
class CheckerTestCase(cytest.TestCase):
  '''A test case under the checker.  The flags are set for the class.'''
  FLAGS = {'backend': 'cxx', 'checker': True}

  @classmethod
  def setUpClass(cls):
    curry.reload(cls.FLAGS)

  @classmethod
  def tearDownClass(cls):
    curry.reload({'backend': 'cxx', 'checker': False})

  def flags(self, **more):
    return dict(self.FLAGS, **more)


class TestFlag(cytest.TestCase):
  def test_default_off(self):
    '''The flag is off by default.'''
    from curry.interpreter import flags
    self.assertEqual(flags.get_default_flags()['checker'], False)

  @unittest.skipIf(not CXX, 'the checker of the C++ runtime')
  def test_off_means_no_checker(self):
    '''With the flag off the runtime state holds no checker, and the debug
    entries refuse.'''
    curry.reload({'backend': 'cxx', 'checker': False})
    try:
      rts = _state(_node(1))
      self.assertFalse(_cb().checker_enabled(rts))
      with self.assertRaises(ValueError):
        _cb().checker_counts(rts)
    finally:
      curry.reload({'backend': 'cxx'})

  @unittest.skipIf(not CXX, 'the checker of the C++ runtime')
  def test_on_means_checker(self):
    curry.reload({'backend': 'cxx', 'checker': True})
    try:
      rts = _state(_node(1))
      self.assertTrue(_cb().checker_enabled(rts))
      self.assertEqual(_cb().checker_counts(rts), {})
    finally:
      curry.reload({'backend': 'cxx', 'checker': False})

  def test_accepted_on_every_backend(self):
    curry.reload({'checker': True})
    try:
      self.assertEqual(curry.flags['checker'], True)
      self.assertEqual([curry.topython(v) for v in curry.eval(curry.expr(1))], [1])
    finally:
      curry.reload({'checker': False})

  @unittest.skipIf(not CXX, 'the checker of the C++ runtime')
  def test_violation_is_an_assertion_error(self):
    '''A report reaches Python as an AssertionError that names the
    invariant, the event, the configuration and the goal position.'''
    curry.reload({'backend': 'cxx', 'checker': True})
    try:
      cb = _cb()
      self.assertTrue(issubclass(cb.InvariantViolation, AssertionError))
      rts = _state(_node(1))
      cb.checker_debug_set_root(rts, _just(_choice(5, 1, 2)))
      with self.assertRaises(cb.InvariantViolation) as cm:
        cb.checker_debug_check_yield(rts)
      text = str(cm.exception)
      self.assertIn('Fair Scheme invariant B1 (yield) violated at yield', text)
      self.assertIn('identifiers: [5]', text)
      self.assertIn('configuration: queue #', text)
      self.assertIn('goal position: []', text)
      self.assertIn('root: (Just (?5 1 2))', text)
    finally:
      curry.reload({'backend': 'cxx', 'checker': False})


class TestKnownGood(CheckerTestCase):
  '''
  The known-good programs run under the checker without a report, and the
  checker changes no value and no counter: the values and the steps and
  forks under the flag equal those without it.
  '''
  def both_ways(self, compute):
    with_checker = compute()
    curry.reload(self.flags(checker=False))
    try:
      without = compute()
    finally:
      curry.reload(self.FLAGS)
    self.assertEqual(with_checker, without)
    return with_checker

  def module_goals(self, modname, names=None, **flags):
    def compute():
      if flags:
        curry.reload(self.flags(checker=curry.flags['checker'], **flags))
      M = curry.import_(modname)
      goals = _goals(M) if names is None else names
      return {name: _values(M, name) for name in goals}
    return self.both_ways(compute)

  def test_setfunction_semantics(self):
    '''The goals of the probe table of the memo, under both failure rules.'''
    for setting in ('encapsulate', 'escape'):
      values = self.module_goals(
          'SetFunctionsSemantics', setfunction_failures=setting
        )
      self.assertEqual(values['s1'], ['[(-1), 1]', '[0, 2]'])

  def test_setfunction_bindings(self):
    values = self.module_goals('SetFunctionsBindings')
    self.assertEqual(values['sharedCase'], ['(0, 1)', '(0, 2)'])

  def test_setfunction_bugs(self):
    values = self.module_goals('SetFunctionsBugs', BUGS_GOALS)
    self.assertEqual(
        values['pick2']
      , ['[1, 2]', '[1, 3]', '[2, 1]', '[2, 3]', '[3, 1]', '[3, 2]']
      )

  def test_functional_patterns(self):
    self.module_goals('FunPatFreeArg')
    self.module_goals('FunPatFreeArgSet')

  def test_free_variables(self):
    '''The goals of unit_cxx_freevars.py.'''
    def compute():
      M = curry.import_('CxxFreeVars')
      return {
          'narrowMany': _values(M, 'narrowMany', 500)
        , 'bindMany': _values(M, 'bindMany', 500)
        , 'uniteMany': _values(M, 'uniteMany', 100)
        , 'triple': _values(M, 'triple')
        , 'wakeByNarrowing': _values(M, 'wakeByNarrowing')
        , 'lasts': _values(M, 'lasts', 10)
        }
    values = self.both_ways(compute)
    self.assertEqual(values['narrowMany'], ['500'])
    self.assertEqual(values['wakeByNarrowing'], ['I', 'I', 'O', 'O'])

  def test_programs(self):
    '''The narrowed name, the released residual, the narrowing, the pairing.'''
    def compute():
      M = curry.compile(PROGRAMS, modulename='CxxCheckerPrograms')
      return {name: _values(M, name) for name in _goals(M)}
    values = self.both_ways(compute)
    self.assertEqual(values['manySource'], ['20'])
    self.assertEqual(values['manySourceS'], ['20'])
    self.assertEqual(values['distinctSource'], ['4'])
    self.assertEqual(values['released'], ['4', '5'])
    self.assertEqual(values['narrowed'], ['1', '2', '3'])
    self.assertEqual(values['paired'], ['(Q, Q)'])

  def test_dropped_box(self):
    '''The program of the defect of the Python backend: the C++ runtime
    passes the checker with the values of weakly encapsulated search.'''
    def compute():
      M = curry.compile(DROPPED_BOX, modulename='CxxCheckerDroppedBox')
      return _values(M, 'oneCaptured')
    self.assertEqual(self.both_ways(compute), ['(2, A)', '(2, B)'])

  def test_counters_unchanged(self):
    '''The steps and the forks of a search are the same with the flag on
    and off.'''
    def compute():
      M = curry.compile(PROGRAMS, modulename='CxxCheckerCounters')
      counters = {}
      for name in ('manySource', 'distinctSource', 'manySourceS', 'paired'):
        before = _totals()
        list(curry.eval(getattr(M, name)))
        after = _totals()
        counters[name] = (after[0] - before[0], after[1] - before[1])
      return counters
    counters = self.both_ways(compute)
    self.assertGreater(counters['manySource'][1], 8)

  def test_counts(self):
    '''The checker saw the events of a search.'''
    M = curry.compile(PROGRAMS, modulename='CxxCheckerCounts')
    rts = _state(_node(M.narrowed))
    self.assertEqual(sorted(str(v) for v in rts.generate_values()), ['1', '2', '3'])
    counts = _cb().checker_counts(rts)
    self.assertGreater(counts['forks'], 0)
    self.assertGreater(counts['pulltabs'], 0)
    self.assertEqual(counts['yields'], 3)
    self.assertEqual(counts['instantiations'], 1)
    self.assertEqual(counts['generators'], 1)
    self.assertGreater(counts['hnfs'], 0)
    self.assertEqual(counts['steps'], rts.steps_total)
    self.assertNotIn('violations', counts)


# The child of the interpreted known-good tests: evaluates the goals the
# body names under the flags of its environment and prints them as JSON.
# A fresh process per run: a process that loaded a module from its compiled
# object does not survive a reload into interpret:all (the TODO entry of
# the C++ checker holds the reproducer), so the mode is set before the
# first import, through the environment of the child.
INTERPRETED_CHILD = '''
import curry, json, sys
from curry import inspect
from curry.common import T_FUNC
PROGRAMS = %(programs)r
DROPPED_BOX = %(dropped_box)r
BUGS_GOALS = %(bugs_goals)r
def goals(M):
  return sorted(
      name for name, sym in inspect.symbols(M).items()
          if sym.info.tag == T_FUNC and sym.info.arity == 0
    )
def values(M, name, *args):
  return sorted(str(v) for v in curry.eval(getattr(M, name), *args))
def module_goals(modname, names=None):
  M = curry.import_(modname)
  return {name: values(M, name) for name in (goals(M) if names is None else names)}
out = {}
%(body)s
print(json.dumps(out))
'''


@unittest.skipIf(not CXX, 'the checker of the C++ runtime')
class TestKnownGoodInterpreted(cytest.TestCase):
  '''
  The known-good programs under the ICurry interpreter of the runtime
  (interpret:all), where the definitional trees are checked as well: the
  same goals as TestKnownGood, in a child per run, with the values and the
  counters they have without the checker.
  '''
  TIMEOUT = 300
  ADDRESS_SPACE = 4 << 30

  def child(self, body, checker):
    import json, os
    flags = 'backend:cxx,interpret:all,checker:%s' % ('true' if checker else 'false')
    code = INTERPRETED_CHILD % {
        'programs': PROGRAMS, 'dropped_box': DROPPED_BOX, 'bugs_goals': BUGS_GOALS
      , 'body': body
      }
    saved = os.environ.get('SPRITE_INTERPRETER_FLAGS')
    os.environ['SPRITE_INTERPRETER_FLAGS'] = flags
    try:
      proc = cytest.run_in_subprocess(
          code, self.TIMEOUT, address_space=self.ADDRESS_SPACE
        )
    finally:
      if saved is None:
        del os.environ['SPRITE_INTERPRETER_FLAGS']
      else:
        os.environ['SPRITE_INTERPRETER_FLAGS'] = saved
    self.assertEqual(
        proc.returncode, 0
      , 'the child (checker=%s) ended with status %s; stdout:\n%s\nstderr:\n%s'
            % (checker, proc.returncode, proc.stdout, proc.stderr)
      )
    return json.loads(proc.stdout.strip().splitlines()[-1])

  def both_ways(self, body):
    with_checker = self.child(body, True)
    without = self.child(body, False)
    self.assertEqual(with_checker, without)
    return with_checker

  def test_setfunction_semantics(self):
    for setting in ('encapsulate', 'escape'):
      values = self.both_ways(
          "curry.reload(dict(curry.flags, setfunction_failures=%r))\n"
          "out.update(module_goals('SetFunctionsSemantics'))" % setting
        )
      self.assertEqual(values['s1'], ['[(-1), 1]', '[0, 2]'])

  def test_setfunction_bindings(self):
    values = self.both_ways("out.update(module_goals('SetFunctionsBindings'))")
    self.assertEqual(values['sharedCase'], ['(0, 1)', '(0, 2)'])

  def test_setfunction_bugs(self):
    values = self.both_ways("out.update(module_goals('SetFunctionsBugs', BUGS_GOALS))")
    self.assertEqual(
        values['pick2']
      , ['[1, 2]', '[1, 3]', '[2, 1]', '[2, 3]', '[3, 1]', '[3, 2]']
      )

  def test_functional_patterns(self):
    self.both_ways(
        "out.update(module_goals('FunPatFreeArg'))\n"
        "out.update(module_goals('FunPatFreeArgSet'))"
      )

  def test_free_variables(self):
    values = self.both_ways(
        "M = curry.import_('CxxFreeVars')\n"
        "out['narrowMany'] = values(M, 'narrowMany', 500)\n"
        "out['bindMany'] = values(M, 'bindMany', 500)\n"
        "out['uniteMany'] = values(M, 'uniteMany', 100)\n"
        "out['triple'] = values(M, 'triple')\n"
        "out['wakeByNarrowing'] = values(M, 'wakeByNarrowing')\n"
        "out['lasts'] = values(M, 'lasts', 10)"
      )
    self.assertEqual(values['narrowMany'], ['500'])
    self.assertEqual(values['wakeByNarrowing'], ['I', 'I', 'O', 'O'])

  def test_programs(self):
    values = self.both_ways(
        "M = curry.compile(PROGRAMS, modulename='CxxCheckerProgramsI')\n"
        "out.update({name: values(M, name) for name in goals(M)})"
      )
    self.assertEqual(values['manySource'], ['20'])
    self.assertEqual(values['narrowed'], ['1', '2', '3'])
    self.assertEqual(values['paired'], ['(Q, Q)'])

  def test_dropped_box(self):
    values = self.both_ways(
        "M = curry.compile(DROPPED_BOX, modulename='CxxCheckerDroppedBoxI')\n"
        "out['oneCaptured'] = values(M, 'oneCaptured')"
      )
    self.assertEqual(values['oneCaptured'], ['(2, A)', '(2, B)'])

  def test_counters_and_counts(self):
    '''The steps and the forks are the same with the flag on and off, and
    under the interpreter the hnf calls checked outnumber the untracked
    ones.'''
    body = (
        "M = curry.compile(PROGRAMS, modulename='CxxCheckerCountersI')\n"
        "def totals():\n"
        "  t = curry.getInterpreter()._evaluation_totals\n"
        "  return t.steps, t.forks\n"
        "for name in ('manySource', 'distinctSource', 'manySourceS', 'paired'):\n"
        "  before = totals()\n"
        "  list(curry.eval(getattr(M, name)))\n"
        "  after = totals()\n"
        "  out[name] = [after[0] - before[0], after[1] - before[1]]\n"
      )
    counters = self.both_ways(body)
    self.assertGreater(counters['manySource'][1], 8)
    counts = self.child(
        body
        + "from curry.backends.cxx import cyrtbindings as cb\n"
          "rts = cb.RuntimeState(curry.getInterpreter(), curry.raw_expr(M.narrowed))\n"
          "out['values'] = sorted(str(v) for v in rts.generate_values())\n"
          "out['counts'] = cb.checker_counts(rts)\n"
      , True)
    self.assertEqual(counts['values'], ['1', '2', '3'])
    self.assertGreater(counts['counts']['hnfs'], counts['counts'].get('hnf_untracked', 0))
    self.assertEqual(counts['counts']['yields'], 3)
    self.assertNotIn('violations', counts['counts'])


class TestIdentifierConsistency(CheckerTestCase):
  '''RI B1.'''
  def test_group_invariant_at_fork(self):
    '''A decided member of a group whose root is undecided.'''
    cb = _cb()
    P = curry.getInterpreter().prelude
    rts = _state(_node([getattr(P, '?'), 0, 1]))
    root = cb.checker_debug_unite(rts, 100, 101)
    # The check reads the ids the union-find united (every member of a
    # group of two or more is among them), not every entry of the
    # fingerprint: the ids must be there.
    united = cb.checker_debug_united(rts)
    self.assertIn(100, united)
    self.assertIn(101, united)
    cb.checker_debug_set_fp(rts, 101 if root == 100 else 100, LEFT)
    with self.assertRaisesRegex(cb.InvariantViolation, r'B1 \(group\)'):
      list(rts.generate_values())

  def test_fork_records_the_decision(self):
    '''Each clone of a fork records the decision, and two clones decide
    the two sides.'''
    cb = _cb()
    rts = _state(_node(0))
    cb.checker_debug_set_root(rts, _choice(5, 1, 2))
    cb.checker_debug_check_fork(rts, [LEFT, RIGHT])
    with self.assertRaisesRegex(cb.InvariantViolation, 'B1.*does not record the decision of 5'):
      cb.checker_debug_check_fork(rts, [0])
    with self.assertRaisesRegex(cb.InvariantViolation, 'B1.*the clones decide 5 as'):
      cb.checker_debug_check_fork(rts, [LEFT, LEFT])

  def test_fork_keeps_the_parents_decisions(self):
    '''Rule D.2: a clone that drops a decision of its parent, and one that
    adds a decision beside the forked identifier and its root.'''
    cb = _cb()
    rts = _state(_node(1))
    cb.checker_debug_check_clone(rts, [(5, LEFT)], [(5, LEFT), (7, RIGHT)], 7)
    with self.assertRaisesRegex(
        cb.InvariantViolation, r'B1 \(fork\).*lost the decision'
      ):
      cb.checker_debug_check_clone(rts, [(5, LEFT)], [(7, RIGHT)], 7)
    with self.assertRaisesRegex(
        cb.InvariantViolation, r'B1 \(fork\).*adds the identifiers \[9\]'
      ):
      cb.checker_debug_check_clone(
          rts, [(5, LEFT)], [(5, LEFT), (7, LEFT), (9, RIGHT)], 7
        )

  def test_pulltab_identifier(self):
    '''The created choice must carry the identifier of its source.'''
    cb = _cb()
    rts = _state(_node(1))
    target = _choice(7, 1, 2)
    a, b = target.successor(1), target.successor(2)
    root = _just(target)
    lhs, rhs = _just(a), _just(b)
    cb.checker_debug_pulltab_begin(rts, root, target, [0])
    cb.checker_debug_pulltab_end(rts, root, target, [0], lhs, rhs, _choice(7, a, b))
    with self.assertRaisesRegex(cb.InvariantViolation, 'pull-tab.*carries identifier 8'):
      cb.checker_debug_pulltab_end(rts, root, target, [0], lhs, rhs, _choice(8, a, b))

  def test_pulltab_copies(self):
    '''The alternatives must be fresh copies of the spine.'''
    cb = _cb()
    rts = _state(_node(1))
    target = _choice(7, 1, 2)
    a, b = target.successor(1), target.successor(2)
    root = _just(target)
    lhs, rhs = _just(a), _just(b)
    cb.checker_debug_pulltab_begin(rts, root, target, [0])
    with self.assertRaisesRegex(cb.InvariantViolation, 'shares the cell'):
      cb.checker_debug_pulltab_end(rts, root, target, [0], lhs, root)
    with self.assertRaisesRegex(cb.InvariantViolation, 'not the replacement'):
      cb.checker_debug_pulltab_end(rts, root, target, [0], rhs, rhs)
    with self.assertRaisesRegex(cb.InvariantViolation, 'not at the path'):
      cb.checker_debug_pulltab_begin(rts, root, target, [0, 1])

  def test_no_choice_in_a_value(self):
    cb = _cb()
    rts = _state(_node(1))
    cb.checker_debug_set_root(rts, _just(_choice(5, 1, 2)))
    with self.assertRaisesRegex(cb.InvariantViolation, r'B1 \(yield\)'):
      cb.checker_debug_check_yield(rts)

  def test_no_operation_in_a_value(self):
    cb = _cb()
    P = curry.getInterpreter().prelude
    rts = _state(_node(1))
    cb.checker_debug_set_root(rts, _just(_node([P.id, 1])))
    with self.assertRaisesRegex(cb.InvariantViolation, r'B1 \(yield\).*the cell id'):
      cb.checker_debug_check_yield(rts)

  def test_dispatch_chain_agrees(self):
    '''A nested configuration that decides an identifier against the
    enclosing configuration.'''
    cb = _cb()
    rts = _state(_node(1))
    cb.checker_debug_set_fp(rts, 40, LEFT)
    capsule = cb.checker_debug_push_capsule(rts, _node(2))
    try:
      cb.checker_debug_check_yield(rts)
      cb.checker_debug_set_fp(rts, 40, RIGHT)
      with self.assertRaisesRegex(cb.InvariantViolation, 'dispatch chain'):
        cb.checker_debug_check_yield(rts)
    finally:
      cb.checker_debug_pop_capsule(rts)
      del capsule


class TestFreeVariables(CheckerTestCase):
  '''RI X1, X-b, X-b', X-c.'''
  def test_one_generator_per_variable(self):
    cb = _cb()
    rts = _state(_node(1))
    x = cb.checker_debug_freshvar(rts)
    vid = _vid(x)
    gen = _make(cb.Choice, vid, _node(True), _node(False))
    cb.checker_debug_generator(rts, x, gen)
    other = _make(cb.Choice, vid, _node(True), _node(False))
    with self.assertRaisesRegex(cb.InvariantViolation, 'X1.*second generator'):
      cb.checker_debug_generator(rts, x, other)

  def test_root_identifier_is_the_variables(self):
    cb = _cb()
    rts = _state(_node(1))
    x = cb.checker_debug_freshvar(rts)
    bad = _make(cb.Choice, 424242, _node(True), _node(False))
    with self.assertRaisesRegex(cb.InvariantViolation, 'X1.*root of the generator'):
      cb.checker_debug_generator(rts, x, bad)

  def test_no_decided_variable_in_a_value(self):
    cb = _cb()
    rts = _state(_node(1))
    x = cb.checker_debug_freshvar(rts)
    cb.checker_debug_set_root(rts, x)
    cb.checker_debug_check_yield(rts)
    cb.checker_debug_set_fp(rts, _vid(x), LEFT)
    with self.assertRaisesRegex(cb.InvariantViolation, 'X-c.*decided'):
      cb.checker_debug_check_yield(rts)

  def test_no_bound_variable_in_a_value(self):
    cb = _cb()
    rts = _state(_node(1))
    x = cb.checker_debug_freshvar(rts)
    cb.checker_debug_set_root(rts, _just(x))
    cb.checker_debug_check_yield(rts)
    cb.checker_debug_bind(rts, _vid(x), _node(3))
    with self.assertRaisesRegex(cb.InvariantViolation, 'X-c.*is bound and remains'):
      cb.checker_debug_check_yield(rts)

  def test_inner_identifiers_decided(self):
    '''A decided root with an undecided inner identifier.'''
    cb = _cb()
    rts = _state(_node(1))
    x = cb.checker_debug_freshvar(rts)
    vid = _vid(x)
    inner = _make(cb.Choice, 7001, _node(True), _node(False))
    gen = _make(cb.Choice, vid, inner, _node(1))
    cb.checker_debug_attach_generator(rts, x, gen)
    cb.checker_debug_set_fp(rts, vid, LEFT)
    with self.assertRaisesRegex(cb.InvariantViolation, 'X-c.*inner identifier 7001'):
      cb.checker_debug_check_yield(rts)
    cb.checker_debug_set_fp(rts, 7001, RIGHT)
    cb.checker_debug_check_yield(rts)

  def test_copy_keeps_the_reduct(self):
    '''A private copy of the spine whose reduct differs from the root it
    replaces.'''
    cb = _cb()
    rts = _state(_node(1))
    old, new = _just(_node(2)), _just(_node(1))
    with self.assertRaisesRegex(cb.InvariantViolation, "X-b'.*copy \\(binding\\)"):
      cb.checker_debug_copied(rts, old, new, [0], new.successor(0), 'binding')
    same = _just(old.successor(0))
    cb.checker_debug_copied(rts, old, same, [0], same.successor(0), 'binding')

  def test_instantiation_keeps_the_reducts(self):
    '''The write of rule S.x: the configuration is corrupted beside the slot
    between the two halves of the check, in the test alone.  A second
    configuration in the queue, so that the reducts are compared (a lone
    configuration skips the comparison).'''
    cb = _cb()
    P = curry.getInterpreter().prelude
    rts = _state(_node(1))
    cb.checker_debug_append(rts, _node(0))
    x = cb.checker_debug_freshvar(rts)
    root = _make(getattr(P, '(,)'), _node(5), x)
    cb.checker_debug_set_root(rts, root)
    gen = _make(cb.Choice, _vid(x), _node(True), _node(False))
    cb.checker_debug_attach_generator(rts, x, gen)
    cb.checker_debug_instantiate_begin(rts, [1], gen)
    root.set_successor(1, gen)
    cb.checker_debug_instantiate_end(rts, [1])
    root.set_successor(1, x)
    cb.checker_debug_instantiate_begin(rts, [1], gen)
    root.set_successor(0, _node(6))
    root.set_successor(1, gen)
    with self.assertRaisesRegex(cb.InvariantViolation, 'X-b.*reduct of a configuration'):
      cb.checker_debug_instantiate_end(rts, [1])

  def test_slot_holds_the_generator(self):
    '''The slot must hold the generator after the write.'''
    cb = _cb()
    rts = _state(_node(1))
    x = cb.checker_debug_freshvar(rts)
    root = _just(x)
    cb.checker_debug_set_root(rts, root)
    gen = _make(cb.Choice, _vid(x), _node(True), _node(False))
    cb.checker_debug_attach_generator(rts, x, gen)
    cb.checker_debug_instantiate_begin(rts, [0], gen)
    root.set_successor(0, _node(3))
    with self.assertRaisesRegex(cb.InvariantViolation, 'X-b.*not the generator'):
      cb.checker_debug_instantiate_end(rts, [0])


class TestSetFunctions(CheckerTestCase):
  '''RI S0, S-split.'''
  def test_escape_set_holds_argument_derived_identifiers(self):
    '''A pull-tab across a box inserts the identifier into the escape set
    of the set (def:s-pull); the identifier must be argument-derived for
    the set (E in A).'''
    cb = _cb()
    rts = _state(_node(1))
    capsule = cb.checker_debug_push_capsule(rts, _node(1))
    try:
      target = _choice(7, 1, 2)
      a, b = target.successor(1), target.successor(2)
      root = _just(cb.checker_debug_guard(rts, target))
      lhs = _just(cb.checker_debug_guard(rts, a))
      rhs = _just(cb.checker_debug_guard(rts, b))
      with self.assertRaisesRegex(cb.InvariantViolation, r'S0 \(E in A\)'):
        cb.checker_debug_pulltab_begin(rts, root, target, [0, 1])
      cb.checker_debug_tag(rts, 7)
      cb.checker_debug_pulltab_begin(rts, root, target, [0, 1])
      with self.assertRaisesRegex(
          cb.InvariantViolation, r'S0 \(pull-tab\).*not in its escape set'
        ):
        cb.checker_debug_pulltab_end(rts, root, target, [0, 1], lhs, rhs)
      cb.checker_debug_escape_insert(rts, 7)
      cb.checker_debug_pulltab_end(rts, root, target, [0, 1], lhs, rhs)
      cb.checker_debug_check_yield(rts)
    finally:
      cb.checker_debug_pop_capsule(rts)
      del capsule

  def test_fork_inside_a_capsule_is_function_derived(self):
    '''A fork of the scheduler inside a capsule on an argument-derived
    identifier that did not escape.'''
    cb = _cb()
    rts = _state(_node(0))
    capsule = cb.checker_debug_push_capsule(rts, _choice(777, 1, 2))
    try:
      cb.checker_debug_tag(rts, 777)
      with self.assertRaisesRegex(cb.InvariantViolation, 'S0.*argument-derived'):
        list(rts.generate_values())
    finally:
      cb.checker_debug_pop_capsule(rts)
      del capsule

  def test_fork_inside_a_nested_capsule_on_an_outer_identifier(self):
    '''An identifier in the escape set of the enclosing capsule forks inside
    the inner capsule (def:s-escapes names the enclosing sets).'''
    cb = _cb()
    rts = _state(_node(0))
    outer = cb.checker_debug_push_capsule(rts, _node(3))
    inner = cb.checker_debug_push_capsule(rts, _choice(778, 1, 2))
    try:
      cb.checker_debug_tag(rts, 778, 1)
      cb.checker_debug_escape_insert(rts, 778, 1, True)
      with self.assertRaisesRegex(
          cb.InvariantViolation, 'S0.*escape sets of the enclosing sets'
        ):
        cb.checker_debug_check_fork(rts)
    finally:
      cb.checker_debug_pop_capsule(rts)
      cb.checker_debug_pop_capsule(rts)
      del inner, outer

  def test_fork_inside_a_capsule_on_a_decided_identifier(self):
    '''An identifier the enclosing configuration decided forks inside the
    capsule without a split.'''
    cb = _cb()
    rts = _state(_node(0))
    cb.checker_debug_set_fp(rts, 779, LEFT)
    capsule = cb.checker_debug_push_capsule(rts, _choice(779, 1, 2))
    try:
      with self.assertRaisesRegex(cb.InvariantViolation, 'S0.*decided by an enclosing'):
        cb.checker_debug_check_fork(rts)
    finally:
      cb.checker_debug_pop_capsule(rts)
      del capsule

  def test_escape_is_argument_derived(self):
    '''A split on a function-derived identifier no enclosing configuration
    decided.'''
    cb = _cb()
    rts = _state(_node(0))
    capsule = cb.checker_debug_push_capsule(rts, _node(1))
    try:
      with self.assertRaisesRegex(cb.InvariantViolation, 'S0.*function-derived'):
        cb.checker_debug_split(rts, 99)
    finally:
      cb.checker_debug_pop_capsule(rts)
      del capsule

  def test_split_invariant(self):
    '''A split that keeps a decided configuration in both queues.'''
    cb = _cb()
    rts = _state(_node(0))
    capsule = cb.checker_debug_push_capsule(rts, _node(1))
    try:
      cb.checker_debug_append(rts, _node(2))
      cb.checker_debug_set_fp(rts, 9, LEFT, 0)
      cb.checker_debug_set_fp(rts, 9, RIGHT, 1)
      cb.checker_debug_tag(rts, 9)
      with self.assertRaisesRegex(cb.InvariantViolation, 'S-split'):
        cb.checker_debug_check_escape_shared(rts, 9)
    finally:
      cb.checker_debug_pop_capsule(rts)
      del capsule

  def test_split_records_and_names(self):
    '''After a split both queues record the identifier, the new queue holds
    configurations of the queue alone, and both queues name one set.'''
    cb = _cb()
    rts = _state(_node(0))
    capsule = cb.checker_debug_push_capsule(rts, _node(1))
    try:
      cb.checker_debug_append(rts, _node(2))
      cb.checker_debug_tag(rts, 9)
      with self.assertRaisesRegex(cb.InvariantViolation, 'S-split.*do not both record 9'):
        cb.checker_debug_check_escape_shared(rts, 9, record=False)
      with self.assertRaisesRegex(
          cb.InvariantViolation, 'S-split.*new queue holds a configuration that was not'
        ):
        cb.checker_debug_check_escape_shared(rts, 9, foreign=True)
      with self.assertRaisesRegex(cb.InvariantViolation, 'S-split.*new queue names set'):
        cb.checker_debug_check_escape_shared(rts, 9, other_set=True)
      cb.checker_debug_check_escape_shared(rts, 9)
    finally:
      cb.checker_debug_pop_capsule(rts)
      del capsule

  def test_split_sorts_the_configurations(self):
    '''A split of the runtime on a tagged identifier passes the checks.'''
    cb = _cb()
    rts = _state(_node(0))
    capsule = cb.checker_debug_push_capsule(rts, _node(1))
    try:
      cb.checker_debug_append(rts, _node(2))
      cb.checker_debug_set_fp(rts, 9, LEFT, 0)
      cb.checker_debug_set_fp(rts, 9, RIGHT, 1)
      cb.checker_debug_tag(rts, 9)
      cb.checker_debug_split(rts, 9)
    finally:
      cb.checker_debug_pop_capsule(rts)
      del capsule

  def test_escape_sets_only_grow(self):
    cb = _cb()
    rts = _state(_node(1))
    capsule = cb.checker_debug_push_capsule(rts, _node(1))
    try:
      cb.checker_debug_escape_insert(rts, 31, 0, True)
      cb.checker_debug_check_yield(rts)
      cb.checker_debug_escape_discard(rts, 31)
      with self.assertRaisesRegex(cb.InvariantViolation, 'escape sets grow.*lost'):
        cb.checker_debug_check_yield(rts)
      cb.checker_debug_escape_insert(rts, 31)
      cb.checker_debug_escape_insert(rts, 55)
      with self.assertRaisesRegex(cb.InvariantViolation, 'escape sets grow.*gained'):
        cb.checker_debug_check_yield(rts)
    finally:
      cb.checker_debug_pop_capsule(rts)
      del capsule


class TestNeededness(CheckerTestCase):
  '''RI B2 against the definitional tree, rebuilt from the bytecode of an
  interpreted operation.  A compiled operation has no tree and is not
  checked (the developer notes state the partial).'''
  SOURCE = '''
k :: Bool -> Bool -> Maybe Int
k x y = if x then (if y then Just 1 else Just 2) else Just 3

h :: Bool -> Int
h True = 1

g :: Int -> Int
g x = x

data T3 = P | Q | R
'''

  @classmethod
  def setUpClass(cls):
    CheckerTestCase.setUpClass()
    cls.M = curry.compile(cls.SOURCE, modulename='CxxCheckerTree')
    cls.interpreted = _cb().icurry_is_interpreted(cls.M.k.info)

  def test_tree(self):
    '''The tree of k: one case on the first argument (the inner case is
    lifted into an operation of its own); a built-in has no tree.'''
    cb = _cb()
    rts = _state(_node(1))
    tree = cb.checker_debug_tree(rts, self.M.k.info)
    if not self.interpreted:
      self.assertIsNone(tree)
      return
    self.assertEqual(tree['kind'], 'case')
    self.assertEqual(tree['path'], [0])
    self.assertFalse(tree['literal'])
    self.assertEqual(sorted(tree['branches']), [0, 1])
    self.assertEqual(tree['branches'][0]['kind'], 'return')
    self.assertEqual(tree['branches'][1]['kind'], 'return')
    self.assertEqual(
        cb.checker_debug_tree(rts, self.M.h.info)['branches'][0]['kind'], 'exempt'
      )
    self.assertEqual(cb.checker_debug_tree(rts, self.M.g.info)['kind'], 'return_ref')
    self.assertIsNone(cb.checker_debug_tree(rts, curry.getInterpreter().prelude.apply.info))

  def test_hnf_at_an_inductive_position(self):
    '''A step that demands the second argument where no branch needs it.'''
    if not self.interpreted:
      self.skipTest('the function is compiled: no tree')
    cb = _cb()
    rts = _state(_node(1))
    cb.checker_debug_set_root(rts, _node([self.M.k, True, False]))
    cb.checker_debug_check_hnf(rts, [0])
    with self.assertRaisesRegex(cb.InvariantViolation, r'B2.*position \[1\]'):
      cb.checker_debug_check_hnf(rts, [1])

  def test_hnf_under_an_unmatched_position(self):
    '''A step that demands the second argument while the inductive position
    above it holds an operation, and one under a constructor no branch
    matches (the node is ill-typed on purpose).'''
    if not self.interpreted:
      self.skipTest('the function is compiled: no tree')
    cb = _cb()
    P = curry.getInterpreter().prelude
    rts = _state(_node(1))
    cb.checker_debug_set_root(rts, _node([self.M.k, [P.id, True], False]))
    cb.checker_debug_check_hnf(rts, [0])
    with self.assertRaisesRegex(
        cb.InvariantViolation, r'B2.*position \[1\] before the inductive position \[0\]'
      ):
      cb.checker_debug_check_hnf(rts, [1])
    cb.checker_debug_set_root(rts, _node([self.M.k, self.M.R, False]))
    with self.assertRaisesRegex(cb.InvariantViolation, r'B2.*matches no branch'):
      cb.checker_debug_check_hnf(rts, [1])

  def test_failure_under_an_unmatched_position(self):
    '''A step that fails while its inductive position holds an operation,
    and one that fails on a constructor no branch matches.'''
    if not self.interpreted:
      self.skipTest('the function is compiled: no tree')
    cb = _cb()
    P = curry.getInterpreter().prelude
    rts = _state(_node(1))
    with self.assertRaisesRegex(cb.InvariantViolation, r'B2 \(failure\).*holds'):
      cb.checker_debug_check_failed_step(rts, _node([self.M.k, [P.id, True], False]))
    with self.assertRaisesRegex(cb.InvariantViolation, r'B2 \(failure\).*matches no branch'):
      cb.checker_debug_check_failed_step(rts, _node([self.M.k, self.M.R, False]))

  def test_failure_from_an_exempt_leaf(self):
    '''A step that fails on a matched rule; a failure from an exempt leaf
    passes, and so does a returned reference, which may be a failure.'''
    if not self.interpreted:
      self.skipTest('the function is compiled: no tree')
    cb = _cb()
    rts = _state(_node(1))
    with self.assertRaisesRegex(cb.InvariantViolation, r'B2 \(failure\).*return leaf'):
      cb.checker_debug_check_failed_step(rts, _node([self.M.k, True, False]))
    cb.checker_debug_check_failed_step(rts, _node([self.M.h, False]))
    cb.checker_debug_check_failed_step(rts, _node([self.M.g, 1]))

  def test_unchanged_step_passes(self):
    self.assertEqual(_values(self.M, 'k', True, False), ['Just 2'])
    self.assertEqual(_values(self.M, 'h', False), [])


class TestSharedArgument(cytest.TestCase):
  '''
  The false alarm of both checkers found in the review of the C++ mirror
  (2026-10-09) and fixed the same day: the step propagation of the flags
  started at the redex, which carries the flags, and stopped there, so a
  `?` cell that a step made at a flagged redex inherited no flag, and the
  choice it created was not argument-derived for the box above the
  argument; the checker reported S0 (E in A) at the pull-tab across the
  box.  The propagation starts at the successors of the result cell now.
  lazyThenOutside2 gives (0, A, [0, 1]) and (0, B, [0, 2]), the values of
  weakly encapsulated search, with the flag off and under the checker.
  '''
  VALUES = {
      'lazyThenOutside2': ['(0, A, [0, 1])', '(0, B, [0, 2])']
    , 'twoCapsulesChoice2': ['(0, 0, A, [0, 1], [0, 1])', '(0, 0, B, [0, 2], [0, 2])']
    , 'capturedThenShared2': ['(0, A, [0, 1], [10])', '(0, B, [0, 2], [20])']
    }
  BIG_VALUES = ['(0, 1, [0, 1])', '(0, 2, [0, 2])']

  def check_values(self, M):
    for name, values in self.VALUES.items():
      self.assertEqual(_values(M, name), values, name)

  def test_values(self):
    M = curry.compile(SHARED_ARGUMENT, modulename='CxxCheckerSharedArgument')
    self.check_values(M)

  def test_big_step_values(self):
    M = curry.compile(BIG_STEP, modulename='CxxCheckerBigStep')
    self.assertEqual(_values(M, 'bigThenOutside'), self.BIG_VALUES)

  @unittest.skipIf(not CXX, 'the checker of the C++ runtime')
  def test_under_the_checker(self):
    '''No report and the same values on the three shapes.'''
    curry.reload({'backend': 'cxx', 'checker': True})
    try:
      M = curry.compile(SHARED_ARGUMENT, modulename='CxxCheckerSharedArgumentChecked')
      self.check_values(M)
    finally:
      curry.reload({'backend': 'cxx', 'checker': False})

  @unittest.skipIf(not CXX, 'the checker of the C++ runtime')
  def test_big_step_under_the_checker(self):
    '''A step over the budget of the walk: the walk is counted, the sets
    of the flags become unbounded, and the pull-tab across the box is not
    reported.  The values are those of the flag-off run.'''
    curry.reload({'backend': 'cxx', 'checker': True})
    try:
      M = curry.compile(BIG_STEP, modulename='CxxCheckerBigStepChecked')
      rts = _state(_node(M.bigThenOutside))
      values = sorted(str(v) for v in rts.generate_values())
      counts = _cb().checker_counts(rts)
    finally:
      curry.reload({'backend': 'cxx', 'checker': False})
    self.assertEqual(values, self.BIG_VALUES)
    self.assertGreaterEqual(counts['propagate_over_budget'], 1)
    self.assertNotIn('violations', counts)


if __name__ == '__main__':
  unittest.main()
