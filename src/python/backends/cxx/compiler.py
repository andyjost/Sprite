from ...exceptions import CompileError
from ..generic import compiler, renderer
from ... import icurry
from ...utility import formatDocstring, strings
import json

__all__ = ['compile', 'write_module']

def compile(interp, imodule):
  compileM = CxxCompiler(interp, imodule)
  return compileM.compile()

class CxxCompiler(compiler.CompilerBase):
  CODE_TYPE = 'C++'

  def vEmitHeader(self):
    yield '#include "cyrt/cyrt.hpp"'
    yield ''
    yield 'using namespace cyrt;'

  def vEmitFooter(self):
    return []

  def vEmitImported(self, modulename):
    yield '// TODO imported modules'

  def vEmitStepfuncLink(self, ifun, h_stepfunc):
    yield 'tag_type %s(RuntimeState *, Configuration *);' % h_stepfunc

  def vEmitInfotabLink(self, isym, h_info):
    yield 'extern InfoTable const %s;' % h_info

  def vEmitDataTypeLink(self, itype, h_datatype):
    yield 'extern Type const %s;' % h_datatype

  def vEmitStepfuncHeader(self, ifun, h_stepfunc):
    yield '/****** %s ******/' % ifun.fullname
    yield 'tag_type %s(RuntimeState * rts, Configuration * C)' % h_stepfunc

  def vEmitStepfuncEntry(self):
    yield 'Cursor _0 = C->cursor();'

  def vEmitBuiltinStepfunc(self, ibuiltin, h_stepfunc):
    breakpoint()

  def vEmitFunctionInfotab(self, ifun, h_info, h_stepfunc):
    yield 'InfoTable const %s{'                 % h_info
    yield '    /*tag*/        T_FUNC'
    yield '  , /*arity*/      %s'               % ifun.arity
    yield '  , /*alloc_size*/ sizeof(Head) + sizeof(Arg[%s])' % ifun.arity
    yield '  , /*flags*/      F_STATIC_OBJECT'
    yield '  , /*name*/       %s'               % _dquote(ifun.name)
    yield '  , /*format*/     "%s"'             % ('p' * ifun.arity)
    yield '  , /*step*/       %s'               % h_stepfunc
    yield '  , /*typecheck*/  nullptr'
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
    yield '  , /*typecheck*/  nullptr'
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
    yield 'Type const %s { %s, %r, %r, F_STATIC_OBJECT };' % (
        h_datatype, h_ctortable, 't', len(itype.constructors)
      )
    yield ''

  def vEmitStringLiteral(self, string, h_string):
    yield 'static char const * %s = %s;' % (h_string, _dquote(string))

  def vEmitValueSetLiteral(self, values, h_valueset):
    yield 'static %s constexpr %s[] = {%s};' % (
        _datatype(values), h_valueset, ', '.join(str(v) for v in values)
      )

  def vEmitModuleDefinition(self, imodule, h_module):
    assert False # TODO

  def vEmitModuleImport(self, imodule, h_module):
    yield '// TODO: vEmitModuleImport'
    pass

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

def write_module(target_object, stream, goal=None):
  render = renderer.CXX_RENDERER.renderLines
  for section_name in compiler.TargetObject.SECTIONS:
    stream.write('/* SECTION: %s */\n' % section_name)
    section_data = target_object[section_name]
    section_text = render(section_data)
    stream.write(section_text)
    stream.write('\n')

