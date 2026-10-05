from ...exceptions import CompileError
from ..generic import compiler, renderer
from ... import common, config, icurry
from . import cyrtbindings as cyrt
from . import passthrough
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
# defines a ModuleBOM object, which the loader no longer reads.  Format 5: a
# step writes its result into the redex when it fits (Node::rewrite,
# vEmit_compileS_IReturn); a file of format 4 forwards every result, which is
# correct but slower.  Format 6: a literal outside the tables of the runtime
# is a node of the module, made once at load (literal_node,
# internLiteralNode); a file of format 5 allocates such a literal on every
# execution, which is correct but slower.  Format 7: an argument that a step
# only passes on is a plain Node * (passthrough.py, vEmit_compileS_IVarDecl);
# a file of format 6 builds a Variable for it, which is correct but slower.
# Format 8: a partial application without arguments is a node of the module,
# made once at load (partial_node, internPartialNode); a file of format 7
# allocates one on every execution, which is correct but slower.
FORMAT_VERSION = 8

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

# The pinned nullary constructors, the info tables behind SINGLETONS.
# Node::create returns the static object for one of these, and a step forwards
# the redex to it.  A heap copy of a pinned node would never be marked by the
# collector, so the generator never writes one into a redex (see
# Node::rewrite in cyrt/graph/node.hxx).
PINNED_INFOS = frozenset(key[len('Node::create(&'):-1] for key in SINGLETONS)

# The size of the block of a node, in bytes, as the generated info tables
# spell it: sizeof(Head) + sizeof(Arg[max(1, arity)]), one word each.  The
# generator compares the block of a result with the block of the redex, so
# that a result that fits is written into the redex (vEmit_compileS_IReturn).
# InfoTable asserts that every block is at least this large.
WORD = 8

def alloc_size(arity):
  return WORD * (1 + max(1, arity))

class CxxCompiler(compiler.CompilerBase):
  CODE_TYPE = 'C++'
  EXCLUDED_METADATA = set(['cxx.material', 'cxx.shlib'])

  def __init__(self, interp, iroot):
    super(CxxCompiler, self).__init__(interp, iroot)
    self.cxxmodule = cyrt.Module.find_or_create(iroot.modulename) \
        if isinstance(iroot, icurry.IModule) \
        else None
    # The size of the block of the redex of the step under compilation, and
    # the variables of the step that are plain pointers.  See
    # vEmitStepfuncHeader.
    self.redex_alloc_size = None
    self.plain_vars = frozenset()

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
    # The redex of this step is a node of the function's own info table,
    # whose block vEmitFunctionInfotab sizes by the arity.
    self.redex_alloc_size = alloc_size(ifun.arity)
    self.plain_vars = passthrough.plain_variables(ifun)
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
    # A variable that the step only passes on is a plain pointer; the rule
    # is in passthrough.py.  It starts null: a recursive let builds a forward
    # reference from a variable not yet assigned, and an unassigned Variable
    # yields null as well (Variable::rvalue).  A variable that a case
    # scrutinizes, or that is the base of a path or of a node assignment, is
    # a Variable.
    if vardecl.vid in self.plain_vars:
      yield 'Node * %s = nullptr;' % varname
    else:
      yield 'Variable %s;' % varname

  def vEmit_compileS_IFreeDecl(self, vardecl, varname):
    yield 'auto %s = rts->freshvar();' % varname

  def vEmit_compileS_IVarAssign(self, assign, lhs, rhs):
    if assign.vid in self.plain_vars:
      # A plain pointer takes the rendered right side: the plain read of a
      # successor (vEmit_compileE_IVarAccess), a new node, a literal, or
      # another plain variable.
      yield '%s = %s;' % (lhs, rhs)
    elif isinstance(assign.expr, icurry.IVarAccess):
      # A Variable takes the indexer, which records the path and the guards.
      yield '%s = %s;' % (lhs, self.variableAccess(assign.expr))
    elif rhs.startswith('Node::create'):
      tmpname = 'tmp%s' % lhs
      yield 'Node * %s = %s;' % (tmpname, rhs)
      yield '%s.target = %s;' % (lhs, tmpname)
    else:
      yield '%s = %s;' % (lhs, rhs)

  def variableAccess(self, ivaraccess):
    '''
    The indexer of Variable for a path: one subscript per entry.
    Variable::operator[] takes one index; a comma list such as _1[0,1] would
    be the C++ comma operator.
    '''
    var = self.vEmit_compileE_IVar(ivaraccess.var)
    return var + ''.join('[%s]' % i for i in ivaraccess.path)

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
    # The result is written into the redex when it fits the block of the
    # redex (Node::rewrite), as the Python backend rewrites every result in
    # place.  Otherwise the redex is forwarded to a new node.  A reference
    # result is forwarded as well, unless it is a primitive value
    # (Node::forward_or_copy).
    if isinstance(iret.expr, (icurry.IVar, icurry.IVarAccess)):
      yield 'return _0->forward_or_copy(%s);' % expr
    elif self.resultFits(iret.expr):
      if isinstance(iret.expr, icurry.ILit):
        # A literal is a reference in ICurry, so the generic compiler rendered
        # it as a new node (int_(0)).  The info table and the value go into
        # the redex instead.
        expr = self.compileE(iret.expr, primary=False)
      yield 'return _0->rewrite(%s);' % expr
    else:
      yield '_0->forward_to(%s);' % expr
      yield 'return T_FWD;'

  def resultFits(self, expr):
    '''
    Whether the node that ``expr`` denotes fits the block of the redex.  A
    pinned constructor never does (see PINNED_INFOS).  A partial application
    and a value of another kind are forwarded.
    '''
    assert self.redex_alloc_size is not None
    if isinstance(expr, icurry.IPartialCall):
      return False
    elif isinstance(expr, icurry.ICall):
      # A call is saturated: one successor per argument.
      if self.importSymbol(expr.symbolname) in PINNED_INFOS:
        return False
      size = alloc_size(len(expr.exprs))
    elif isinstance(expr, icurry.IOr):
      # The node is Prelude.? applied to both sides.
      size = alloc_size(2)
    else:
      # A boxed literal or a string: a head and one word.
      lit = expr.lit if isinstance(expr, icurry.ILit) else expr
      if not isinstance(
          lit, (icurry.IInt, icurry.IChar, icurry.IFloat, icurry.IString)
        ):
        return False
      size = alloc_size(1)
    return size <= self.redex_alloc_size

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
    # An access in an expression passes its value on (an argument, or the
    # result of the step), so a path of one entry is read as a plain node: a
    # successor of the redex through Node::successor_node, which keeps a set
    # guard in the slot, and a successor of a Variable through
    # Variable::successor_node, which wraps the value in the guards the
    # Variable crossed.  A longer path takes the indexer.  An assignment to a
    # Variable takes the indexer as well (vEmit_compileS_IVarAssign).
    if len(ivaraccess.path) == 1:
      arrow = '->' if ivaraccess.vid == 0 else '.'
      return '%s%ssuccessor_node(%s)' % (var, arrow, ivaraccess.path[0])
    return self.variableAccess(ivaraccess)

  LIT_CONSTRUCTOR = {
      'CyI7Prelude3Int'  : 'int_'
    , 'CyI7Prelude5Float': 'float_'
    , 'CyI7Prelude4Char' : 'char_'
    }

  def vEmit_compileE_ILiteral(self, iliteral, h_ctor, primary):
    # A primary literal is a node.  The runtime keeps one node for each
    # small integer and each ASCII character (int_ and char_ in
    # cyrt/builtins.hpp return them), and the module keeps one node for each
    # of its other literals (internLiteralNode).  So a step allocates nothing
    # for a literal.  A non-primary literal is the info table and the value,
    # for a rewrite of the redex.
    shown = _cxxshow(iliteral.value, use_char=True)
    if not primary:
      return '&%s, Arg(%s)' % (h_ctor, shown)
    elif self.isSmallValue(iliteral):
      return '%s(%s)' % (self.LIT_CONSTRUCTOR[h_ctor], shown)
    else:
      return self.internLiteralNode(h_ctor, shown)

  def isSmallValue(self, iliteral):
    '''
    Whether the runtime keeps a shared node for the literal: an Int from
    SMALL_INT_MIN to SMALL_INT_MAX or a Char up to SMALL_CHAR_MAX.
    '''
    if isinstance(iliteral, icurry.IInt):
      return cyrt.SMALL_INT_MIN <= iliteral.value <= cyrt.SMALL_INT_MAX
    elif isinstance(iliteral, icurry.IChar):
      return ord(iliteral.value) <= cyrt.SMALL_CHAR_MAX
    else:
      return False

  def internLiteralNode(self, h_ctor, shown):
    '''
    The symbol of the node of a literal of this module.  The node is made
    when the module loads and lives as long as the process (literal_node in
    cyrt/builtins.hpp).  One node serves every occurrence of the literal in
    the module.  The key is the spelling: -0.0 and 0.0 are two literals.
    '''
    key = compiler.LITERAL_NODE, h_ctor, shown
    existing = self.intern_store.get(key)
    if existing is not None:
      return existing
    h_lit = self.next_private_symbolname(compiler.LITERAL_NODE)
    self.symtab.insert(
        h_lit, compiler.LITERAL_NODE, '<literal node: %s>' % shown
      )
    self.target_object['.strings'].append(
        'static Node * const %s = literal_node(&%s, Arg(%s));'
            % (h_lit, h_ctor, shown)
      )
    self.symtab.make_defined(h_lit)
    self.intern_store[key] = h_lit
    return h_lit

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
    # 'primary' intentionally ignored: a partial application is always a
    # node.  One without arguments is a node of the module, made once at
    # load (see internPartialNode); one with arguments is allocated with
    # the arguments inline (Node::create_partial).
    if not ipcall.exprs:
      return self.internPartialNode(h_info, ipcall.missing)
    text = '&%s%s' % (h_info, ''.join(', ' + e for e in args))
    return 'Node::create_partial(%s)' % text

  def internPartialNode(self, h_info, missing):
    '''
    The symbol of the node of a partial application without arguments: the
    symbol ``h_info`` as a value, as in ``map f xs``.  The node is made when
    the module loads and lives as long as the process (partial_node in
    cyrt/builtins.hpp); one node serves every occurrence in the module.  The
    missing count is spelled, because the info table of a head of this
    module is not yet initialized when the node is made.
    '''
    key = compiler.PARTIAL_NODE, h_info
    existing = self.intern_store.get(key)
    if existing is not None:
      return existing
    h_partial = self.next_private_symbolname(compiler.PARTIAL_NODE)
    self.symtab.insert(
        h_partial, compiler.PARTIAL_NODE, '<partial node: %s>' % h_info
      )
    self.target_object['.strings'].append(
        'static Node * const %s = partial_node(&%s, %d);'
            % (h_partial, h_info, missing)
      )
    self.symtab.make_defined(h_partial)
    self.intern_store[key] = h_partial
    return h_partial

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

