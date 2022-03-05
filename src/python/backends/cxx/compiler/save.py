from ...generic.compiler import render, save, statics
from .... import config

class PackageCreator(save.PackageCreator):
  FILES = '__init__.py', '_symbols_.cpp', '_link_.py'

  def generate__init__(self):
    return ModuleInterfaceGenerator(self.ir, self.defaultgoal).render()

  def generate_symbols_(self):
    return SymbolsGenerator(self.ir).render()

  def generate_link_(self):
    return LinkGenerator(self.ir).render()


class SymbolsGenerator(save.FileGenerator):
  RENDERER = render.CXX_RENDERER
  SECTIONS = 'body',

  def __init__(self, ir):
    self.ir = ir

  def body(self):
    for line in self.ir.lines:
      yield line


class LinkGenerator(save.FileGenerator):
  RENDERER = render.PY_RENDERER
  SECTIONS = 'imports', 'body'

  def __init__(self, ir):
    self.ir = ir

  def imports(self):
    yield 'from . import _symbols_'

  def body(self):
    return save.generateLinkSection(self.ir, self.RENDERER, prefix='_symbols_.')


class ModuleInterfaceGenerator(save.ModuleInterfaceGenerator):
  def symbolDefs(self):
    yield '# Symbol Definitions'
    yield '# ------------------'
    yield 'from ._symbols_ import *'

  def link(self):
    yield '# Linking'
    yield '# -------'
    yield 'from . import _link_'


def save_module(ir, filename, goal=None):
  creator = PackageCreator(ir, filename, goal)
  creator.createPackage()

