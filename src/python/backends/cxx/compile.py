from ...exceptions import CompileError
from ..generic import compiler, renderer
from ... import config, icurry
from ...utility import formatDocstring, strings
import collections, itertools, json, re

__all__ = ['compile', 'demangle', 'mangle', 'write_module']

def compile(interp, imodule, extern=None):
  compileM = CxxCompiler(interp, imodule, extern)
  return compileM.compile()

TR = {
    '_' : '__' , '&' : '_M' , '@' : '_A' , '!' : '_B' , '`' : '_T'
  , '^' : '_c' , ':' : '_C' , ',' : '_m' , '$' : '_D' , '.' : '_d'
  , '"' : '_Q' , '=' : '_E' , '\\': '_z' , '>' : '_G' , '{' : '_R'
  , '[' : '_K' , '(' : '_Y' , '<' : '_L' , '-' : '_n' , '#' : '_h'
  , '%' : '_s' , '|' : '_p' , '+' : '_P' , '?' : '_u' , '}' : '_r'
  , ']' : '_k' , ')' : '_y' , ';' : '_S' , '/' : '_l' , '\'': '_q'
  , '*' : '_a' , '~' : '_t'
  }
TRR = {v:k for k,v in TR.items()}

# Check for duplicates in TR and TRR.
assert all(n == 1 for n in collections.Counter(TR.values()).values())
assert all(n == 1 for n in collections.Counter(TRR.values()).values())
assert len(TR) == len(TRR)

KIND_CODE = {
    compiler.DATA_TYPE         : 'D'
  , compiler.INFO_TABLE        : 'I'
  , compiler.STRING_DATA       : 'S'
  , compiler.VALUE_SET         : 'V'
  , compiler.STEP_FUNCTION     : 'F'
  , compiler.CONSTRUCTOR_TABLE : 'C'
}

KIND_CODE_R = {v:k for k,v in KIND_CODE.items()}

def encode(name):
  '''Encode a Curry identifier string to alphnumeric.'''
  enc = ''.join(TR.get(ch, ch) for ch in name)
  # assert decode(enc) == name
  return enc

def decode(name):
  '''Decode an encoded Curry identifier string.'''
  def gen():
    i = 0
    n = len(name)
    while i<n:
      if name[i] == '_':
        enc = name[i:i+2]
        yield TRR[enc]
        i += 2
      else:
        yield name[i]
        i += 1
  return ''.join(gen())

def mangle(parts, kind):
  # E.g., Prelude.: -> CyI7Prelude5_col_
  #    Cy       = prefix for all Curry symbols
  #    I        = symbol kind (info table)
  #    7Prelude = name qualifier
  #    5_col_   = encoded name
  parts_ = parts[:-1] + [encode(parts[-1])]
  tail = ''.join('%s%s' % (len(p), p) for p in parts_)
  symbolname = 'Cy%s%s' % (KIND_CODE[kind], tail)
  # assert demangle(symbolname) == (parts, kind)
  return symbolname

P_INTEGER = re.compile('(^\d+)')
def demangle(symbolname):
  assert symbolname.startswith('Cy')
  kind = KIND_CODE_R[symbolname[2]]
  def gen():
    i = 3
    n = len(symbolname)
    while i<n:
      text = re.match(P_INTEGER, symbolname[i:]).group()
      chunksz = int(text)
      i += len(text)
      chunk = symbolname[i:i+chunksz]
      yield decode(chunk)
      i += chunksz
  return list(gen()), kind


class CxxCompiler(compiler.CompilerBase):
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
    compiler.CompilerBase.__init__(self, interp, imodule, extern)
    self.counts = collections.defaultdict(itertools.count)

  def next_private_symbolname(self, kind):
    i = next(self.counts[kind])
    return mangle(['_%s' % i], kind)

  def vGetSymbolName(self, iobj, kind):
    return mangle(iobj.splitname(), kind)

  def vEmitHeader(self):
    yield '#include "cyrt/cyrt.hpp"'
    yield ''
    yield 'using namespace cyrt;'

  def vEmitStepfuncFwd(self, h_stepfunc):
    yield 'tag_type %s(RuntimeState *, Configuration *);' % h_stepfunc

  def vEmitInfotabFwd(self, h_info):
    yield 'extern InfoTable const %s;' % h_info

  def vEmitDataTypeFwd(self, h_datatype):
    yield 'extern Type const %s;' % h_datatype

  def vEmitStepfuncHead(self, ifun, h_stepfunc):
    yield '/****** %s ******/' % ifun.fullname
    yield 'tag_type %s(RuntimeState * rts, Configuration * C)' % h_stepfunc

  def vEmitStepfuncEntry(self):
    yield 'Cursor _0 = C->cursor();'

  def vEmitFunctionInfotab(self, ifun, h_info, h_stepfunc):
    yield 'InfoTable const %s{'                 % h_info
    yield '    /*tag*/        T_FUNC'
    yield '  , /*arity*/      %s'               % ifun.arity
    yield '  , /*alloc_size*/ %s'               % _sizeof(ifun.arity)
    yield '  , /*flags*/      F_STATIC_OBJECT'
    yield '  , /*name*/       %s'               % _dquote(ifun.name)
    yield '  , /*format*/     "%s"'             % ('p' * ifun.arity)
    yield '  , /*step*/       %s'               % h_stepfunc
    yield '  , /*typecheck*/  nullptr'
    yield '  , /*type*/       nullptr'
    yield '  };'
    yield ''

  def vEmitConstructorInfotab(self, i, ictor, h_info, h_datatype):
    flags = ictor.metadata.get('all.flags', 0)
    yield 'InfoTable const %s{'                     % h_info
    yield '    /*tag*/        T_CTOR + %s'          % str(i)
    yield '  , /*arity*/      %s'                   % ictor.arity
    yield '  , /*alloc_size*/ %s'                   % _sizeof(ictor.arity)
    yield '  , /*flags*/      F_STATIC_OBJECT | %s' % flags
    yield '  , /*name*/       %s'                   % _dquote(ictor.name)
    yield '  , /*format*/     "%s"'                 % ('p' * ictor.arity)
    yield '  , /*step*/       nullptr'
    yield '  , /*typecheck*/  nullptr'
    yield '  , /*type*/       &%s'                  % h_datatype
    yield '  };'
    yield ''

  def vEmitDataType(self, itype, h_datatype, ctor_handles):
    # h_ctortable = self.vGetSymbolName(itype, CONSTRUCTOR_TABLE)
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

  def vEmit_compileS_IReturn(self, expr):
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

  def vEmit_compileS_ICaseLit(self, icase, h_sel, values):
    h_values = self.next_private_symbolname(compiler.VALUE_SET)
    self.symtab.insert(h_values, compiler.VALUE_SET, '<literal case values>')
    self.target_object['.valuesets'].append(
        'static %s constexpr %s[] = {%s};' % (
            _datatype(values), h_values, ', '.join(str(v) for v in values)
          )
      )
    self.symtab.make_defined(h_values)

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

  def vEmit_compileE_IString(self, istring, primary):
    string = strings.ensure_str(istring.value)
    h_string = self.next_private_symbolname(compiler.STRING_DATA)
    self.symtab.insert(h_string, compiler.STRING_DATA, '<string data %r>' % string)
    self.target_object['.strings'].append(
        'static char const * %s = %s;' % (h_string, _dquote(string))
      )
    self.symtab.make_defined(h_string)
    text = '&CString_Info, Arg(%s)' % h_string
    return 'Node::create(%s)' % text if primary else text

  def vEmit_compileE_IUnboxedLiteral(self, iunboxed, primary):
    return repr(iunboxed)

  def vEmit_compileE_ICall(self, icall, h_info, args, primary):
    text = '&%s%s' % (h_info, ''.join(', ' + e for e in args))
    return 'Node::create(%s)' % text if primary else text

  def vEmit_compileE_IPartialCall(self, icall, h_info, args, primary):
    text = '&%s%s' % (h_info, ''.join(', ' + e for e in args))
    # 'primary' intentionally ignored.
    return 'Node::create_partial(%s)' % text

  def vEmit_compileE_IOr(self, ior, h_info, lhs, rhs, primary):
    text = "&%s, %s, %s" % (h_info, lhs, rhs)
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

def _sizeof(arity):
    return 'sizeof(Head) + sizeof(Arg[%s])' % arity

def write_module(target_object, stream, goal=None):
  render = renderer.CXX_RENDERER.renderLines
  for section_name in compiler.TargetObject.SECTIONS:
    section_data = target_object[section_name]
    section_text = render(section_data)
    stream.write(section_text)
    stream.write('\n')

