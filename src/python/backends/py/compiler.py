from .currylib.prelude.math import apply_unboxed
from ...exceptions import CompileError
from ..generic import compiler, renderer
from ... import config, icurry
from ...utility.showflags import showflags
import collections, itertools, json, re, six, sys

__all__ = ['compile', 'write_module']

def compile(interp, iobj):
  compileM = PyCompiler(interp, iobj)
  return compileM.compile()

class PyCompiler(compiler.CompilerBase):
  CODE_TYPE = 'Python'
  SYNTH_TAGS = 'py.boxedfunc', 'py.rawfunc', 'py.unboxedfunc'
  EXCLUDED_METADATA = set(SYNTH_TAGS + ('py.material',))

  def __init__(self, interp, iobj):
    compiler.CompilerBase.__init__(self, interp, iobj)
    self.counts = collections.defaultdict(itertools.count)

  def vIsBuiltin(self, iobj):
    return False

  def vIsSynthesized(self, ifun):
    return any(md in ifun.metadata for md in self.SYNTH_TAGS)

  def vBackendFunctionKey(self, func):
    return hex(id(func))

  def vEmitHeader(self):
    curry = config.python_package_name()
    yield 'import %s' % curry
    yield 'from %s.common import *' % curry
    yield 'from %s.backends.py.graph import DataType, InfoTable' % curry
    if self.root_isa_module:
      yield 'from %s.icurry import IModule, PUBLIC, PRIVATE' % curry
      yield "if 'interp' not in globals():"
      yield "  interp = %s.getInterpreter()" % curry

  def vEmitFooter(self):
    return []

  def vEmitImported(self, modulename):
    yield 'interp.import_(%r)' % modulename

  def vEmitStepfuncLink(self, ifun, h_stepfunc):
    return []

  def vEmitInfotabLink(self, isym, h_info):
    if self.isExternal(isym):
      yield '%s = interp.symbol(%r).info' % (h_info, isym.fullname)

  def vEmitDataTypeLink(self, itype, h_datatype):
    if self.isExternal(itype):
      yield '%s = interp.type(%r).datatype' % (h_datatype, itype.fullname)

  def vEmitStepfuncHeader(self, ifun, h_stepfunc):
    yield 'def %s(rts, _0):' % h_stepfunc, ifun.fullname

  def vEmitStepfuncEntry(self):
    return []

  def vEmitImportBackendFunction(self, func, h_func):
    yield 'from %s import %s as %s' % (func.__module__, func.__name__, h_func)

  def vEmitSynthesizedStepfunc(self, ibuiltin, h_stepfunc):
    if 'py.boxedfunc' in ibuiltin.metadata:
      boxedfunc = ibuiltin.metadata['py.boxedfunc']
      assert importable(boxedfunc)
      h_func = self.internBackendFunction(boxedfunc)
      yield 'args = (rts.variable(_0, i).hnf() for i in range(len(_0.successors)))'
      yield '_0.rewrite(%s(rts, *args))' % h_func
    elif 'py.rawfunc' in ibuiltin.metadata:
      rawfunc = ibuiltin.metadata['py.rawfunc']
      assert importable(rawfunc)
      h_func = self.internBackendFunction(rawfunc)
      yield 'rts.Node(%s(rts, _0), target=_0.target)' % h_func
    elif 'py.unboxedfunc' in ibuiltin.metadata:
      unboxedfunc = ibuiltin.metadata['py.unboxedfunc']
      assert importable(unboxedfunc)
      h_func = self.internBackendFunction(unboxedfunc)
      h_apply = self.internBackendFunction(apply_unboxed)
      yield 'return %s(rts, %s, _0)' % (h_apply, h_func)
    else:
      raise CompileError('no built-in Python definition found')

  def vEmitFunctionInfotab(self, ifun, h_info, h_stepfunc):
    yield '%s = InfoTable(%r, %r, T_FUNC, %s, %s, %r)' % (
        h_info, ifun.name, ifun.arity
      , showflags(ifun.metadata.get('all.flags', 0))
      , h_stepfunc
      , getattr(ifun.metadata, 'py.format', None)
      )

  def vEmitConstructorInfotab(self, ictor, h_info, h_datatype):
    builtin = 'all.tag' in ictor.metadata
    yield '%s = InfoTable(%r, %r, %r, %s, None, %r)' % (
        h_info, ictor.name, ictor.arity
      , ictor.index if not builtin else ictor.metadata['all.tag']
      , showflags(ictor.metadata.get('all.flags', 0))
      , getattr(ictor.metadata, 'py.format', None)
      )

  def vEmitDataType(self, itype, h_datatype, ctor_handles):
    if self.root_isa_module:
      yield '%s = DataType(%r, [%s])' % (
          h_datatype, itype.name, ', '.join(str(h) for h in ctor_handles)
        )

  def vEmitStringLiteral(self, string, h_string):
    yield '%s = b%r' % (h_string, string)

  def vEmitValueSetLiteral(self, values, h_valueset):
    yield '%s = %r' % (h_valueset, values)

  def vEmitMetadata(self, metadata, h_md):
    yield '%s = %r' % (h_md, metadata)

  def vEmitModuleDefinition(self, imodule, h_module):
    py = renderer.PY_RENDERER
    def _close(level, string):
      return (2 * level + 1) * py.INDENT * ' ' + string
    yield '%s = IModule.fromBOM(' % h_module
    yield '    fullname=%r' % imodule.fullname
    yield '  , filename=%r' % imodule.filename
    yield '  , imports=%s'  % repr(imodule.imports)
    yield '  , metadata=%s' % self.internMetadata(imodule.metadata)
    yield '  , mdkey=%r'    % 'py.material'
    yield '  , aliases=%r'  % imodule.aliases
    if not imodule.types:
      yield '  , types=[]'
    else:
      yield '  , types=['
      types = imodule.types.values()
      for prefix, itype in py.prettylist(types, level=1):
        h_type = self.vGetSymbolName(itype, compiler.DATA_TYPE)
        type_md = self.internMetadata(itype.metadata)
        ctor_mds = tuple(
            self.internMetadata(ictor.metadata)
                for ictor in itype.constructors
          )
        yield '%s(%s, [%s], %s)' % (prefix, type_md, ', '.join(ctor_mds), h_type)
      yield _close(1, ']')
    if not imodule.functions:
      yield '  , functions=[]'
    else:
      yield '  , functions=['
      functions = imodule.functions.values()
      for prefix, ifun in py.prettylist(functions, level=1):
        vis = 'PRIVATE' if ifun.is_private else 'PUBLIC '
        h_info = self.vGetSymbolName(ifun, compiler.INFO_TABLE)
        h_md = self.internMetadata(ifun.metadata)
        yield '%s(%s, %s, %s)' % (prefix, vis, h_md, h_info)
      yield _close(1, ']')
    yield _close(0, ')')

  def vEmitModuleImport(self, imodule, h_module):
    yield '_module_ = interp.import_(%s)' % h_module

  def vEmit_compileS_IVarDecl(self, vardecl, varname):
    yield '%s = None' % varname

  def vEmit_compileS_IFreeDecl(self, vardecl, varname):
    yield '%s = rts.freshvar()' % varname

  def vEmit_compileS_IVarAssign(self, assign, lhs, rhs):
    yield '%s = %s' % (lhs, rhs)

  def vEmit_compileS_INodeAssign(self, assign, lhs, rhs):
    yield '%s = %s' % (lhs, rhs)

  def vEmit_compileS_IExempt(self, exempt):
    yield '_0.rewrite(rts.prelude._Failure)'

  def vEmit_compileS_IReturn(self, iret, expr):
    if isinstance(iret.expr, icurry.IReference):
      yield '_0.rewrite(rts.prelude._Fwd, %s)' % expr
    else:
      yield '_0.rewrite(%s)' % expr

  def vEmit_compileS_ICaseCons(self, icase, h_datatype, varident):
    yield '%s.hnf(typedef=%s)' % (varident, h_datatype)
    yield 'selector = %s.tag' % varident
    el = ''
    for branch in icase.branches[:-1]:
      rhs = self.interp.symbol(branch.symbolname).info.tag
      yield '%sif selector == %s:' % (el, rhs), branch.symbolname
      yield list(self.compileS(branch.block))
      el = 'el'
    if el:
      yield 'else:', icase.branches[-1].symbolname
      yield list(self.compileS(icase.branches[-1].block))
    else:
      for line in self.compileS(icase.branches[-1].block):
        yield line

  _TYPENAMES = {
      icurry.IInt  : 'Prelude.Int'
    , icurry.IChar : 'Prelude.Char'
    , icurry.IFloat: 'Prelude.Float'
    }

  def vEmit_compileS_ICaseLit(self, icase, h_sel, h_values):
    h_datatype = self.importDataType(icase.branches[0].lit.fullname)
    yield '%s.hnf(typedef=%s, values=%s)' % (h_sel, h_datatype, h_values)
    yield 'selector = %s.unboxed_value' % h_sel
    el = ''
    for branch in icase.branches:
      rhs = repr(branch.lit.value)
      yield '%sif selector == %s:' % (el, rhs)
      yield list(self.compileS(branch.block))
      el = 'el'
    last_line = '_0.rewrite(rts.prelude._Failure)'
    if el:
      yield 'else:'
      yield [last_line]
    else:
      yield last_line

  def vEmit_compileE_IVar(self, ivar):
    return '_%s' % ivar.vid

  def vEmit_compileE_IVarAccess(self, ivaraccess, var):
    return '%s[%s]' % (var, ','.join(map(str, ivaraccess.path)))

  def vEmit_compileE_ILiteral(self, iliteral, h_ctor, primary):
    text = '%s, %r' % (h_ctor, iliteral.value)
    return 'rts.Node(%s)' % text if primary else text

  def vEmit_compileE_IString(self, istring, h_string, primary):
    text = 'rts.prelude._PyString, memoryview(%s)' % h_string
    return 'rts.Node(%s)' % text if primary else text

  def vEmit_compileE_IUnboxedLiteral(self, iunboxed, primary):
    return repr(iunboxed)

  def vEmit_compileE_ICall(self, icall, h_info, args, primary):
    text = '%s%s' % (h_info, ''.join(', ' + e for e in args))
    return 'rts.Node(%s)' % text if primary else text

  def vEmit_compileE_IPartialCall(self, ipcall, h_info, args, primary):
    text = 'rts.prelude._PartApplic, %s, rts.Node(%s%s, partial=True)' % (
        self.compileE(ipcall.missing)
      , h_info
      , ''.join(', ' + e for e in args)
      )
    return 'rts.Node(%s)' % text if primary else text

  def vEmit_compileE_IOr(self, ior, lhs, rhs, primary):
    h_choice = self.importSymbol('Prelude.?')
    text = "%s, %s, %s" % (h_choice, lhs, rhs)
    return 'rts.Node(%s)' % text if primary else text

def importable(obj):
  modulename = getattr(obj, '__module__', None)
  name = getattr(obj, '__name__', None)
  module = sys.modules.get(modulename, None)
  found = getattr(module, name, None)
  return found is not None

def write_module(
    target_object, stream, goal=None, section_headers=True, module_main=True
  ):
  render = renderer.PY_RENDERER.renderLines
  SECTIONS = (
      '.header'
    , '.imports'
    , '.strings'
    , '.valuesets'
    , '.primitives'
    , '.metadata'
    , '.stepfuncs'
    , '.infotabs'
    , '.datatypes'
    , '.stepfuncs.link'
    , '.infotabs.link'
    , '.datatypes.link'
    , '.moduledef'
    , '.moduleimp'
    , '.footer'
    )
  assert sorted(SECTIONS) == sorted(compiler.TargetObject.SECTIONS)
  for section_name in SECTIONS:
    if section_headers:
      stream.write('# SECTION: %s\n' % section_name)
    section_data = target_object[section_name]
    section_text = render(section_data)
    stream.write(section_text)
    if section_text:
      stream.write('\n\n')
  if module_main:
    stream.write('''if __name__ == '__main__':\n''')
    stream.write(  '  from %s import __main__\n' % config.python_package_name())
    stream.write(  '  __main__.moduleMain(__file__, %r, goal=%r)\n' %
              (target_object.unitname, goal)
      )
    stream.write('\n\n')

