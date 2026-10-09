'''
Runs the two API pages of the documentation as doctests: the examples of
docs/source/Quickstart.rst and docs/source/PythonAPI/UsingTheAPI.rst, in the
order a reader types them.  Each page runs in a child process, from a
directory that holds examples/Peano.curry, with ``curry`` imported, on the
backend of the session, in step mode (the environment of the session), and
with the doctest option ELLIPSIS.  A directive on an example is in the page:
``# doctest: +SKIP`` on help(curry) and dir(curry), whose output varies by
machine, and on the load of Fib.so, which needs a new process.  Every example
of a page must pass.

Using the API names an object file (Fib.so), so it runs on the C++ backend
alone.  The Quickstart up to its section "Saving Compiled Curry" names none
and runs on both backends.  That section saves Peano and loads Peano.so while
the background compile of the module may run, which fails the load or ends
the process at exit (issue #109), so the whole page is a known failure on the
C++ backend until the issue is fixed.

A functional test, because every run compiles Curry with the front end
(Peano, Fib and the text goals of the pages); it uses no oracle.  The ICurry
cache of the session serves the texts after the first run.
'''
import cytest # from ./lib; must be first
import curry, os, shutil, subprocess, sys, tempfile, unittest

TESTDIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTDIR)
DOCS = os.path.join(ROOT, 'docs', 'source')
EXAMPLES = os.path.join(ROOT, 'examples')
QUICKSTART = os.path.join(DOCS, 'Quickstart.rst')
USING_THE_API = os.path.join(DOCS, 'PythonAPI', 'UsingTheAPI.rst')
# The heading of the section of the Quickstart that issue #109 covers.
SAVING = 'Saving Compiled Curry'
ADDRESS_SPACE = 2 * 1024 ** 3  # bytes; the Curry front end peaks near 1 GB
TIMEOUT = 300                  # seconds for one page
KILL_AFTER = 10                # seconds from SIGTERM to SIGKILL in the timeout command

# The child: the examples of a page as a doctest, from the working directory,
# up to a heading when one is given.  It prints the report of doctest and one
# line RESULT, and exits with 1 when an example failed.
CHILD = '''
import doctest, os, sys
page, workdir, stop_at = sys.argv[1:4]
os.chdir(workdir)
with open(page, encoding='utf-8') as stream:
  text = stream.read()
if stop_at:
  text = text[:text.index(stop_at)]
import curry
parser = doctest.DocTestParser()
test = parser.get_doctest(text, {'curry': curry}, os.path.basename(page), page, 0)
runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS)
runner.run(test)
results = runner.summarize(verbose=False)
print('RESULT: %d of %d examples failed' % (results.failed, results.attempted))
sys.exit(1 if results.failed else 0)
'''

def launcher():
  '''The Python of the installation, which puts the package on the path.'''
  home = os.environ.get('SPRITE_HOME')
  if not home:
    home = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(curry.__file__))))
  return os.path.join(home, 'bin', 'python')

class TestPages(cytest.TestCase):
  '''Runs each page in a child and checks that every example passed.'''

  def run_page(self, page, stop_at='', backends=('cxx', 'py')):
    '''
    Runs the examples of ``page`` up to the heading ``stop_at`` in a child
    on the backend of the session, from a fresh directory that holds
    Peano.curry, as a reader would, without the library path of the test
    suite.  Returns the completed process.  Skips when the page does not
    run on the backend of the session.
    '''
    backend = curry.flags['backend']
    if backend not in backends:
      self.skipTest(
          '%s names an object file and runs on the %s backend alone'
        % (os.path.basename(page), ', '.join(backends))
        )
    workdir = tempfile.mkdtemp(prefix='func_docs-')
    try:
      examples = os.path.join(workdir, 'examples')
      os.mkdir(examples)
      shutil.copy(os.path.join(EXAMPLES, 'Peano.curry'), examples)
      env = dict(
          os.environ, SPRITE_INTERPRETER_FLAGS='backend:' + backend
        , LC_ALL='C.UTF-8', PYTHONIOENCODING='utf-8'
        )
      env.pop('CURRYPATH', None)
      env.pop('PYTHONPATH', None)
      cmd = [
          'prlimit', '--as=%d' % ADDRESS_SPACE
        , 'timeout', '-k', str(KILL_AFTER), str(TIMEOUT)
        , launcher(), '-c', CHILD, page, examples, stop_at
        ]
      return subprocess.run(
          cmd, cwd=examples, env=env, capture_output=True
        , encoding='utf-8', errors='replace'
        )
    finally:
      shutil.rmtree(workdir, ignore_errors=True)

  def assertPassed(self, proc, page):
    '''The child ran every example of the page and none failed.'''
    report = 'status %d\n%s\n%s' % (proc.returncode, proc.stdout, proc.stderr)
    self.assertNotEqual(
        proc.returncode, cytest.TIMEOUT_STATUS
      , '%s did not finish in %d s' % (os.path.basename(page), TIMEOUT)
      )
    self.assertEqual(proc.returncode, 0, report)
    result = [line for line in proc.stdout.splitlines() if line.startswith('RESULT:')]
    self.assertEqual(len(result), 1, report)
    failed, _, attempted = result[0].split()[1:4]
    self.assertEqual(int(failed), 0, report)
    self.assertGreater(int(attempted), 30, report)

  def test_using_the_api(self):
    '''Every example of Using the API passes, on the C++ backend.'''
    proc = self.run_page(USING_THE_API, backends=('cxx',))
    self.assertPassed(proc, USING_THE_API)

  def test_quickstart(self):
    '''Every example of the Quickstart before "Saving Compiled Curry" passes.'''
    proc = self.run_page(QUICKSTART, stop_at=SAVING)
    self.assertPassed(proc, QUICKSTART)

  @unittest.expectedFailure
  def test_quickstart_saving_compiled_curry(self):
    '''
    The whole Quickstart, with "Saving Compiled Curry": the load of Peano.so
    during the background compile of Peano fails or ends the process at exit
    (issue #109).  Remove the mark when the issue is fixed.
    '''
    proc = self.run_page(QUICKSTART, backends=('cxx',))
    self.assertPassed(proc, QUICKSTART)
