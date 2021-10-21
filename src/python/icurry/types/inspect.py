
def isa_module(iobj):
  from . import imodule
  return isinstance(iobj, imodule.IModule)

def isa_package(iobj):
  from . import ipackage
  return isinstance(iobj, ipackage.IPackage)

def isa_module_or_package(iobj):
  from . import imodule, ipackage
  return isinstance(iobj, (imodule.IModule, ipackage.IPackage))
