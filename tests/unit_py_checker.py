'''
Tests for the checker mode of the Fair Scheme proofs program: the
interpreter flag ``checker`` and the checker of the Python backend
(backends/py/eval/checker.py), section 6.5 of the memo on the Fair Scheme
proofs.

Two kinds of tests.  The known-good programs of the suite (the set-function,
functional-pattern, free-variable and residuation programs) run under the
checker without a report and with the values they have without it.  And one
constructed violation per check: a state corrupted on purpose through the
Python API, or a step function replaced in the test, which the checker
reports with the name of the invariant.  The program the checker found
wrong, a captured choice behind a forward node in front of its box (issue
#123), is pinned as fixed (TestDroppedBox), with the report of the defect
built from a pull-tab whose path is short of its source.

The checker drives the Python backend, so the white-box tests skip on the
C++ backend; the flag is accepted there and ignored.
'''
import cytest # from ./lib; must be first
from curry.common import LEFT, RIGHT, UNDETERMINED, T_CHOICE, T_FUNC
import curry, unittest

PY = curry.flags['backend'] == 'py'

def _checker():
  from curry.backends.py.eval import checker
  return checker

def _state(goal):
  '''A runtime state of the global interpreter over ``goal``.'''
  from curry.backends.py.eval.rts import RuntimeState
  return RuntimeState(curry.getInterpreter(), goal)

def _values(module, name, *args):
  return sorted(str(v) for v in curry.eval(getattr(module, name), *args))

def _goals(module):
  '''The nullary functions of a module, by name.'''
  from curry import inspect
  return sorted(
      name for name, sym in inspect.symbols(module).items()
          if sym.info.tag == T_FUNC and sym.info.arity == 0
    )

# The goals of the probe table that assert on the Python backend without the
# checker (a guard of an enclosing set at the root; see
# unit_setfunctions_semantics.py).
PY_KNOWN_FAILURES = {'capNested', 'nestFail'}

# Goals of unit_setfunctions_bugs.py that run under the checker.
# nestedBound, the known failure of the Python backend (a guard of an
# enclosing set at the root), is out.  capturedThenGuarded failed under the
# checker before the fix of issue #123.
BUGS_GOALS = [
    'anyOfSet', 'tailsSet', 'headOrLastSet', 'argAfterStart', 'boundVar'
  , 'capturedChoiceAfterStart', 'capturedThenGuarded', 'capturedVarAfterStart'
  , 'choiceAfterStart'
  , 'choiceArg', 'choiceCaptured', 'escapeUndecided', 'forced', 'forcedStrict'
  , 'longArg', 'longPlain', 'longPlainChoice', 'narrowedAfterStart'
  , 'narrowedInData', 'nestedAfterStart', 'nestedAlive', 'nestedAliveChoice'
  , 'pick2', 'twoCapsules', 'twoSets'
  ]

# A name a functional pattern produced, read many times (the shape of
# unit_funcpat_narrowed.py), and a residuation that another alternative
# releases.
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

# The program of issue #123: a captured choice reached through a forward
# node in front of its box.
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
# after the capsule started, creates a choice.
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


@unittest.skipIf(not PY, 'the checker drives the Python backend')
class CheckerTestCase(cytest.TestCase):
  '''A test case under the checker.  The flag is set for the class.'''
  @classmethod
  def setUpClass(cls):
    curry.reload({'backend': 'py', 'checker': True})

  @classmethod
  def tearDownClass(cls):
    curry.reload({'backend': 'py', 'checker': False})


class TestFlag(cytest.TestCase):
  def test_default_off(self):
    '''The flag is off by default.'''
    from curry.interpreter import flags
    self.assertEqual(flags.get_default_flags()['checker'], False)

  @unittest.skipIf(not PY, 'the checker drives the Python backend')
  def test_off_means_no_checker(self):
    '''With the flag off the runtime state holds no checker.'''
    curry.reload({'backend': 'py', 'checker': False})
    try:
      rts = _state(curry.raw_expr(1))
      self.assertIsNone(rts.checker)
    finally:
      curry.reload({'backend': 'py'})

  @unittest.skipIf(not PY, 'the checker drives the Python backend')
  def test_on_means_checker(self):
    curry.reload({'backend': 'py', 'checker': True})
    try:
      rts = _state(curry.raw_expr(1))
      self.assertIsInstance(rts.checker, _checker().Checker)
    finally:
      curry.reload({'backend': 'py', 'checker': False})

  def test_accepted_on_every_backend(self):
    '''The flag is accepted on the backend of the process; the C++ backend
    ignores it.'''
    curry.reload({'checker': True})
    try:
      self.assertEqual(curry.flags['checker'], True)
      self.assertEqual([curry.topython(v) for v in curry.eval(curry.expr(1))], [1])
    finally:
      curry.reload({'checker': False})


class TestKnownGood(CheckerTestCase):
  '''
  The known-good programs run under the checker without a report, and the
  checker changes no value: the values under the flag equal those without
  it.
  '''
  def values_both_ways(self, compute):
    with_checker = compute()
    curry.reload({'backend': 'py', 'checker': False})
    try:
      without = compute()
    finally:
      curry.reload({'backend': 'py', 'checker': True})
    self.assertEqual(with_checker, without)
    return with_checker

  def module_goals(self, modname, names=None, **flags):
    def compute():
      if flags:
        curry.reload(dict(flags, backend='py', checker=curry.flags['checker']))
      M = curry.import_(modname)
      goals = _goals(M) if names is None else names
      return {name: _values(M, name) for name in goals}
    return self.values_both_ways(compute)

  def test_setfunction_semantics(self):
    '''The goals of the probe table of the memo, under both failure rules.'''
    M = curry.import_('SetFunctionsSemantics')
    names = [g for g in _goals(M) if g not in PY_KNOWN_FAILURES]
    for setting in ('encapsulate', 'escape'):
      values = self.module_goals(
          'SetFunctionsSemantics', names, setfunction_failures=setting
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

  def test_captured_forward(self):
    '''The goals of issue #123, which the checker found: a captured
    choice behind a forward node in front of its box.'''
    values = self.module_goals('CapturedFwd')
    self.assertEqual(values['oneCaptured'], ['(2, A)', '(2, B)'])
    self.assertEqual(
        values['oneCapturedSet'], ['([[A], [A]], A)', '([[A], [B]], B)']
      )

  def test_free_variables(self):
    '''The goals of unit_cxx_freevars.py on the Python backend.'''
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
    values = self.values_both_ways(compute)
    self.assertEqual(values['narrowMany'], ['500'])
    self.assertEqual(values['wakeByNarrowing'], ['I', 'I', 'O', 'O'])

  def test_programs(self):
    '''The narrowed name, the released residual, the pairing.'''
    def compute():
      M = curry.compile(PROGRAMS, modulename='CheckerPrograms')
      return {name: _values(M, name) for name in _goals(M)}
    values = self.values_both_ways(compute)
    self.assertEqual(values['manySource'], ['20'])
    self.assertEqual(values['manySourceS'], ['20'])
    self.assertEqual(values['distinctSource'], ['4'])
    self.assertEqual(values['released'], ['4', '5'])
    self.assertEqual(values['narrowed'], ['1', '2', '3'])
    self.assertEqual(values['paired'], ['(Q, Q)'])

  def test_counts(self):
    '''The checker saw the events of a search.'''
    M = curry.compile(PROGRAMS, modulename='CheckerCounts')
    rts = _state(curry.raw_expr(M.narrowed))
    self.assertEqual(sorted(str(v) for v in rts.generate_values()), ['1', '2', '3'])
    counts = rts.checker.counts
    self.assertGreater(counts['forks'], 0)
    self.assertGreater(counts['pulltabs'], 0)
    self.assertEqual(counts['yields'], 3)
    self.assertEqual(counts['instantiations'], 1)
    self.assertEqual(counts['generators'], 1)
    self.assertGreater(counts['hnfs'], 0)
    self.assertEqual(counts['violations'], 0)


class TestIdentifierConsistency(CheckerTestCase):
  '''RI B1.'''
  def test_group_invariant_at_fork(self):
    '''A decided member of a group whose root is undecided.'''
    P = curry.getInterpreter().prelude
    rts = _state(curry.raw_expr([getattr(P, '?'), 0, 1]))
    C = rts.C
    uf = C.strict_constraints.write
    uf.unite(100, 101)
    root = uf.root(100)
    C.fingerprint[101 if root == 100 else 100] = LEFT
    with self.assertRaisesRegex(_checker().InvariantViolation, r'B1 \(group\)'):
      list(rts.generate_values())

  def test_fork_keeps_the_parents_decisions(self):
    '''Rule D.2: a clone that drops the fingerprint of its parent.  Without
    the check the goal gives every combination (16 values for 4).'''
    from curry.backends.py.eval import configuration
    from curry.common import Fingerprint
    M = curry.compile('''
dup2 :: (Bool, Bool, Bool, Bool)
dup2 = let x = True ? False in let y = True ? False in (x, y, x, y)
''', modulename='CheckerDup2')
    self.assertEqual(len(_values(M, 'dup2')), 4)
    original = configuration.Configuration.clone
    def drop(self, root):
      cp = original(self, root)
      cp.fingerprint = Fingerprint()
      return cp
    configuration.Configuration.clone = drop
    try:
      with self.assertRaisesRegex(
          _checker().InvariantViolation, r'B1 \(fork\).*lost the decision'
        ):
        _values(M, 'dup2')
    finally:
      configuration.Configuration.clone = original

  def test_pulltab_identifier(self):
    '''The created choice must carry the identifier of its source.'''
    from curry.backends.py import graph
    rts = _state(curry.raw_expr(1))
    a, b = rts.expr(1), rts.expr(2)
    target = graph.Node(rts.Choice, 7, a, b)
    wrong = graph.Node(rts.Choice, 8, a, b)
    with self.assertRaisesRegex(_checker().InvariantViolation, 'pull-tab'):
      rts.checker.pulltab_done(wrong, target)

  def test_pulltab_copies(self):
    '''The alternatives must be fresh copies of the spine.'''
    from curry.backends.py import graph
    rts = _state(curry.raw_expr(1))
    a, b = rts.expr(1), rts.expr(2)
    target = graph.Node(rts.Choice, 7, a, b)
    root = graph.Node(rts.prelude.Just, target)
    lhs = graph.Node(rts.prelude.Just, a)
    rhs = graph.Node(rts.prelude.Just, b)
    rts.checker.pulltab(root, target, [0], lhs, rhs)  # a faithful pull-tab
    with self.assertRaisesRegex(_checker().InvariantViolation, 'shares the cell'):
      rts.checker.pulltab(root, target, [0], lhs, root)
    with self.assertRaisesRegex(_checker().InvariantViolation, 'not the replacement'):
      rts.checker.pulltab(root, target, [0], rhs, rhs)

  def test_no_choice_in_a_value(self):
    from curry.backends.py import graph
    from curry.backends.py.eval import configuration
    rts = _state(curry.raw_expr(1))
    choice = graph.Node(rts.Choice, 5, rts.expr(1), rts.expr(2))
    config = configuration.Configuration(graph.Node(rts.prelude.Just, choice))
    with self.assertRaisesRegex(_checker().InvariantViolation, r'B1 \(yield\)'):
      rts.checker.yield_(config)

  def test_dispatch_chain_agrees(self):
    '''A nested configuration that decides an identifier against the
    enclosing configuration.'''
    from curry.backends.py.eval import configuration
    rts = _state(curry.raw_expr(1))
    rts.C.fingerprint[40] = LEFT
    sid = rts.create_setfunction()
    qid = rts.create_queue(sid, rts.expr(2))
    rts.push_queue(qid=qid)
    try:
      rts.C.fingerprint[40] = RIGHT
      with self.assertRaisesRegex(_checker().InvariantViolation, 'dispatch chain'):
        rts.checker.yield_(rts.C)
    finally:
      rts.pop_queue()


class TestFreeVariables(CheckerTestCase):
  '''RI X1, X-b', X-c.'''
  def test_one_generator_per_variable(self):
    from curry.backends.py import graph
    rts = _state(curry.raw_expr(1))
    x = rts.freshvar()
    vid = x.successors[0]
    gen = graph.Node(rts.Choice, vid, rts.expr(True), rts.expr(False))
    rts.checker.generator(x, gen)
    other = graph.Node(rts.Choice, vid, rts.expr(True), rts.expr(False))
    with self.assertRaisesRegex(_checker().InvariantViolation, 'X1.*second generator'):
      rts.checker.generator(x, other)

  def test_root_identifier_is_the_variables(self):
    from curry.backends.py import graph
    rts = _state(curry.raw_expr(1))
    x = rts.freshvar()
    bad = graph.Node(rts.Choice, 424242, rts.expr(True), rts.expr(False))
    with self.assertRaisesRegex(_checker().InvariantViolation, 'X1.*root of the generator'):
      rts.checker.generator(x, bad)

  def test_no_decided_variable_in_a_value(self):
    from curry.backends.py.eval import configuration
    rts = _state(curry.raw_expr(1))
    x = rts.freshvar()
    config = configuration.Configuration(x)
    config.fingerprint[x.successors[0]] = LEFT
    with self.assertRaisesRegex(_checker().InvariantViolation, 'X-c.*decided'):
      rts.checker.yield_(config)

  def test_inner_identifiers_decided(self):
    '''A decided root with an undecided inner identifier.'''
    from curry.backends.py.eval import configuration, rts_freevars
    M = curry.compile('data T3 = P | Q | R', modulename='CheckerT3')
    interp = curry.getInterpreter()
    rts = _state(curry.raw_expr(1))
    x = rts.freshvar()
    rts_freevars._make_generator(rts, x, interp.type('CheckerT3.T3'))
    # The left alternative of the root holds the inner choice (P ? Q).
    config = configuration.Configuration(rts.expr(1))
    config.fingerprint[x.successors[0]] = LEFT
    with self.assertRaisesRegex(_checker().InvariantViolation, 'X-c.*inner identifier'):
      rts.checker.yield_(config)

  def test_copy_keeps_the_reduct(self):
    '''A private copy of the spine whose reduct differs from the root it
    replaces.'''
    from curry.backends.py import graph
    rts = _state(curry.raw_expr(1))
    old = graph.Node(rts.prelude.Just, rts.expr(2))
    new = graph.Node(rts.prelude.Just, rts.expr(1))
    with self.assertRaisesRegex(_checker().InvariantViolation, 'X-b'):
      rts.checker.copied(old, new, [0], new.successors[0], 'binding')

  def test_instantiation_keeps_the_reducts(self):
    '''The write of rule S.x changes the reduct of the configuration: the
    copy of the spine is corrupted off its path, in the test alone.'''
    from curry.backends.py.graph import utility
    M = curry.compile('''
data T3 = P | Q | R
g2 :: Int -> T3 -> Int
g2 n P = n
g2 n Q = n + 1
g2 n R = n + 2
h2 :: Int
h2 = g2 5 y where y free
''', modulename='CheckerInst')
    original = utility.copy_spine
    interp = curry.getInterpreter()
    def corrupt(root, realpath, end=None, rewrite=None):
      result = original(root, realpath, end=end, rewrite=rewrite)
      if rewrite is not None:
        rewrite.successors[0] = interp.raw_expr(6)
      return result
    utility.copy_spine = corrupt
    try:
      with self.assertRaisesRegex(_checker().InvariantViolation, 'X-b'):
        list(curry.eval(M.h2))
    finally:
      utility.copy_spine = original


class TestSetFunctions(CheckerTestCase):
  '''RI S0, S-split.'''
  def test_escape_set_holds_argument_derived_identifiers(self):
    rts = _state(curry.raw_expr(1))
    sid = rts.create_setfunction()
    with self.assertRaisesRegex(_checker().InvariantViolation, r'S0 \(E in A\)'):
      rts.update_escape_set(sid, 4242)

  def test_fork_inside_a_capsule_is_function_derived(self):
    from curry.backends.py import graph
    from curry.backends.py.eval.fairscheme import D
    rts = _state(curry.raw_expr(0))
    sid = rts.create_setfunction()
    choice = graph.Node(rts.Choice, 777, rts.expr(1), rts.expr(2))
    qid = rts.create_queue(sid, choice)
    rts.checker.tags[777] = frozenset([sid])
    rts.push_queue(qid=qid)
    try:
      with self.assertRaisesRegex(_checker().InvariantViolation, 'S0.*argument-derived'):
        next(D(rts))
    finally:
      rts.pop_queue()

  def test_fork_inside_a_nested_capsule_on_an_outer_identifier(self):
    '''An identifier in the escape set of the enclosing capsule forks inside
    the inner capsule (def:s-escapes names the enclosing sets).  The
    runtime would split the queue (choice_escapes), so the test turns that
    rule off for the state.'''
    from curry.backends.py import graph
    from curry.backends.py.eval.fairscheme import D
    rts = _state(curry.raw_expr(0))
    outer = rts.create_setfunction()
    inner = rts.create_setfunction()
    choice = graph.Node(rts.Choice, 778, rts.expr(1), rts.expr(2))
    outer_qid = rts.create_queue(outer, rts.expr(3))
    inner_qid = rts.create_queue(inner, choice)
    rts.checker.tags[778] = frozenset([outer])
    rts.update_escape_set(outer, 778)
    rts.choice_escapes = lambda cid: False
    rts.push_queue(qid=outer_qid)
    rts.push_queue(qid=inner_qid)
    try:
      with self.assertRaisesRegex(
          _checker().InvariantViolation, 'S0.*escape sets of the enclosing sets'
        ):
        next(D(rts))
    finally:
      rts.pop_queue()
      rts.pop_queue()

  def test_fork_inside_a_capsule_on_a_decided_identifier(self):
    '''An identifier the enclosing configuration decided forks inside the
    capsule without a split (choice_escapes turned off for the state).'''
    from curry.backends.py import graph
    from curry.backends.py.eval.fairscheme import D
    rts = _state(curry.raw_expr(0))
    rts.C.fingerprint[779] = LEFT
    sid = rts.create_setfunction()
    choice = graph.Node(rts.Choice, 779, rts.expr(1), rts.expr(2))
    qid = rts.create_queue(sid, choice)
    rts.choice_escapes = lambda cid: False
    rts.push_queue(qid=qid)
    try:
      with self.assertRaisesRegex(
          _checker().InvariantViolation, 'S0.*decided by an enclosing'
        ):
        next(D(rts))
    finally:
      rts.pop_queue()

  def test_pulltab_across_a_box_inserts(self):
    '''A pull-tab whose path crosses a box without an insertion into the
    escape set of the set (def:s-pull).'''
    from curry.backends.py import graph
    rts = _state(curry.raw_expr(1))
    sid = rts.create_setfunction()
    a, b = rts.expr(1), rts.expr(2)
    target = graph.Node(rts.Choice, 7, a, b)
    box = graph.Node(rts.SetGuard, sid, target)
    root = graph.Node(rts.prelude.Just, box)
    lhs = graph.Node(rts.prelude.Just, graph.Node(rts.SetGuard, sid, a))
    rhs = graph.Node(rts.prelude.Just, graph.Node(rts.SetGuard, sid, b))
    with self.assertRaisesRegex(
        _checker().InvariantViolation, r'S0 \(pull-tab\).*not in its escape set'
      ):
      rts.checker.pulltab(root, target, [0, 1], lhs, rhs)
    rts.checker.tags[7] = frozenset([sid])
    rts.update_escape_set(sid, 7)
    rts.checker.pulltab(root, target, [0, 1], lhs, rhs)  # the insertion made

  def test_escape_is_argument_derived(self):
    '''A split on a function-derived identifier no enclosing configuration
    decided.'''
    from curry.backends.py.eval import configuration, queue
    rts = _state(curry.raw_expr(0))
    sid = rts.create_setfunction()
    c1 = configuration.Configuration(rts.expr(1))
    Q = queue.Queue([c1], sid=sid)
    rts.qtable[500] = Q
    with self.assertRaisesRegex(_checker().InvariantViolation, 'S0.*function-derived'):
      rts.split_queue(500, 99)

  def test_split_invariant(self):
    from curry.backends.py.eval import configuration, queue
    rts = _state(curry.raw_expr(0))
    sid = rts.create_setfunction()
    rts.checker.tags[9] = frozenset([sid])
    c1 = configuration.Configuration(rts.expr(1))
    c1.fingerprint[9] = LEFT
    c2 = configuration.Configuration(rts.expr(2))
    c2.fingerprint[9] = RIGHT
    Q = queue.Queue([c1, c2], sid=sid)
    R = queue.Queue([c1, c2], sid=sid)
    rts.qtable[500], rts.qtable[501] = Q, R
    Q.decisions.add(9)
    R.decisions.add(9)
    with self.assertRaisesRegex(_checker().InvariantViolation, 'S-split'):
      rts.checker.escape(500, 9, [c1, c2], 501)

  def test_escape_sets_only_grow(self):
    from curry.backends.py.eval import configuration
    rts = _state(curry.raw_expr(1))
    sid = rts.create_setfunction()
    rts.checker.tags[31] = frozenset([sid])
    rts.update_escape_set(sid, 31)
    rts.sftable[sid].escape_set.discard(31)
    with self.assertRaisesRegex(_checker().InvariantViolation, 'escape sets grow'):
      rts.checker.yield_(configuration.Configuration(rts.expr(1)))


class TestNeededness(CheckerTestCase):
  '''RI B2 against the definitional tree.'''
  SOURCE = '''
k :: Bool -> Bool -> Int
k x y = if x then (if y then 1 else 2) else 3
'''

  def replace_step(self, module, name, make_step):
    info = getattr(module, name).info
    original = info.step
    info.step = make_step(original)
    self.addCleanup(setattr, info, 'step', original)

  def test_tree(self):
    '''The tree of k: one case on the first argument.'''
    M = curry.compile(self.SOURCE, modulename='CheckerTree')
    rts = _state(curry.raw_expr(1))
    tree = rts.checker._tree(M.k.info)
    self.assertEqual(tree.path, [0])
    self.assertEqual(sorted(tree.branches), [0, 1])
    self.assertIsNone(rts.checker._tree(curry.getInterpreter().prelude.apply.info))

  def test_hnf_at_an_inductive_position(self):
    '''A step that demands the second argument first.'''
    M = curry.compile(self.SOURCE, modulename='CheckerHnf')
    def make_step(original):
      def step(rts, _0):
        rts.variable(_0, 1).hnf()
        return original(rts, _0)
      return step
    self.replace_step(M, 'k', make_step)
    with self.assertRaisesRegex(_checker().InvariantViolation, r'B2.*position \[1\]'):
      list(curry.eval(curry.raw_expr([M.k, True, False])))

  def test_failure_from_an_exempt_leaf(self):
    '''A step that fails on a matched rule.'''
    M = curry.compile(self.SOURCE, modulename='CheckerFail')
    def make_step(original):
      def step(rts, _0):
        rts.variable(_0, 0).hnf()
        _0.rewrite(rts.Failure)
      return step
    self.replace_step(M, 'k', make_step)
    with self.assertRaisesRegex(_checker().InvariantViolation, r'B2 \(failure\)'):
      list(curry.eval(curry.raw_expr([M.k, True, False])))

  def test_unchanged_step_passes(self):
    M = curry.compile(self.SOURCE, modulename='CheckerPass')
    self.assertEqual(
        [curry.topython(v) for v in curry.eval(curry.raw_expr([M.k, True, False]))]
      , [2]
      )


class TestDroppedBox(cytest.TestCase):
  '''
  The defect the checker found (2026-10-09, issue #123): in the walk of N
  of the Python backend a forward node in front of a set guard was spliced
  out together with the guard (logical_subexpr skips both), but the real
  path and the set ids of the walk were not extended.  The pull-tab of the
  choice behind the guard copied the spine without the box and inserted
  nothing into the escape set, so a captured choice reached through a
  forward node alone was encapsulated: oneCaptured gave (3, A) and (3, B),
  where the C++ backend and the semantics of weakly encapsulated search
  give (2, A) and (2, B).  The checker reported it at the pull-tab (B1: the
  source is not at the path of the target).  The walk splices the chain of
  forward nodes alone now and crosses the guard as one met directly.
  '''
  def test_values(self):
    M = curry.compile(DROPPED_BOX, modulename='CheckerDroppedBox')
    self.assertEqual(_values(M, 'oneCaptured'), ['(2, A)', '(2, B)'])

  @unittest.skipIf(not PY, 'the checker drives the Python backend')
  def test_under_the_checker(self):
    curry.reload({'backend': 'py', 'checker': True})
    try:
      M = curry.compile(DROPPED_BOX, modulename='CheckerDroppedBoxChecked')
      self.assertEqual(_values(M, 'oneCaptured'), ['(2, A)', '(2, B)'])
    finally:
      curry.reload({'backend': 'py', 'checker': False})

  @unittest.skipIf(not PY, 'the checker drives the Python backend')
  def test_report(self):
    '''The report of the defect, from a pull-tab whose recorded path ends
    one step short of its source: it names the invariant, the event and
    the position.'''
    from curry.backends.py import graph
    curry.reload({'backend': 'py', 'checker': True})
    try:
      rts = _state(curry.raw_expr(1))
      a, b = rts.expr(1), rts.expr(2)
      target = graph.Node(rts.Choice, 7, a, b)
      Just = rts.prelude.Just
      root = graph.Node(Just, graph.Node(Just, target))
      lhs = graph.Node(Just, graph.Node(Just, a))
      rhs = graph.Node(Just, graph.Node(Just, b))
      with self.assertRaisesRegex(
          _checker().InvariantViolation
        , r'B1 \(pull-tab\) violated at pull-tab: the source is not at the '
          r'path \[0\] of the target'
        ):
        rts.checker.pulltab(root, target, [0], lhs, rhs)
    finally:
      curry.reload({'backend': 'py', 'checker': False})


@unittest.skipIf(not PY, 'the walk of N of the Python backend')
class TestForwardChain(cytest.TestCase):
  '''
  The walk of N over a chain of forward nodes, on hand-built graphs.  The
  generated code reads an argument through a logical path, which compresses
  a chain before the step, so no goal of the suite puts a chain of two or
  more forward nodes, or a guard directly before a chain, in front of the
  walk.  The walk splices the chain out of its parent and meets the guard
  behind it on the next pass: the recorded set ids and the alternatives of
  the pull-tab hold every box on the way.  The old walk dropped the boxes
  behind the chain and, with a guard met directly before the chain,
  returned a value with the choice still inside.
  '''
  def walk(self, make):
    '''
    Runs N over ``Just (make(sids, choice))`` with two set ids.  Returns
    the sids recorded at the pull-tab and the root after it.
    '''
    from curry.backends.py import graph
    from curry.backends.py.eval.fairscheme import N
    rts = _state(curry.raw_expr(1))
    sids = [rts.create_setfunction(), rts.create_setfunction()]
    choice = graph.Node(rts.Choice, 7, rts.expr(1), rts.expr(2))
    rts.E = graph.Node(rts.prelude.Just, make(rts, sids, choice))
    if rts.checker is not None:
      rts.checker.tags[7] = frozenset(sids)
    recorded = []
    original = rts.update_escape_sets
    def record(sids, cid):
      recorded.append(([sid for sid in sids if sid is not None], cid))
      original(sids=sids, cid=cid)
    rts.update_escape_sets = record
    self.assertFalse(N(rts, rts.variable(rts.E)))
    return sids, recorded, str(rts.E)

  def test_chain_then_guard(self):
    '''Fwd -> Fwd -> SetGuard -> Choice.'''
    from curry.backends.py import graph
    def make(rts, sids, choice):
      box = graph.Node(rts.SetGuard, sids[0], choice)
      return graph.Node(rts.Fwd, graph.Node(rts.Fwd, box))
    (s, _), recorded, root = self.walk(make)
    self.assertEqual(recorded, [([s], 7)])
    self.assertEqual(
        root, '_Choice 7 (Just (_SetGuard %s 1)) (Just (_SetGuard %s 2))' % (s, s)
      )

  def test_guard_then_chain(self):
    '''SetGuard -> Fwd -> Fwd -> SetGuard -> Choice.'''
    from curry.backends.py import graph
    def make(rts, sids, choice):
      inner = graph.Node(rts.SetGuard, sids[1], choice)
      chain = graph.Node(rts.Fwd, graph.Node(rts.Fwd, inner))
      return graph.Node(rts.SetGuard, sids[0], chain)
    (s, t), recorded, root = self.walk(make)
    self.assertEqual(recorded, [([s, t], 7)])
    self.assertEqual(
        root
      , '_Choice 7 (Just (_SetGuard %s (_SetGuard %s 1))) '
        '(Just (_SetGuard %s (_SetGuard %s 2)))' % (s, t, s, t)
      )

  def test_alternating(self):
    '''Fwd -> SetGuard -> Fwd -> SetGuard -> Choice.'''
    from curry.backends.py import graph
    def make(rts, sids, choice):
      inner = graph.Node(rts.Fwd, graph.Node(rts.SetGuard, sids[1], choice))
      return graph.Node(rts.Fwd, graph.Node(rts.SetGuard, sids[0], inner))
    (s, t), recorded, root = self.walk(make)
    self.assertEqual(recorded, [([s, t], 7)])
    self.assertEqual(
        root
      , '_Choice 7 (Just (_SetGuard %s (_SetGuard %s 1))) '
        '(Just (_SetGuard %s (_SetGuard %s 2)))' % (s, t, s, t)
      )


class TestSharedArgument(cytest.TestCase):
  '''
  The false alarm of both checkers found in the review of the C++ mirror
  (2026-10-09) and fixed the same day: the step propagation of the flags
  started at the redex, which carries the flags, and stopped there, so a
  `?` cell that a step made at a flagged redex inherited no flag, and the
  choice it created was not argument-derived for the box above the
  argument.  The capsule of lazyThenOutside2 yields 0 without demanding
  the argument; the enclosing configuration steps g2 at the flagged cell
  and then `?`; the second alternative of the capsule pulls the choice
  across the box, and the checker reported S0 (E in A).  The propagation
  starts at the successors of the result cell now, on both backends.  The
  values, (0, A, [0, 1]) and (0, B, [0, 2]), are those of weakly
  encapsulated search, with the flag off and under the checker.
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
    M = curry.compile(SHARED_ARGUMENT, modulename='CheckerSharedArgument')
    self.check_values(M)

  def test_big_step_values(self):
    M = curry.compile(BIG_STEP, modulename='CheckerBigStep')
    self.assertEqual(_values(M, 'bigThenOutside'), self.BIG_VALUES)

  @unittest.skipIf(not PY, 'the checker drives the Python backend')
  def test_under_the_checker(self):
    '''No report and the same values on the three shapes.'''
    curry.reload({'backend': 'py', 'checker': True})
    try:
      M = curry.compile(SHARED_ARGUMENT, modulename='CheckerSharedArgumentChecked')
      self.check_values(M)
    finally:
      curry.reload({'backend': 'py', 'checker': False})

  @unittest.skipIf(not PY, 'the checker drives the Python backend')
  def test_big_step_under_the_checker(self):
    '''A step over the budget of the walk: the walk is counted, the sets
    of the flags become unbounded, and the pull-tab across the box is not
    reported.  The values are those of the flag-off run.'''
    curry.reload({'backend': 'py', 'checker': True})
    try:
      M = curry.compile(BIG_STEP, modulename='CheckerBigStepChecked')
      rts = _state(curry.raw_expr(M.bigThenOutside))
      values = sorted(str(v) for v in rts.generate_values())
      counts = rts.checker.counts
    finally:
      curry.reload({'backend': 'py', 'checker': False})
    self.assertEqual(values, self.BIG_VALUES)
    self.assertGreaterEqual(counts['propagate_over_budget'], 1)
    self.assertNotIn('violations', counts)


if __name__ == '__main__':
  unittest.main()
