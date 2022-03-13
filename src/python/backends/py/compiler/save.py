from ...generic.compiler import save, statics
from .... import config

class PackageCreator(save.PackageCreator):
  @property
  def generate__init__(self):
    return ModuleInterfaceGenerator(self.ir, self.defaultgoal)


class ModuleInterfaceGenerator(save.ModuleInterfaceGenerator):
  def symbolDefs(self):
    yield '# Symbol Definitions'
    yield '# ------------------'
    for line in self.ir.lines:
      yield line

def generate_module(ir, filename, goal=None):
  creator = PackageCreator(ir, filename, goal)
  creator.createPackage()

