from ...exceptions import CompileError
from ..generic import compiler, renderer
from ... import common, config, icurry
from . import cyrtbindings as cyrt
from ...utility import formatDocstring, strings, visitation
from ...utility.showflags import showflags
import collections, json, six

__all__ = ['compile', 'write_module']

def compile(interp, imodule):
  compileM = CxxCompiler(interp, imodule)
  return compileM.compile()

SINGLETONS = {
    'Node::create(&CyI7Prelude4_K_k)' : 'nil()'
  , 'Node::create(&CyI7Prelude4_Y_y)' : 'unit()'
  , 'Node::create(&CyI7Prelude4True)' : 'true_()'
  , 'Node::create(&CyI7Prelude5False)': 'false_()'
  , 'Node::create(&CyI7Prelude4Fail)' : 'fail()'
  }

def replace_singletons(f):
  def emitter(*args, **kwds):
    result = f(*args, **kwds)
    return SINGLETONS.get(result, result)
  return emitter

class CxxCompiler(compiler.CompilerBase):
  CODE_TYPE = 'C++'
  EXCLUDED_METADATA = set(['cxx.material', 'cxx.shlib'])

  def __init__(self, interp, iroot):
    super(CxxCompiler, self).__init__(interp, iroot)
    self.cxxmodule = cyrt.Module.find_or_create(iroot.modulename) \
        if isinstance(iroot, icurry.IModule) \
        else None

  def vIsBuiltin(self, iobj):
    if self.cxxmodule is not None:
      if isinstance(iobj, (icurry.IFunction, icurry.IConstructor)):
        return self.cxxmodule.get_builtin_symbol(iobj.name) is not None
      elif isinstance(iobj, icurry.IDataType):
        return self.cxxmodule.get_builtin_type(iobj.name) is not None
      else:
        assert False
    return False

  def vIsSynthesized(self, ifun):
    return False

  def vBackendFunctionKey(self, ifun):
    assert False

  def vEmitHeader(self):
    yield '// IMPORTS: ' + ' '.join(str(mod) for mod in self.iroot.imports)
    yield '#include "cyrt/cyrt.hpp"'
    yield ''
    yield 'using namespace cyrt;'
    yield ''
    yield 'extern "C" {'

  def vEmitFooter(self):
    yield '} // extern "C"'

  def vEmitImported(self, modulename):
    return []

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
    flags = ifun.metadata.get('all.flags', 0) | common.F_STATIC_OBJECT
    yield 'InfoTable const %s{'                 % h_info
    yield '    /*tag*/        T_FUNC'
    yield '  , /*arity*/      %s'               % ifun.arity
    yield '  , /*alloc_size*/ sizeof(Head) + sizeof(Arg[%s])' % max(1, ifun.arity)
    yield '  , /*flags*/      %s'                   % showflags(flags)
    yield '  , /*name*/       %s'               % _dquote(ifun.name)
    yield '  , /*format*/     "%s"'             % ('p' * ifun.arity)
    yield '  , /*step*/       %s'               % h_stepfunc
    yield '  , /*type*/       nullptr'
    yield '  };'
    yield ''

  def vEmitConstructorInfotab(self, ictor, h_info, h_datatype):
    flags = ictor.metadata.get('all.flags', 0) | common.F_STATIC_OBJECT
    yield 'InfoTable const %s{'                     % h_info
    yield '    /*tag*/        T_CTOR + %r'          % ictor.index
    yield '  , /*arity*/      %s'                   % ictor.arity
    yield '  , /*alloc_size*/ sizeof(Head) + sizeof(Arg[%s])' % max(1, ictor.arity)
    yield '  , /*flags*/      %s'                   % showflags(flags)
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

  def vEmitValueSetLiteral(self, values, h_valueset, h_valueset_data):
    if len(values) == 0 or isinstance(values[0], int):
      dt_name, dt_code = 'unboxed_int_type', 'i'
    elif isinstance(values[0], float):
      dt_name, dt_code = 'unboxed_float_type', 'f'
    elif isinstance(values[0], str):
      dt_name, dt_code = 'unboxed_char_type', 'c'
    yield 'static %s const %s[] = {%s};' % (
        dt_name, h_valueset_data, ', '.join(repr(v) for v in values)
      )
    yield 'static ValueSet const %s{(Arg *) %s, %r, %r};' % (
        h_valueset, h_valueset_data, len(values), dt_code
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
    yield '  , /*metadata */ %s' % self.internMetadata(imodule.metadata)
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
    return []

  def vEmit_compileS_IVarDecl(self, vardecl, varname):
    yield 'Variable %s;' % varname

  def vEmit_compileS_IFreeDecl(self, vardecl, varname):
    yield 'auto %s = rts->freshvar();' % varname

  def vEmit_compileS_IVarAssign(self, assign, lhs, rhs):
    if rhs.startswith('Node::create'):
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
    yield 'if(tag < T_CTOR) return tag;'
    assert icase.branches
    br = icase.branches[0]
    if isinstance(br.lit, icurry.IFloat):
      yield 'auto switch_value = NodeU{%s.target}.float_->value;' % h_sel
      for branch in icase.branches:
        yield 'if(switch_value == %r)' % branch.lit.value
        yield list(self.compileS(branch.block))
      yield 'else return _0->make_failure();'
    else:
      if isinstance(br.lit, icurry.IChar):
        yield 'switch(NodeU{%s.target}.char_->value)' % h_sel
      elif isinstance(br.lit, icurry.IInt):
        yield 'switch(NodeU{%s.target}.int_->value)' % h_sel
      else:
        raise CompileError('bad switch type: %r' % type(br.lit))
      switchbody = []
      for branch in icase.branches:
        switchbody.append('case %r:' % branch.lit.value)
        switchbody.append(list(self.compileS(branch.block)))
      switchbody.append('default: return _0->make_failure();')
      yield switchbody

  def vEmit_compileE_IVar(self, ivar):
    return '_%s' % ivar.vid

  def vEmit_compileE_IVarAccess(self, ivaraccess, var):
    return '%s[%s]' % (var, ','.join(map(str, ivaraccess.path)))

  LIT_CONSTRUCTOR = {
      'CyI7Prelude3Int'  : 'int_'
    , 'CyI7Prelude5Float': 'float_'
    , 'CyI7Prelude4Char' : 'char_'
    }

  def vEmit_compileE_ILiteral(self, iliteral, h_ctor, primary):
    shown = _cxxshow(iliteral.value, use_char=True)
    if primary:
      return '%s(%s)' % (self.LIT_CONSTRUCTOR[h_ctor], shown)
    else:
      # text = '&%s, Arg(%r)' % (h_ctor, iliteral.value)
      # return 'Node::create(%s)' % text if primary else text
      return '&%s, Arg(%s)' % (h_ctor, shown)

  def vEmit_compileE_IString(self, istring, h_string, primary):
    text = '&_biString_Info, Arg(%s)' % h_string
    return 'Node::create(%s)' % text if primary else text

  def vEmit_compileE_IUnboxedLiteral(self, iunboxed, primary):
    return repr(iunboxed)

  @replace_singletons
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

def _dquote(string):
  # Note: Use JSON to get double-quote-style escaping.
  string_data = strings.ensure_str(string)
  return json.dumps(string_data)

@visitation.dispatch.on('arg')
def _cxxshow(arg, use_char=False):
  assert False

@_cxxshow.when(bool)
def _cxxshow(bit, use_char=False):
  return 'true' if bit else 'false'

@_cxxshow.when((int, float))
def _cxxshow(i, use_char=False):
  return repr(i)

@_cxxshow.when(six.string_types)
def _cxxshow(string, use_char=False):
  # Ensure characters always begin with a single quote.  Python uses "'" for
  # that particular string.
  if use_char:
    assert len(string) == 1
    if string == "'":
      return "'\\''"
    else:
      result = repr(string)
      assert result.startswith("'")
      return result
  else:
    return _dquote(string)

@_cxxshow.when(collections.Mapping)
def _cxxshow(mapping, use_char=False):
  return '{%s}' % ', '.join(
      '{%s, %s}' % (_cxxshow(k, use_char), _cxxshow(v, use_char)) for k,v in mapping.items()
    )

@_cxxshow.when(collections.Sequence, no=six.string_types)
def _cxxshow(sequence, use_char=False):
  return '{%s}' % ', '.join(_cxxshow(part, use_char) for part in sequence)

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
    for line in _generate_main(target_object, goal):
      stream.write(line)
      stream.write('\n')
    stream.write('\n\n')

def _generate_main(target_object, goal):
  yield '#include <iostream>'
  yield ''
  yield 'const char my_interp[] __attribute__((section(".interp")))' \
        ' = %s;' % _dquote(config.ld_interpreter_path())
  yield ''
  yield 'extern "C" void entry()'
  yield '{'
  yield '  std::cout << "Entry for %r" << std::endl;' % target_object.unitname
  yield '  std::exit(0);'
  yield '}'

