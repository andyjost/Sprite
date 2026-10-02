import cytest # from ./lib; must be first
from curry import config
import curry, os, signal, subprocess, tempfile, unittest

class CompleteTestCase(cytest.TestCase):
  @cytest.with_flags(backend='cxx', defaultconverter='topython')
  def test_complete(self):
    Loop = curry.compile(
      '''
      loop = loop
      main :: Int
      main = 1 ? loop ? 2
      '''
      )
    e = curry.eval(Loop.main)
    self.assertEqual(sorted([next(e), next(e)]), [1,2])


LOOP = '''
loop :: Int
loop = loop

main :: Int
main = loop ? 1 ? loop
'''

LENGTH = '''
main :: Int
main = length [1..] ? 1 ? length [1..]
'''

class FairnessTestCase(cytest.TestCase):
  '''
  Fairness checks.  Covers a 2023 report by Michael Hanus: ``loop ? 1 ? loop``
  never printed on the Python backend, and ``length [1..] ? 1 ? length [1..]``
  died with RecursionError (Python) or a segmentation fault (C++).

  Each program must print ``1`` first.  The test reads the first line of
  output only, because the programs do not end on their own.  ``loop ? 1 ?
  loop`` runs on without end on both backends.  On the C++ backend it
  allocates a node per step and no collection runs, so the child that
  evaluates a program runs under an address-space cap.  ``length [1..] ? 1 ?
  length [1..]`` ends with an error after the ``1``.  The Python backend
  reports the RecursionError of the deep alternatives once they are stuck,
  and the C++ backend reports the stack-limit error.  The test does not wait
  for that.

  Each program runs in a subprocess under ``timeout``.  A timeout is a
  failure.
  '''
  # The limit covers the compilation of Fair.curry too, which runs the PAKCS
  # front end and, on the C++ backend, the C++ compiler.
  TIMEOUT = 120
  # The cap on the address space of the child that evaluates a program.  The
  # C++ backend needs about 600 MB at load.  The child that compiles the
  # program runs without the cap: the front end and the C++ compiler need
  # more.
  ADDRESS_SPACE = 1 << 30

  def first_line(self, source, backend):
    with tempfile.TemporaryDirectory() as tmpdir:
      with open(os.path.join(tmpdir, 'Fair.curry'), 'w') as ostream:
        ostream.write(source)
      env = dict(os.environ)
      env['SPRITE_INTERPRETER_FLAGS'] = 'backend:' + backend
      env['PYTHONUNBUFFERED'] = '1'
      # Compile the program first.  The second child loads it from the cache.
      cmd = [
          'timeout', str(self.TIMEOUT), config.sprite_exec(), '-g', ''
        , 'Fair.curry'
        ]
      proc = subprocess.run(
          cmd, cwd=tmpdir, env=env, capture_output=True, text=True
        )
      self.assertEqual(
          proc.returncode, 0
        , 'compilation failed on the %s backend; stderr:\n%s'
              % (backend, proc.stderr)
        )
      cmd = [
          'prlimit', '--as=%d' % self.ADDRESS_SPACE
        , 'timeout', str(self.TIMEOUT), config.sprite_exec(), 'Fair.curry'
        ]
      proc = subprocess.Popen(
          cmd, cwd=tmpdir, env=env, start_new_session=True
        , stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
      try:
        line = proc.stdout.readline()
      finally:
        try:
          os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
          pass
        _, stderr = proc.communicate()
      if not line:
        self.fail(
            'no output from the %s backend within %s seconds; stderr:\n%s'
          % (backend, self.TIMEOUT, stderr)
          )
      return line.rstrip('\n')

  def test_loop_py(self):
    self.assertEqual(self.first_line(LOOP, 'py'), '1')

  def test_loop_cxx(self):
    self.assertEqual(self.first_line(LOOP, 'cxx'), '1')

  def test_length_py(self):
    self.assertEqual(self.first_line(LENGTH, 'py'), '1')

  def test_length_cxx(self):
    self.assertEqual(self.first_line(LENGTH, 'cxx'), '1')


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'about 200 seconds on the Python backend'
  )
class SomeNumTestCase(cytest.TestCase):
  '''
  Covers a 2023 report by Michael Hanus at the reported size: ``isZero
  (addSomeNum2 2000)`` never yielded a value on the Python backend.  On the
  C++ backend the evaluation takes about two seconds and 1.4 GB of memory, so
  the check belongs to this tier.  The goal runs in a child under a cap and a
  timeout: SIGALRM does not interrupt the C++ scheduler, and a crash would end
  the runner.  The program is in data/curry/SomeNum.curry.  unit_py_evaluation
  checks it at 50 on both backends.
  '''
  TIMEOUT = 120
  ADDRESS_SPACE = 2 << 30

  def test_addSomeNum2_reported_size(self):
    curry.import_('SomeNum') # compile once, so the child loads the cache
    code = '''
import curry
curry.reload({'backend': 'cxx', 'defaultconverter': 'topython'})
M = curry.import_('SomeNum')
print(list(curry.eval(M.main)))
'''
    proc = cytest.run_in_subprocess(
        code, self.TIMEOUT, address_space=self.ADDRESS_SPACE
      )
    self.assertEqual(
        proc.returncode, 0
      , 'the child ended with status %s; stderr:\n%s'
            % (proc.returncode, proc.stderr)
      )
    self.assertEqual(proc.stdout, '[True]\n')
