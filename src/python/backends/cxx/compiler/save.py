from ...generic.compiler import render, save, statics
from .... import common, config
from ....utility import strings
import json

class PackageCreator(save.PackageCreator):
  FILES = '__init__.py', '_symbols_.cpp', 'make.sh'

  @property
  def generate__init__(self):
    return ModuleInterfaceGenerator(self.target_object, self.defaultgoal)

  @property
  def generatemake(self):
    return MakescriptGenerator()

  @property
  def generate_symbols_(self):
    return SymbolsGenerator(self.target_object)


class SymbolsGenerator(save.FileGenerator):
  RENDERER = render.CXX_RENDERER
  SECTIONS = 'header', 'declarations', 'stepfuncs', 'infotables', 'typedefs', 'footer'

  def __init__(self, target_object):
    self.target_object = target_object
    self.path = target_object.imodule_linked.splitname()

  def header(self):
    yield '#include "cyrt/cyrt.hpp"'
    yield ''
    yield 'using namespace cyrt;'
    yield ' '.join(
        'namespace %s {' % part for part in ['curry', 'lib'] + self.path
      )

  def _datatype(self, values):
    if len(values) == 0 or isinstance(values[0], int):
      return 'unboxed_int_type';
    elif isinstance(values[0], float):
      return 'unboxed_float_type';
    elif isinstance(values[0], str):
      return 'unboxed_char_type';
    assert False

  def declarations(self):
    items = self.ir.closure.dict.items()
    for name, value in sorted(items, key=statics.sortkey):
      if name.startswith(statics.PX_DATA):
        yield 'static %s constexpr %s[] = {%s};' % (
            self._datatype(value), name, ', '.join(map(str, value))
          )
      elif name.startswith(statics.PX_INFO):
        yield 'extern InfoTable const %s;' % name
      elif name.startswith(statics.PX_STR):
        string_data = strings.ensure_str(value)
        yield 'static char const * %s = %s;' % (name, _dquote(value))
      elif name.startswith(statics.PX_TYPE):
        yield 'extern Type const %s;' % name

  def stepfuncs(self):
    for line in self.ir.lines:
      yield line

  def infotables(self):
    items = self.ir.closure.dict.items()
    for name, value in sorted(items, key=statics.sortkey):
      if name.startswith(statics.PX_INFO):
        arity = value.info.arity
        if value.info.tag == common.T_FUNC:
          tag = 'T_FUNC'
          try:
            step = self.ir.closure.data[statics.PX_SYMB, value.fullname]
          except:
            print('skipping %s' % value.fullname)
            continue
          ty = 'nullptr'
        else:
          assert value.info.tag >= common.T_CTOR
          tag = 'T_CTOR + %s' % value.info.tag
          step = 'nullptr'
          try:
            ty = '&%s' % self.ir.closure.data[statics.PX_TYPE, value.typedef]
          except:
            print('skipping %s' % value.fullname)
            continue
        alloc_size = 'sizeof(Head) + sizeof(Arg[%s])' % arity
        flags = 'F_STATIC_OBJECT%s' % (
            ' | %s' % value.info.flags if value.info.flags else ''
            )
        yield 'InfoTable const %s{'     % name
        yield '    /*tag*/        %s'   % tag
        yield '  , /*arity*/      %s'   % arity
        yield '  , /*alloc_size*/ %s'   % alloc_size
        yield '  , /*flags*/      %s'   % flags
        yield '  , /*name*/       %s'   % _dquote(value.name)
        yield '  , /*format*/     "%s"' % ('p' * arity)
        yield '  , /*step*/       %s'   % step
        yield '  , /*typecheck*/  %s'   % 'nullptr'
        yield '  , /*type*/       %s'   % ty
        yield '  };'
        yield ''

  def typedefs(self):
    types = dict(self.ir.closure.typedefs())
    for name, ty in sorted(
        self.ir.closure.typedefs()
      , key=lambda item: item[1].fullname
      ):
      ctable_name = '__%s_Ctors' % name
      ctors = (
          '&%s' % self.ir.closure.nodeinfo(ctor)
              for ctor in ty.constructors
        )
      yield 'static InfoTable const * %s[] = { %s };' % (
          ctable_name, ', '.join(ctors)
        )
      yield "Type const %s { %s, %s, 't', F_STATIC_OBJECT };" % (
          name, ctable_name, len(ty.constructors)
        )
      yield ''

  def footer(self):
    yield '}' * (len(self.path) + 2)


class MakescriptGenerator(save.FileGenerator):
  RENDERER = render.SH_RENDERER
  SECTIONS = 'shebang', 'body'
  PERMISSIONS = int('755', 8)

  def shebang(self):
    yield '#!/bin/sh'

  def body(self):
    cxx = config.cxx_compiler()
    cxxflags = config.cxx_flags()
    include = config.installed_path('include')
    yield '%s %s -I%s _symbols_.cpp -o _symbols_.so' % (cxx, cxxflags, include)


# class LinkGenerator(save.FileGenerator):
#   RENDERER = render.PY_RENDERER
#   SECTIONS = 'imports', 'body'
#
#   def __init__(self, ir):
#     self.ir = ir
#
#   def imports(self):
#     yield 'from . import _symbols_'
#
#   def body(self):
#     return save.generateLinkSection(self.ir, self.RENDERER, prefix='_symbols_.')


class ModuleInterfaceGenerator(save.ModuleInterfaceGenerator):
  def symbolDefs(self):
    yield '# Symbol Definitions'
    yield '# ------------------'
    yield 'from ._symbols_ import *'

  def link(self):
    yield '# Linking'
    yield '# -------'
    yield '# from . import _link_'


def generate_module(ir, filename, goal=None):
  creator = PackageCreator(ir, filename, goal)
  creator.createPackage()

def _dquote(string):
  # Note: Use JSON to get double-quote-style escaping.
  string_data = strings.ensure_str(string)
  return json.dumps(string_data)
