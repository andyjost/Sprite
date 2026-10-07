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

The last test is a known failure: a capsule that two configurations share
and that reads a variable they bind differently after it started gives both
the value of the first (section 5 of the module; the owner's item in the
TODO entry of 2026-10-07).
'''
import cytest # from ./lib; must be first
import curry, unittest

ADDRESS_SPACE = 1 << 30
TIMEOUT = 120

# Evaluates goals of the test module and prints one line per goal: its name
# and the sorted values as Curry text, or the name of the error.
CHILD = '''
import curry
curry.reload(%(flags)r)
M = curry.import_('SetFunctionsBindings')
for name in %(goals)r:
  try:
    values = curry.eval(getattr(M, name))
    print(name, sorted(str(value) for value in values))
  except curry.EvaluationError as exc:
    print(name, 'error', type(exc).__name__, str(exc))
'''

def run_child(testcase, *goals, **flags):
  '''
  Evaluates ``goals`` in a child on the backend of this test process and
  returns a dict from the name to the sorted list of values (as text) or to
  the error line.
  '''
  flags.setdefault('backend', curry.flags['backend'])
  code = CHILD % {'flags': flags, 'goals': goals}
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

  @unittest.expectedFailure
  def test_shared_capsule(self):
    '''
    A capsule shared by two configurations that bind a variable of its
    argument differently after it started.  The first to run the capsule
    puts its binding into the nested spine; the other reads a value made
    with that binding.  Both alternatives give (0, 1) where the plain goals
    give (0, 1) and (0, 2) (and (0, 1) alone for the functional pattern).
    The case and == shapes suspended before the fix; the functional-pattern
    shape ran out of memory.  The owner's item: routes (a) and (b) of the
    TODO entry of 2026-10-07.
    '''
    results = run_child(self, 'sharedCase', 'sharedEq', 'sharedPat')
    self.assertEqual(results, {
        'sharedCase': ['(0, 1)', '(0, 2)'], 'sharedEq': ['(0, 1)', '(0, 2)']
      , 'sharedPat': ['(0, 1)']
      })
