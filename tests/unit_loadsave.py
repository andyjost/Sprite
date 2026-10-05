import cytest # from ./lib; must be first

import curry, logging, os, unittest
import tempfile
from cytest.logging import capture_log

@unittest.skipIf(curry.flags['backend'] == 'cxx', 'Skip offline compile.')
class LoadSaveTestCase(cytest.TestCase):
  def check(self, modulename, has_externs):
    with tempfile.TemporaryDirectory() as tmpdir:
      Module = curry.import_(modulename)

      # Save the module as a library: no goal, so no main program.
      filename = os.path.join(tmpdir, 'Module.py')
      curry.save(Module, filename, module_main=False)

      # Load the module.
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
        lambda self, modulename=name, has_externs=ext: self.check(modulename, has_externs)

