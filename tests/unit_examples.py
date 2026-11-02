'''
Runs every example under examples/ and compares its output with the file
expected.out in the example directory.

Each example has a run script.  The test runs it in a child process on the
backend of the test session, under an address-space cap and a time limit, and
compares the standard output of the child, decoded as UTF-8, with the text of
expected.out.  Only the standard output is compared; the standard error is
shown when a test fails.

The file reports the elapsed time of every example.  The first run also
compiles file modules; examples that compile Curry text pay the front-end
cost again on each run.

To regenerate the expected output after a deliberate change, run

    SPRITE_UPDATE_EXPECTED=1 ./run_tests unit_examples.py

once per backend that the example declares, and review the diff.  The file
must come out the same on every backend of the example.
'''
import cytest # from ./lib; must be first
from unittest import mock
import ast, contextlib, curry, importlib.util, os, signal, subprocess, sys, tempfile, time, unittest

EXAMPLES_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'examples')
  )
ADDRESS_SPACE = 2 * 1024 ** 3  # bytes; the Curry front end peaks near 1 GB
TIMEOUT = 120                  # seconds for the compile and the run of one example
KILL_AFTER = 10                # seconds from SIGTERM to SIGKILL in the timeout command
KILLED_STATUS = 128 + 9        # the status of timeout when its SIGKILL fires
DUMP_LEAD_TIME = 30            # seconds before the example time limit
STACK_TEXT_LIMIT = 256 * 1024  # aggregate bytes collected from dump files

# The runnable examples.
EXAMPLES = [
    '00-run-curry-programs'
  , '01-run-with-python'
  , '02-dynamic-code-generation'
  , '03-inspect'
  , '04-static-compile'
  , '05-trees'
  , '06-variables'
  , '07-choices'
  , '08-permutation-sort'
  , '09-streams'
  , '10-queens-set-functions'
  , '11-sudoku'
  , '12-cryptarithm'
  , '13-regex-nondeterminism'
  , '14-parser-functional-patterns'
  , '15-dependency-solver'
  , '16-scheduling'
  , '17-type-inference'
  , '18-text-extraction'
  , '19-blocks-world-app'
  , '20-cxx-types-deduction'
  , '21-cxx-types-overloads'
  , '22-cxx-types-trait-check'
  , '23-cxx-types-layout'
  , '24-build-system'
  , '25-perfect-hash'
  ]

# Directories with a run script that the test does not run, and why.  Every
# directory with a run script is in EXAMPLES or here; a test checks that.
EXCLUDED = {}

# Directory -> Python modules outside the standard library that the example
# imports.  The test skips the example when one of them is missing.  No
# example needs one at present.
REQUIRES = {}

# Directory -> the reason the example runs on Linux alone, and why; empty since the
# objects of the C++ backend load on macOS (issue #162).
LINUX_ONLY = {}

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
  , '25-perfect-hash':
        'a search over a large live state (nine alternatives per position), '
        'unfinished after 120 s'
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

@contextlib.contextmanager
def example_diagnostics(env):
  """Register signal dumps in Python descendants without a watchdog thread."""
  if os.name != 'posix':
    yield env, None
    return
  with tempfile.TemporaryDirectory(prefix='example-stacks-') as directory:
    with open(os.path.join(directory, 'sitecustomize.py'), 'w') as stream:
      stream.write('''import faulthandler, importlib.machinery, importlib.util, os, signal, sys
if os.name == "posix" and not hasattr(sys, "_sprite_example_dump"):
    _directory = os.environ["SPRITE_EXAMPLE_DUMP_DIR"]
    def _example_register():
        # Integer descriptors avoid buffered-file locks inherited at fork.
        path = os.path.join(_directory, str(os.getpid()) + ".log")
        fd = os.open(path + ".pending", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        faulthandler.register(signal.SIGUSR1, file=fd, all_threads=True)
        old = getattr(sys, "_sprite_example_dump", None)
        sys._sprite_example_dump = fd
        if old is not None:
            os.close(old)
        # Publish only after SIGUSR1 is safe to send.
        os.replace(path + ".pending", path)
    _example_register()
    os.register_at_fork(after_in_child=_example_register)
# Delegate past every injected copy, preserving ordinary self-imports.
_injected = os.environ["SPRITE_EXAMPLE_HOOK_PATHS"].split(os.pathsep)
_paths = [p for p in sys.path if os.path.realpath(p) not in _injected]
_spec = importlib.machinery.PathFinder.find_spec("sitecustomize", _paths)
if _spec is not None:
    _module = importlib.util.module_from_spec(_spec)
    sys.modules["sitecustomize"] = _module
    _spec.loader.exec_module(_module)
''')
    env = dict(env, SPRITE_EXAMPLE_DUMP_DIR=directory,
               SPRITE_EXAMPLE_HOOK_PATHS=os.pathsep.join(filter(None, [
                   os.path.realpath(directory), env.get('SPRITE_EXAMPLE_HOOK_PATHS', '')
                 ])))
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [
        directory, env.get('PYTHONPATH', '')
      ]))
    yield env, directory


def signal_example_stacks(directory, group):
  """Signal only published registrations still in the example's group."""
  for name in os.listdir(directory):
    if name.endswith('.log') and name[:-4].isdigit():
      try:
        pid = int(name[:-4])
        # A descendant that starts its own session gets no signal and no dump.
        if os.getpgid(pid) == group:
          # An exec before handler setup is acceptable: timeout ends this tree.
          os.kill(pid, signal.SIGUSR1)
      except ProcessLookupError:
        pass


def communicate_example(proc, directory):
  try:
    return proc.communicate(timeout=max(0.01, TIMEOUT - DUMP_LEAD_TIME))
  except subprocess.TimeoutExpired:
    try:
      # timeout has started by now and put itself and its tree in its own group.
      group = os.getpgid(proc.pid)
    except ProcessLookupError:
      pass
    else:
      signal_example_stacks(directory, group)
    # Keep draining pipes while allowing dumps to finish. The external timeout
    # retains responsibility for the original deadline and process-tree kill.
    try:
      return proc.communicate(timeout=min(0.2, DUMP_LEAD_TIME))
    except subprocess.TimeoutExpired:
      return proc.communicate()


def example_stacks(directory):
  """Read even the dumps of descendants whose parents captured their stderr."""
  stacks = []
  remaining = STACK_TEXT_LIMIT
  omitted = 0
  for name in sorted(os.listdir(directory)):
    if name.endswith('.log'):
      with open(os.path.join(directory, name), 'rb') as stream:
        size = os.fstat(stream.fileno()).st_size
        if not size:
          continue
        header = ('Python process %s:\n' % name[:-4]).encode('utf-8')
        if stacks:
          header = b'\n' + header
        prefix = header[:remaining]
        remaining -= len(prefix)
        text = stream.read(min(size, remaining))
        remaining -= len(text)
        omitted += len(header) - len(prefix) + size - len(text)
        stacks.append(prefix + text)
  result = b''.join(stacks).decode('utf-8', errors='replace')
  if omitted:
    result += '\n[Python stacks truncated: %d bytes omitted]\n' % omitted
  return result


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

  @cytest.posix_only('executes POSIX shell drivers')
  def run_example(self, name):
    '''
    Runs the run script of an example in a child and returns the completed
    process.  The test fails when the child does not finish in TIMEOUT
    seconds or exits with a non-zero status.  It is skipped when the example
    does not run on the backend of the session or needs a Python module that
    is missing.  A second call for the same example returns the first run.
    '''
    backend = curry.flags['backend']
    for module in REQUIRES.get(name, ()):
      if importlib.util.find_spec(module) is None:
        self.skipTest('%s needs the Python module %s' % (name, module))
    if sys.platform == 'darwin' and name in LINUX_ONLY:
      self.skipTest('%s %s (issue #162)' % (name, LINUX_ONLY[name]))
    if cytest.GC_STRESS and name in STRESS_EXCLUDED:
      self.skipTest(
          'collector stress mode: %s is %s' % (name, STRESS_EXCLUDED[name])
        )
    if name in self.procs:
      return self.procs[name]
    exdir = os.path.join(EXAMPLES_DIR, name)
    # Golden output exercises source execution; JIT behavior has its own tests.
    env = dict(
        os.environ, SPRITE_INTERPRETER_FLAGS=(
            'backend:' + backend + ',interpret:new,jit:off'
          )
      , LC_ALL='C.UTF-8', PYTHONIOENCODING='utf-8'
      )
    # An example finds its own modules, and it runs as a user would run it,
    # without the library path of the test suite.
    env.pop('CURRYPATH', None)
    env.pop('PYTHONPATH', None)
    cmd = cytest.limit_prefix(ADDRESS_SPACE, TIMEOUT, KILL_AFTER) + ['bash', './run']
    start = time.time()
    with example_diagnostics(env) as (env, directory):
      with subprocess.Popen(
          cmd, cwd=exdir, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        , encoding='utf-8', errors='replace'
        ) as child:
        stdout, stderr = communicate_example(child, directory)
        proc = subprocess.CompletedProcess(cmd, child.returncode, stdout, stderr)
      stacks = example_stacks(directory)
    elapsed = time.time() - start
    self.times[name] = elapsed
    # timeout exits with 124 when SIGTERM ends the child.  When the child
    # ignores SIGTERM, the SIGKILL that follows also ends timeout itself, so
    # the status is then 137.
    timed_out = proc.returncode == cytest.TIMEOUT_STATUS or (
        proc.returncode == KILLED_STATUS and elapsed >= TIMEOUT
      )
    self.assertFalse(timed_out, '%s did not finish in %d s\n%s'
                     % (name, TIMEOUT, proc.stderr + '\n' + stacks))
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


class TestExampleDiagnostics(cytest.TestCase):
  @cytest.posix_only('needs POSIX process groups and signals')
  def test_registration_outside_example_group_is_not_signalled(self):
    prefix = cytest.limit_prefix(ADDRESS_SPACE, 8, 1)
    if not any(os.path.basename(part) in ('timeout', 'gtimeout') for part in prefix):
      self.skipTest('needs the coreutils timeout command')
    with example_diagnostics(os.environ) as (env, directory):
      example = subprocess.Popen(
          prefix + [sys.executable, '-c',
                    'import os, time; print(os.getpgrp(), flush=True); time.sleep(60)']
        , env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
      try:
        # The child's output proves timeout has established its group.
        self.assertEqual(int(example.stdout.readline()), example.pid)
        group = os.getpgid(example.pid)
        self.assertEqual(group, example.pid)
        outside = subprocess.Popen(['sleep', '60'])
        try:
          self.assertNotEqual(os.getpgid(outside.pid), group)
          with open(os.path.join(directory, '%d.log' % outside.pid), 'w'):
            pass
          with mock.patch.object(os, 'kill', wraps=os.kill) as kill:
            signal_example_stacks(directory, group)
          self.assertTrue(kill.called)
          self.assertNotIn(mock.call(outside.pid, signal.SIGUSR1), kill.call_args_list)
          self.assertIsNone(outside.poll())
        finally:
          outside.terminate()
          outside.wait()
      finally:
        if example.poll() is None:
          example.terminate()
        example.communicate()

  @cytest.posix_only('executes a POSIX shell driver')
  def test_stalled_descendants_appear_in_failure(self):
    prefix = cytest.limit_prefix(timeout=8)
    if not any(os.path.basename(part) in ('timeout', 'gtimeout') for part in prefix):
      self.skipTest('needs the coreutils timeout command')
    with tempfile.TemporaryDirectory(prefix='example-timeout-test-') as directory:
      exdir = os.path.join(directory, 'stalled')
      os.mkdir(exdir)
      with open(os.path.join(exdir, 'run'), 'w') as stream:
        stream.write(
            'echo "driver stderr" >&2\n'
            '"$EXAMPLE_TEST_PYTHON" -c \'import time; time.sleep(60)\' 2>/dev/null &\n'
            '"$EXAMPLE_TEST_PYTHON" -c \'import time; time.sleep(60)\' 2>/dev/null &\n'
            'wait\n'
          )
      case = TestExamples()
      case.times, case.procs = {}, {}
      # Both children discard stderr. Their independent dump files must still
      # reach the assertion that reports the timeout of the whole shell tree.
      with mock.patch.multiple(sys.modules[__name__], EXAMPLES_DIR=directory,
                               TIMEOUT=8, DUMP_LEAD_TIME=3, KILL_AFTER=1), \
           mock.patch.dict(os.environ, EXAMPLE_TEST_PYTHON=sys.executable):
        with self.assertRaisesRegex(AssertionError, 'did not finish in 8 s') as caught:
          case.run_example('stalled')
    message = str(caught.exception)
    self.assertIn('driver stderr', message)
    self.assertEqual(message.count('Python process '), 2)
    # Accept startup frames as well as the sleeping main thread.
    self.assertEqual(message.count('most recent call first'), 2)

  def test_existing_sitecustomize(self):
    with tempfile.TemporaryDirectory(prefix='example-site-test-') as directory:
      with open(os.path.join(directory, 'sitecustomize.py'), 'w') as stream:
        stream.write('import sitecustomize\nsitecustomize.example_ready = "customized"\n')
      env = dict(os.environ, PYTHONPATH=directory)
      with example_diagnostics(env) as (env, _):
        proc = subprocess.run(
            [sys.executable, '-c',
             'import sitecustomize; print(sitecustomize.example_ready)']
          , env=env, capture_output=True, text=True, timeout=15
          )
      self.assertEqual(proc.returncode, 0, proc.stderr)
      self.assertEqual(proc.stdout, 'customized\n')

  def run_fork_case(self, code):
    with example_diagnostics(os.environ) as (env, directory):
      proc = subprocess.Popen(
          [sys.executable, '-c', code], env=env, start_new_session=True
        , stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
      try:
        stdout, stderr = proc.communicate(timeout=10)
        stacks = example_stacks(directory)
      finally:
        if proc.poll() is None:
          os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
      self.assertEqual(proc.returncode, 0, stderr)
      return stdout, stacks

  @unittest.skipUnless(hasattr(os, 'fork'), 'needs fork without exec')
  def test_fork_normal_exit(self):
    for after_signal in (False, True):
      code = (
          'import os, signal\n'
          'if %r: os.kill(os.getpid(), signal.SIGUSR1)\n'
          'pid = os.fork()\n'
          'if pid == 0 and %r: os.kill(os.getpid(), signal.SIGUSR1)\n'
          'if pid != 0:\n'
          '    assert os.waitpid(pid, 0)[1] == 0\n'
          '    print("reaped")\n'
        ) % (after_signal, after_signal)
      stdout, _ = self.run_fork_case(code)
      self.assertEqual(stdout, 'reaped\n')

  @unittest.skipUnless(hasattr(os, 'fork'), 'needs fork without exec')
  def test_concurrent_forks(self):
    code = (
        'import os, threading\n'
        'barrier = threading.Barrier(2)\n'
        'statuses = []\n'
        'def fork():\n'
        '    barrier.wait()\n'
        '    pid = os.fork()\n'
        '    if pid == 0: raise SystemExit(0)\n'
        '    statuses.append(os.waitpid(pid, 0)[1])\n'
        'threads = [threading.Thread(target=fork) for _ in range(2)]\n'
        'for thread in threads: thread.start()\n'
        'for thread in threads: thread.join()\n'
        'assert statuses == [0, 0], statuses\n'
      )
    self.run_fork_case(code)

  @unittest.skipUnless(hasattr(os, 'fork'), 'needs fork without exec')
  def test_blocked_fork_child(self):
    code = (
        'import os, signal\n'
        'r, w = os.pipe()\n'
        'ready_r, ready_w = os.pipe()\n'
        'pid = os.fork()\n'
        'if pid == 0:\n'
        '    os.close(w)\n'
        '    def blocked_child():\n'
        '        os.write(ready_w, b"r")\n'
        '        os.read(r, 1)\n'
        '    blocked_child()\n'
        'else:\n'
        '    import time\n'
        '    os.read(ready_r, 1)\n'
        '    os.kill(pid, signal.SIGUSR1)\n'
        '    path = os.path.join(os.environ["SPRITE_EXAMPLE_DUMP_DIR"], str(pid) + ".log")\n'
        '    while os.stat(path).st_size == 0: time.sleep(0.01)\n'
        '    os.write(w, b"x")\n'
        '    assert os.waitpid(pid, 0)[1] == 0\n'
        '    print(pid)\n'
      )
    stdout, stacks = self.run_fork_case(code)
    self.assertIn('Python process %s:' % stdout.strip(), stacks)
    self.assertIn('in blocked_child', stacks)

  @cytest.posix_only('needs POSIX signal registration')
  def test_nested_diagnostics(self):
    with example_diagnostics(os.environ) as (outer_env, outer):
      with example_diagnostics(outer_env) as (env, inner):
        proc = subprocess.run(
            [sys.executable, '-c',
             'import runpy, os, sys; '
             'fd = sys._sprite_example_dump; '
             'runpy.run_path(os.path.join(os.environ["SPRITE_EXAMPLE_HOOK_PATHS"]'
             '.split(os.pathsep)[1], "sitecustomize.py")); '
             'assert fd == sys._sprite_example_dump; print("ready")']
          , env=env, capture_output=True, text=True, timeout=10
          )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, 'ready\n')
        self.assertFalse(any(name.endswith('.log') for name in os.listdir(outer)))
        self.assertEqual(len([n for n in os.listdir(inner) if n.endswith('.log')]), 1)

  def test_stack_collection_is_bounded(self):
    with tempfile.TemporaryDirectory(prefix='example-stack-limit-') as directory:
      for name in ('1.log', '2.log'):
        with open(os.path.join(directory, name), 'wb') as stream:
          stream.write(b'x' * STACK_TEXT_LIMIT)
      text = example_stacks(directory)
    headers = len('Python process 1:\n') + len('\nPython process 2:\n')
    omitted = STACK_TEXT_LIMIT + headers
    marker = '\n[Python stacks truncated: %d bytes omitted]\n' % omitted
    self.assertEqual(len(text), STACK_TEXT_LIMIT + len(marker))
    self.assertTrue(text.endswith(marker))


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
