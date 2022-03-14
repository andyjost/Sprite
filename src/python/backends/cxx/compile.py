from ...exceptions import CompileError
from ..generic.compiler import ExternallyDefined
from ..generic.compiler.render import CXX_RENDERER
from ... import config, icurry
# from ...objects import handle
from ...utility import formatDocstring, strings, visitation
import collections, functools, itertools, json, logging, re, six, sys

logger = logging.getLogger(__name__)

__all__ = ['compile', 'demangle', 'mangle', 'write_module']

def compile(interp, imodule, extern=None):
  compileM = CxxCompiler(interp, imodule, extern)
  return compileM.compile()

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

KIND_CODE_R = {v:k for k,v in KIND_CODE.items()}

# Symbol status.
DEFINED   = 'T'
UNDEFINED = 'U'

Symbol = collections.namedtuple('Symbol', ['name', 'stat', 'kind', 'descr'])

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

# E.g.: the symbol for Prelude.: might appear in the symbol table for the
# Prelude as follows:
#
#   ('_7Prelude4Cons', 'T', INFO_TABLE, EXTERNAL, 'Prelude.:')

def recursionLimitDisabled(f):
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
    self.extern = extern
    self.target_object = TargetObject('C++', imodule.fullname)
    self.counts = collections.defaultdict(itertools.count)

  def insert_symbol(self, name, kind, descr):
    tab = self.target_object.symtab
    if name not in tab:
      tab[name] = Symbol(name, UNDEFINED, kind, descr)
      return True
    else:
      return False

  def make_symbol_defined(self, name):
    tab = self.target_object.symtab
    existing = tab.get(name)
    if existing and existing.stat == DEFINED:
      raise CompileError('multiple definition of %r' % existing.descr)
    else:
      assert name == existing.name
      tab[name] = Symbol(name, DEFINED, existing.kind, existing.descr)

  def next_private_symbolname(self, kind):
    i = next(self.counts[kind])
    return mangle(['_%s' % i], kind)

  @formatDocstring(config.python_package_name())
  @recursionLimitDisabled
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
    self.insert_symbol(
        h_stepfunc, STEP_FUNCTION, 'step function for %r' % ifun.fullname
      )
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
      linesF.clear()
      try:
        self.compileF(ifun, linesF)
      except ExternallyDefined as e:
        # Retry if compileF resolved an external definition.
        ifun = e.ifun
      else:
        break

    self.make_symbol_defined(h_stepfunc)

    # Emit the info table.
    h_info = mangle(ifun.splitname(), INFO_TABLE)
    self.insert_symbol(h_info, INFO_TABLE, 'info table for %r' % ifun.fullname)
    self.target_object['.infotab.fwd'].append(
        'extern InfoTable const %s;' % h_info
      )

    infotab = self.target_object['.infotab']
    infotab.append('InfoTable const %s{'                 % h_info)
    infotab.append('    /*tag*/        T_FUNC')
    infotab.append('  , /*arity*/      %s'               % ifun.arity)
    infotab.append('  , /*alloc_size*/ %s'               % _sizeof(ifun.arity))
    infotab.append('  , /*flags*/      F_STATIC_OBJECT')
    infotab.append('  , /*name*/       %s'               % _dquote(ifun.name))
    infotab.append('  , /*format*/     "%s"'             % ('p' * ifun.arity))
    infotab.append('  , /*step*/       %s'               % h_stepfunc)
    infotab.append('  , /*typecheck*/  nullptr')
    infotab.append('  , /*type*/       nullptr')
    infotab.append('  };')
    infotab.append('')
    self.make_symbol_defined(h_info)

    return ifun.copy(body=icurry.ILink(h_stepfunc))

  @compileEx.when(icurry.IDataType)
  def compileEx(self, itype):
    h_datatype = mangle(itype.splitname(), DATA_TYPE)
    self.insert_symbol(h_datatype, DATA_TYPE, itype.fullname)
    self.target_object['.datatype.fwd'].append(
        'extern Type const %s;' % h_datatype
      )
    
    constructor_handles = []
    infotab = self.target_object['.infotab']
    for i,ictor in enumerate(itype.constructors):
      h_ctorinfo = mangle(ictor.splitname(), INFO_TABLE)
      constructor_handles.append(h_ctorinfo)
      self.insert_symbol(
          h_ctorinfo, INFO_TABLE, 'info table for %r' % ictor.fullname
        )
      self.target_object['.infotab.fwd'].append(
          'extern InfoTable const %s;' % h_ctorinfo
        )

      flags = ictor.metadata.get('all.flags', 0)
      infotab.append('InfoTable const %s{'                     % h_ctorinfo)
      infotab.append('    /*tag*/        T_CTOR + %s'          % str(i))
      infotab.append('  , /*arity*/      %s'                   % ictor.arity)
      infotab.append('  , /*alloc_size*/ %s'                   % _sizeof(ictor.arity))
      infotab.append('  , /*flags*/      F_STATIC_OBJECT | %s' % flags)
      infotab.append('  , /*name*/       %s'                   % _dquote(ictor.name))
      infotab.append('  , /*format*/     "%s"'                 % ('p' * ictor.arity))
      infotab.append('  , /*step*/       nullptr')
      infotab.append('  , /*typecheck*/  nullptr')
      infotab.append('  , /*type*/       &%s'                  % h_datatype)
      infotab.append('  };')
      infotab.append('')

      self.make_symbol_defined(h_ctorinfo)

    datatype = self.target_object['.datatype']
    h_ctortable = mangle(itype.splitname(), CONSTRUCTOR_TABLE)
    datatype.append(
        'static InfoTable const * %s[] = { %s };' % (
            h_ctortable, ', '.join('&%s' % h for h in constructor_handles)
          )
      )
    datatype.append(
        'Type const %s { %s, %r, %r, F_STATIC_OBJECT };' % (
            h_datatype, h_ctortable, 't', len(itype.constructors)
          )
      )
    datatype.append('')
    self.make_symbol_defined(h_datatype)

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
    if self.insert_symbol(h_typename, DATA_TYPE, typedef.fullname):
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
    h_values = self.next_private_symbolname(VALUE_SET)
    self.insert_symbol(h_values, VALUE_SET, '<literal case values>')
    self.target_object['.valuesets'].append(
        'static %s constexpr %s[] = {%s};' % (
            _datatype(values), h_values, ', '.join(str(v) for v in values)
          )
      )
    self.make_symbol_defined(h_values)

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
    ctorname = iliteral.fullname
    ctor = self.interp.symbol(ctorname)
    h_ctor = mangle(ctor.icurry.splitname(), INFO_TABLE)
    if self.insert_symbol(h_ctor, INFO_TABLE, ctorname):
      self.target_object['.infotab.fwd'].append(
         'extern InfoTable const %s;' % h_ctor
       )

    text = '&%s, Arg(%r)' % (h_ctor, iliteral.value)
    return 'Node::create(%s)' % text if primary else text

  @compileE.when(icurry.IString)
  def compileE(self, istring, primary=False):
    string = strings.ensure_str(istring.value)
    h_string = self.next_private_symbolname(STRING_DATA)
    self.insert_symbol(h_string, STRING_DATA, '<string data %r>' % string)
    self.target_object['.strings'].append(
        'static char const * %s = %s;' % (h_string, _dquote(string))
      )
    self.make_symbol_defined(h_string)

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
    if self.insert_symbol(h_info, INFO_TABLE, infoname):
      self.target_object['.infotab.fwd'].append(
          'extern InfoTable const %s;' % h_info
        )
    else:
      assert 'extern InfoTable const %s;' % h_info in self.target_object['.infotab.fwd']

    subexprs = (self.compileE(x, primary=True) for x in icall.exprs)
    text = '&%s%s' % (h_info, ''.join(', ' + e for e in subexprs))
    return 'Node::create(%s)' % text if primary else text

  @compileE.when(icurry.IPartialCall)
  def compileE(self, ipcall, primary=False):
    infoname = ipcall.symbolname
    info = self.interp.symbol(infoname)
    h_info = mangle(info.icurry.splitname(), INFO_TABLE)
    if self.insert_symbol(h_info, INFO_TABLE, infoname):
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
    if self.insert_symbol(h_info, INFO_TABLE, infoname):
      self.target_object['.infotab.fwd'].append(
          'extern InfoTable const %s;' % h_info
        )

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

def _sizeof(arity):
    return 'sizeof(Head) + sizeof(Arg[%s])' % arity

def write_module(target_object, stream, goal=None):
  render = CXX_RENDERER.renderLines
  for section_name in TargetObject.SECTIONS:
    section_data = target_object[section_name]
    section_text = render(section_data)
    stream.write(section_text)
    stream.write('\n')

