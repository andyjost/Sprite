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
import curry, logging, os, unittest
import tempfile
from cytest.logging import capture_log

IS_CXX = curry.flags['backend'] == 'cxx'
TIMEOUT = 300

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
