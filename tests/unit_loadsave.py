'''
curry.save and curry.load.  On the Python backend the saved form of a module
is a Python file, which curry.load reads back; the four library modules of
LoadSaveTestCase make that round trip.  On the C++ backend curry.save writes
C++ source and curry.load reads a shared object, so the same round trip does
not exist: those tests are known failures there (issue #82, stage 5: a C++
form of curry.save is an open decision).  TestRoundTrip pins what does work
on each backend: a module that no loaded library provides is saved, compiled
into the object of the backend where one is needed, and loaded back.
'''
import cytest # from ./lib; must be first

from curry import config
import curry, logging, os, shutil, subprocess, unittest
import tempfile
from cytest.logging import capture_log

IS_CXX = curry.flags['backend'] == 'cxx'
TIMEOUT = 300
# The cap on the address space of a child, in bytes.
ADDRESS_SPACE = 2 << 30

NO_ROUND_TRIP = (
    'curry.save writes C++ source on the C++ backend and curry.load reads a '
    'shared object; the round trip exists on the Python backend alone '
    '(issue #82, stage 5)'
  )

class LoadSaveTestCase(cytest.TestCase):
  def check(self, modulename, has_externs):
    with tempfile.TemporaryDirectory() as tmpdir:
      Module = curry.import_(modulename)

      # Save the module as a library: no goal, so no main program.  The file
      # takes the suffix of the form the backend writes.
      filename = os.path.join(tmpdir, 'Module' + ('.cpp' if IS_CXX else '.py'))
      curry.save(Module, filename, module_main=False)

      # Load the module.  The C++ backend refuses the file: it loads a .so.
      Module2 = curry.load(filename)

      # They should compare equal.
      self.assertEqual(Module, Module2)

  for name, ext in [
      ('Control.SetFunctions', True)
    , ('Data.Either'         , False)
    , ('Data.List'           , False)
    , ('Prelude'             , True)
    ]:
    locals()['test_' + name.replace('.', '')] = \
        cytest.expectedFailureIf(IS_CXX, NO_ROUND_TRIP)(
            lambda self, modulename=name, has_externs=ext:
                self.check(modulename, has_externs)
          )


class TestRoundTrip(cytest.TestCase):
  '''
  The round trip of each backend, in a child process.  A module of its own
  is saved without a main program and loaded with curry.load, in the session
  that saved it and again after a reset.  On the Python backend the saved
  file is the Python form.  On the C++ backend the C++ source that
  curry.save writes is compiled into a shared object by the step of the
  toolchain that sprite-make --so runs (backends.cxx.toolchain.Cpp2So), and
  curry.load reads the object.  The child runs under interpret:new on the
  C++ backend: the fresh module stays interpreted and no object of it is
  loaded before curry.load, because the runtime keeps one library per
  module name for the life of the process and refuses a second file of a
  loaded module (the library modules of LoadSaveTestCase are such modules).
  '''
  CODE = r'''
import os, sys, tempfile
os.environ['SPRITE_INTERPRETER_FLAGS'] = %(flags)r
import curry
tmpdir = tempfile.mkdtemp(prefix='sprite-loadsave-')
with open(os.path.join(tmpdir, 'SaveLoadFresh.curry'), 'w') as stream:
  stream.write('double :: Int -> Int\ndouble x = x + x\n\nmain :: Int\nmain = double 21\n')
curry.path.insert(0, tmpdir)
M = curry.import_('SaveLoadFresh')
if curry.flags['backend'] == 'cxx':
  # The step reads the generated file under the product directory of the
  # source, where the import wrote the ICurry and the JSON of the module.
  from curry import config
  from curry.backends.cxx import toolchain
  cppfile = os.path.join(
      tmpdir, '.curry', config.intermediate_subdir(), 'SaveLoadFresh.cpp'
    )
  curry.save(M, cppfile, module_main=False)
  saved = toolchain.Cpp2So(curry.getInterpreter())(cppfile, curry.path)
else:
  saved = os.path.join(tmpdir, 'SaveLoadFresh.py')
  curry.save(M, saved, module_main=False)
print(os.path.splitext(saved)[1])
M2 = curry.load(saved)
print(M2 is M, [str(v) for v in curry.eval(M2.main)])
curry.reset()
M3 = curry.load(saved)
print('SaveLoadFresh' in curry.modules, [str(v) for v in curry.eval(M3.main)])
'''

  @unittest.skipIf(
      IS_CXX and config.cxx_tool() is None
    , 'the shared object needs the C++ compiler of the installation'
    )
  def test_round_trip(self):
    flags = 'backend:cxx,interpret:new' if IS_CXX else 'backend:py'
    proc = cytest.run_in_subprocess(self.CODE % {'flags': flags}, TIMEOUT)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(
        proc.stdout.splitlines()
      , ['.so' if IS_CXX else '.py', "True ['42']", "True ['42']"]
      , proc.stderr
      )


@unittest.skipUnless(
    IS_CXX and config.cxx_tool() is not None
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
  CODE = r"""
import os, sys
# The child runs under tiered execution whatever the runner's mode: a load
# needs the object of the Prelude, which runs interpreted under 'all'.
os.environ['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx,interpret:tiered'
import curry
from curry.backends.cxx import cyrtbindings as cyrt
soA, soB, case = %(soA)r, %(soB)r, %(case)r
curry.path.insert(0, %(dirA)r)
def main():
  return [str(v) for v in curry.eval(curry.modules['M'].main)]
def refused():
  try:
    curry.load(soB)
  except curry.exceptions.DynloadError as exc:
    assert 'already loaded from' in str(exc), exc
    print('refused')
  else:
    print('not refused')
if case == 'D':
  curry.load(soA); refused(); print(main())
elif case == 'I':
  curry.import_('M'); curry.load(soA); refused(); curry.reset()
  curry.load(soA); print(main())
elif case == 'J':
  curry.import_('M'); refused(); curry.reset(); curry.load(soA); print(main())
elif case == 'K':
  curry.load(soA); curry.load(soA); print(main())
registered = cyrt.SharedCurryModule.find_sofilename('M')
print(os.path.realpath(registered) == os.path.realpath(soA))
print('exiting normally')
"""

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
      cmd = [
          'prlimit', '--as=%d' % ADDRESS_SPACE, 'timeout', str(TIMEOUT)
        , config.installed_path('bin', 'sprite-make'), '--so', '-z', 'M'
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
    IS_CXX and config.cxx_tool() is not None
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
  CODE = r"""
import os, re
os.environ['SPRITE_INTERPRETER_FLAGS'] = %(flags)r
import curry
from curry.objects.handle import getHandle
curry.path.insert(0, %(tmpdir)r)
M = curry.import_('SaveFromObject')
print('object', getHandle(M).sofilename is not None)
text = curry.save(M, module_main=False)
print('steps', len(re.findall(r'^tag_type Cy', text, re.M)))
with open(%(out)r, 'w', encoding='utf-8') as stream:
  stream.write(text)
print('values', [str(v) for v in curry.eval(M.main)])
"""

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
    cmd = [
        'prlimit', '--as=%d' % ADDRESS_SPACE, 'timeout', str(TIMEOUT)
      , config.installed_path('bin', 'sprite-make'), '--so', '-z'
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
  A program saved with a goal (curry.save(M, file, goal='main')) names no
  program interpreter.  The C++ text of a program carried an .interp
  section with the dynamic loader of the build machine
  (config.ld_interpreter_path), which nothing read: the objects are loaded
  by the runtime, never run by the dynamic loader (pothole batch 4,
  2026-10-10).  The saved program still runs: on the C++ backend compiled
  by the step of the toolchain and loaded with curry.load after a reset, as
  TestRoundTrip loads a module; on the Python backend as a script.
  '''
  CODE = r'''
import os, subprocess, sys, tempfile
os.environ['SPRITE_INTERPRETER_FLAGS'] = %(flags)r
import curry
from curry import config
tmpdir = tempfile.mkdtemp(prefix='sprite-savedprog-')
with open(os.path.join(tmpdir, 'SavedProgram.curry'), 'w') as stream:
  stream.write('double :: Int -> Int\ndouble x = x + x\n\nmain :: Int\nmain = double 21\n')
curry.path.insert(0, tmpdir)
M = curry.import_('SavedProgram')
text = curry.save(M, None, goal='main')
print('.interp' in text, 'my_interp' in text, 'ld-linux' in text)
if curry.flags['backend'] == 'cxx':
  cppfile = os.path.join(
      tmpdir, '.curry', config.intermediate_subdir(), 'SavedProgram.cpp'
    )
  curry.save(M, cppfile, goal='main')
  from curry.backends.cxx import toolchain
  saved = toolchain.Cpp2So(curry.getInterpreter())(cppfile, curry.path)
  curry.reset()
  M2 = curry.load(saved)
  print([str(v) for v in curry.eval(M2.main)])
else:
  saved = os.path.join(tmpdir, 'SavedProgram.py')
  curry.save(M, saved, goal='main')
  proc = subprocess.run(
      [sys.executable, saved], capture_output=True, text=True
    )
  print(proc.returncode, proc.stdout.split(), bool(proc.stderr.strip()))
'''

  @unittest.skipIf(
      IS_CXX and config.cxx_tool() is None
    , 'the shared object needs the C++ compiler of the installation'
    )
  def test_saved_program_runs_without_an_interpreter_line(self):
    flags = 'backend:cxx,interpret:new' if IS_CXX else 'backend:py'
    proc = cytest.run_in_subprocess(self.CODE % {'flags': flags}, TIMEOUT)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    lines = proc.stdout.splitlines()
    self.assertEqual(lines[0], 'False False False', proc.stderr)
    if IS_CXX:
      self.assertEqual(lines[1:], ["['42']"], proc.stderr)
    else:
      self.assertEqual(lines[1:], ["0 ['42'] False"], proc.stderr)
