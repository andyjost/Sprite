'''
Runs the Quickstart and Using the API as doctests, in reading order, in
separate child processes.  The temporary examples directory holds only
the authored Curry sources used by each page, without build products.
Every transcript must pass.  The guide uses curry.stream and requires C++;
the short Quickstart runs on either backend.  No oracle is needed.
'''
import cytest # from ./lib; must be first
import curry, glob, os, shutil, subprocess, sys, tempfile

TESTDIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTDIR)
DOCS = os.path.join(ROOT, 'docs', 'source')
EXAMPLES = os.path.join(ROOT, 'examples')
QUICKSTART = os.path.join(DOCS, 'Quickstart.rst')
USING_THE_API = os.path.join(DOCS, 'PythonAPI', 'UsingTheAPI.rst')
ADDRESS_SPACE = 2 * 1024 ** 3  # bytes; the Curry front end peaks near 1 GB
TIMEOUT = 300                  # seconds for one page
KILL_AFTER = 10                # seconds from SIGTERM to SIGKILL in the timeout command

# The child runs a page as a doctest from the working directory, prints
# its report and one RESULT line, and exits with 1 if an example failed.
CHILD = '''
import doctest, os, sys
page, workdir = sys.argv[1:3]
os.chdir(workdir)
with open(page, encoding='utf-8') as stream:
  text = stream.read()
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

  def run_page(self, page, backends=('cxx', 'py')):
    '''
    Runs all the examples of ``page`` in a child
    on the backend of the session, from a fresh directory that holds
    the lesson sources, as a reader would, without the library path of the test
    suite.  Returns the completed process.  Skips when the page does not
    run on the backend of the session.
    '''
    backend = curry.flags['backend']
    if backend not in backends:
      self.skipTest(
          '%s uses the stream channel and runs on the %s backend alone'
        % (os.path.basename(page), ', '.join(backends))
        )
    workdir = tempfile.mkdtemp(prefix='func_docs-')
    try:
      examples = os.path.join(workdir, 'examples')
      os.mkdir(examples)
      shutil.copy(os.path.join(EXAMPLES, 'Peano.curry'), examples)
      for lesson in ('01-run-with-python', '05-trees', '07-choices', '09-streams'):
        destination = os.path.join(examples, lesson)
        os.mkdir(destination)
        for source in glob.glob(os.path.join(EXAMPLES, lesson, '*.curry')):
          if os.path.isfile(source):
            shutil.copy(source, destination)
      env = dict(
          os.environ, SPRITE_INTERPRETER_FLAGS='backend:' + backend
        , LC_ALL='C.UTF-8', PYTHONIOENCODING='utf-8'
        )
      env.pop('CURRYPATH', None)
      env.pop('PYTHONPATH', None)
      cmd = [
          'prlimit', '--as=%d' % ADDRESS_SPACE
        , 'timeout', '-k', str(KILL_AFTER), str(TIMEOUT)
        , launcher(), '-c', CHILD, page, examples
        ]
      return subprocess.run(
          cmd, cwd=examples, env=env, capture_output=True
        , encoding='utf-8', errors='replace'
        )
    finally:
      shutil.rmtree(workdir, ignore_errors=True)

  def assertPassed(self, proc, page, minimum):
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
    self.assertGreaterEqual(int(attempted), minimum, report)

  def test_using_the_api(self):
    '''Every example of Using the API passes, on the C++ backend.'''
    proc = self.run_page(USING_THE_API, backends=('cxx',))
    self.assertPassed(proc, USING_THE_API, minimum=60)

  def test_quickstart(self):
    '''Every example of the five-minute Quickstart passes.'''
    proc = self.run_page(QUICKSTART)
    self.assertPassed(proc, QUICKSTART, minimum=8)
