from ...exceptions import CompileError
from ... import config, icurry
from ...utility import formatDocstring, maxrecursion, strings, visitation
import abc, collections, itertools, logging, re, six

logger = logging.getLogger(__name__)

__all__ = [
    'CompilerBase', 'SymbolTable', 'TargetObject'
  , 'decode', 'demangle', 'encode', 'mangle'

  , 'CONSTRUCTOR_TABLE', 'DATA_TYPE', 'DEFINED', 'INFO_TABLE', 'STEP_FUNCTION'
  , 'STRING_DATA', 'UNDEFINED', 'VALUE_SET'
  ]


# Symbol kind.
CONSTRUCTOR_TABLE = 'CONSTRUCTOR_TABLE'
DATA_TYPE         = 'DATA_TYPE'         # A Curry data type (for narrowing).
INFO_TABLE        = 'INFO_TABLE'        # Constructor or Function info table.
MODULE_DEF        = 'MODULE_DEF'
STEP_FUNCTION     = 'STEP_FUNCTION'     # A step function.
STRING_DATA       = 'STRING_DATA'       # Static string data.
VALUE_SET         = 'VALUE_SET'         # Case values (for narrowing).
BUILTIN_FUNCTION  = 'BUILTIN_FUNCTION'  # A function provided by the execution environment.

# Symbol status.
DEFINED   = 'T'
UNDEFINED = 'U'

Symbol = collections.namedtuple('Symbol', ['name', 'stat', 'kind', 'descr'])
# E.g.: the symbol for Prelude.: might appear in the symbol table for the
# Prelude as follows:
#
#   ('_7Prelude4Cons', 'T', INFO_TABLE, EXTERNAL, 'Prelude.:')

class SymbolTable(dict): # {str: Symbol}
  def insert(self, name, kind, descr):
    if name not in self:
      self[name] = Symbol(name, UNDEFINED, kind, descr)
      return True
    else:
      return False

  def make_defined(self, name):
    existing = self[name]
    if existing.stat == DEFINED:
      raise CompileError('multiple definition of %r' % existing.descr)
    else:
      assert name == existing.name
      self[name] = Symbol(name, DEFINED, existing.kind, existing.descr)

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
    BUILTIN_FUNCTION  : 'B'
  , CONSTRUCTOR_TABLE : 'C'
  , DATA_TYPE         : 'D'
  , INFO_TABLE        : 'I'
  , MODULE_DEF        : 'M'
  , STEP_FUNCTION     : 'F'
  , STRING_DATA       : 'S'
  , VALUE_SET         : 'V'
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


class TargetObject(object):
  SECTIONS = (
      '.header'
  ### Forward declarations.
    , '.imports'        # Imported Curry modules.
    , '.stepfuncs.link' # Step function forward declarations.
    , '.infotabs.link'  # InfoTable forward declarations.
    , '.datatypes.link' # Type definition forward declarations.
  ### Read-only data.
    , '.strings'        # String literals.
    , '.valuesets'      # Value sets.
    , '.primitives'     # Primitive functions.
  ### Code.
    , '.stepfuncs'      # Step function definitions.
  ### Object definitions.
    , '.infotabs'       # InfoTable definitions.
    , '.datatypes'      # Type definitions.
    , '.moduledef'      # Module definition.
    , '.moduleimp'      # Module import.
  ###
    , '.footer'
    )

  def __init__(self, codetype, unitname):
    self.codetype = codetype
    self.unitname = unitname
    self.sections = collections.defaultdict(list) # {str: [str]}
    self.symtab = SymbolTable()

  def __getitem__(self, sectname):
    assert sectname in self.SECTIONS
    return self.sections[sectname]

  def __repr__(self):
    return '<%r TargetObject for %r>' % (self.codetype, self.unitname)


class CompilerBase(abc.ABC):
  # Customization points.
  CODE_TYPE = None

  def vGetSymbolName(self, iobj, kind):
    return mangle(iobj.splitname(), kind)

  locals().update({
      methname: abc.abstractmethod(lambda *args: None)
              for methname in [
          'vEmitHeader'
        , 'vEmitFooter'
        , 'vEmitImported'
        , 'vEmitStepfuncLink'
        , 'vEmitInfotabLink'
        , 'vEmitDataTypeLink'
        , 'vEmitStepfuncHeader'
        , 'vEmitStepfuncEntry'
        , 'vEmitBuiltinStepfunc'
        , 'vEmitFunctionInfotab'
        , 'vEmitConstructorInfotab'
        , 'vEmitDataType'
        , 'vEmitStringLiteral'
        , 'vEmitValueSetLiteral'
        , 'vEmitModuleDefinition'
        , 'vEmitModuleImport'
        , 'vEmit_compileS_IVarDecl'
        , 'vEmit_compileS_IFreeDecl'
        , 'vEmit_compileS_IVarAssign'
        , 'vEmit_compileS_INodeAssign'
        , 'vEmit_compileS_IExempt'
        , 'vEmit_compileS_IReturn'
        , 'vEmit_compileS_ICaseCons'
        , 'vEmit_compileS_ICaseLit'
        , 'vEmit_compileE_IVar'
        , 'vEmit_compileE_IVarAccess'
        , 'vEmit_compileE_ILiteral'
        , 'vEmit_compileE_IString'
        , 'vEmit_compileE_IUnboxedLiteral'
        , 'vEmit_compileE_ICall'
        , 'vEmit_compileE_IPartialCall'
        , 'vEmit_compileE_IOr'
        ]
    })

  @formatDocstring(config.python_package_name())
  def __init__(self, interp, iroot):
    '''
    Compiles ICurry to a C++ target object.

    Args:
      interp:
        The interpreter that owns this module.

      iroot:
        The ICurry object to compile.  Must be an IModule or IFunction.
    '''
    self.interp = interp
    self.iroot = iroot
    self.target_object = TargetObject(self.CODE_TYPE, iroot.fullname)
    self.counts = collections.defaultdict(itertools.count)
    self.intern_store = {}
    self._is_external_check = is_external_check(iroot)

  @property
  def root_isa_module(self):
    return isinstance(self.iroot, icurry.IModule)

  def isExternal(self, iobj):
    if self.iroot.modulename != iobj.modulename:
      return True
    else:
      return self._is_external_check(iobj)

  def next_private_symbolname(self, kind, suffix=None):
    i = next(self.counts[kind])
    if suffix is None:
      return mangle(['_%s' % i], kind)
    else:
      return mangle(['_%s' % i, suffix], kind)

  ### importSymbol
  @visitation.dispatch.on('symbol')
  def importSymbol(self, symbol):
    '''Import a symbol into the taget object by name.'''
    assert False

  @importSymbol.when(six.string_types)
  def importSymbol(self, symbolname):
    cy_symbol = self.interp.symbol(symbolname)
    return self.importSymbol(cy_symbol.icurry)

  @importSymbol.when(icurry.ISymbol)
  def importSymbol(self, isymbol):
    h_info, new = self.declareSymbol(isymbol)
    if new and self.isExternal(isymbol):
      self.target_object['.infotabs.link'].extend(self.vEmitInfotabLink(isymbol, h_info))
    return h_info

  ### declareSymbol
  def declareSymbol(self, isymbol):
    h_info = self.vGetSymbolName(isymbol, INFO_TABLE)
    new = self.symtab.insert(h_info, INFO_TABLE, 'info table for %r' % isymbol.fullname)
    return h_info, new

  ### importDataType
  @visitation.dispatch.on('symbol')
  def importDataType(self, symbol):
    '''Import a symbol into the taget object by name.'''
    assert False

  @importDataType.when(six.string_types)
  def importDataType(self, symbolname):
    cy_datatype = self.interp.type(symbolname)
    return self.importDataType(cy_datatype.icurry)

  @importDataType.when(icurry.ISymbol)
  def importDataType(self, itype):
    h_datatype, new = self.declareDataType(itype)
    if new and self.isExternal(itype):
      self.target_object['.datatypes.link'].extend(self.vEmitDataTypeLink(itype, h_datatype))
    return h_datatype

  ### declareDataType
  def declareDataType(self, itype):
    h_datatype = self.vGetSymbolName(itype, DATA_TYPE)
    new = self.symtab.insert(h_datatype, DATA_TYPE, 'datatype %r' % itype.fullname)
    return h_datatype, new

  def internStringLiteral(self, string):
    existing = self.intern_store.get(string)
    if existing is not None:
      return existing
    else:
      h_string = self.next_private_symbolname(STRING_DATA)
      self.symtab.insert(h_string, STRING_DATA, '<string data: %r>' % string)
      prog_text = self.vEmitStringLiteral(string, h_string)
      self.target_object['.strings'].extend(prog_text)
      self.symtab.make_defined(h_string)
      self.intern_store[string] = h_string
      return h_string

  def internValueSetLiteral(self, values):
    existing = self.intern_store.get(values)
    if existing is not None:
      return existing
    else:
      h_valueset = self.next_private_symbolname(VALUE_SET)
      self.symtab.insert(h_valueset, VALUE_SET, '<case values: %r>' % (values,))
      prog_text = self.vEmitValueSetLiteral(values, h_valueset)
      self.target_object['.valuesets'].extend(prog_text)
      self.symtab.make_defined(h_valueset)
      self.intern_store[values] = h_valueset
      return h_valueset

  def internBuiltinFunction(self, func, key):
    existing = self.intern_store.get(key)
    if existing is not None:
      return existing
    else:
      h_func = self.next_private_symbolname(BUILTIN_FUNCTION, func.__name__)
      self.symtab.insert(h_func, BUILTIN_FUNCTION, '<function: %r>' % func)
      prog_text = self.vEmitImportBackendFunction(func, h_func)
      self.target_object['.primitives'].extend(prog_text)
      self.symtab.make_defined(h_func)
      self.intern_store[key] = h_func
      return h_func

  @property
  def symtab(self):
    return self.target_object.symtab

  def compile(self):
    '''
    Performs compilation.

    Returns:
      A target object containing the generated object code.

    '''
    self.target_object['.header'].extend(self.vEmitHeader())
    with maxrecursion():
      self.compileEx(self.iroot)
    self.target_object['.footer'].extend(self.vEmitFooter())
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
    imported_names = set(imodule.imports)
    imported_names.update(imodule.splitname()[:-1])
    for imported in sorted(imported_names):
      self.target_object['.imports'].extend(self.vEmitImported(imported))

    types = [
        self.compileEx(itype)
            for itype in six.itervalues(imodule.types)
      ]
    functions = [
        self.compileEx(ifun)
            for ifun in six.itervalues(imodule.functions)
      ]
    h_module = self.vGetSymbolName(imodule, MODULE_DEF)
    self.symtab.insert(h_module, MODULE_DEF, 'module %r' % imodule.fullname)
    self.target_object['.moduledef'].extend(
        self.vEmitModuleDefinition(imodule, h_module)
      )
    self.symtab.make_defined(h_module)
    self.target_object['.moduleimp'].extend(
        self.vEmitModuleImport(imodule, h_module)
      )

  @compileEx.when(icurry.IFunction)
  def compileEx(self, ifun):
    # Build the symbol and update the symbol table.
    h_stepfunc = self.vGetSymbolName(ifun, STEP_FUNCTION)
    self.symtab.insert(
        h_stepfunc, STEP_FUNCTION, 'step function for %r' % ifun.fullname
      )
    self.target_object['.stepfuncs.link'].extend(
        self.vEmitStepfuncLink(ifun, h_stepfunc)
      )

    # Append to section '.stepfuncs'.
    out = self.target_object['.stepfuncs']
    if out:
      out.append('')
    out.extend(self.vEmitStepfuncHeader(ifun, h_stepfunc))
    linesF = [] # the function body
    out.append(linesF)
    self.compileF(ifun, h_stepfunc, linesF)
    self.symtab.make_defined(h_stepfunc)

    # Emit the info table.
    h_info, _ = self.declareSymbol(ifun)
    self.target_object['.infotabs'].extend(self.vEmitFunctionInfotab(ifun, h_info, h_stepfunc))
    self.symtab.make_defined(h_info)

  @compileEx.when(icurry.IDataType)
  def compileEx(self, itype):
    h_datatype, _ = self.declareDataType(itype)
    ctor_handles = []
    for ictor in itype.constructors:
      h_ctorinfo, _ = self.declareSymbol(ictor)
      ctor_handles.append(h_ctorinfo)
      self.target_object['.infotabs'].extend(
          self.vEmitConstructorInfotab(ictor, h_ctorinfo, h_datatype)
        )
      self.symtab.make_defined(h_ctorinfo)
    self.target_object['.datatypes'].extend(
        self.vEmitDataType(itype, h_datatype, ctor_handles)
      )
    self.symtab.make_defined(h_datatype)

  ################
  ### compileF ###
  ################

  @visitation.dispatch.on('iobj')
  def compileF(self, iobj, h_stepfunc, linesF):
    assert False

  @compileF.when(collections.Sequence, no=str)
  def compileF(self, seq, h_stepfunc, linesF):
    for x in seq:
      self.compileF(x, h_stepfunc, linesF)

  @compileF.when(icurry.IFunction)
  def compileF(self, ifun, h_stepfunc, linesF):
    if ifun.is_builtin:
      linesF.extend(self.vEmitBuiltinStepfunc(ifun, h_stepfunc))
    else:
      try:
        return self.compileF(ifun.body, h_stepfunc, linesF)
      except CompileError as e:
        raise CompileError(
            'failed to compile function %r: %s' % (ifun.fullname, e)
          )

  @compileF.when(icurry.IExternal)
  def compileF(self, iexternal, h_stepfunc, linesF):
    msg = 'external function %r is not defined' % iexternal.symbolname
    logger.warn(msg)
    stmt = icurry.IReturn(icurry.IFCall('Prelude.prim_error', [msg]))
    body = icurry.IBody(stmt)
    self.compileF(body, h_stepfunc, linesF)

  @compileF.when(icurry.IBody)
  def compileF(self, ibody, h_stepfunc, linesF):
    linesF.extend(self.vEmitStepfuncEntry())
    linesF.extend(self.compileS(ibody.block))

  @compileF.when(icurry.IBuiltin)
  def compileF(self, ibuiltin, h_stepfunc, linesF):
    assert False # handled, above, in case IFunction.

  @compileF.when(icurry.IStatement)
  def compileF(self, stmt, h_stepfunc, linesF):
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
    return self.vEmit_compileS_IVarDecl(vardecl, varname)

  @compileS.when(icurry.IFreeDecl)
  def compileS(self, vardecl):
    varname = self.compileE(vardecl.lhs)
    return self.vEmit_compileS_IFreeDecl(vardecl, varname)

  @compileS.when(icurry.IVarAssign)
  def compileS(self, assign):
    lhs = self.compileE(assign.lhs, primary=True)
    rhs = self.compileE(assign.rhs, primary=True)
    return self.vEmit_compileS_IVarAssign(assign, lhs, rhs)

  @compileS.when(icurry.INodeAssign)
  def compileS(self, assign):
    lhs = self.compileE(assign.lhs)
    rhs = self.compileE(assign.rhs, primary=True)
    return self.vEmit_compileS_INodeAssign(assign, lhs, rhs)

  @compileS.when(icurry.IBlock)
  def compileS(self, block):
    for sect in [block.vardecls, block.assigns, block.stmt]:
      for line in self.compileS(sect):
        yield line

  @compileS.when(icurry.IExempt)
  def compileS(self, exempt):
    return self.vEmit_compileS_IExempt(exempt)

  @compileS.when(icurry.IReturn)
  def compileS(self, iret):
    primary = isinstance(iret.expr, icurry.IReference)
    expr = self.compileE(iret.expr, primary=primary)
    return self.vEmit_compileS_IReturn(iret, expr)

  @compileS.when(icurry.ICaseCons)
  def compileS(self, icase):
    assert icase.branches
    cy_ctorobj = self.interp.symbol(icase.branches[0].symbolname)
    h_datatype = self.importDataType(cy_ctorobj.typename)
    varident = self.compileE(icase.var)
    return self.vEmit_compileS_ICaseCons(icase, h_datatype, varident)

  @compileS.when(icurry.ICaseLit)
  def compileS(self, icase):
    h_sel = self.compileE(icase.var)
    values = tuple(branch.lit.value for branch in icase.branches)
    h_values = self.internValueSetLiteral(values)
    return self.vEmit_compileS_ICaseLit(icase, h_sel, h_values)

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
    return self.vEmit_compileE_IVar(ivar)

  @compileE.when(icurry.IVarAccess)
  def compileE(self, ivaraccess, primary=False):
    var = self.compileE(ivaraccess.var, primary=primary)
    return self.vEmit_compileE_IVarAccess(ivaraccess, var)

  @compileE.when(icurry.ILiteral)
  def compileE(self, iliteral, primary=False):
    h_ctor = self.importSymbol(iliteral.fullname)
    return self.vEmit_compileE_ILiteral(iliteral, h_ctor, primary)

  @compileE.when(icurry.IString)
  def compileE(self, istring, primary=False):
    string = strings.ensure_str(istring.value)
    h_string = self.internStringLiteral(string)
    return self.vEmit_compileE_IString(istring, h_string, primary)

  @compileE.when(icurry.IUnboxedLiteral)
  def compileE(self, iunboxed, primary=False):
    return self.vEmit_compileE_IUnboxedLiteral(iunboxed, primary)

  @compileE.when(icurry.ILit)
  def compileE(self, ilit, primary=False):
    return self.compileE(ilit.lit, primary)

  @compileE.when(icurry.ICall)
  def compileE(self, icall, primary=False):
    h_info = self.importSymbol(icall.symbolname)
    args = (self.compileE(x, primary=True) for x in icall.exprs)
    return self.vEmit_compileE_ICall(icall, h_info, args, primary)

  @compileE.when(icurry.IPartialCall)
  def compileE(self, ipcall, primary=False):
    h_info = self.importSymbol(ipcall.symbolname)
    args = (self.compileE(x, primary=True) for x in ipcall.exprs)
    return self.vEmit_compileE_IPartialCall(ipcall, h_info, args, primary)

  @compileE.when(icurry.IOr)
  def compileE(self, ior, primary=False):
    lhs = self.compileE(ior.lhs, primary=True)
    rhs = self.compileE(ior.rhs, primary=True)
    return self.vEmit_compileE_IOr(ior, lhs, rhs, primary)


@visitation.dispatch.on('iobj')
def is_external_check(iobj):
  assert False

@is_external_check.when(icurry.IModule)
def is_external_check(imodule):

  @visitation.dispatch.on('iobj')
  def check(iobj):
    assert False

  @check.when((icurry.IDataType, icurry.IConstructor))
  def check(iobj):
    _, _, name = iobj.typename.rpartition('.')
    return itype.name not in imodule.types

  @check.when(icurry.IFunction)
  def check(ifun):
    return ifun.name not in imodule.functions

  return check

@is_external_check.when(icurry.IFunction)
def is_external_check(ifun):

  @visitation.dispatch.on('iobj')
  def check(iobj):
    assert False

  @check.when((icurry.IDataType, icurry.IConstructor))
  def check(iobj):
    return True

  @check.when(icurry.IFunction)
  def check(ifun2):
    return ifun2.name != ifun.name

  return check
