from ....exceptions import CompileError
from ...generic.compiler import ExternallyDefined
# from ....icurry import analysis
from .... import config, icurry
from ....objects import handle
from ....utility import encoding, formatDocstring, strings, visitation
import abc, collections, functools, itertools, json, logging, six, sys

logger = logging.getLogger(__name__)

__all__ = ['compile']

# Symbol kind.
DATA_TYPE         = 'DATA_TYPE'     # A Curry data type (for narrowing).
INFO_TABLE        = 'INFO_TABLE'    # Constructor or Function info table.
STRING_DATA       = 'STRING_DATA'   # Static string data.
VALUE_SET         = 'VALUE_SET'     # Case values (for narrowing).
STEP_FUNCTION     = 'STEP_FUNCTION' # A step function.
CONSTRUCTOR_TABLE = 'CONSTRUCTOR_TABLE'

KIND_CODE = {
    DATA_TYPE         : 'D'
  , INFO_TABLE        : 'I'
  , STRING_DATA       : 'S'
  , VALUE_SET         : 'V'
  , STEP_FUNCTION     : 'F'
  , CONSTRUCTOR_TABLE : 'C'
}

# Symbol status.
DEFINED   = 'T'
UNDEFINED = 'U'

Symbol = collections.namedtuple(
    'Symbol', ['tgtname', 'stat', 'kind', 'descr']
  )

def mangle(parts, kind):
  # E.g., Prelude.: -> CyI7Prelude5_col_
  #    Cy       = prefix for all Curry symbols
  #    I        = symbol kind (info table)
  #    7Prelude = name qualifier
  #    5_col_   = encoded name

  parts = parts[:-1] + [encoding.encode_nospecial(parts[-1])]
  return 'Cy%s%s' % (kind[0], ''.join('%s%s' % (len(p), p) for p in parts))

# E.g.: the symbol for Prelude.: might appear in the symbol table for the
# Prelude as follows:
#
#   ('_7Prelude4Cons', 'T', INFO_TABLE, EXTERNAL, 'Prelude.:')

def compile(interp, imodule, extern=None):
  compileM = CxxCompiler(interp, imodule, extern)
  return compileM.compile()

def disableRecursionLimit(f):
  limit = sys.getrecursionlimit()
  @functools.wraps(f)
  def decorator(*args, **kwds):
    try:
      sys.setrecursionlimit(1<<30)
      return f(*args, **kwds)
    finally:
      sys.setrecursionlimit(limit)
  return decorator

class TargetObject(object):
  SECTIONS = (
      '.header'
    , '.footer'
    , '.infotab'      # InfoTable definitions.
    , '.infotab.fwd'  # InfoTable forward declarations.
    , '.module'       # Module definition.
    , '.rodata'       # Value sets, string literals.
    , '.stepfunc'     # Step function definitions.
    , '.stepfunc.fwd' # Step function forward declarations.
    , '.datatype'     # Type definitions.
    , '.datatype.fwd' # Type definition forward declarations.
    )

  def __init__(self, codetype, unitname):
    self.codetype = codetype
    self.unitname = unitname
    self.sections = collections.defaultdict(list) # {str: [str]}
    self.symtab = {}   # {str: Symbol}
    # After compilation, imodule_linked contains an IModule in which every
    # IFunction body is implemented as an ILink object that references a symbol
    # defined in this target object.
    self.imodule_linked = None

  def __getitem__(self, sectname):
    assert sectname in self.SECTIONS
    return self.sections[sectname]

  def __repr__(self):
    return '<%r TargetObject for %r>' % (self.codetype, self.unitname)


class CxxCompiler(object):
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
    self.interp = interp
    self.imodule = imodule
    moduleobj = interp.module(imodule.fullname)
    self.module_handle = handle.getHandle(moduleobj)
    self.extern = extern
    self.target_object = TargetObject('C++', imodule.fullname)
    self.count = itertools.count()

  def insert_symbol(self, symbol):
    tab = self.target_object.symtab
    existing = tab.get(symbol.tgtname)
    if existing is None:
      tab[symbol.tgtname] = symbol
      return True
    else:
      assert symbol.tgtname == existing.tgtname
      assert symbol.kind    == existing.kind
      assert symbol.descr == existing.descr
      if symbol.stat == DEFINED:
        if existing.stat == DEFINED:
          raise CompileError('multiple definition of %r' % symbol.descr)
        else:
          tab[symbol.tgtname] = symbol
          return True
    return False

  def make_private_name(self, kind):
    i = next(self.count)
    return mangle([str(i)], kind)

  @formatDocstring(config.python_package_name())
  @disableRecursionLimit
  def compile(self):
    '''
    Performs compilation.

    Returns:
      A target object containing object code and with imodule_linked set to non-None.

    '''
    header = self.target_object['.header']
    header.append('#include "cyrt/cyrt.hpp"')
    header.append('')
    header.append('using namespace cyrt;')
    header.append('namespace curryprog {')

    footer = self.target_object['.footer']
    footer.append('} // curryprog')

    assert self.target_object.imodule_linked is None
    self.target_object.imodule_linked = self.compileEx(self.imodule)
    return self.target_object

  @visitation.dispatch.on('icy')
  def compileEx(self, icy):
    '''
    Compiles an ICurry object.

    Updates the TargetObject and returns a new ICurry 'interface' object in which
    each function body has been replaced with IMaterial.

    Args:
      ``icy``
        An IPackage, IModule, or IFunction to compile.

    Returns:
      The ICurry interface.
    '''
    raise TypeError('Cannot compile type %r' % type(icy).__name__)

  @compileEx.when(icurry.IModule)
  def compileEx(self, imodule):
    for itype in six.itervalues(imodule.types):
      # if not itype.is_builtin  ### FIXME
      self.compileEx(itype)
    functions = [
        self.compileEx(ifun)
            for ifun in six.itervalues(imodule.functions)
                if not ifun.is_builtin
      ]
    return imodule.copy(functions=functions)

  @compileEx.when(icurry.IFunction)
  def compileEx(self, ifun):
    # Build the symbol and update the symbol table.
    h_stepfunc = mangle(ifun.splitname(), STEP_FUNCTION)
    symbol = Symbol(h_stepfunc, DEFINED, STEP_FUNCTION, ifun.fullname)
    if self.insert_symbol(symbol):
      # Append to section '.stepfunc.fwd'.
      self.target_object['.stepfunc.fwd'].append(
          'tag_type %s(RuntimeState *, Configuration *);' % h_stepfunc
        )

    # Append to section '.stepfunc'.
    out = self.target_object['.stepfunc']
    if out:
      out.append('')
    out.append('/****** %s ******/' % ifun.fullname)
    out.append('tag_type %s(RuntimeState * rts, Configuration * C)' % h_stepfunc)
    linesF = [] # the function body
    out.append(linesF)

    # Compile the function body.
    while True:
      # Needed??
      # varinfo = analysis.varinfo(ifun.body)
      linesF.clear()
      try:
        self.compileF(ifun, linesF)
      except ExternallyDefined as e:
        # Retry if compileF resolved an external definition.
        ifun = e.ifun
      else:
        break

    # Emit the info table.
    h_info = mangle(ifun.splitname(), INFO_TABLE)
    if h_info not in self.target_object.symtab:
      self.target_object['.infotab.fwd'].append(
          'extern InfoTable const %s;' % h_info
        )

    symbol = Symbol(h_info, DEFINED, INFO_TABLE, ifun.fullname)
    inserted = self.insert_symbol(symbol)
    assert inserted

    infotab = self.target_object['.infotab']
    infotab.append('InfoTable const %s{'       % h_info)
    infotab.append('    /*tag*/        T_FUNC')
    infotab.append('  , /*arity*/      %s'     % ifun.arity)
    infotab.append('  , /*alloc_size*/ sizeof(Head) + sizeof(Arg[%s])' % ifun.arity)
    infotab.append('  , /*flags*/      F_STATIC_OBJECT')
    infotab.append('  , /*name*/       %s'     % _dquote(ifun.name))
    infotab.append('  , /*format*/     "%s"'   % ('p' * ifun.arity))
    infotab.append('  , /*step*/       %s'     % h_stepfunc)
    infotab.append('  , /*typecheck*/  nullptr')
    infotab.append('  , /*type*/       nullptr')
    infotab.append('  };')
    infotab.append('')

    return ifun.copy(body=icurry.ILink(h_stepfunc))

  @compileEx.when(icurry.IDataType)
  def compileEx(self, itype):
    h_datatype = mangle(itype.splitname(), DATA_TYPE)
    symbol = Symbol(h_datatype, DEFINED, DATA_TYPE, itype.fullname)
    inserted = self.insert_symbol(symbol)
    assert inserted

    self.target_object['.datatype.fwd'].append(
        'extern Type const %s;' % h_datatype
      )
    
    constructor_handles = []
    infotab = self.target_object['.infotab']
    for i,ictor in enumerate(itype.constructors):
      h_info = mangle(ictor.splitname(), INFO_TABLE)
      constructor_handles.append(h_info)
      symbol = Symbol(h_info, DEFINED, INFO_TABLE, ictor.fullname)
      inserted = self.insert_symbol(symbol)
      assert inserted
      if h_info not in self.target_object.symtab:
        self.target_object['.infotab.fwd'].append(
            'extern InfoTable const %s;' % h_info
          )

      flags = self.interp.symbol(ictor.fullname).info.flags # FIXME
      infotab.append('InfoTable const %s{'     % h_info)
      infotab.append('    /*tag*/        T_CTOR + %s'   % str(i))
      infotab.append('  , /*arity*/      %s'   % ictor.arity)
      infotab.append('  , /*alloc_size*/ sizeof(Head) + sizeof(Arg[%s])' % ictor.arity)
      infotab.append('  , /*flags*/      F_STATIC_OBJECT | %s' % flags)
      infotab.append('  , /*name*/       %s'   % _dquote(ictor.name))
      infotab.append('  , /*format*/     "%s"' % ('p' * ictor.arity))
      infotab.append('  , /*step*/       %s'   % h_info)
      infotab.append('  , /*typecheck*/  %s'   % 'nullptr')
      infotab.append('  , /*type*/       %s'   % h_datatype)
      infotab.append('  };')
      infotab.append('')

    datatype = self.target_object['.datatype']
    h_ctortable = mangle(itype.splitname(), CONSTRUCTOR_TABLE)
    datatype.append(
        'static InfoTable const * %s[] = { %s };' % (
            h_ctortable, ', '.join(constructor_handles)
          )
      )
    datatype.append(
        'Type const %s { %s, %s, %r, F_STATIC_OBJECT };' % (
            h_datatype, h_ctortable, 't', len(itype.constructors)
          )
      )
    datatype.append('')

  ################
  ### compileF ###
  ################

  @visitation.dispatch.on('iobj')
  def compileF(self, iobj, linesF):
    assert False

  @compileF.when(collections.Sequence, no=str)
  def compileF(self, seq, linesF):
    for x in seq:
      self.compileF(x, linesF)

  @compileF.when(icurry.IFunction)
  def compileF(self, ifun, linesF):
    try:
      return self.compileF(ifun.body, linesF)
    except CompileError as e:
      raise CompileError(
          'failed to compile function %r: %s' % (ifun.fullname, e)
        )

  @compileF.when(icurry.IExternal)
  def compileF(self, iexternal, linesF):
    try:
      localname = iexternal.symbolname[len(self.extern.fullname)+1:]
      ifun = self.extern.functions[localname]
    except (KeyError, AttributeError):
      msg = 'external function %r is not defined' % iexternal.symbolname
      logger.warn(msg)
      stmt = icurry.IReturn(icurry.IFCall('Prelude.prim_error', [msg]))
      body = icurry.IBody(stmt)
      self.compileF(body, linesF)
    else:
      raise ExternallyDefined(ifun)

  @compileF.when(icurry.IBody)
  def compileF(self, function, linesF):
    linesF.append('Cursor _0 = C->cursor();')
    linesF.extend(self.compileS(function.block))

  @compileF.when(icurry.IBuiltin)
  def compileF(self, ibuiltin, linesF):
    raise CompileError('expected a built-in definition')

  @compileF.when(icurry.IStatement)
  def compileF(self, stmt, linesF):
    linesS = list(self.compileS(stmt))
    linesF.append(linesS)

  ################
  ### compileS ###
  ################

  @visitation.dispatch.on('stmt')
  def compileS(self, stmt):
    '''
    Compile a statement into nested lists of target code lines.
    '''
    assert False

  @compileS.when(collections.Sequence, no=str)
  def compileS(self, seq):
    for lines in (self.compileS(x) for x in seq):
      for line in lines:
        yield line

  @compileS.when(icurry.IVarDecl)
  def compileS(self, vardecl):
    varname = self.compileE(vardecl.lhs)
    yield 'Variable %s;' % varname

  @compileS.when(icurry.IFreeDecl)
  def compileS(self, vardecl):
    varname = self.compileE(vardecl.lhs)
    yield 'auto %s = rts->freshvar();' % varname

  @compileS.when(icurry.IVarAssign)
  def compileS(self, assign):
    lhs = self.compileE(assign.lhs, primary=True)
    rhs = self.compileE(assign.rhs, primary=True)
    if isinstance(assign.rhs, icurry.ICall):
      tmpname = 'tmp%s' % lhs
      yield 'Node * %s = %s;' % (tmpname, rhs)
      yield '%s.target = %s;' % (lhs, tmpname)
    else:
      yield '%s = %s;' % (lhs, rhs)

  @compileS.when(icurry.INodeAssign)
  def compileS(self, assign):
    lhs = self.compileE(assign.lhs)
    rhs = self.compileE(assign.rhs, primary=True)
    yield '%s = %s;' % (lhs, rhs)

  @compileS.when(icurry.IBlock)
  def compileS(self, block):
    for sect in [block.vardecls, block.assigns, block.stmt]:
      for line in self.compileS(sect):
        yield line

  @compileS.when(icurry.IExempt)
  def compileS(self, exempt):
    yield 'return _0->make_failure();'

  @compileS.when(icurry.IReturn)
  def compileS(self, ret):
    primary = isinstance(ret.expr, icurry.IReference)
    expr = self.compileE(ret.expr, primary=primary)
    yield '_0->forward_to(%s);' % expr
    yield 'return T_FWD;'

  @compileS.when(icurry.ICaseCons)
  def compileS(self, icase):
    assert icase.branches
    infoname = icase.branches[0].symbolname
    typedef = self.interp.symbol(infoname).typedef
    h_typename = mangle(typedef.icurry.splitname(), DATA_TYPE)
    symbol = Symbol(h_typename, UNDEFINED, DATA_TYPE, typedef.fullname)
    if self.insert_symbol(symbol):
      self.target_object['.datatype.fwd'].append(
          'extern Type const %s;' % h_typename
        )

    varident = self.compileE(icase.var)
    yield 'auto tag = rts->hnf(C, &%s, &%s);' % (varident, h_typename)
    yield 'switch(tag)'
    switchbody = []
    for branch in icase.branches:
      value = self.interp.symbol(branch.symbolname).info.tag
      switchbody.append(('case %s:' % value, branch.symbolname))
      switchbody.append(list(self.compileS(branch.block)))
    switchbody.append('default: return tag;')
    yield switchbody

  @compileS.when(icurry.ICaseLit)
  def compileS(self, icase):
    h_sel = self.compileE(icase.var)
    values = tuple(branch.lit.value for branch in icase.branches)
    h_values = self.make_private_name(VALUE_SET)
    symbol = Symbol(h_values, DEFINED, VALUE_SET, '<literal case values>')
    inserted = self.insert_symbol(symbol)
    assert inserted
    self.target_object['.rodata'].append(
        'static %s constexpr %s[] = {%s};' % (
            _datatype(values), h_values, ', '.join(str(v) for v in values)
          )
      )

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

  ################
  ### compileE ###
  ################

  @visitation.dispatch.on('expr')
  def compileE(self, expr, primary=False):
    '''
    Compile an expression into a string.  For primary expressions, the string
    evaluates to a value (boxed or unboxed).  For non-primary expressions, it
    contains comma-separated arguments that may be passed to the Node constructor
    or Node->forward_to.
    '''
    assert False

  @compileE.when(icurry.IVar)
  def compileE(self, ivar, primary=False):
    return '_%s' % ivar.vid

  @compileE.when(icurry.IVarAccess)
  def compileE(self, ivaraccess, primary=False):
    return '%s[%s]' % (
        self.compileE(ivaraccess.var, primary=primary)
      , ','.join(map(str, ivaraccess.path))
      )

  @compileE.when(icurry.ILiteral)
  def compileE(self, iliteral, primary=False):
    typename = iliteral.fullname
    typedef = self.interp.type(typename)
    h_typename = mangle(typedef.icurry.splitname(), DATA_TYPE)
    symbol = Symbol(h_typename, UNDEFINED, DATA_TYPE, typename)
    if self.insert_symbol(symbol):
      self.target_object['.datatype.fwd'].append(
         'extern Type const %s;' % h_typename
       )

    text = '&%s, Arg(%r)' % (h_typename, iliteral.value)
    return 'Node::create(%s)' % text if primary else text

  @compileE.when(icurry.IString)
  def compileE(self, istring, primary=False):
    string = strings.ensure_str(istring.value)
    h_string = self.make_private_name(STRING_DATA)
    symbol = Symbol(h_string, DEFINED, STRING_DATA, '<string data %r>' % string)
    if self.insert_symbol(symbol):
      self.target_object['.rodata'].append(
          'static char const * %s = %s;' % (h_string, _dquote(string))
        )

    text = '&CString_Info, Arg(%s)' % h_string
    return 'Node::create(%s)' % text if primary else text

  @compileE.when(icurry.IUnboxedLiteral)
  def compileE(self, iunboxed, primary=False):
    return repr(iunboxed)

  @compileE.when(icurry.ILit)
  def compileE(self, ilit, primary=False):
    return self.compileE(ilit.lit, primary)

  @compileE.when(icurry.ICall)
  def compileE(self, icall, primary=False):
    infoname = icall.symbolname
    info = self.interp.symbol(infoname)
    h_info = mangle(info.icurry.splitname(), INFO_TABLE)
    symbol = Symbol(h_info, UNDEFINED, INFO_TABLE, infoname)
    if self.insert_symbol(symbol):
      self.target_object['.infotab.fwd'].append(
          'extern InfoTable const %s;' % h_info
        )

    subexprs = (self.compileE(x, primary=True) for x in icall.exprs)
    text = '&%s%s' % (h_info, ''.join(', ' + e for e in subexprs))
    return 'Node::create(%s)' % text if primary else text

  @compileE.when(icurry.IPartialCall)
  def compileE(self, ipcall, primary=False):
    infoname = ipcall.symbolname
    info = self.interp.symbol(infoname)
    h_info = mangle(info.icurry.splitname(), INFO_TABLE)
    symbol = Symbol(h_info, UNDEFINED, INFO_TABLE, infoname)
    if self.insert_symbol(symbol):
      self.target_object['.infotab.fwd'].append(
          'extern InfoTable const %s;' % h_info
        )

    subexprs = (self.compileE(x, primary=True) for x in ipcall.exprs)
    text = '&%s%s' % (
        h_info
      , ''.join(', ' + e for e in subexprs)
      )
    # 'primary' intentionally ignored.
    return 'Node::create_partial(%s)' % text

  @compileE.when(icurry.IOr)
  def compileE(self, ior, primary=False):
    infoname = 'Prelude.?'
    info = self.interp.symbol(infoname)
    h_info = mangle(info.icurry.splitname(), INFO_TABLE)
    symbol = Symbol(h_info, UNDEFINED, INFO_TABLE, infoname)
    self.insert_symbol(symbol)

    text = "&%s, %s, %s" % (
        h_info
      , self.compileE(ior.lhs, primary=True)
      , self.compileE(ior.rhs, primary=True)
      )
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
