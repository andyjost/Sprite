import cytest # from ./lib; must be first

import curry, logging, os
from curry.utility import _tempfile
from cytest.logging import capture_log


class LoadSaveTestCase(cytest.TestCase):
  def check(self, modulename, has_externs):
    with _tempfile.TemporaryDirectory() as tmpdir:
      Module = curry.import_(modulename)

      # Save the module.
      filename = os.path.join(tmpdir, 'Module.py')
      with capture_log('curry.backends.py.compiler.compiler.function') as log:
        curry.save(Module, filename)

      # Ensure warnings were issued (only) for external functions.
      has_warnings = bool(log.data[logging.WARNING])
      self.assertEqual(has_externs, has_warnings)

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
