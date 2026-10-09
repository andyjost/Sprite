'''
Tests for defects of the set functions and the scheduler: issues #61, #32,
and #36, whose programs are in data/curry/SetFunctionsBugs.curry, the two
findings of the differential harness on the Python backend, issues #120
and #121, whose programs are data/curry/PyGeneratorAssert.curry and
data/curry/PyFingerprintNone.curry, and the finding of the checker mode on
the Python backend, issue #123, whose programs are
data/curry/CapturedFwd.curry.

Issue #61: a set function over a free variable that a choice bound saw the
binding of the first alternative in every branch.  The application sits
below the pull-tab of the constraint, so the alternatives share it.  The
first alternative to reach it rewrote the shared node into a SetEval whose
nested queue read the bindings of that alternative, and the second found the
values in the shared graph.  A choice the configuration decided before the
set function saw it, in the argument or in the function position, had the
same defect.  The step that creates the SetEval rewrites through a private
copy of the spine when the application holds a variable that the
configuration bound, narrowed, or grouped, or a choice that it decided, as
the step that puts a binding into an expression does (evalS_step in
currylib/setfunctions.cpp, evalS in backends/py/currylib/setfunctions.py).
That rule covers the state the configuration holds when the set function
starts.  The general case is the escape (rule SF.1 of the dissertation): a
choice of the escape set always leaves the capsule, whatever the enclosing
configurations decided, and the split of the queue puts a configuration
that made the choice on its side, keeps one that has not made it in both
queues, and records the choice in both, so that no configuration escapes
it twice (choice_escapes and Queue::split of the C++ runtime,
choice_escapes and split_queue of the Python backend).  So a capsule that
starts before the variable is narrowed, is consumed in part, and resumes
under alternatives that narrowed the variable differently gives each
alternative its side (test_narrowed_after_start and TestResumedCapsule).
Two more rules keep a configuration from writing the side of a choice that
the outside decided into state the alternatives share: a choice in no escape
set that an enclosing configuration decided, a captured occurrence, escapes
as well, and a configuration takes the side of an escaped choice at once
only when it owns the decision (owns_decision): it made the choice, or its
queue was split on it.  Otherwise the choice node escapes in turn, up to the
configuration that decided it.

Issue #32: a set function whose values are sub-terms of its guarded argument
put the guard at the root of the nested configuration, where the C++
scheduler asserted.  The set guard at the root (2026-10-04) fixed it; the
three forms of the issue are pinned here on both backends.

Issue #36: a recursion that picks from a shrinking pool with a let did not
end on either backend.  Its rules overlap: the second rule matches n = 0 as
well, and its recursion never ends, because nothing forces anyOf [] once
the pool is empty.  PAKCS does not end on it either.  With a guard the rules
are exclusive, and both backends give the six values and end.

Issue #120: the values of a set function hold a free variable of the goal,
and sortValues compares them.  The copier that makes a value copied the
node of the variable, so the value held a second node with the id of the
variable.  The comparison narrowed the copy: the generator went onto the
copy, and get_generator, which reads the node of the id from the table,
asserted that the node had one.  The copier shares a free variable now, as
the C++ copier does: one node stands for one id.

Issue #121: a strict constraint between a variable of the capsule and a
variable of the goal reached through the box of a captured argument.  The
step of =:= built the pair of the constraint from the rvalues of the two
sides, with the guard crossed on the way to the second, and constrain_equal
read no id from the guard.  The pair holds the two variables themselves,
as the pair of the C++ step does.  The pair of a value binding of a
variable of a builtin type (make_value_bindings) had the same defect: the
binding was dropped, and the Python backend suspended.  It holds the node
of the variable now.

Issue #123: a captured choice that the walk of N reaches through a forward
node in front of its box.  constT x 0 rewrites to a forward node to the
guarded x.  The walk of the Python backend replaced the forward node
through logical_subexpr, which skips the chain and the set guards behind
it, and left the real path and the set ids of the walk short of the guard.
The pull-tab of the choice copied the spine without the box and put
nothing into the escape set, so the captured choice was encapsulated: the
set function had one value more than on the C++ backend.  The walk splices
the chain of forward nodes alone now, as the C++ walk does, and crosses
the guard behind it as a guard met directly.

The children run under prlimit and timeout, because a regression can spin
inside C++ (see cytest.run_in_subprocess).
'''
import cytest # from ./lib; must be first
import curry, unittest

ADDRESS_SPACE = 2 << 30
TIMEOUT = 120

# Evaluates goals of the test module and prints one line per goal: its name
# and the sorted values as Curry text, or the name of the error.  A limit
# takes the first values of a goal that does not end.
CHILD = '''
import curry, itertools
curry.reload(%(flags)r)
M = curry.import_(%(module)r)
for name, limit in %(goals)r:
  try:
    values = curry.eval(getattr(M, name))
    if limit is not None:
      values = itertools.islice(values, limit)
    print(name, sorted(str(value) for value in values))
  except curry.EvaluationError as exc:
    print(name, 'error', type(exc).__name__, str(exc))
'''

def run_child(testcase, goals, module='SetFunctionsBugs', **flags):
  '''
  Evaluates ``goals`` of ``module``, pairs of a goal name and a limit on the
  number of values (None for all of them), in a child on the backend of this
  test process, and returns a dict from the name to the sorted list of
  values (as text) or to the error line.
  '''
  flags.setdefault('backend', curry.flags['backend'])
  code = CHILD % {'flags': flags, 'goals': goals, 'module': module}
  proc = cytest.run_in_subprocess(code, TIMEOUT, address_space=ADDRESS_SPACE)
  testcase.assertEqual(
      proc.returncode, 0
    , 'the child ended with status %s; stdout:\n%s\nstderr:\n%s'
          % (proc.returncode, proc.stdout, proc.stderr)
    )
  results = {}
  for line in proc.stdout.splitlines():
    name, _, rest = line.partition(' ')
    results[name] = eval(rest) if rest.startswith('[') else rest
  return results

def goals(*names):
  return [(name, None) for name in names]


class TestBoundVariable(cytest.TestCase):
  '''
  Issue #61.  A choice binds a free variable, and a set function below the
  pull-tab of the constraint takes the variable as its argument.  Each
  alternative must see its own binding.
  '''
  @classmethod
  def setUpClass(cls):
    # Compile the module here; the children load it from the cache.
    curry.import_('SetFunctionsBugs')

  def test_issue_example(self):
    results = run_child(self, goals('boundVar'))
    self.assertEqual(results, {'boundVar': ['[[A]]', '[[B]]']})

  def test_two_set_functions(self):
    results = run_child(self, goals('twoSets'))
    self.assertEqual(
        results, {'twoSets': ['[([A], [[A, A]])]', '[([B], [[B, B]])]']}
      )

  @unittest.skipIf(
      curry.flags['backend'] != 'cxx'
    , 'the Python backend asserts on a guard of an enclosing set at the root'
    )
  def test_nested_set_function(self):
    results = run_child(self, goals('nestedBound'))
    self.assertEqual(results, {'nestedBound': ['[[[A]]]', '[[[B]]]']})

  @unittest.skipIf(
      curry.flags['backend'] != 'py', 'the known failure of the Python backend'
    )
  @unittest.expectedFailure
  def test_nested_set_function_python(self):
    '''
    On the Python backend a guard of an enclosing set function at the root
    of a nested configuration unwinds to allValues, which expects a choice
    (see TestNestedSetGuardPython in unit_cxx_scheduler.py).
    '''
    results = run_child(self, goals('nestedBound'))
    self.assertEqual(results, {'nestedBound': ['[[[A]]]', '[[[B]]]']})

  def test_forced_argument(self):
    '''
    The variable forced to normal form before the set function sees it: the
    form the examples used before the fix.
    '''
    results = run_child(self, goals('forced', 'forcedStrict'))
    self.assertEqual(results, {
        'forced': ['[[A]]', '[[B]]'], 'forcedStrict': ['[[A]]', '[[B]]']
      })

  def test_narrowed_after_start(self):
    '''
    The set function starts while the variable is unbound, so the two
    alternatives of the constraint that narrows it afterwards share the
    SetEval node and its queue.  The choice of the generator of the variable
    escapes the capsule under either alternative, and each prunes the
    escaped choice to its side.  Before the repair at the escape the nested
    queue read the fingerprint of the alternative that resumed it first, and
    the shared allValues node kept that value for the other: [A, A] twice.
    '''
    results = run_child(self, goals('narrowedAfterStart'))
    self.assertEqual(
        results, {'narrowedAfterStart': ['[A, A]', '[A, B]']}
      )

  def test_decided_choice(self):
    '''
    A choice, not a variable, decides the argument.  The pull-tab of the
    first component of the pair makes the choice before the set function
    sees it, in the argument (choiceArg) and in the function position
    (choiceCaptured).  Each alternative must see its own side.
    '''
    results = run_child(self, goals('choiceArg', 'choiceCaptured'))
    self.assertEqual(results, {
        'choiceArg': ['(A, [A])', '(B, [B])']
      , 'choiceCaptured': ['(A, [A])', '(B, [B])']
      })

  def test_walk_coverage(self):
    '''
    The walk reaches the bound variable behind a call, behind the forward
    node a forced call leaves, inside a partial application in the function
    position, and inside a data structure.
    '''
    names = ['viaCall', 'viaForward', 'viaPartial', 'viaData']
    results = run_child(self, goals(*names))
    self.assertEqual(results, {name: ['[[A]]', '[[B]]'] for name in names})

  def test_long_argument(self):
    '''
    The walk that looks for private state in the application visits 64
    nodes.  A longer argument counts as private, so a variable behind the
    bound still gets its own binding, and a long argument without a
    variable still gives its value, in a deterministic program (where the
    one configuration skips the walk) and under a decided choice (where the
    walk gives up).
    '''
    results = run_child(self, goals('longArg', 'longPlain', 'longPlainChoice'))
    self.assertEqual(results, {
        'longArg': ['[[A]]', '[[B]]']
      , 'longPlain': ['[A]']
      , 'longPlainChoice': ['(A, [A])', '(B, [A])']
      })


class TestResumedCapsule(cytest.TestCase):
  '''
  The repair at the escape (rule SF.1).  Every capsule starts before the
  choice or the variable is decided, gives its first value, and resumes
  under the alternatives that decided it.  The escaped choice is a node of
  the shared graph, and each alternative prunes it to its side.  The first
  six shapes decide a guarded argument; the captured shapes decide a choice
  of the function position, in no escape set; the last keeps the outer of
  two capsules alive across the decision.
  '''
  @classmethod
  def setUpClass(cls):
    curry.import_('SetFunctionsBugs')

  def test_variable_in_data(self):
    '''The variable inside a list; the second value is the variable itself.'''
    results = run_child(self, goals('narrowedInData'))
    self.assertEqual(results, {'narrowedInData': ['[A, A]', '[A, B]']})

  def test_choice_decided_after_start(self):
    '''A choice of the argument that the outside decides after the start.'''
    results = run_child(self, goals('choiceAfterStart'))
    self.assertEqual(
        results, {'choiceAfterStart': ['(A, [A, A])', '(B, [A, B])']}
      )

  def test_two_capsules_over_one_variable(self):
    results = run_child(self, goals('twoCapsules'))
    self.assertEqual(
        results, {'twoCapsules': ['([A, A], [B, A])', '([A, B], [B, B])']}
      )

  def test_nested_set_function(self):
    '''
    The inner capsule is in the value of the outer set function, so the
    enclosing configuration runs it after the outer capsule is gone.
    '''
    results = run_child(self, goals('nestedAfterStart'))
    self.assertEqual(results, {'nestedAfterStart': ['[[A, A]]', '[[A, B]]']})

  def test_set_function_in_argument(self):
    '''The inner set function is the argument of the outer one.'''
    results = run_child(self, goals('argAfterStart'))
    self.assertEqual(results, {'argAfterStart': ['[[A, A]]', '[[A, B]]']})

  def test_escape_of_undecided_choice(self):
    '''The outside has not decided the choice: it forks on the escape.'''
    results = run_child(self, goals('escapeUndecided'))
    self.assertEqual(results, {'escapeUndecided': ['[A, A]', '[A, B]']})

  def test_captured_choice_decided_after_start(self):
    '''
    The choice comes through the function position, so it is in no escape
    set, and the outside decides it after the start.  A choice an enclosing
    configuration decided escapes too (choice_escapes); a fork would prune
    it inside the capsule that both alternatives share, and the second got
    the value of the first: (B, [A, A]) before the rule.
    '''
    results = run_child(self, goals('capturedChoiceAfterStart'))
    self.assertEqual(
        results, {'capturedChoiceAfterStart': ['(A, [A, A])', '(B, [A, B])']}
      )

  def test_captured_variable_narrowed_after_start(self):
    '''The same with a free variable: [A, A] twice before the rule.'''
    results = run_child(self, goals('capturedVarAfterStart'))
    self.assertEqual(
        results, {'capturedVarAfterStart': ['[A, A]', '[A, B]']}
      )

  def test_captured_then_guarded(self):
    '''
    The captured occurrence is reached before the guarded one.  Before the
    rule the captured element came from the first alternative and the
    guarded one from the second: (B, [[A], [A, B]]).
    '''
    results = run_child(self, goals('capturedThenGuarded'))
    self.assertEqual(
        results
      , {'capturedThenGuarded': ['(A, [[A], [A, A]])', '(B, [[A], [B, B]])']}
      )

  def test_outer_capsule_alive(self):
    '''
    The escape from the inner capsule reaches a configuration of the outer
    capsule, which both alternatives share.  That configuration owns no
    decision of the choice (owns_decision), so it escapes the choice in
    turn instead of taking the side of the alternative that runs it.
    Before the test both alternatives got [A, A].
    '''
    results = run_child(self, goals('nestedAlive', 'nestedAliveChoice'))
    self.assertEqual(results, {
        'nestedAlive': ['[A, A]', '[A, B]']
      , 'nestedAliveChoice': ['(A, [A, A])', '(B, [A, B])']
      })


class TestSubtermValues(cytest.TestCase):
  '''
  Issue #32.  The values of the set function are sub-terms of its guarded
  argument.
  '''
  @classmethod
  def setUpClass(cls):
    curry.import_('SetFunctionsBugs')

  def test_three_forms(self):
    results = run_child(self, goals('anyOfSet', 'tailsSet', 'headOrLastSet'))
    self.assertEqual(results, {
        'anyOfSet': ['[1, 2, 3]']
      , 'tailsSet': ['[[[1, 2, 3], [2, 3], [3], []]]']
      , 'headOrLastSet': ['[1, 3]']
      })


class TestShrinkingPool(cytest.TestCase):
  '''
  Issue #36.  Two picks from a pool of three, each pick a let-bound choice
  that the guard of the next pick and the result share.
  '''
  SIX = ['[1, 2]', '[1, 3]', '[2, 1]', '[2, 3]', '[3, 1]', '[3, 2]']

  @classmethod
  def setUpClass(cls):
    curry.import_('SetFunctionsBugs')

  def test_six_values_and_the_end(self):
    results = run_child(self, goals('pick2'))
    self.assertEqual(results, {'pick2': self.SIX})

  def test_overlapping_rules(self):
    '''
    The program of the issue.  Its first six values are the six; the
    evaluation does not end after them, on PAKCS as on Sprite, because the
    second rule also matches n = 0.
    '''
    results = run_child(self, [('pickOverlap', 6)])
    self.assertEqual(results, {'pickOverlap': self.SIX})


class TestHarnessFindings(cytest.TestCase):
  '''
  Issues #120 and #121: two programs the differential harness generated,
  which ended with an internal error on the Python backend.  Each is pinned
  on both backends to the values of the C++ backend.
  '''
  @classmethod
  def setUpClass(cls):
    curry.import_('PyGeneratorAssert')
    curry.import_('PyFingerprintNone')

  def test_free_variable_in_values(self):
    '''
    Issue #120.  The first component has three values (S (S Z) twice and
    Z), and the third component narrows the free variable of the argument,
    x15, which the set function returns among its values, when sortValues
    compares them: two lists.  The six values are their product.  The issue
    recorded four values of the C++ backend at 1b7ae501, before the shared
    capsule was cloned at its first divergence (#86): the capsule of the
    third component is shared by the three alternatives of the first, and
    two of them lost the side x15 = True.
    '''
    results = run_child(self, goals('goal'), module='PyGeneratorAssert')
    self.assertEqual(results, {'goal': [
        '(S (S Z), [], [False, False, False, False, True])'
      , '(S (S Z), [], [False, False, False, False, True])'
      , '(S (S Z), [], [False, False, False, True, True])'
      , '(S (S Z), [], [False, False, False, True, True])'
      , '(Z, [], [False, False, False, False, True])'
      , '(Z, [], [False, False, False, True, True])'
      ]})

  def test_constraint_through_a_guard(self):
    '''
    Issue #121.  The set function has one value, False, under each of the
    two alternatives of the choice Z ? Z in its captured argument, and the
    other alternative of f3 is [].  The two variables of the goal stay
    free.
    '''
    results = run_child(self, goals('goal'), module='PyFingerprintNone')
    self.assertEqual(
        results, {'goal': ['(_a, _b, [False])', '(_a, _b, [False])', '(_a, _b, [])']}
      )

  def test_value_binding_through_a_guard(self):
    '''
    The same cause through a value binding: a variable of the goal of a
    builtin type is narrowed inside the capsule through the box of the
    captured argument.  The pair of the value binding held the guard, and
    the binding was dropped: the Python backend suspended.  The binding is
    private to the capsule, so the variable stays free outside.
    '''
    results = run_child(self, goals('valueBinding'), module='PyFingerprintNone')
    self.assertEqual(results, {'valueBinding': ['(_a, [True])']})


class TestCapturedForward(cytest.TestCase):
  '''
  Issue #123.  The captured choice x comes through the function position
  (constT x), and the step of constT leaves a forward node to the guarded
  x.  The pull-tab of x must keep the box and put x into the escape set,
  so that x escapes the capsule and each alternative of the outside sees
  one value of f 0.  The Python backend gave (3, A) and (3, B) for
  oneCaptured, and ([[A], [A], [B]], A) for oneCapturedSet.  The five
  goals are pinned to the values of the C++ backend on both backends.
  '''
  @classmethod
  def setUpClass(cls):
    curry.import_('CapturedFwd')

  def test_captured_through_forward_node(self):
    '''The choice is reached through the forward node alone.'''
    results = run_child(
        self, goals('oneCaptured', 'oneCapturedSet'), module='CapturedFwd'
      )
    self.assertEqual(results, {
        'oneCaptured': ['(2, A)', '(2, B)']
      , 'oneCapturedSet': ['([[A], [A]], A)', '([[A], [B]], B)']
      })

  def test_captured_and_guarded(self):
    '''The choice is captured and a guarded argument as well; the shapes
    of the issue around the goal of test_captured_then_guarded.'''
    results = run_child(
        self, goals('lengthFirst', 'setFirst', 'capturedThenGuarded')
      , module='CapturedFwd'
      )
    self.assertEqual(results, {
        'lengthFirst': ['(2, A)', '(2, B)']
      , 'setFirst': ['([[A], [A, A]], A)', '([[A], [B, B]], B)']
      , 'capturedThenGuarded': ['(A, [[A], [A, A]])', '(B, [[A], [B, B]])']
      })


if __name__ == '__main__':
  unittest.main()
