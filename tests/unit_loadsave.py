import cytest # from ./lib; must be first

import curry, logging, os, unittest
from curry.utility import _tempfile
from cytest.logging import capture_log

@unittest.skipIf(curry.flags['backend'] == 'cxx', 'Skip offline compile.')
class LoadSaveTestCase(cytest.TestCase):
  def check(self, modulename, has_externs):
    with _tempfile.TemporaryDirectory() as tmpdir:
      Module = curry.import_(modulename)

      # Save the module.
      filename = os.path.join(tmpdir, 'Module.py')
      curry.save(Module, filename)

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

