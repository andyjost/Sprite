
__all__ = ['compile', 'write_module']

def compile(interp, imodule, extern=None):
  compileM = PyCompiler(interp, imodule, extern)
  return compileM.compile()

class PyCompiler(object):
  @formatDocstring(config.python_package_name())
  def __init__(self, interp, imodule, extern=None):
    '''
    Compiles ICurry to a C++ target object.

    Args:
      interp:
        The interpreter that owns this module.

      imodule:
        The IModule object representing the module to compile.

      extern:
        An instance of ``{0}.icurry.IModule`` used to resolve external
        declarations.
    '''
    self.interp = interp
    self.imodule = imodule
    self.extern = extern
    self.target_object = TargetObject('Python', imodule.fullname)

  @property
  def symtab(self):
    return self.target_object.symtab
