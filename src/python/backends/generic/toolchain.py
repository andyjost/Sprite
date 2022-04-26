from ...toolchain import _filenames, _loadcurry, _system
from ...utility import binding

class Json2TargetSource(object):
  def __init__(self, interp):
    self.interp = interp

  def __repr__(self):
    return self.NAME

  @_system.updateCheck
  def __call__(self, file_in, currypath, **ignored):
    icurry = _loadcurry.loadjson(file_in)
    # The module is imported only to bootstrap the call to 'save'.  Remove it
    # when done so that a subsequent step can import the real module produced.
    assert icurry.fullname not in self.interp.modules
    with binding.binding(self.interp.modules, icurry.fullname, binding.del_):
      module = self.interp.import_(icurry)
      file_out = _filenames.replacesuffix(file_in, self.SUFFIX)
      _system.makeOutputDir(file_out)
      self.interp.save(module, file_out, module_main=False)
    assert icurry.fullname not in self.interp.modules
    return file_out

