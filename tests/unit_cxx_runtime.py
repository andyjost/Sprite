import cytest # from ./lib; must be first
from curry.backends.cxx import cyrtbindings as cyrt
from curry import common, config
import curry, os, subprocess, unittest

class TestCxxRuntime(cytest.TestCase):
  def testModuleCreation(self):
    count_modules = lambda: len(cyrt.Module.getall())
    # Earlier tests in the same process may leave the Prelude loaded, so count
    # relative to the state at entry.
    base = count_modules()
    self.assertNotIn('Hello', cyrt.Module.getall())

    # Create.
    Hello = cyrt.Module.find_or_create('Hello')
    self.assertEqual(count_modules(), base + 1)
    self.assertIs(cyrt.Module.getall()['Hello'], Hello)

    # Attributes.
    self.assertEqual(Hello.name, 'Hello')

    # Recreate.
    Hello2 = cyrt.Module.find_or_create('Hello')
    self.assertIs(Hello, Hello2)

    # Delete
    del Hello, Hello2
    self.assertEqual(count_modules(), base)

  def testTypeCreation(self):
    Hello = cyrt.Module.find_or_create('Hello')

    Cons = Hello.create_infotable(':', 2, common.T_CTOR  , common.F_LIST_TYPE)
    Nil = Hello.create_infotable('[]', 0, common.T_CTOR+1, common.F_LIST_TYPE)
    List = Hello.create_type('[]', [Cons, Nil], 0)

    self.assertEqual(Cons.arity, 2)
    self.assertEqual(Cons.flags, common.F_LIST_TYPE)
    self.assertEqual(Cons.format, 'pp')
    self.assertEqual(Cons.name, ':')
    self.assertEqual(Cons.tag, common.T_CTOR)
    # self.assertIs(Cons.step, None)
    # self.assertIs(Cons.typecheck, None)
    self.assertIs(Cons.typedef, List)

    self.assertIs(List.constructors[0], Cons)
    self.assertIs(List.constructors[1], Nil)

@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestCxxProcess(cytest.TestCase):
  '''
  Tests that run the C++ backend in a subprocess: a program that runs out of
  memory, and the order of a program's output.  The programs are in
  data/curry/CxxRuntime.curry.
  '''
  TIMEOUT = 120

  @classmethod
  def setUpClass(cls):
    # Compile the module once here.  The children then load it from the cache.
    curry.import_('CxxRuntime')

  def test_out_of_memory_raises_MemoryError(self):
    '''
    An audit finding: when malloc failed, node allocation returned a null
    pointer, and the process crashed or aborted.  std::bad_alloc now leaves
    the step functions and the scheduler, and pybind11 turns it into
    MemoryError.  The child runs under a 1 GiB address-space cap.  The
    backend needs about 600 MB at load, so the fill is a few hundred MB.
    '''
    code = '''
import curry, os
curry.reload({'backend': 'cxx', 'defaultconverter': 'topython'})
M = curry.import_('CxxRuntime')
try:
  next(curry.eval(M.unbounded))
except MemoryError:
  os._exit(42)
os._exit(1)
'''
    proc = cytest.run_in_subprocess(code, self.TIMEOUT, address_space=1 << 30)
    self.assertEqual(
        proc.returncode, 42
      , 'the child ended with status %s; stderr:\n%s'
            % (proc.returncode, proc.stderr)
      )

  def test_program_output_precedes_value(self):
    '''
    An audit finding: the program wrote to the C standard output buffer, and
    Python printed the value from its own, so sprite-exec showed ``()``
    before the text of putStrLn when the output was a pipe.  The C buffer is
    now flushed when control returns to Python.
    '''
    env = dict(os.environ)
    env['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx'
    cmd = ['timeout', str(self.TIMEOUT), config.sprite_exec(), '-m', 'CxxRuntime']
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, 'Hello from Curry\n()\n')

class TestBackendOption(cytest.TestCase):
  '''
  The ``-b,--backend`` option of sprite-exec.  It overrides a ``backend`` flag
  from SPRITE_INTERPRETER_FLAGS, in both directions.
  '''
  TIMEOUT = 120

  def backend_seen(self, option, flag):
    '''
    Starts the interactive prompt of sprite-exec with ``-b option`` while the
    environment names ``flag``, and returns what the prompt prints for the
    backend flag.
    '''
    env = dict(os.environ)
    env['SPRITE_INTERPRETER_FLAGS'] = 'backend:' + flag
    cmd = ['timeout', str(self.TIMEOUT), config.sprite_exec(), '-b', option]
    proc = subprocess.run(
        cmd, env=env, input="print('backend', __package__.flags['backend'])\n"
      , capture_output=True, text=True
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    return proc.stdout

  def test_backend_option_overrides_flag(self):
    self.assertIn('backend cxx', self.backend_seen('cxx', 'py'))
    self.assertIn('backend py', self.backend_seen('py', 'cxx'))
