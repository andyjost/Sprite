'''Stack-floor ownership, dictionary flags and sparse constraint stores.'''
import cytest # from ./lib; must be first
import curry
from curry import config
from curry.backends.cxx import curryrtbindings as rt
from curry.objects.handle import getHandle
from cytest.buildtools import runtime_test_command, runtime_test_environment
import os, subprocess, sys, tempfile, unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))

class TestRuntimeBookkeeping(cytest.TestCase):
  @unittest.skipIf(config.cxx_tool() is None, 'no C++ compiler is installed')
  def test_native(self):
    self.run_native()

  @unittest.skipUnless(sys.platform == 'darwin', 'macOS stack API')
  @unittest.skipIf(config.cxx_tool() is None, 'no C++ compiler is installed')
  def test_macos_floor_matches_pthread_stack_api(self):
    self.run_native()

  @unittest.skipUnless(sys.platform == 'win32', 'Windows stack API')
  @unittest.skipIf(config.cxx_tool() is None, 'no C++ compiler is installed')
  def test_windows_floor_matches_stack_limits_api(self):
    self.run_native()

  def run_native(self):
    source = os.path.join(HERE, 'data', 'cxx', 'perfrt_test.cpp')
    with tempfile.TemporaryDirectory() as directory:
      target = os.path.join(directory, 'perfrt_test')
      libdir = config.installed_path('lib')
      command = [config.cxx_tool(), '-std=c++17', '-O2', '-Wall',
          '-fno-strict-aliasing', '-pthread',
          '-I' + config.installed_path('include'), source, '-o', target,
          '-L' + libdir, '-lcurryrt', '-Wl,-rpath,' + libdir]
      if os.name == 'nt':
        target += '.exe'
        command = runtime_test_command(source, target)
      result = subprocess.run(command, capture_output=True, text=True)
      self.assertEqual(result.returncode, 0, result.stderr)
      self.assertEqual(result.stderr, '')
      result = subprocess.run([target], timeout=60, capture_output=True,
          text=True, env=runtime_test_environment())
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      self.assertEqual(result.stdout, 'ok\n')

  def test_guard_on_repeated_thread_and_fork_evaluations(self):
    curry.import_('StackGuard')
    code = r'''
import curry, os, threading
curry.reset(backend='cxx', stack_limit=65536, worker_stack=None, jit='off')
M = curry.import_('StackGuard')
def evaluate():
  assert curry.eval(M.deep(10)).one() == 10
  try:
    curry.eval(M.deep(5000)).one()
  except curry.EvaluationError as error:
    assert 'stack limit of ' in str(error), str(error)
  else:
    raise AssertionError('deep evaluation did not reach its stack guard')
evaluate()
evaluate()
errors = []
def worker():
  try: evaluate()
  except BaseException as error: errors.append(error)
thread = threading.Thread(target=worker)
thread.start()
thread.join()
assert not errors, errors
if hasattr(os, 'fork'):
  child = os.fork()
  if child == 0:
    try: evaluate()
    except BaseException: os._exit(1)
    os._exit(0)
  _, status = os.waitpid(child, 0)
  assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0, status
print('ok')
'''
    result = cytest.run_in_subprocess(code, 60, address_space=2 << 30)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    self.assertEqual(result.stdout.splitlines(), ['ok'])

  @unittest.skipUnless(sys.platform == 'linux', 'Linux soft stack limit')
  def test_guard_after_lowering_soft_stack_limit(self):
    self.run_floor_guard("""
import resource
_, hard = resource.getrlimit(resource.RLIMIT_STACK)
resource.setrlimit(resource.RLIMIT_STACK, (8 << 20, hard))
assert curry.eval(M.deep(10)).one() == 10
resource.setrlimit(resource.RLIMIT_STACK, (2 << 20, hard))
evaluate()
""")

  @unittest.skipUnless(sys.platform in ('linux', 'darwin', 'win32'),
      'no independent stack API on this platform')
  def test_guard_on_small_thread_stack(self):
    self.run_floor_guard("""
# Leave room above the runtime's 1 MiB safety margin.
threading.stack_size(2 << 20)
errors = []
def worker():
  try:
    evaluate()
    evaluate()
  except BaseException as error:
    errors.append(error)
thread = threading.Thread(target=worker)
thread.start()
thread.join()
assert not errors, errors
""")

  @unittest.skipUnless(sys.platform in ('linux', 'darwin') and hasattr(os, 'fork'),
      'requires fork and a pthread stack API')
  def test_guard_after_fork_from_evaluating_thread(self):
    self.run_floor_guard("""
# Leave room above the runtime's 1 MiB safety margin.
threading.stack_size(2 << 20)
errors = []
def worker():
  try:
    evaluate()
    child = os.fork()
    if child == 0:
      try:
        evaluate()
      except BaseException:
        os._exit(1)
      os._exit(0)
    _, status = os.waitpid(child, 0)
    assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0, status
    evaluate()
  except BaseException as error:
    errors.append(error)
thread = threading.Thread(target=worker)
thread.start()
thread.join()
assert not errors, errors
""")

  def run_floor_guard(self, body):
    curry.import_('StackGuard')
    code = r'''
import curry, os, threading
curry.reset(backend='cxx', stack_limit=1 << 40, worker_stack=None, jit='off')
M = curry.import_('StackGuard')
def evaluate():
  assert curry.eval(M.deep(10)).one() == 10
  try:
    curry.eval(M.deep(100000)).one()
  except curry.EvaluationError as error:
    assert 'stack limit of ' in str(error), str(error)
  else:
    raise AssertionError('deep evaluation did not reach its stack guard')
''' + body + "\nprint('ok')\n"
    result = cytest.run_in_subprocess(code, 60, address_space=2 << 30)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    self.assertEqual(result.stdout.splitlines(), ['ok'])

  def test_dictionary_flag_image_and_compiled(self):
    for mode in ('all', 'off'):
      with self.subTest(mode=mode):
        curry.reset(backend='cxx', interpret=mode, jit='off')
        module = curry.import_('Prelude')
        if mode == 'all':
          curry.reset(backend='cxx', interpret=mode, jit='off')
          with mock.patch('curry.toolchain._loadcurry.loadicurry',
              side_effect=AssertionError('image load read ICurry text')):
            module = curry.import_('Prelude')
        types = getHandle(module).backend_handle
        dictionary = types.get_type('_Dict#Ord')
        self.assertIsNotNone(dictionary)
        flags = dictionary.flags
        self.assertTrue(flags & rt.F_DICTIONARY)
        compare = curry.symbol('Prelude.compare').info
        if mode == 'all':
          self.assertFalse(flags & rt.F_STATIC_OBJECT)
          self.assertIsNotNone(rt.icurry_bytecode(compare))
        else:
          # Adoption may retain a runtime type's identity. Its function
          # tables must nevertheless be compiled, and keep all type bits.
          self.assertIsNone(rt.icurry_bytecode(compare))
        self.assertTrue(curry.eval(getattr(module, '<')(1, 2)).one())
        self.assertFalse(curry.eval(getattr(module, '<')(2, 1)).one())
        ordinary = types.get_type('Bool')
        flags = ordinary.flags
        self.assertFalse(flags & rt.F_DICTIONARY)

  def test_branching_unions_keep_value_order(self):
    module = curry.compile('''
module BranchUnions where
branch :: Int -> [(Bool, Bool)]
branch 0 = []
branch n | n > 0 & (x == False || x == True) & x =:= y = (x,y) : branch (n-1) where x,y free
''')
    before = curry.stats()
    values = list(curry.eval(module.branch(3)))
    after = curry.stats()
    order = [(False,False,False), (False,False,True), (False,True,False),
        (True,False,False), (False,True,True), (True,False,True),
        (True,True,False), (True,True,True)]
    expected = [[(a,a), (b,b), (c,c)] for a,b,c in order]
    self.assertEqual(values, expected)
    self.assertEqual(after['steps'] - before['steps'], 295)
    self.assertEqual(after['forks'] - before['forks'], 57)

  @cytest.skipIfGcStress('a full Mergesort search collects at every step')
  def test_mergesort_representatives_and_counters(self):
    directory = os.path.join(HERE, 'data', 'curry', 'benchmarks')
    code = '''
import curry
M = curry.import_('Mergesort', path=[%r] + curry.path)
before = curry.stats()
assert list(curry.eval(M.main)) == [True]
after = curry.stats()
assert after['steps'] - before['steps'] == 57880  # 61313 before class defaults resolved at compile time
assert after['forks'] - before['forks'] == 1129
print('ok')
''' % directory
    result = cytest.run_in_subprocess(code, 60, address_space=4_000_000_000)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    self.assertEqual(result.stdout.splitlines(), ['ok'])

if __name__ == '__main__':
  unittest.main()
