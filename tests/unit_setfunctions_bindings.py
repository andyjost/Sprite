'''
Tests for issue #97: a set function over a variable that a functional pattern
of the enclosing function bound.  The programs are in
data/curry/SetFunctionsBindings.curry.

A binding is private to the configuration that made it.  The capsule of a set
function is a nested configuration with an empty binding map, and before the
fix it read its own map alone, where the decisions of the enclosing
configurations are read through the queue stack (read_fp).  So a variable of
the argument that the enclosing configuration bound looked unbound inside the
capsule, with two consequences.  A character or a number compared against a
literal was bound anew, to the literal, and the comparison held whatever the
outer value was: outerChar "cx.o" gave [1] where the stem does not end in
'c' (PAKCS: no value).  A list was narrowed, which put a generator on the
shared variable node; the choice escaped to the enclosing configuration,
which forked on the generator of a variable it had bound, and fork applied
the binding as the constraint (generator =:<= binding) &> e.  The constraint
pull-tabbed the same generator to the root, the fork applied the binding
again, and so on without end: std::bad_alloc after six seconds at the 2 GB
cap on the C++ backend, 6.9 million forks; the Python backend named a
symbol the Prelude handle does not expose (nonstrictEq) and raised.  The
same loop runs without a set function when one alternative binds a variable
with =:<= and reads it after another alternative narrowed it (sibling).

The fix, on both backends: get_binding and has_binding read through the
queue stack as read_fp does (RuntimeState::get_binding in rts_freevars.cpp,
rts_bindings.py), and apply_binding consumes the binding it applies, so a
configuration that forks on the generator again applies nothing
(rts_bindings.cpp, rts_bindings.py).  The expected values are those of
PAKCS 3.4.1 on the plain goals (the pinned installation has no
Control.SetFunctions).

The children run under prlimit and timeout, because a regression spins
inside C++ and exhausts the memory (see cytest.run_in_subprocess).

The shared capsule (sections 5 and 6 of the module; decision D3 of the memo
on the Fair Scheme proofs, route (c); issue #86).  A capsule that two
configurations share, started while a variable of its goal was free, is
read again after each configuration bound the variable: the first to run
it put its binding into the nested spine, and the other read a value made
with that binding (the known failure test_shared_capsule before the rule).
Now the nested evaluation's read of a binding of an enclosing configuration
is the divergence: get_binding reports the level the binding was found at,
the reader returns E_DIVERGE (RuntimeState::diverge; E_DIVERGE in
rts_bindings.py), and the allValues step of the configuration that holds
the binding clones the capsule for it, absorbs the binding into the clone
(Queue::absorbed; Queue.absorbed) and restarts through a private copy of
its spine.  The read then finds the binding in the clone.  A binding found
at the outermost configuration while it is alone in its queue is absorbed
in place, without a clone.  The tests of the shapes run the children under
both settings of the flag setfunction_failures.
'''
import cytest # from ./lib; must be first
import curry, unittest

ADDRESS_SPACE = 1 << 30
TIMEOUT = 120
SETTINGS = ('encapsulate', 'escape')

# Evaluates goals of the test module and prints one line per goal: its name
# and the sorted values as Curry text, or the name of the error.
CHILD = '''
import curry
curry.reload(%(flags)r)
M = curry.import_('SetFunctionsBindings')
clones = []
if %(clones)r:
  # The Python backend alone: the clones of a capsule go through
  # RuntimeState.clone_queue (eval/rts_setfunctions.py).
  from curry.backends.py.eval import rts as rtsmod
  orig_clone = rtsmod.RuntimeState.clone_queue
  def clone_queue(self, *args):
    clones.append(args)
    return orig_clone(self, *args)
  rtsmod.RuntimeState.clone_queue = clone_queue
for name in %(goals)r:
  del clones[:]
  try:
    values = curry.eval(getattr(M, name))
    print(name, sorted(str(value) for value in values))
  except curry.EvaluationError as exc:
    print(name, 'error', type(exc).__name__, str(exc))
  if %(clones)r:
    print(name + '.clones', len(clones))
'''

def run_child(testcase, *goals, **flags):
  '''
  Evaluates ``goals`` in a child on the backend of this test process and
  returns a dict from the name to the sorted list of values (as text) or to
  the error line.  On the Python backend, with ``clones=True``, the dict
  also maps ``NAME.clones`` to the number of capsule clones the goal made.
  '''
  flags.setdefault('backend', curry.flags['backend'])
  clones = flags.pop('clones', False) and flags['backend'] == 'py'
  code = CHILD % {'flags': flags, 'goals': goals, 'clones': clones}
  proc = cytest.run_in_subprocess(code, TIMEOUT, address_space=ADDRESS_SPACE)
  testcase.assertEqual(
      proc.returncode, 0
    , 'the child ended with status %s; stdout:\n%s\nstderr:\n%s'
          % (proc.returncode, proc.stdout, proc.stderr)
    )
  results = {}
  for line in proc.stdout.splitlines():
    name, _, rest = line.partition(' ')
    literal = rest.startswith('[') or name.endswith('.clones')
    results[name] = eval(rest) if literal else rest
  return results


class TestBoundArgument(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    # Compile the module here; the children load it from the cache.
    curry.import_('SetFunctionsBindings')

  def test_issue_module(self):
    '''The four goals of the issue.  issue3 and issue4 exhausted the memory.'''
    results = run_child(self, 'issue1', 'issue2', 'issue3', 'issue4')
    self.assertEqual(results, {
        'issue1': ['[3]'], 'issue2': ['[4]'], 'issue3': ['[1]']
      , 'issue4': ['[1]']
      })

  def test_bound_character(self):
    '''
    The capsule compares a character the outer pattern bound against a
    literal.  Bound anew inside the capsule, the mismatch gave [1].
    '''
    results = run_child(
        self, 'charMatch', 'charMismatch', 'charPlainMatch'
      , 'charPlainMismatch'
      )
    self.assertEqual(results, {
        'charMatch': ['[1]'], 'charMismatch': ['[]']
      , 'charPlainMatch': ['1'], 'charPlainMismatch': []
      })

  def test_bound_int_field(self):
    '''An Int field and a list tail the outer pattern bound.'''
    results = run_child(self, 'intMatch', 'intMismatch')
    self.assertEqual(results, {'intMatch': ['[1]'], 'intMismatch': ['[]']})

  def test_bound_list(self):
    '''
    A list the outer pattern bound non-strictly, whose structure the capsule
    narrows.  Both goals ran out of memory on the C++ backend.
    '''
    results = run_child(self, 'listWhole', 'listTail')
    self.assertEqual(results, {'listWhole': ['[2]'], 'listTail': ['[1]']})

  def test_sibling_alternatives(self):
    '''
    No set function: one alternative binds x with =:<= and reads it after
    another alternative narrowed x.  The C++ backend ran out of memory on
    the read; the Python backend raised in apply_binding.
    '''
    results = run_child(self, 'sibling')
    self.assertEqual(results, {'sibling': ['0', '1', '2', '7']})

  def test_private_capsule(self):
    '''
    A character bound before the capsule starts, read inside it by a case
    and by a comparison.  Both goals suspended before the fix: the capsule
    took the bound variable for free.
    '''
    results = run_child(
        self, 'privateCase', 'privateEq', 'plainCase', 'plainEq', 'plainPat'
      )
    self.assertEqual(results, {
        'privateCase': ['(0, 1)', '(0, 2)'], 'privateEq': ['(0, 1)', '(0, 2)']
      , 'plainCase': ['(0, 1)', '(0, 2)'], 'plainEq': ['(0, 1)', '(0, 2)']
      , 'plainPat': ['(0, 1)']
      })

  def check_settings(self, expected, clones=None):
    '''
    Evaluates the goals of ``expected`` under both settings of the flag.
    ``clones`` maps a goal to the number of capsule clones it makes, checked
    on the Python backend alone (the C++ runtime has no counter of them); a
    goal of ``expected`` it leaves out makes none.
    '''
    goals = tuple(expected)
    if clones and curry.flags['backend'] == 'py':
      expected = dict(expected)
      for name in goals:
        expected[name + '.clones'] = clones.get(name, 0)
    for setting in SETTINGS:
      with self.subTest(setfunction_failures=setting):
        results = run_child(
            self, *goals, setfunction_failures=setting, clones=bool(clones)
          )
        self.assertEqual(results, expected)

  def test_shared_capsule(self):
    '''
    A capsule shared by two configurations that bind a variable of its
    argument differently after it started, by =:<= (the binding a functional
    pattern makes).  Before the rule the first to run the capsule put its
    binding into the nested spine and the other read a value made with it:
    both alternatives gave (0, 1).  Now each alternative gets a clone of the
    capsule at its first read of the binding and computes its own value,
    as the plain goals do: (0, 1) and (0, 2), and (0, 1) alone for the
    string, whose other binding fails the functional pattern inside.  The
    case and == shapes suspended before the fix of #97; the string shape
    ran out of memory.
    '''
    self.check_settings({
        'sharedCase': ['(0, 1)', '(0, 2)'], 'sharedEq': ['(0, 1)', '(0, 2)']
      , 'sharedPat': ['(0, 1)']
      })

  def test_shared_strict(self):
    '''The binding made by =:=, a value binding of a character.'''
    self.check_settings({
        'plainStrict': ['(0, 1)', '(0, 2)']
      , 'sharedStrict': ['(0, 1)', '(0, 2)']
      })

  def test_shared_narrowed(self):
    '''
    A variable of a data type narrowed after the start: the generator
    escapes the capsule and the queue splits (the repair of issue #61); no
    binding is read, and no clone is made.
    '''
    self.check_settings({
        'plainNarrow': ['(0, 1)', '(0, 2)']
      , 'sharedNarrow': ['(0, 1)', '(0, 2)']
      })

  def test_shared_functional_pattern(self):
    '''
    A functional pattern applied to the shared variable after the start
    narrows its spine and binds its characters.  The alternative whose
    string does not end in 'a' has no value.
    '''
    self.check_settings({
        'plainFunPat': ['(0, 2)'], 'sharedFunPat': ['(0, 2)']
      })

  def test_shared_nested(self):
    '''
    Nested capsules that share the variable of the outer goal: the outer
    capsule is cloned for the alternative and the inner one for the clone's
    configuration, one level at a time.
    '''
    self.check_settings({'sharedNested': ['(0, 1)', '(0, 2)']})

  def test_shared_two_variables(self):
    '''
    Two variables bound after the start: the clone made at the read of the
    first diverges again at the read of the second.
    '''
    self.check_settings({
        'plainTwo': ['(0, 11)', '(0, 12)', '(0, 21)', '(0, 22)']
      , 'sharedTwo': ['(0, 11)', '(0, 12)', '(0, 21)', '(0, 22)']
      })

  def test_sole_reader(self):
    '''
    One alternative alone binds the variable after the start: the capsule
    absorbs the binding in place, without a clone.
    '''
    self.check_settings({'soleReader': ['(0, 1)']}, clones={'soleReader': 0})

  def test_clone_per_reader(self):
    '''
    Each alternative that reads the binding clones the capsule once, and
    the last one alive absorbs in place: one clone for each shared shape
    of section 5, none for a capsule that starts after the binding.
    '''
    self.check_settings({
        'privateCase': ['(0, 1)', '(0, 2)']
      , 'sharedCase': ['(0, 1)', '(0, 2)'], 'sharedEq': ['(0, 1)', '(0, 2)']
      , 'sharedPat': ['(0, 1)']
      }, clones={
        'privateCase': 0, 'sharedCase': 1, 'sharedEq': 1, 'sharedPat': 1
      })

  def test_binding_before_fork(self):
    '''
    The binding predates the capsule and the alternative forks later on
    something else: every alternative holds the binding, so the capsule
    absorbs it at its creation and no alternative clones it.  Before the
    absorption at the top level the first alternative to read cloned.
    '''
    self.check_settings({
        'boundThenFork': ['1', '11'], 'plainBoundThenFork': ['1', '11']
      }, clones={'boundThenFork': 0})

  def test_two_references(self):
    '''
    One alternative reads the shared capsule through two references: each
    reference clones the capsule at its first read, since the clone is
    private to the spine of one reference.  The values are right; the
    second clone is the owner's item in the TODO entry of 2026-10-09.
    '''
    self.check_settings({
        'twoRefs': ['(0, 11)', '(0, 22)']
      , 'plainTwoRefs': ['(0, 11)', '(0, 22)']
      }, clones={'twoRefs': 2})
