from ...exceptions import CompileError
from ..generic import compiler, renderer
from ... import icurry
from ...utility import formatDocstring, strings, visitation
import collections, json, six

__all__ = ['compile', 'write_module']

def compile(interp, imodule):
  compileM = CxxCompiler(interp, imodule)
  return compileM.compile()

class CxxCompiler(compiler.CompilerBase):
  CODE_TYPE = 'C++'
  EXCLUDED_METADATA = set(['cxx.material'])

  def vIsBuiltin(self, ifun):
    return ifun.is_builtin

  def vIsSynthesized(self, ifun):
    return False

  def vBackendFunctionKey(self, ifun):
    assert False

  def vEmitHeader(self):
    yield '#include "cyrt/cyrt.hpp"'
    yield '#include <iostream>' # DEBUG
    yield ''
    yield 'using namespace cyrt;'
    yield ''
    yield 'extern "C" {'

  def vEmitFooter(self):
    yield '} // extern "C"'

  def vEmitImported(self, modulename):
    yield '// TODO imported modules'

  def vEmitStepfuncLink(self, ifun, h_stepfunc):
    yield 'tag_type %s(RuntimeState *, Configuration *);' % h_stepfunc

  def vEmitInfotabLink(self, isym, h_info):
    yield 'extern InfoTable const %s;' % h_info

  def vEmitDataTypeLink(self, itype, h_datatype):
    yield 'extern DataType const %s;' % h_datatype

  def vEmitStepfuncHeader(self, ifun, h_stepfunc):
    yield '/****** %s ******/' % ifun.fullname
    yield 'tag_type %s(RuntimeState * rts, Configuration * C)' % h_stepfunc

  def vEmitStepfuncEntry(self):
    yield 'Cursor _0 = C->cursor();'

  def vEmitSynthesizedStepfunc(self, ibuiltin, h_stepfunc):
    assert False

  def vEmitFunctionInfotab(self, ifun, h_info, h_stepfunc):
    yield 'InfoTable const %s{'                 % h_info
    yield '    /*tag*/        T_FUNC'
    yield '  , /*arity*/      %s'               % ifun.arity
    yield '  , /*alloc_size*/ sizeof(Head) + sizeof(Arg[%s])' % ifun.arity
    yield '  , /*flags*/      F_STATIC_OBJECT'
    yield '  , /*name*/       %s'               % _dquote(ifun.name)
    yield '  , /*format*/     "%s"'             % ('p' * ifun.arity)
    yield '  , /*step*/       %s'               % h_stepfunc
    yield '  , /*type*/       nullptr'
    yield '  };'
    yield ''

  def vEmitConstructorInfotab(self, ictor, h_info, h_datatype):
    flags = ictor.metadata.get('all.flags', 0)
    yield 'InfoTable const %s{'                     % h_info
    yield '    /*tag*/        T_CTOR + %r'          % ictor.index
    yield '  , /*arity*/      %s'                   % ictor.arity
    yield '  , /*alloc_size*/ sizeof(Head) + sizeof(Arg[%s])' % ictor.arity
    yield '  , /*flags*/      F_STATIC_OBJECT | %s' % flags
    yield '  , /*name*/       %s'                   % _dquote(ictor.name)
    yield '  , /*format*/     "%s"'                 % ('p' * ictor.arity)
    yield '  , /*step*/       nullptr'
    yield '  , /*type*/       &%s'                  % h_datatype
    yield '  };'
    yield ''

  def vEmitDataType(self, itype, h_datatype, ctor_handles):
    h_ctortable = self.next_private_symbolname(compiler.CONSTRUCTOR_TABLE)
    self.symtab.insert(
        h_ctortable, compiler.CONSTRUCTOR_TABLE
      , 'constructor table for %r' % itype.fullname
      )
    yield 'static InfoTable const * %s[] = { %s };' % (
        h_ctortable, ', '.join('&%s' % h for h in ctor_handles)
      )
    self.symtab.make_defined(h_ctortable)
    yield 'DataType const %s { %s, %r, %r, F_STATIC_OBJECT, %s };' % (
        h_datatype, h_ctortable, len(itype.constructors), 't'
      , _dquote(itype.name)
      )
    yield ''

  def vEmitStringLiteral(self, string, h_string):
    yield 'static char const * %s = %s;' % (h_string, _dquote(string))

  def vEmitValueSetLiteral(self, values, h_valueset):
    yield 'static %s constexpr %s[] = {%s};' % (
        _datatype(values), h_valueset, ', '.join(str(v) for v in values)
      )

  def vEmitMetadata(self, md, h_md):
    yield 'static Metadata const %s = %s;' % (h_md, _cxxshow(md))

  def vEmitModuleDefinition(self, imodule, h_module):
    cxx = renderer.PY_RENDERER
    def _close(level, string):
      return (2 * level + 1) * cxx.INDENT * ' ' + string
    yield 'static ModuleBOM const %s{' % h_module
    yield '    /*fullname */ %s' % _dquote(imodule.fullname)
    yield '  , /*filename */ %s' % _dquote(imodule.filename)
    yield '  , /*imports  */ %s' % _cxxshow(imodule.imports)
    yield '  , /*metadata */ %s' % _cxxshow(imodule.metadata._asdict)
    yield '  , /*aliases  */ %s' % _cxxshow(imodule.aliases)
    if not imodule.types:
      yield '  , /*types    */ {}'
    else:
      yield '  , /*types    */ {'
      types = imodule.types.values()
      for prefix, itype in cxx.prettylist(types, level=1):
        h_type = self.vGetSymbolName(itype, compiler.DATA_TYPE)
        type_md = self.internMetadata(itype.metadata)
        ctor_mds = tuple(
            self.internMetadata(ictor.metadata)
                for ictor in itype.constructors
          )
        yield '%s{&%s, {%s}, &%s}' % (
            prefix, type_md, ', '.join('&%s' % md for md in ctor_mds), h_type
          )
      yield _close(1, '}')
    if not imodule.functions:
      yield '  , /*functions*/ {}'
    else:
      yield '  , /*functions*/ {'
      functions = imodule.functions.values()
      for prefix, ifun in cxx.prettylist(functions, level=1):
        vis = 'PRIVATE' if ifun.is_private else 'PUBLIC '
        h_info = self.vGetSymbolName(ifun, compiler.INFO_TABLE)
        h_md = self.internMetadata(ifun.metadata)
        yield '%s{%s, &%s, &%s}' % (prefix, vis, h_md, h_info)
      yield _close(1, '}')
    yield _close(0, '};')
    yield 'ModuleBOM const * _bom_ = &%s;' % h_module

  def vEmitModuleImport(self, imodule, h_module):
    yield '// TODO: vEmitModuleImport'

  def vEmit_compileS_IVarDecl(self, vardecl, varname):
    yield 'Variable %s;' % varname

  def vEmit_compileS_IFreeDecl(self, vardecl, varname):
    yield 'auto %s = rts->freshvar();' % varname

  def vEmit_compileS_IVarAssign(self, assign, lhs, rhs):
    if isinstance(assign.rhs, icurry.ICall):
      tmpname = 'tmp%s' % lhs
      yield 'Node * %s = %s;' % (tmpname, rhs)
      yield '%s.target = %s;' % (lhs, tmpname)
    else:
      yield '%s = %s;' % (lhs, rhs)

  def vEmit_compileS_INodeAssign(self, assign, lhs, rhs):
    yield '%s = %s;' % (lhs, rhs)

  def vEmit_compileS_IExempt(self, exempt):
    yield 'return _0->make_failure();'

  def vEmit_compileS_IReturn(self, iret, expr):
    yield '_0->forward_to(%s);' % expr
    yield 'return T_FWD;'

  def vEmit_compileS_ICaseCons(self, icase, h_datatype, varident):
    yield 'auto tag = rts->hnf(C, &%s, &%s);' % (varident, h_datatype)
    yield 'switch(tag)'
    switchbody = []
    for branch in icase.branches:
      value = self.interp.symbol(branch.symbolname).info.tag
      switchbody.append(('case %s:' % value, branch.symbolname))
      switchbody.append(list(self.compileS(branch.block)))
    switchbody.append('default: return tag;')
    yield switchbody

  def vEmit_compileS_ICaseLit(self, icase, h_sel, h_values):
    yield 'auto tag = rts->hnf(C, &%s, &%s);' % (h_sel, h_values)
    yield 'if(tag != T_UNBOXED) return tag;'
    yield 'switch(%s.target.arg->ub_int)' % h_sel
    switchbody = []
    for branch in icase.branches:
      value = repr(branch.lit.value)
      switchbody.append('case %s:' % value)
      switchbody.append(list(self.compileS(branch.block)))
    switchbody.append('default: return _0->make_failure();')
    yield switchbody

  def vEmit_compileE_IVar(self, ivar):
    return '_%s' % ivar.vid

  def vEmit_compileE_IVarAccess(self, ivaraccess, var):
    return '%s[%s]' % (var, ','.join(map(str, ivaraccess.path)))

  def vEmit_compileE_ILiteral(self, iliteral, h_ctor, primary):
    text = '&%s, Arg(%r)' % (h_ctor, iliteral.value)
    return 'Node::create(%s)' % text if primary else text

  def vEmit_compileE_IString(self, istring, h_string, primary):
    text = '&CString_Info, Arg(%s)' % h_string
    return 'Node::create(%s)' % text if primary else text

  def vEmit_compileE_IUnboxedLiteral(self, iunboxed, primary):
    return repr(iunboxed)

  def vEmit_compileE_ICall(self, icall, h_info, args, primary):
    text = '&%s%s' % (h_info, ''.join(', ' + e for e in args))
    return 'Node::create(%s)' % text if primary else text

  def vEmit_compileE_IPartialCall(self, ipcall, h_info, args, primary):
    text = '&%s%s' % (h_info, ''.join(', ' + e for e in args))
    # 'primary' intentionally ignored.
    return 'Node::create_partial(%s)' % text

  def vEmit_compileE_IOr(self, ior, lhs, rhs, primary):
    h_choice = self.importSymbol('Prelude.?')
    text = "&%s, %s, %s" % (h_choice, lhs, rhs)
    return 'Node::create(%s)' % text if primary else text


def _datatype(values):
  if len(values) == 0 or isinstance(values[0], int):
    return 'unboxed_int_type';
  elif isinstance(values[0], float):
    return 'unboxed_float_type';
  elif isinstance(values[0], str):
    return 'unboxed_char_type';
  assert False

def _dquote(string):
  # Note: Use JSON to get double-quote-style escaping.
  string_data = strings.ensure_str(string)
  return json.dumps(string_data)

class FooError(RuntimeError):
  def __init__(self, obj):
    self.obj = obj

@visitation.dispatch.on('arg')
def _cxxshow(arg):
  assert False

@_cxxshow.when(bool)
def _cxxshow(bit):
  return 'true' if bit else 'false'

@_cxxshow.when(int)
def _cxxshow(i):
  return repr(i)

@_cxxshow.when(six.string_types)
def _cxxshow(string):
  return _dquote(string)

@_cxxshow.when(collections.Mapping)
def _cxxshow(mapping):
  return '{%s}' % ', '.join(
      '{%s, %s}' % (_cxxshow(k), _cxxshow(v)) for k,v in mapping.items()
    )

@_cxxshow.when(collections.Sequence, no=six.string_types)
def _cxxshow(sequence):
  return '{%s}' % ', '.join(_cxxshow(part) for part in sequence)

def write_module(
    target_object, stream, goal=None, section_headers=True, module_main=True
  ):
  render = renderer.CXX_RENDERER.renderLines
  for section_name in compiler.TargetObject.SECTIONS:
    if section_headers:
      stream.write('/* SECTION: %s */\n' % section_name)
    section_data = target_object[section_name]
    section_text = render(section_data)
    stream.write(section_text)
    if section_text:
      stream.write('\n\n')
  if module_main:
    stream.write('/* TODO: module main */\n')
    stream.write('\n\n')

