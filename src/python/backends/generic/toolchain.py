from ...toolchain import _filenames, _findcurry, _loadcurry, _system
from ...utility import binding

class Json2TargetSource(object):
  def __init__(self, interp):
    self.interp = interp

  def __repr__(self):
    return self.NAME

  @_system.updateCheck
  def __call__(self, file_in, currypath, **ignored):
    icurry = _loadcurry.loadjson(file_in)
    # A module inside a package needs the package imported first.  An import
    # by name does this through the name prefixes; an import of the ICurry
    # object does not.  So sprite-make --py Data.Maybe failed with KeyError.
    packagename, _, _ = icurry.fullname.rpartition('.')
    if packagename:
      self.interp.import_(packagename, currypath=currypath)
    # The module is imported only to bootstrap the call to 'save'.  Remove it
    # when done so that a subsequent step can import the real module produced.
    assert icurry.fullname not in self.interp.modules
    with binding.binding(self.interp.modules, icurry.fullname, binding.del_):
      # The imports of a program given as a file are searched on the path
      # of the step, which names its directory first; those of a module
      # given by name on the path of the interpreter, as before.
      module = self.interp.import_(
          icurry, currypath=_findcurry.imports_path(currypath, **ignored)
        )
      file_out = _filenames.replacesuffix(file_in, self.SUFFIX)
      _system.makeOutputDir(file_out)
      self.interp.save(module, file_out, module_main=False)
    assert icurry.fullname not in self.interp.modules
    return file_out

