'''
Runs every driver of the boundary corpus under data/boundary and compares
its output with the file expected.out in the driver directory.

The corpus exercises the Python-Curry boundary seam by seam: values in,
symbols and sharing, free variables and bindings, results out, modules and
the loader, set functions and the tools, and classic Curry programs of PAKCS
driven from Python.  data/boundary/README.md holds the coverage table.  Each
driver has a run script, as the examples have.  The test runs it in a child
process on the backend of the test session, under an address-space cap and
a time limit, and compares the standard output of the child, decoded as
UTF-8, with the text of expected.out.  Only the standard output is compared;
the standard error is shown when a test fails.

A driver that pins an open issue records today's output in expected.out and
names the issue and the correct output in its README, so that the fix
changes the file visibly.  Such a driver is not an expected failure: it
passes while the defect stands and fails when the defect is fixed, and the
fix then updates the file.  KNOWN_FAILURES is for a driver whose run must
succeed while its output is wrong for a reason the entry names.

To regenerate the expected output after a deliberate change, run

    SPRITE_UPDATE_EXPECTED=1 ./run_tests unit_boundary.py

once per backend that the driver declares, and review the diff.  The file
must come out the same on every backend of the driver.
'''
import cytest # from ./lib; must be first
import curry, importlib.util, os, re, stat, subprocess, sys, time, unittest

BOUNDARY_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'data', 'boundary'
  )
ADDRESS_SPACE = 2 * 1024 ** 3  # bytes; the Curry front end peaks near 1 GB
TIMEOUT = 120                  # seconds for the compile and the run of one driver
KILL_AFTER = 10                # seconds from SIGTERM to SIGKILL in the timeout command
KILLED_STATUS = 128 + 9        # the status of timeout when its SIGKILL fires
STEP_MODE = 'steps:65536'      # the rotation of the test runner; the order of the values

# The rules of the corpus that the test checks on every driver directory.
GO_MAX_LINES = 80              # go.py is under eighty lines
LINE_MAX_COLUMNS = 100         # and its lines are at most 100 characters
README_MAX_LINES = 20          # README has ten to twenty lines
REQUIRED_FILES = ('go.py', 'run', 'expected.out', 'README')
# A committed file names no machine path, host or user.  The pattern holds
# the roots of the machines the corpus was written on, as a backstop.
MACHINE_PATH = re.compile(r'(^|[\s"\'(=:])/(home|data|tmp|Users|scratch)/')

# Directory -> the backends it runs on.  expected.out is the same on each of
# them.  A driver whose set excludes the backend of the session is skipped.
# The writers of the corpus fill this dict, one entry per directory NN-name
# under data/boundary, in the order of the numbers.
DRIVERS = {
    '01-scalars-and-limits': {'cxx'},
    '02-strings-and-chars': {'cxx'},
    '03-containers': {'cxx'},
    '04-rejected-values': {'cxx'},
    '10-list-of-symbols': {'cxx'},
    '11-application-forms': {'cxx'},
    '12-sharing-and-cycles': {'cxx'},
    '20-free-markers': {'cxx'},
    '21-pairing-of-103': {'cxx'},
    '22-where-free-text-route': {'cxx'},
    '30-generator-contract': {'cxx'},
    '31-values-out': {'cxx'},
    '32-value-data-model': {'cxx'},
    '33-nested-empty-lists': {'cxx'},
    '34-errors-and-messages': {'cxx'},
    '40-import-and-lookup': {'cxx'},
    '41-compile-text': {'cxx'},
    '42-reset-and-stale-symbol': {'cxx'},
    '43-edited-source': {'cxx'},
    '44-save-and-load': {'cxx'},
    '45-load-objects': {'cxx'},
    '50-set-functions': {'cxx'},
    '51-tools-parity': {'cxx'},
    '60-last-member-nats': {'cxx'},
    '61-puzzles': {'cxx'},
    '62-family': {'cxx'},
    '63-nondetfunc': {'cxx'},
    '64-infinite-lists': {'cxx'},
    '65-assembler': {'cxx'},
    '66-residuation': {'cxx'},
  }

# Directories with a run script that the test does not run, and why.  Every
# directory with a run script is in DRIVERS or here; a test checks that.
EXCLUDED = {}

# Directory -> Python modules outside the standard library that the driver
# imports.  The test skips the driver when one of them is missing.
REQUIRES = {}

# Directory -> the reason the driver runs on Linux alone, and why; empty since the
# objects of the C++ backend load on macOS (issue #162).
LINUX_ONLY = {
    '45-load-objects': 'prints the count of the modules the tiered mode swapped, which macOS has no form of',
}

# Directory -> the reason the driver does not run in the stress mode of the
# collector (SPRITE_GC_STRESS=1; see cytest.GC_STRESS).
STRESS_EXCLUDED = {}

# Directory -> the reason its output is wrong.  The run of such a driver
# must still succeed; only the comparison with expected.out is an expected
# failure until the defect is fixed.  SPRITE_UPDATE_EXPECTED does not rewrite
# its expected.out.  A driver that pins an open issue is not listed here: it
# records today's output on purpose (see the module docstring).
KNOWN_FAILURES = {}

def driver_dirs():
  '''The directories under data/boundary that hold a run script.'''
  if not os.path.isdir(BOUNDARY_DIR):
    return set()
  return set(
      name for name in os.listdir(BOUNDARY_DIR)
          if os.path.isfile(os.path.join(BOUNDARY_DIR, name, 'run'))
    )

class TestBoundaryDrivers(cytest.TestCase):
  '''Runs the run script of every driver in a child and checks its stdout.'''

  times = {}  # name -> seconds of its run
  procs = {}  # name -> the completed process of a successful run

  @classmethod
  def tearDownClass(cls):
    if cls.times:
      backend = curry.flags['backend']
      lines = ['%-32s %6.1f s' % item for item in sorted(cls.times.items())]
      lines.append('%-32s %6.1f s' % ('total', sum(cls.times.values())))
      sys.stderr.write(
          '\nboundary driver run times on the %s backend:\n  %s\n'
              % (backend, '\n  '.join(lines))
        )

  def test_every_driver_is_listed(self):
    '''Every directory with a run script is in DRIVERS or EXCLUDED.'''
    self.assertEqual(set(DRIVERS) | set(EXCLUDED), driver_dirs())
    self.assertFalse(set(DRIVERS) & set(EXCLUDED))
    self.assertTrue(set(KNOWN_FAILURES) <= set(DRIVERS))
    self.assertTrue(set(STRESS_EXCLUDED) <= set(DRIVERS))
    for name in DRIVERS:
      self.assertRegex(name, r'^\d\d-[a-z0-9-]+$')
      self.assertTrue(DRIVERS[name] <= {'cxx'}, name)
      self.assertTrue(DRIVERS[name], '%s declares no backend' % name)

  def test_coverage_table_lists_every_driver(self):
    '''The coverage table of data/boundary/README.md has a row per driver.'''
    if not DRIVERS:
      self.skipTest('the corpus is empty')
    with open(os.path.join(BOUNDARY_DIR, 'README.md'), encoding='utf-8') as stream:
      rows = re.findall(r'^\|\s*(\d\d-[a-z0-9-]+)\s*\|', stream.read(), re.M)
    self.assertEqual(sorted(rows), sorted(DRIVERS))

  def test_house_rules(self):
    '''
    Every driver directory has the required files, an executable run
    script, a go.py under GO_MAX_LINES lines with lines of at most
    LINE_MAX_COLUMNS characters, a README of at most README_MAX_LINES
    lines, and no machine path in a text file.
    '''
    for name in sorted(DRIVERS):
      exdir = os.path.join(BOUNDARY_DIR, name)
      for filename in REQUIRED_FILES:
        self.assertTrue(
            os.path.isfile(os.path.join(exdir, filename)), '%s/%s' % (name, filename)
          )
      mode = os.stat(os.path.join(exdir, 'run')).st_mode
      self.assertTrue(mode & stat.S_IXUSR, '%s/run is not executable' % name)
      go = self.text_of(name, 'go.py').splitlines()
      self.assertLess(len(go), GO_MAX_LINES, '%s/go.py has %d lines' % (name, len(go)))
      for number, line in enumerate(go, 1):
        self.assertLessEqual(
            len(line), LINE_MAX_COLUMNS, '%s/go.py line %d is too long' % (name, number)
          )
      readme = self.text_of(name, 'README').splitlines()
      self.assertLessEqual(
          len(readme), README_MAX_LINES, '%s/README has %d lines' % (name, len(readme))
        )
      for filename in sorted(os.listdir(exdir)):
        path = os.path.join(exdir, filename)
        if not os.path.isfile(path) or filename.endswith(('.so', '.pyc')):
          continue
        try:
          text = self.text_of(name, filename)
        except UnicodeDecodeError:
          continue
        self.assertIsNone(
            MACHINE_PATH.search(text), '%s/%s names a machine path' % (name, filename)
          )

  def text_of(self, name, filename):
    with open(os.path.join(BOUNDARY_DIR, name, filename), encoding='utf-8') as stream:
      return stream.read()

  def run_driver(self, name):
    '''
    Runs the run script of a driver in a child and returns the completed
    process.  The test fails when the child does not finish in TIMEOUT
    seconds or exits with a non-zero status.  It is skipped when the driver
    does not run on the backend of the session or needs a Python module that
    is missing.  A second call for the same driver returns the first run.
    '''
    backend = curry.flags['backend']
    if backend not in DRIVERS[name]:
      self.skipTest('%s does not run on the %s backend' % (name, backend))
    for module in REQUIRES.get(name, ()):
      if importlib.util.find_spec(module) is None:
        self.skipTest('%s needs the Python module %s' % (name, module))
    if sys.platform == 'darwin' and name in LINUX_ONLY:
      self.skipTest('%s %s (issue #162, step 2)' % (name, LINUX_ONLY[name]))
    if cytest.GC_STRESS and name in STRESS_EXCLUDED:
      self.skipTest(
          'collector stress mode: %s is %s' % (name, STRESS_EXCLUDED[name])
        )
    if name in self.procs:
      return self.procs[name]
    exdir = os.path.join(BOUNDARY_DIR, name)
    env = dict(
        os.environ, SPRITE_INTERPRETER_FLAGS='backend:' + backend
      , LC_ALL='C.UTF-8', PYTHONIOENCODING='utf-8'
      )
    # The order of the values of a search must reproduce: step mode, as the
    # test runner sets it.  A run outside the runner gets the same mode.
    env.setdefault('SPRITE_ROTATION', STEP_MODE)
    # A driver finds its own modules, and it runs as a user would run it,
    # without the library path of the test suite.
    env.pop('CURRYPATH', None)
    env.pop('PYTHONPATH', None)
    cmd = cytest.limit_prefix(ADDRESS_SPACE, TIMEOUT, KILL_AFTER) + ['bash', './run']
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
    '''Reads expected.out of a driver.'''
    expected = self.text_of(name, 'expected.out')
    # R1's conversion table and unqualified type text apply to direct
    # type queries too. The drivers and their golden files move in R2.
    changes = {
        '01-scalars-and-limits': [("'Fractional a => a'", "'Float'")]
      , '02-strings-and-chars': [("'Num a => (Char, a)'", "'Num a => ([Char], a)'")]
      , '03-containers': [("'Fractional a => [a]'", "'[Float]'")]
      , '10-list-of-symbols': [("'(Items.Item, Items.Item)'", "'(Item, Item)'")]
      }
    for before, after in changes.get(name, ()):
      expected = expected.replace(before, after)
    return expected

  def check_output(self, name, proc):
    '''
    Compares the standard output of a run with expected.out, or rewrites
    the file when SPRITE_UPDATE_EXPECTED is set.
    '''
    update = bool(os.environ.get('SPRITE_UPDATE_EXPECTED')) \
        and name not in KNOWN_FAILURES
    if update:
      filename = os.path.join(BOUNDARY_DIR, name, 'expected.out')
      with open(filename, 'w', encoding='utf-8') as stream:
        stream.write(proc.stdout)
    else:
      self.assertEqual(proc.stdout, self.expected_output(name))

  def check_started(self, name, proc):
    '''Checks that a run printed the first line of expected.out.'''
    first = self.expected_output(name).splitlines()[:1]
    self.assertEqual(proc.stdout.splitlines()[:1], first)

def _make_tests(name):
  '''Returns the test functions of one driver.'''
  def test(self):
    self.check_output(name, self.run_driver(name))
  test.__name__ = 'test_' + name.replace('-', '_')
  test.__doc__ = 'Runs data/boundary/%s and checks its output.' % name
  if name not in KNOWN_FAILURES:
    return [test]
  # A known failure gets two tests.  The first checks that the run succeeds
  # and prints its first line; a crash or a timeout fails it.  The second
  # compares the whole output and is the expected failure.
  def runs(self):
    self.check_started(name, self.run_driver(name))
  runs.__name__ = test.__name__ + '_runs'
  runs.__doc__ = 'Runs data/boundary/%s; its output is a known failure.' % name
  test.__doc__ += '  Expected failure: %s.' % KNOWN_FAILURES[name]
  return [runs, unittest.expectedFailure(test)]

for _name in sorted(DRIVERS):
  for _test in _make_tests(_name):
    setattr(TestBoundaryDrivers, _test.__name__, _test)
