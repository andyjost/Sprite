'''
Tests for the scheduler of the C++ backend (src/cyrt/fairscheme.cpp): a set
guard at the root of a configuration, and a step of a nested set function
interrupted while it holds a residual.

A set function whose value is a sub-term of its guarded argument (set1 id x,
set1 anyOf xs) puts the guard of the argument at the root of the nested
configuration.  The scheduler asserted there, and the release build looped.
A step interrupted by the periodic rotation or the stack limit left the
residual of its group in the configuration, and the nested scheduler then
reported a false suspension.  The programs are in data/curry/CxxScheduler.curry.

The children run under prlimit and timeout, because a regression spins
inside C++ (see cytest.run_in_subprocess).
'''
import cytest # from ./lib; must be first
import curry, unittest

ADDRESS_SPACE = 2 << 30
TIMEOUT = 120

# Evaluates goals of the test module and prints one line per goal: its name
# and the values as Curry text, or the name of the error.
CHILD = '''
import curry
curry.reload(%(flags)r)
M = curry.import_('CxxScheduler')
for name, args in %(goals)r:
  try:
    values = [str(value) for value in curry.eval(getattr(M, name), *args)]
    print(name, values)
  except curry.EvaluationError as exc:
    print(name, 'error', type(exc).__name__, str(exc))
'''

def run_child(testcase, goals, **flags):
  '''
  Evaluates ``goals``, pairs of a function name and its arguments, in a child
  on the backend of this test process, and returns a dict from the name to
  the list of values (as text) or to the error line.
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


class TestSetGuardRoot(cytest.TestCase):
  '''
  The guard of the argument of a set function reaches the root of the
  nested configuration when the value is a sub-term of the argument.  Both
  backends give the values of the argument.
  '''
  @classmethod
  def setUpClass(cls):
    # Compile the module here; the children load it from the cache.
    curry.import_('CxxScheduler')

  def test_value_is_the_argument(self):
    results = run_child(self, [
        ('idSet', (1,)), ('emptyId', ()), ('anyOfSet', ([3, 1, 2],))
      , ('tailsSet', ([1, 2],)), ('headOrLastSet', ([1, 2, 3],))
      ])
    self.assertEqual(results, {
        'idSet': ['[1]'], 'emptyId': ['False'], 'anyOfSet': ['[1, 2, 3]']
      , 'tailsSet': ['[[[1, 2], [2], []]]'], 'headOrLastSet': ['[1, 3]']
      })

  def test_choice_of_the_argument_escapes(self):
    results = run_child(self, [('argChoice', ())])
    self.assertEqual(results, {'argChoice': ['[1]', '[2]']})

  def test_free_variable_argument(self):
    results = run_child(self, [('freeId', ())])
    self.assertEqual(results, {'freeId': ['[_a]']})

  def test_captured_argument_under_case(self):
    '''
    The inner function captures the argument of the outer set function and
    scrutinizes it, so the guard of the outer set is below the root of the
    inner configuration.  The choice is in the escape set of the outer set
    alone and escapes both set functions (choice_escapes); both backends
    run this shape.  TestNestedSetGuard has the shape with the guard at the
    root.
    '''
    results = run_child(self, [('nestedCaptureCase', ())])
    self.assertEqual(results, {'nestedCaptureCase': ['[[1]]', '[[2]]']})


@unittest.skipIf(
    curry.flags['backend'] != 'cxx'
  , 'the Python backend asserts on a guard of an enclosing set at the root'
  )
class TestNestedSetGuard(cytest.TestCase):
  '''
  The inner of two nested set functions returns its argument, which carries
  the guards of both.  The inner scheduler descends into them; a choice
  below them joins the escape sets of both sets and escapes both set
  functions.
  '''
  @classmethod
  def setUpClass(cls):
    curry.import_('CxxScheduler')

  def test_nested_set_functions(self):
    results = run_child(self, [('nestedPlain', ()), ('nested', ())])
    self.assertEqual(
        results, {'nestedPlain': ['[[1]]'], 'nested': ['[[1]]', '[[2]]']}
      )

  def test_captured_argument(self):
    '''
    The inner function captures the argument of the outer set function, so
    the argument carries the guard of the outer set only.  The choice
    belongs to the argument of the outer set function and escapes both: a
    choice of the escape set of an enclosing set escapes the inner capsule
    too (choice_escapes).  Before that rule the inner set function
    encapsulated it and gave one value, [[1, 2]].
    '''
    results = run_child(self, [('nestedCapture', ())])
    self.assertEqual(results, {'nestedCapture': ['[[1]]', '[[2]]']})


@unittest.skipIf(
    curry.flags['backend'] != 'py', 'the known failure of the Python backend'
  )
class TestNestedSetGuardPython(cytest.TestCase):
  '''
  On the Python backend a guard of an enclosing set function at the root of
  a nested configuration unwinds to allValues, which expects a choice.
  '''
  @classmethod
  def setUpClass(cls):
    curry.import_('CxxScheduler')

  @unittest.expectedFailure
  def test_nested_set_functions(self):
    results = run_child(self, [('nestedPlain', ()), ('nested', ())])
    self.assertEqual(
        results, {'nestedPlain': ['[[1]]'], 'nested': ['[[1]]', '[[2]]']}
      )


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestInterruptedStep(cytest.TestCase):
  '''
  A step of a nested set function is interrupted (E_ROTATE, E_UNWIND) after
  its probe of a free variable recorded a residual for the variable and its
  group.  hnf_or_free takes both back, and the yield sets the forced flag of
  the configuration, so the nested scheduler accepts it when it resumes
  instead of reporting a false suspension (rts_control.cpp, _make_ready).
  '''
  # The depth of the strict applications around the constraint: the window
  # of the interruption, in forward nodes.  Well below the nesting the
  # default stack limit admits.
  DEPTH = 3000

  @classmethod
  def setUpClass(cls):
    curry.import_('CxxScheduler')

  def test_stack_limit_inside_the_constraint(self):
    '''
    The right side of x =:= e nests deeper than the stack limit after the
    probe of x recorded the residual of its group.  The set function unwinds
    to the enclosing queue, the alternative 7 runs, and the stuck set
    function ends with the stack error, not with a suspension.
    '''
    results = run_child(self, [('unwound', (5000,))], stack_limit=1 << 16)
    self.assertRegex(
        results['unwound']
      , r'^error EvaluationError stack limit of \d+ bytes exceeded'
      )

  @cytest.skipIfGcStress('a collection at every step hides the rotation path')
  def test_rotation_inside_the_constraint(self):
    '''
    The periodic rotation lands inside the grouped constraint for some
    length of the preamble.  The lengths scanned cover one period in steps
    shorter than the window, so one of them hits.  The set function then
    resumes with the residual of the group still recorded, and must give its
    value.  The scan pins the cadence of 65536 completed steps, so the child
    forces step mode whatever SPRITE_ROTATION says (see
    unit_cxx_rotation.py for the modes).
    '''
    goals = [
        ('rotated', (self.DEPTH, k, 5000)) for k in range(60, 3400, 60)
      ]
    code = CHILD % {
        'flags': {'backend': 'cxx', 'rotation': 'steps:65536'}, 'goals': goals
      }
    proc = cytest.run_in_subprocess(code, TIMEOUT, address_space=ADDRESS_SPACE)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    lines = proc.stdout.splitlines()
    self.assertEqual(len(lines), len(goals))
    self.assertEqual(set(lines), {"rotated ['1', '3']"}, lines)
