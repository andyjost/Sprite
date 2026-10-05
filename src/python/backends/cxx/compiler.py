from ...exceptions import CompileError
from ..generic import compiler, renderer
from ... import common, config, icurry
from . import cyrtbindings as cyrt
from ...utility import formatDocstring, strings, visitation
from ...utility.showflags import showflags

__all__ = ['compile', 'write_module', 'FORMAT_VERSION']

# The format of the generated C++.  vEmitHeader writes it into every file as
# "// FORMAT: N".  The toolchain refuses a cached file with another stamp, or
# none (Cpp2So.is_stale): such a file was written for another runtime, and the
# runtime would read its static data with the wrong layout.  A file without a
# stamp is format 1.  Raise the number when the generated code, or a layout it
# depends on, changes.  Format 3: the optimizer replaces calls of alias
# functions (interpreter.optimize.inline_aliases), so a cached file of format
# 2 is correct but slower.  Format 4: the bill of materials is plain data
# (cyrt/bom.hpp; vEmitMetadata and vEmitModuleDefinition).  A file of format 3
# defines a ModuleBOM object, which the loader no longer reads.
FORMAT_VERSION = 4

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
    yield '// FORMAT: %d' % FORMAT_VERSION
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
      dt_code = 'i'
    elif isinstance(values[0], float):
      dt_code = 'f'
    elif isinstance(values[0], str):
      dt_code = 'c'
    # The runtime reads the values through an Arg pointer, so each element
    # has the size of an Arg.  A char value is a char32_t literal.
    yield 'static Arg const %s[] = {%s};' % (
        h_valueset_data, ', '.join(_cxxshow(v, use_char=True) for v in values)
      )
    yield 'static ValueSet const %s{(Arg *) %s, %r, %r};' % (
        h_valueset, h_valueset_data, len(values), dt_code
      )

  def vEmitMetadata(self, md, h_md):
    # A metadata object as plain data (cyrt/bom.hpp): an array of entries, in
    # key order, and the record that names it.  The entries of an empty
    # object are a null pointer.
    if not md:
      yield 'static bom::Metadata const %s = {nullptr, 0};' % h_md
      return
    h_entries = self.next_private_symbolname(compiler.MODULE_DATA, 'md')
    self.symtab.insert(h_entries, compiler.MODULE_DATA, '<metadata entries>')
    yield 'static bom::Entry const %s[] = {%s};' % (
        h_entries, ', '.join(_bom_entry(key, md[key]) for key in sorted(md))
      )
    self.symtab.make_defined(h_entries)
    yield 'static bom::Metadata const %s = {%s, %d};' % (
        h_md, h_entries, len(md)
      )

  def vEmitModuleDefinition(self, imodule, h_module):
    # The module record _bom_ and its tables, as plain data (cyrt/bom.hpp).
    # The loader finds the record by its name, checks its version, and
    # decodes it.  A table comes before the table that points to it.
    cxx = renderer.PY_RENDERER
    lines = []

    def table(ctype, suffix, descr, rows):
      '''
      Appends a static array of ``ctype`` that holds ``rows``.  Returns the
      name of the array and its length; an empty table is null.
      '''
      rows = list(rows)
      if not rows:
        return 'nullptr', 0
      h_table = self.next_private_symbolname(compiler.MODULE_DATA, suffix)
      self.symtab.insert(h_table, compiler.MODULE_DATA, descr)
      lines.append('static %s %s[] = {' % (ctype, h_table))
      for prefix, row in cxx.prettylist(rows, level=0):
        lines.append(prefix + row)
      lines.append('  };')
      self.symtab.make_defined(h_table)
      return h_table, len(rows)

    def with_length(name_and_length):
      return '%s, %d' % name_and_length

    imports = table(
        'char const * const', 'imports', 'imports of %r' % imodule.fullname
      , (_dquote(name) for name in imodule.imports)
      )
    h_md = self.internMetadata(imodule.metadata)
    aliases = table(
        'bom::Alias const', 'aliases', 'aliases of %r' % imodule.fullname
      , (
            '{%s, %s}' % (_dquote(k), _dquote(v))
                for k, v in imodule.aliases.items()
          )
      )
    type_rows = []
    for itype in imodule.types.values():
      h_type = self.vGetSymbolName(itype, compiler.DATA_TYPE)
      type_md = self.internMetadata(itype.metadata)
      ctor_mds = [
          self.internMetadata(ictor.metadata) for ictor in itype.constructors
        ]
      ctors, _ = table(
          'bom::Metadata const * const', 'ctors'
        , 'constructor metadata of %r' % itype.fullname
        , ('&%s' % md for md in ctor_mds)
        )
      type_rows.append('{&%s, %s, &%s}' % (type_md, ctors, h_type))
    types = table(
        'bom::Type const', 'types', 'types of %r' % imodule.fullname, type_rows
      )
    function_rows = []
    for ifun in imodule.functions.values():
      vis = 'PRIVATE' if ifun.is_private else 'PUBLIC '
      h_info = self.vGetSymbolName(ifun, compiler.INFO_TABLE)
      fun_md = self.internMetadata(ifun.metadata)
      function_rows.append('{%s, &%s, &%s}' % (vis, fun_md, h_info))
    functions = table(
        'bom::Function const', 'functions'
      , 'functions of %r' % imodule.fullname, function_rows
      )
    filename = 'nullptr' if imodule.filename is None \
          else _dquote(imodule.filename)
    # A const object at namespace scope has internal linkage unless it is
    # declared extern; the loader looks the record up by name.
    lines.append('extern bom::Module const _bom_;')
    lines.append('bom::Module const _bom_ = {')
    lines.append('    /*version  */ bom::VERSION')
    lines.append('  , /*fullname */ %s' % _dquote(imodule.fullname))
    lines.append('  , /*filename */ %s' % filename)
    lines.append('  , /*imports  */ %s' % with_length(imports))
    lines.append('  , /*metadata */ &%s' % h_md)
    lines.append('  , /*aliases  */ %s' % with_length(aliases))
    lines.append('  , /*types    */ %s' % with_length(types))
    lines.append('  , /*functions*/ %s' % with_length(functions))
    lines.append('  };')
    return lines

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
    # Patch a forward reference of a recursive let.  Index to the parent of
    # the slot, then write the slot through Variable::set_successor.  The
    # rendered ``lhs`` is not used: ``_1[1] = _2`` would assign to a temporary
    # Variable and never write the successor.
    path = list(assign.path)
    assert path
    var = self.vEmit_compileE_IVar(assign.lhs.var)
    parent = var + ''.join('[%s]' % i for i in path[:-1])
    yield '%s.set_successor(%s, %s);' % (parent, path[-1], rhs)

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
        switchbody.append('case %s:' % _cxxshow(branch.lit.value, use_char=True))
        switchbody.append(list(self.compileS(branch.block)))
      switchbody.append('default: return _0->make_failure();')
      yield switchbody

  def vEmit_compileE_IVar(self, ivar):
    return '_%s' % ivar.vid

  def vEmit_compileE_IVarAccess(self, ivaraccess, var):
    # One subscript per path element.  Variable::operator[] takes one index;
    # a comma list such as _1[0,1] would be the C++ comma operator.
    return var + ''.join('[%s]' % i for i in ivaraccess.path)

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

# The bytes that a C++ string literal spells with a symbolic escape.
_CXX_ESCAPES = {
    ord('"') : '\\"'
  , ord('\\'): '\\\\'
  , ord('\n'): '\\n'
  , ord('\r'): '\\r'
  , ord('\t'): '\\t'
  }

def _dquote(string):
  '''
  A C++ string literal that holds the UTF-8 encoding of ``string``.  Printable
  ASCII is written as is.  Every other byte is written as a three-digit octal
  escape, which no following character can extend.  The question mark is
  escaped as well, so that no trigraph can form.
  '''
  parts = ['"']
  for byte in strings.ensure_binary(string):
    escape = _CXX_ESCAPES.get(byte)
    if escape is not None:
      parts.append(escape)
    elif 0x20 <= byte < 0x7f and byte != ord('?'):
      parts.append(chr(byte))
    else:
      parts.append('\\%03o' % byte)
  parts.append('"')
  return ''.join(parts)

def _char_literal(char):
  '''
  A char32_t literal that holds the code point of ``char``.  Printable ASCII
  is written as is; every other code point is written as a hex escape.
  '''
  assert len(char) == 1
  if char in '\\\'':
    return "U'\\%s'" % char
  codepoint = ord(char)
  if 0x20 <= codepoint < 0x7f:
    return "U'%s'" % char
  return "U'\\x%x'" % codepoint

def _bom_entry(key, value):
  '''
  One bom::Entry (cyrt/bom.hpp): the key, the kind, the number, and the text
  of a metadata entry.  MDValue holds a string, an int, or a bool; another
  value is an error here, not in the C++ compiler.
  '''
  if isinstance(value, bool):
    return '{%s, bom::BOOLEAN, %d, nullptr}' % (_dquote(key), int(value))
  elif isinstance(value, int):
    if not -2 ** 31 <= value < 2 ** 31:
      raise CompileError(
          'metadata %r holds %r, which does not fit a C++ int' % (key, value)
        )
    return '{%s, bom::INTEGER, %d, nullptr}' % (_dquote(key), value)
  elif isinstance(value, str):
    return '{%s, bom::STRING, 0, %s}' % (_dquote(key), _dquote(value))
  else:
    raise CompileError(
        'metadata %r holds a value of type %r; the C++ backend stores str, '
        'int, and bool' % (key, type(value).__name__)
      )

@visitation.dispatch.on('arg')
def _cxxshow(arg, use_char=False):
  assert False

@_cxxshow.when(bool)
def _cxxshow(bit, use_char=False):
  return 'true' if bit else 'false'

@_cxxshow.when((int, float))
def _cxxshow(i, use_char=False):
  return repr(i)

@_cxxshow.when(str)
def _cxxshow(string, use_char=False):
  if use_char:
    return _char_literal(string)
  else:
    return _dquote(string)

def write_module(
    target_object, stream, goal=None, section_headers=True, module_main=True
  , goalscheme=None
  ):
  # goalscheme, the type of the goal, serves the footer of the Python
  # backend; the entry point written here runs no goal.
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

