'''
Runs every example under examples/ and compares its output with the file
expected.out in the example directory.

Each example has a run script.  The test runs it in a child process on the
backend of the test session, under an address-space cap and a time limit, and
compares the standard output of the child, decoded as UTF-8, with the text of
expected.out.  Only the standard output is compared; the standard error is
shown when a test fails.

The file takes about 15 s warm and 30 s cold on the C++ backend, and about
90 s on the Python backend.  The first run compiles the Curry module of each
example, and two examples compile Curry text on every run.

To regenerate the expected output after a deliberate change, run

    SPRITE_UPDATE_EXPECTED=1 ./run_tests unit_examples.py

once per backend that the example declares, and review the diff.  The file
must come out the same on every backend of the example.
'''
import cytest # from ./lib; must be first
import ast, curry, importlib.util, os, subprocess, sys, time, unittest

EXAMPLES_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'examples')
  )
ADDRESS_SPACE = 2 * 1024 ** 3  # bytes; the Curry front end peaks near 1 GB
TIMEOUT = 120                  # seconds for the compile and the run of one example
KILL_AFTER = 10                # seconds from SIGTERM to SIGKILL in the timeout command
KILLED_STATUS = 128 + 9        # the status of timeout when its SIGKILL fires

# Directory -> the backends it runs on.  expected.out is the same on each of
# them.  An example whose set excludes the backend of the session is skipped.
EXAMPLES = {
    '00-run-curry-programs'         : {'py', 'cxx'}
  , '01-run-with-python'            : {'py', 'cxx'}
  , '02-dynamic-code-generation'    : {'py', 'cxx'}
  , '03-inspect'                    : {'py'}
  , '04-static-compile'             : {'py'}
  , '10-queens-set-functions'       : {'py', 'cxx'}
  , '11-sudoku'                     : {'cxx'}
  , '12-cryptarithm'                : {'cxx'}
  , '13-regex-nondeterminism'       : {'py', 'cxx'}
  , '14-parser-functional-patterns' : {'py', 'cxx'}
  , '15-dependency-solver'          : {'py', 'cxx'}
  , '16-scheduling'                 : {'py', 'cxx'}
  , '17-type-inference'             : {'py', 'cxx'}
  , '18-text-extraction'            : {'py', 'cxx'}
  , '19-blocks-world-app'           : {'py', 'cxx'}
  , '20-cxx-types-deduction'        : {'py', 'cxx'}
  , '21-cxx-types-overloads'        : {'py', 'cxx'}
  , '22-cxx-types-trait-check'      : {'cxx'}
  , '23-cxx-types-layout'           : {'py', 'cxx'}
  , '24-build-system'               : {'py', 'cxx'}
  }

# Directories with a run script that the test does not run, and why.  Every
# directory with a run script is in EXAMPLES or here; a test checks that.
EXCLUDED = {
    '05-blocks-in-flask':
        'needs the Flask package and a slow solver; 19-blocks-world-app '
        'replaces it'
  }

# Directory -> Python modules outside the standard library that the example
# imports.  The test skips the example when one of them is missing.  No
# example needs one at present.
REQUIRES = {}

# Directory -> the reason the example does not run in the stress mode of the
# collector (SPRITE_GC_STRESS=1; see cytest.GC_STRESS).  In that mode every
# rewrite step marks the live state, and a search that keeps thousands of
# alternatives alive does not end in TIMEOUT.  The three cxx-types examples
# below take one to three seconds in the default mode and more than 580 s in
# the stress mode, each in one search; their output up to that search is
# right.
STRESS_EXCLUDED = {
    '11-sudoku': 'a search over a large live state'
  , '12-cryptarithm': 'a search over a large live state'
  , '20-cxx-types-deduction':
        'two inverse searches in (d) over every type of a depth, unfinished '
        'after 580 s'
  , '21-cxx-types-overloads':
        'an inverse search in (d) over every argument type of depth 2, '
        'unfinished after 580 s'
  , '22-cxx-types-trait-check': 'seven searches over 1245 types, each a set function'
  , '23-cxx-types-layout':
        'a search in (b) over every order of six members, unfinished after '
        '580 s'
  }

# Directory -> the reason its output is wrong.  The run of such an example
# must still succeed; only the comparison with expected.out is an expected
# failure until the defect is fixed.  SPRITE_UPDATE_EXPECTED does not rewrite
# its expected.out.
KNOWN_FAILURES = {}

class TestExamples(cytest.TestCase):
  '''Runs the run script of every example in a child and checks its stdout.'''

  times = {}  # name -> seconds of its run
  procs = {}  # name -> the completed process of a successful run

  @classmethod
  def tearDownClass(cls):
    if cls.times:
      backend = curry.flags['backend']
      lines = ['%-32s %6.1f s' % item for item in sorted(cls.times.items())]
      lines.append('%-32s %6.1f s' % ('total', sum(cls.times.values())))
      sys.stderr.write(
          '\nexample run times on the %s backend:\n  %s\n'
              % (backend, '\n  '.join(lines))
        )

  def test_every_example_is_listed(self):
    '''Every directory with a run script is in EXAMPLES or EXCLUDED.'''
    on_disk = set(
        name for name in os.listdir(EXAMPLES_DIR)
            if os.path.isfile(os.path.join(EXAMPLES_DIR, name, 'run'))
      )
    self.assertEqual(set(EXAMPLES) | set(EXCLUDED), on_disk)
    self.assertFalse(set(EXAMPLES) & set(EXCLUDED))
    self.assertTrue(set(KNOWN_FAILURES) <= set(EXAMPLES))
    self.assertTrue(set(STRESS_EXCLUDED) <= set(EXAMPLES))

  def run_example(self, name):
    '''
    Runs the run script of an example in a child and returns the completed
    process.  The test fails when the child does not finish in TIMEOUT
    seconds or exits with a non-zero status.  It is skipped when the example
    does not run on the backend of the session or needs a Python module that
    is missing.  A second call for the same example returns the first run.
    '''
    backend = curry.flags['backend']
    if backend not in EXAMPLES[name]:
      self.skipTest('%s does not run on the %s backend' % (name, backend))
    for module in REQUIRES.get(name, ()):
      if importlib.util.find_spec(module) is None:
        self.skipTest('%s needs the Python module %s' % (name, module))
    if cytest.GC_STRESS and name in STRESS_EXCLUDED:
      self.skipTest(
          'collector stress mode: %s is %s' % (name, STRESS_EXCLUDED[name])
        )
    if name in self.procs:
      return self.procs[name]
    exdir = os.path.join(EXAMPLES_DIR, name)
    env = dict(
        os.environ, SPRITE_INTERPRETER_FLAGS='backend:' + backend
      , LC_ALL='C.UTF-8', PYTHONIOENCODING='utf-8'
      )
    # An example finds its own modules, and it runs as a user would run it,
    # without the library path of the test suite.
    env.pop('CURRYPATH', None)
    env.pop('PYTHONPATH', None)
    cmd = [
        'prlimit', '--as=%d' % ADDRESS_SPACE
      , 'timeout', '-k', str(KILL_AFTER), str(TIMEOUT)
      , 'bash', './run'
      ]
    start = time.time()
    proc = subprocess.run(
        cmd, cwd=exdir, env=env, capture_output=True
      , encoding='utf-8', errors='replace'
      )
    elapsed = time.time() - start
    self.times[name] = elapsed
    # timeout exits with 124 when SIGTERM ends the child.  When the child
    # ignores SIGTERM, the SIGKILL that follows also ends timeout itself, so
    # the status is then 137.
    timed_out = proc.returncode == cytest.TIMEOUT_STATUS or (
        proc.returncode == KILLED_STATUS and elapsed >= TIMEOUT
      )
    self.assertFalse(timed_out, '%s did not finish in %d s' % (name, TIMEOUT))
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.procs[name] = proc
    return proc

  def expected_output(self, name):
    '''Reads expected.out of an example.'''
    with open(os.path.join(EXAMPLES_DIR, name, 'expected.out'), encoding='utf-8') as stream:
      return stream.read()

  def check_output(self, name, proc):
    '''
    Compares the standard output of a run with expected.out, or rewrites
    the file when SPRITE_UPDATE_EXPECTED is set.
    '''
    update = bool(os.environ.get('SPRITE_UPDATE_EXPECTED')) \
        and name not in KNOWN_FAILURES
    if update:
      filename = os.path.join(EXAMPLES_DIR, name, 'expected.out')
      with open(filename, 'w', encoding='utf-8') as stream:
        stream.write(proc.stdout)
    else:
      self.assertEqual(proc.stdout, self.expected_output(name))

  def check_started(self, name, proc):
    '''Checks that a run printed the first line of expected.out.'''
    first = self.expected_output(name).splitlines()[:1]
    self.assertEqual(proc.stdout.splitlines()[:1], first)

def _make_tests(name):
  '''Returns the test functions of one example.'''
  def test(self):
    self.check_output(name, self.run_example(name))
  test.__name__ = 'test_' + name.replace('-', '_')
  test.__doc__ = 'Runs examples/%s and checks its output.' % name
  if name not in KNOWN_FAILURES:
    return [test]
  # A known failure gets two tests.  The first checks that the run succeeds
  # and prints its first line; a crash or a timeout fails it.  The second
  # compares the whole output and is the expected failure.
  def runs(self):
    self.check_started(name, self.run_example(name))
  runs.__name__ = test.__name__ + '_runs'
  runs.__doc__ = 'Runs examples/%s; its output is a known failure.' % name
  test.__doc__ += '  Expected failure: %s.' % KNOWN_FAILURES[name]
  return [runs, unittest.expectedFailure(test)]

for _name in sorted(EXAMPLES):
  for _test in _make_tests(_name):
    setattr(TestExamples, _test.__name__, _test)


def function_of(relpath, name):
  '''
  The function ``name`` of a Python file under examples/, compiled from its
  definition alone.  A driver imports curry and its Curry module when it is
  imported; a function of it that uses neither is tested without that.
  '''
  path = os.path.join(EXAMPLES_DIR, relpath)
  with open(path, encoding='utf-8') as stream:
    tree = ast.parse(stream.read(), path)
  for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == name:
      namespace = {}
      exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), namespace)
      return namespace[name]
  raise AssertionError('%s defines no function %s' % (relpath, name))


class TestBuildSystemDriver(cytest.TestCase):
  '''The lint lines of the driver of 24-build-system (make.py).'''

  def test_show_recipes(self):
    '''
    One line per target whose recipe has several values: the recipes after
    the count when the line fits in the width, else the count alone.  The
    recipes of the example are compiler command lines, so expected.out
    takes the second branch alone; the first is checked here.
    '''
    show_recipes = function_of('24-build-system/make.py', 'show_recipes')
    short = 't has 2 recipes: a | b'
    self.assertEqual(show_recipes('t', ['a', 'b']), short)
    self.assertEqual(
        show_recipes('t', ['a', 'b', 'c']), 't has 3 recipes: a | b | c'
      )
    # A line of exactly the width fits; one column more does not.
    self.assertEqual(show_recipes('t', ['a', 'b'], width=len(short)), short)
    self.assertEqual(
        show_recipes('t', ['a', 'b'], width=len(short) - 1), 't has 2 recipes'
      )
    # The two recipes of main.o in step 7 of the example: 94 columns.
    recipes = [
        'cc -O2 -Wall -c main.c -o main.o', 'cc -g -O0 -Wall -c main.c -o main.o'
      ]
    self.assertEqual(show_recipes('main.o', recipes), 'main.o has 2 recipes')
    self.assertEqual(show_recipes('main.o', recipes, width=94)[:22], 'main.o has 2 recipes: ')
