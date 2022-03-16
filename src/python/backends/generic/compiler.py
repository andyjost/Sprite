from ...exceptions import CompileError
from ... import config, icurry
from ...utility import formatDocstring, maxrecursion, strings, visitation
import abc, collections, itertools, logging, re, six

logger = logging.getLogger(__name__)

__all__ = [
    'CompilerBase', 'ExternallyDefined', 'SymbolTable', 'TargetObject'
  , 'decode', 'demangle', 'encode', 'mangle'

  , 'CONSTRUCTOR_TABLE', 'DATA_TYPE', 'DEFINED', 'INFO_TABLE', 'STEP_FUNCTION'
  , 'STRING_DATA', 'UNDEFINED', 'VALUE_SET'
  ]


class ExternallyDefined(Exception):
  '''
  Raised to indicate that a function is externally defined.  Provides the
  replacement.
  '''
  def __init__(self, ifun):
    self.ifun = ifun

# Symbol kind.
CONSTRUCTOR_TABLE = 'CONSTRUCTOR_TABLE'
DATA_TYPE         = 'DATA_TYPE'     # A Curry data type (for narrowing).
INFO_TABLE        = 'INFO_TABLE'    # Constructor or Function info table.
STEP_FUNCTION     = 'STEP_FUNCTION' # A step function.
STRING_DATA       = 'STRING_DATA'   # Static string data.
VALUE_SET         = 'VALUE_SET'     # Case values (for narrowing).

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
    DATA_TYPE         : 'D'
  , INFO_TABLE        : 'I'
  , STRING_DATA       : 'S'
  , VALUE_SET         : 'V'
  , STEP_FUNCTION     : 'F'
  , CONSTRUCTOR_TABLE : 'C'
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
    , '.stepfunc.fwd' # Step function forward declarations.
    , '.infotab.fwd'  # InfoTable forward declarations.
    , '.datatype.fwd' # Type definition forward declarations.
  ### Read-only data.
    , '.strings'      # String literals.
    , '.valuesets'    # Value sets.
  ### Code.
    , '.stepfunc'     # Step function definitions.
  ### Object definitions.
    , '.infotab'      # InfoTable definitions.
    , '.datatype'     # Type definitions.
    , '.module'       # Module definition.
    )

  def __init__(self, codetype, unitname):
    self.codetype = codetype
    self.unitname = unitname
    self.sections = collections.defaultdict(list) # {str: [str]}
    self.symtab = SymbolTable()
    # After compilation, imodule_linked contains an IModule in which every
    # IFunction body is implemented as an ILink object that references a symbol
    # defined in this target object.
    self.imodule_linked = None

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
        , 'vEmitStepfuncFwd'
        , 'vEmitInfotabFwd'
        , 'vEmitDataTypeFwd'
        , 'vEmitStepfuncHead'
        , 'vEmitStepfuncEntry'
        , 'vEmitFunctionInfotab'
        , 'vEmitConstructorInfotab'
        , 'vEmitDataType'
        , 'vEmitStringLiteral'
        , 'vEmitValueSetLiteral'
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
    self.extern = extern
    self.target_object = TargetObject(self.CODE_TYPE, imodule.fullname)
    self.counts = collections.defaultdict(itertools.count)

  def next_private_symbolname(self, kind):
    i = next(self.counts[kind])
    return mangle(['_%s' % i], kind)

  def importSymbol(self, symbolname):
    '''Import a symbol into the taget object by name.'''
    info = self.interp.symbol(symbolname)
    h_info = self.vGetSymbolName(info.icurry, INFO_TABLE)
    if self.symtab.insert(h_info, INFO_TABLE, symbolname):
      self.target_object['.infotab.fwd'].extend(self.vEmitInfotabFwd(h_info))
    return h_info

  def internStringLiteral(self, string):
    h_string = self.next_private_symbolname(STRING_DATA)
    self.symtab.insert(h_string, STRING_DATA, '<string data: %r>' % string)
    prog_text = self.vEmitStringLiteral(h_string, string)
    self.target_object['.strings'].extend(prog_text)
    self.symtab.make_defined(h_string)
    return h_string

  def internValueSetLiteral(self, values):
    h_valueset = self.next_private_symbolname(VALUE_SET)
    self.symtab.insert(h_valueset, VALUE_SET, '<case values: %r>' % (values,))
    prog_text = self.vEmitValueSetLiteral(h_valueset, values)
    self.target_object['.valuesets'].extend(prog_text)
    self.symtab.make_defined(h_valueset)
    return h_valueset

  @property
  def symtab(self):
    return self.target_object.symtab

  def compile(self):
    '''
    Performs compilation.

    Returns:
      A target object containing object code and with imodule_linked set to non-None.

    '''
    self.target_object['.header'].extend(self.vEmitHeader())

    assert self.target_object.imodule_linked is None
    with maxrecursion():
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
    types = [
        self.compileEx(itype)
            for itype in six.itervalues(imodule.types)
                # if not itype.is_builtin  ### FIXME
      ]
    functions = [
        self.compileEx(ifun)
            for ifun in six.itervalues(imodule.functions)
                if not ifun.is_builtin
      ]
    return imodule.copy(functions=functions)

  @compileEx.when(icurry.IFunction)
  def compileEx(self, ifun):
    # Build the symbol and update the symbol table.
    h_stepfunc = self.vGetSymbolName(ifun, STEP_FUNCTION)
    self.symtab.insert(
        h_stepfunc, STEP_FUNCTION, 'step function for %r' % ifun.fullname
      )
    self.target_object['.stepfunc.fwd'].extend(self.vEmitStepfuncFwd(h_stepfunc))

    # Append to section '.stepfunc'.
    out = self.target_object['.stepfunc']
    if out:
      out.append('')
    out.extend(self.vEmitStepfuncHead(ifun, h_stepfunc))
    linesF = [] # the function body
    out.append(linesF)

    # Compile the function body.
    while True:
      linesF.clear()
      try:
        self.compileF(ifun, linesF)
      except ExternallyDefined as e:
        # Retry if compileF resolved an external definition.
        ifun = e.ifun
      else:
        break

    self.symtab.make_defined(h_stepfunc)

    # Emit the info table.
    h_info = self.vGetSymbolName(ifun, INFO_TABLE)
    self.symtab.insert(h_info, INFO_TABLE, 'info table for %r' % ifun.fullname)
    self.target_object['.infotab.fwd'].extend(self.vEmitInfotabFwd(h_info))
    self.target_object['.infotab'].extend(self.vEmitFunctionInfotab(ifun, h_info, h_stepfunc))
    self.symtab.make_defined(h_info)

    return ifun.copy(body=icurry.ILink(h_stepfunc))

  @compileEx.when(icurry.IDataType)
  def compileEx(self, itype):
    h_datatype = self.vGetSymbolName(itype, DATA_TYPE)
    self.symtab.insert(h_datatype, DATA_TYPE, itype.fullname)
    self.target_object['.datatype.fwd'].extend(self.vEmitDataTypeFwd(h_datatype))
    ctor_handles = []
    for i,ictor in enumerate(itype.constructors):
      h_ctorinfo = self.vGetSymbolName(ictor, INFO_TABLE)
      ctor_handles.append(h_ctorinfo)
      self.symtab.insert(
          h_ctorinfo, INFO_TABLE, 'info table for %r' % ictor.fullname
        )
      self.target_object['.infotab.fwd'].extend(self.vEmitInfotabFwd(h_ctorinfo))
      self.target_object['.infotab'].extend(
          self.vEmitConstructorInfotab(i, ictor, h_ctorinfo, h_datatype)
        )
      self.symtab.make_defined(h_ctorinfo)
    self.target_object['.datatype'].extend(
        self.vEmitDataType(itype, h_datatype, ctor_handles)
      )
    self.symtab.make_defined(h_datatype)

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
  def compileF(self, ibody, linesF):
    linesF.extend(self.vEmitStepfuncEntry())
    linesF.extend(self.compileS(ibody.block))

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
    infoname = icase.branches[0].symbolname
    datatype = self.interp.symbol(infoname).typedef
    h_datatype = self.vGetSymbolName(datatype.icurry, DATA_TYPE)
    if self.symtab.insert(h_datatype, DATA_TYPE, datatype.fullname):
      self.target_object['.datatype.fwd'].extend(self.vEmitDataTypeFwd(h_datatype))
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
    ctorname = iliteral.fullname
    ctor = self.interp.symbol(ctorname)
    h_ctor = self.vGetSymbolName(ctor.icurry, INFO_TABLE)
    if self.symtab.insert(h_ctor, INFO_TABLE, ctorname):
      self.target_object['.infotab.fwd'].extend(vEmitInfotabFwd(h_ctor))
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
    infoname = icall.symbolname
    info = self.interp.symbol(infoname)
    h_info = self.vGetSymbolName(info.icurry, INFO_TABLE)
    if self.symtab.insert(h_info, INFO_TABLE, infoname):
      self.target_object['.infotab.fwd'].extend(self.vEmitInfotabFwd(h_info))
    args = (self.compileE(x, primary=True) for x in icall.exprs)
    return self.vEmit_compileE_ICall(icall, h_info, args, primary)

  @compileE.when(icurry.IPartialCall)
  def compileE(self, ipcall, primary=False):
    infoname = ipcall.symbolname
    info = self.interp.symbol(infoname)
    h_info = self.vGetSymbolName(info.icurry, INFO_TABLE)
    if self.symtab.insert(h_info, INFO_TABLE, infoname):
      self.target_object['.infotab.fwd'].extend(self.vEmitInfotabFwd(h_info))
    args = (self.compileE(x, primary=True) for x in ipcall.exprs)
    return self.vEmit_compileE_IPartialCall(ipcall, h_info, args, primary)

  @compileE.when(icurry.IOr)
  def compileE(self, ior, primary=False):
    h_choice = self.importSymbol('Prelude.?')
    lhs = self.compileE(ior.lhs, primary=True)
    rhs = self.compileE(ior.rhs, primary=True)
    return self.vEmit_compileE_IOr(ior, h_choice, lhs, rhs, primary)



