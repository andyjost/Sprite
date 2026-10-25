from ...toolchain import _filenames, _findcurry, _loadcurry, _system, _productlock
from ... import cache
from ...objects import CurryPackage
from ...utility import binding, filesys

class Json2TargetSource(object):
  manages_product_lock = True
  def __init__(self, interp):
    self.interp = interp

  def __repr__(self):
    return self.NAME

  @_system.updateCheck
  def __call__(self, file_in, currypath, **ignored):
    icurry = _loadcurry.loadjson(file_in)
    _findcurry.reject_library_shadow(icurry.fullname, icurry.filename, self.interp)
    # Dependencies are real imports. Only the bootstrap module stays in a
    # private registry; dropping its imports would lose source-relative scope.
    imports = _findcurry.imports_path(currypath, **ignored)
    self.interp.import_(icurry.imports,
        currypath=_findcurry.import_path(self.interp, imports))
    with self.interp._private_modules():
      return self._generate(file_in, currypath, **ignored)

  def _generate(self, file_in, currypath, **ignored):
    icurry = _loadcurry.loadjson(file_in)
    # The importer creates parent namespaces without loading their modules:
    # a parent module may itself import this child (issue #168).
    # The module is imported only to bootstrap the call to 'save'.  Remove it
    # when done so that a subsequent step can import the real module produced.
    assert icurry.fullname not in self.interp.modules or isinstance(
        self.interp.modules[icurry.fullname], CurryPackage)
    with binding.binding(self.interp.modules, icurry.fullname, binding.del_):
      # The imports of a program given as a file are searched on the path
      # of the step, which names its directory first; those of a module
      # given by name on the path of the interpreter, as before.
      module = self.interp.import_(
          icurry, currypath=_findcurry.imports_path(currypath, **ignored)
        )
      file_out = _filenames.replacesuffix(file_in, self.SUFFIX)
      _system.makeOutputDir(file_out)
      text = self.interp.save(module, None, module_main=False)
    # Rendering/importing can enter the heap. Only publication holds the lock.
    with _productlock.locked(file_out):
      try:
        with open(file_out, encoding='utf-8') as stream:
          current = stream.read()
      except OSError:
        current = None
      if current != text or filesys.newer(file_in, file_out):
        cache.write_file(file_out, text)
    assert icurry.fullname not in self.interp.modules or isinstance(
        self.interp.modules[icurry.fullname], CurryPackage)
    return file_out

