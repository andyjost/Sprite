'''curry.save and curry.load through C++ source and shared objects.'''
import cytest # from ./lib; must be first

from curry import config
import curry, logging, os, shutil, subprocess, unittest
import tempfile
from unittest import mock
from cytest.logging import capture_log

TIMEOUT = 300
# The cap on the address space of a child, in bytes.
ADDRESS_SPACE = 2 << 30


class TestRoundTrip(cytest.TestCase):
  '''
  The round trip of each backend, in a child process.  A module of its own
  is saved without a main program and loaded with curry.load, in the session
  that saved it and again after a reset.  The C++ source that
  curry.save writes is compiled into a shared object by the step of the
  toolchain that sprite-make --so runs (backends.cxx.toolchain.Cpp2So), and
  curry.load reads the object.  Each child has an empty product cache and
  fresh source.  The new, tiered and off modes exercise foreground adoption
  and an object already loaded by an import; all refuses the swap with its
  reason and keeps the interpreted steps.
  '''
  CODE = r'''
import os, sys, tempfile
cache = tempfile.TemporaryDirectory(prefix='sprite-empty-products-')
os.environ['SPRITE_PRODUCT_CACHE'] = cache.name
os.environ['SPRITE_INTERPRETER_FLAGS'] = %(flags)r
import cytest, curry
tmpdir = tempfile.mkdtemp(prefix='sprite-loadsave-')
with open(os.path.join(tmpdir, 'SaveLoadFresh.curry'), 'w') as stream:
  stream.write('double :: Int -> Int\ndouble x = x + x\n\nmain :: Int\nmain = double 21\n')
curry.path.insert(0, tmpdir)
M = curry.import_('SaveLoadFresh')
if curry.flags['interpret'] == 'tiered':
  from curry.backends.cxx import tiered, curryrtbindings as curryrt
  # Leave the foreground load to do the swap, independently of how quickly
  # the background compiler runs on this machine.
  tiered.cancel()
  assert curryrt.icurry_is_interpreted(M.main.info)
print([str(v) for v in curry.eval(M.main)])
# The step reads the generated file under the product directory of the
# source, where the import wrote the ICurry and the JSON of the module.
from curry import config
from curry.backends.cxx import toolchain, tiered
tiered.wait(interp=cytest.raw.interp())
cppfile = os.path.join(
    tmpdir, '.curry', config.intermediate_subdir(), 'SaveLoadFresh.cpp'
  )
curry._interpreter_.save(M, cppfile, module_main=False)
saved = toolchain.Cpp2So(cytest.raw.interp())(cppfile, curry.path)
print(os.path.splitext(saved)[1])
M2 = curry._interpreter_.load(saved)
print(M2 is M, [str(v) for v in curry.eval(M2.main)])
curry.reset()
M3 = curry._interpreter_.load(saved)
print('SaveLoadFresh' in curry.modules, [str(v) for v in curry.eval(M3.main)])
'''

  @unittest.skipIf(
      config.cxx_tool() is None
    , 'the shared object needs the C++ compiler of the installation'
    )
  def test_round_trip(self):
    flags = 'backend:cxx,interpret:new'
    proc = cytest.run_in_subprocess(self.CODE % {'flags': flags}, TIMEOUT)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(
        proc.stdout.splitlines()
      , ["['42']", '.so', "True ['42']", "True ['42']"]
      , proc.stderr
      )

  @unittest.skipUnless(config.cxx_tool() is not None,
                       'the cold object needs the C++ backend and its compiler')
  def test_cold_cache_tiered(self):
    self.check_cold_cache('tiered')

  @unittest.skipUnless(config.cxx_tool() is not None,
                       'the cold object needs the C++ backend and its compiler')
  def test_cold_cache_off(self):
    self.check_cold_cache('off')

  def check_cold_cache(self, mode):
    proc = cytest.run_in_subprocess(
        self.CODE % {'flags': 'backend:cxx,interpret:' + mode}, TIMEOUT
      )
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertEqual(proc.stdout.splitlines(),
                     ["['42']", '.so', "True ['42']", "True ['42']"], proc.stderr)

  @unittest.skipUnless(config.cxx_tool() is not None,
                       'interpret:all belongs to the C++ backend')
  def test_all_refuses_the_swap_with_a_reason(self):
    code = self.CODE % {'flags': 'backend:cxx,interpret:all'}
    code = code.replace(
        'saved = toolchain.Cpp2So(cytest.raw.interp())(cppfile, curry.path)',
        "import subprocess\nenv = dict(os.environ, SPRITE_INTERPRETER_FLAGS="
        "'backend:cxx,interpret:off', CURRYPATH=os.pathsep.join(curry.path))\n"
        "subprocess.run([config.installed_path('bin', 'sprite-make'), '--so', "
        "os.path.join(tmpdir, 'SaveLoadFresh.curry')], env=env, "
        "check=True, capture_output=True, text=True)\n"
        "saved = os.path.splitext(cppfile)[0] + '.so'"
      )
    code = code[:code.index('M2 = curry._interpreter_.load(saved)')] + r'''
from curry.backends.cxx import curryrtbindings as curryrt
try:
  curry._interpreter_.load(saved)
except curry.LoadError as exc:
  assert 'interpret:all' in str(exc), exc
  assert 'replaces the live interpreted steps' in str(exc), exc
else:
  raise AssertionError('interpret:all accepted a swap')
assert curryrt.icurry_is_interpreted(M.main.info)
print([str(v) for v in curry.eval(M.main)])
'''
    proc = cytest.run_in_subprocess(code, TIMEOUT)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertEqual(proc.stdout.splitlines(), ["['42']", '.so', "['42']"])


@unittest.skipUnless(
    config.cxx_tool() is not None
  , 'the refused load belongs to the C++ backend and needs its compiler'
  )
class TestRefusedLoad(cytest.TestCase):
  '''
  A second object of a loaded module name is refused before it is opened,
  and the module runs on (issue #109).  The loader opened the second library
  before it compared the registered file: the dynamic linker bound the
  symbols of the second library to the tables of the first, the initializers
  of the second wrote those tables, and the refusal dropped the second
  library, so the tables pointed into unmapped memory and the next use of
  the module ended the process (the sequences D, I and J of the API study;
  exit status 139).  Each sequence runs in a child process, so that a
  regression ends the child and not the test runner.  The two objects of
  the module are compiled with sprite-make, once for the class.  The child
  runs under interpret:tiered whatever the mode of the runner, since a load
  needs the compiled object of the Prelude (under 'all' it runs
  interpreted, and the nightly job of 2026-10-09 failed these four cases
  that way).
  '''
  SOURCE = 'module M where\n\nf :: Int -> Int\nf x = x + 1\n\nmain :: Int\nmain = f 41\n'
  CODE = r'''
import os, sys
# The child runs under tiered execution whatever the runner's mode: a load
# needs the object of the Prelude, which runs interpreted under 'all'.
os.environ['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx,interpret:tiered'
import curry
from curry.backends.cxx import curryrtbindings as curryrt
soA, soB, case = %(soA)r, %(soB)r, %(case)r
curry.path.insert(0, %(dirA)r)
def main():
  return [str(v) for v in curry.eval(curry.modules['M'].main)]
def refused():
  try:
    curry._interpreter_.load(soB)
  except curry.exceptions.LoadError as exc:
    assert 'already loaded from' in str(exc), exc
    print('refused')
  else:
    print('not refused')
if case == 'D':
  curry._interpreter_.load(soA); refused(); print(main())
elif case == 'I':
  curry.import_('M'); curry._interpreter_.load(soA); refused(); curry.reset()
  curry._interpreter_.load(soA); print(main())
elif case == 'J':
  curry.import_('M'); refused(); curry.reset(); curry._interpreter_.load(soA); print(main())
elif case == 'K':
  curry._interpreter_.load(soA); curry._interpreter_.load(soA); print(main())
registered = curryrt.SharedCurryModule.find_sofilename('M')
print(os.path.realpath(registered) == os.path.realpath(soA))
print('exiting normally')
'''

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    cls.tmpdir = tempfile.mkdtemp(prefix='sprite-loadsave-refused-')
    cls.objects = {}
    for sub in 'A', 'B':
      directory = os.path.join(cls.tmpdir, sub)
      os.mkdir(directory)
      with open(os.path.join(directory, 'M.curry'), 'w') as stream:
        stream.write(cls.SOURCE)
      env = dict(os.environ, CURRYPATH=directory)
      env['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx,interpret:tiered'
      cmd = cytest.limit_prefix(ADDRESS_SPACE, TIMEOUT) + [
          config.installed_path('bin', 'sprite-make'), '--so', '-z', 'M'
        ]
      proc = subprocess.run(
          cmd, cwd=directory, env=env, capture_output=True, text=True
        )
      if proc.returncode != 0:
        raise RuntimeError(
            'sprite-make failed in %s:\n%s%s'
            % (directory, proc.stdout, proc.stderr)
          )
      cls.objects[sub] = os.path.join(
          directory, '.curry', config.intermediate_subdir(), 'M.so'
        )

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.tmpdir, ignore_errors=True)
    super().tearDownClass()

  def run_case(self, case):
    code = self.CODE % dict(
        soA=self.objects['A'], soB=self.objects['B'], case=case
      , dirA=os.path.join(self.tmpdir, 'A')
      )
    proc = cytest.run_in_subprocess(code, TIMEOUT, address_space=ADDRESS_SPACE)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    expected = ["['42']", 'True', 'exiting normally']
    if case != 'K':
      expected.insert(0, 'refused')
    self.assertEqual(proc.stdout.splitlines(), expected, proc.stderr)

  def test_refused_then_used(self):
    # Case D: load, the refused load of the copy, then a use.
    self.run_case('D')

  def test_refused_after_an_import_then_reset(self):
    # Case I: import, load, the refused load, a reset, a load, then a use.
    self.run_case('I')

  def test_refused_on_an_imported_module_then_reset(self):
    # Case J: import, the refused load, a reset, a load, then a use.
    self.run_case('J')

  def test_loaded_twice_then_used(self):
    # Case K: the same file loaded twice (no refusal), then a use.
    self.run_case('K')


@unittest.skipUnless(
    config.cxx_tool() is not None
  , 'the saved text of a module loaded from its object belongs to the C++ '
    'backend and needs its compiler'
  )
class TestSaveFromObject(cytest.TestCase):
  '''
  curry.save of a module that runs from its compiled object writes the text
  it writes for the same module interpreted (issue #113).  The compiler
  took every static info table for a built-in of the runtime, and the
  tables of a module loaded from its object are static, so the saved module
  had an extern declaration per function and no step function (3,763
  characters against 30,399 for the module of the issue).  The ICurry read
  back from the JSON file is taken through the steps of an import as well
  (the merge of the built-ins, the passes of the optimizer, with the
  complete module standing in for the loaded one), so the metadata of the
  record agrees too.  Two children save the same module: the first before
  any object exists, under interpret:new, where the module is interpreted
  and never compiled; sprite-make --so then compiles the object; the second,
  under the default interpret:tiered, loads the object.  The texts must
  agree.
  '''
  SOURCE = (
      'module SaveFromObject where\n\n'
      'data Color = Red | Green | Blue\n  deriving (Eq, Show)\n\n'
      'next :: Color -> Color\nnext Red = Green\nnext Green = Blue\n'
      'next Blue = Red\n\n'
      'twice :: (a -> a) -> a -> a\ntwice f x = f (f x)\n\n'
      'count :: Int -> Int\n'
      'count n = if n <= 0 then 0 else 1 + count (n - 1)\n\n'
      'main :: Color\nmain = twice next Red\n'
    )
  CODE = r'''
import os, re
os.environ['SPRITE_INTERPRETER_FLAGS'] = %(flags)r
import curry
from curry.objects.handle import getHandle
curry.path.insert(0, %(tmpdir)r)
M = curry.import_('SaveFromObject')
print('object', getHandle(M).sofilename is not None)
text = curry._interpreter_.save(M, module_main=False)
print('steps', len(re.findall(r'^tag_type Cy', text, re.M)))
with open(%(out)r, 'w', encoding='utf-8') as stream:
  stream.write(text)
print('values', [str(v) for v in curry.eval(M.main)])
'''

  def save_in_child(self, flags, tmpdir, out):
    code = self.CODE % dict(flags=flags, tmpdir=tmpdir, out=out)
    proc = cytest.run_in_subprocess(code, TIMEOUT, address_space=ADDRESS_SPACE)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    with open(out, encoding='utf-8') as stream:
      return proc.stdout.splitlines(), stream.read()

  def test_same_text_from_the_object(self):
    tmpdir = tempfile.mkdtemp(prefix='sprite-loadsave-object-')
    self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
    with open(os.path.join(tmpdir, 'SaveFromObject.curry'), 'w') as stream:
      stream.write(self.SOURCE)
    lines, before = self.save_in_child(
        'backend:cxx,interpret:new', tmpdir, os.path.join(tmpdir, 'before.cpp')
      )
    self.assertEqual(lines[0], 'object False')
    self.assertEqual(lines[2], "values ['Blue']")
    nsteps = int(lines[1].split()[1])
    self.assertGreater(nsteps, 0)
    # The object, as sprite-make --so writes it beside the source.
    env = dict(os.environ, CURRYPATH=tmpdir)
    env['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx,interpret:tiered'
    cmd = cytest.limit_prefix(ADDRESS_SPACE, TIMEOUT) + [
        config.installed_path('bin', 'sprite-make'), '--so', '-z'
      , 'SaveFromObject'
      ]
    proc = subprocess.run(
        cmd, cwd=tmpdir, env=env, capture_output=True, text=True
      )
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    lines, after = self.save_in_child(
        'backend:cxx,interpret:tiered', tmpdir
      , os.path.join(tmpdir, 'after.cpp')
      )

    self.assertEqual(lines[0], 'object True')
    self.assertEqual(lines[1], 'steps %d' % nsteps)
    self.assertEqual(lines[2], "values ['Blue']")
    self.assertEqual(after, before)


class TestSavedProgram(cytest.TestCase):
  '''
  A program saved with a goal (curry._interpreter_.save(M, file, goal='main')) names no
  program interpreter.  The C++ text of a program carried an .interp
  section with the dynamic loader of the build machine
  (config.ld_interpreter_path), which nothing read: the objects are loaded
  by the runtime, never run by the dynamic loader (pothole batch 4,
  2026-10-10).  The saved program still runs: on the C++ backend compiled
  by the step of the toolchain and loaded with curry.load after a reset, as
  TestRoundTrip loads a module.
  '''
  CODE = r'''
import os, subprocess, sys, tempfile
os.environ['SPRITE_INTERPRETER_FLAGS'] = %(flags)r
import cytest, curry
from curry import config
tmpdir = tempfile.mkdtemp(prefix='sprite-savedprog-')
with open(os.path.join(tmpdir, 'SavedProgram.curry'), 'w') as stream:
  stream.write('double :: Int -> Int\ndouble x = x + x\n\nmain :: Int\nmain = double 21\n')
curry.path.insert(0, tmpdir)
M = curry.import_('SavedProgram')
text = curry._interpreter_.save(M, None, goal='main')
print('.interp' in text, 'my_interp' in text, 'ld-linux' in text)
cppfile = os.path.join(
    tmpdir, '.curry', config.intermediate_subdir(), 'SavedProgram.cpp'
  )
curry._interpreter_.save(M, cppfile, goal='main')
from curry.backends.cxx import toolchain
saved = toolchain.Cpp2So(cytest.raw.interp())(cppfile, curry.path)
curry.reset()
M2 = curry._interpreter_.load(saved)
print([str(v) for v in curry.eval(M2.main)])
'''

  @unittest.skipIf(
      config.cxx_tool() is None
    , 'the shared object needs the C++ compiler of the installation'
    )
  def test_saved_program_runs_without_an_interpreter_line(self):
    flags = 'backend:cxx,interpret:new'
    proc = cytest.run_in_subprocess(self.CODE % {'flags': flags}, TIMEOUT)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    lines = proc.stdout.splitlines()
    self.assertEqual(lines[0], 'False False False', proc.stderr)
    self.assertEqual(lines[1:], ["['42']"], proc.stderr)


class TestPublicObjects(cytest.TestCase):
  @cytest.skipUnlessObjectsLoad('curry.load opens a compiled object')
  def test_loaded_object_keeps_its_typed_interface(self):
    module = curry.compile('f :: Int -> Int\nf x = x + 1', name='SavedTyped')
    with tempfile.TemporaryDirectory() as work:
      suffix = '.so'
      product = os.path.join(work, 'SavedTyped' + suffix)
      curry.save(module, product)
      curry.reset()
      loaded = curry.load(product)
      self.assertEqual(curry.eval(loaded.f(41)).one(), 42)
      self.assertEqual(curry.typeof(loaded.f), 'Int -> Int')
      backend = curry._interpreter_.backend
      with mock.patch.object(type(backend), 'load_module',
                             side_effect=AssertionError('backend called')), \
           mock.patch('builtins.open', side_effect=AssertionError('object read')):
        self.assertIs(curry.load(product), loaded)
      from curry.lib import SavedTyped
      self.assertIs(SavedTyped, loaded)

  @cytest.skipUnlessObjectsLoad('a saved program loads its object')
  def test_saved_constrained_program_prints_the_defaulted_goal(self):
    module = curry.compile('main = Just 5', name='SavedConstrained')
    with tempfile.TemporaryDirectory() as work:
      program = os.path.join(work, 'saved.exe')
      curry.save(module, program, main=module.main)
      run = subprocess.run([program], check=True, capture_output=True, text=True)
      self.assertEqual(run.stdout, 'Just 5\n')
