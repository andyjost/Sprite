from ...generic.compiler import function_compiler, ir, module_compiler
from .... import icurry
from ....utility import visitation
import collections

__all__ = ['compile']

def compile(interp, icy, extern=None):
  compileM = ModuleCompiler()
  return compileM.compile(interp, icy, extern)

class IR(ir.IR):
  CODETYPE = 'C++'

class ModuleCompiler(module_compiler.ModuleCompiler):
  @property
  def IR(self):
    return IR

  @property
  def FunctionCompiler(self):
    return FunctionCompiler

  def synthesize_function(self, *args, **kwds):
    return


class FunctionCompiler(function_compiler.FunctionCompiler):
  def make_function_decl(self):
    yield '/****** %s ******/' % self.ifun.fullname
    yield 'tag_type %s(RuntimeState * rts, Configuration * C)' % self.entry

  def make_funcion_prelude(self):
    yield 'Cursor _0 = C->cursor();'

  @visitation.dispatch.on('stmt')
  def compileS(self, stmt):
    '''
    Compile a statement.  Returns list-structured Python code.
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
    varident = self.compileE(icase.var)
    assert icase.branches
    h_typedef = self.intern(self.casetype(self.interp, icase))
    yield 'auto tag = rts->hnf(C, &%s, &%s);' % (varident, h_typedef)
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
    h_values = self.intern(values)
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
    h_lit = self.intern(iliteral.fullname)
    text = '&%s, Arg(%r)' % (h_lit, iliteral.value)
    return 'Node::create(%s)' % text if primary else text

  @compileE.when(icurry.IString)
  def compileE(self, istring, primary=False):
    h_str = self.intern(istring)
    text = '&CString_Info, Arg(%s)' % h_str
    return 'Node::create(%s)' % text if primary else text

  @compileE.when(icurry.IUnboxedLiteral)
  def compileE(self, iunboxed, primary=False):
    return repr(iunboxed)

  @compileE.when(icurry.ILit)
  def compileE(self, ilit, primary=False):
    return self.compileE(ilit.lit, primary)

  @compileE.when(icurry.ICall)
  def compileE(self, icall, primary=False):
    subexprs = (self.compileE(x, primary=True) for x in icall.exprs)
    h_info = self.intern(icall.symbolname)
    text = '&%s%s' % (h_info, ''.join(', ' + e for e in subexprs))
    return 'Node::create(%s)' % text if primary else text

  @compileE.when(icurry.IPartialCall)
  def compileE(self, ipcall, primary=False):
    subexprs = (self.compileE(x, primary=True) for x in ipcall.exprs)
    h_info = self.intern(ipcall.symbolname)
    text = '&%s%s' % (
        h_info
      , ''.join(', ' + e for e in subexprs)
      )
    # 'primary' intentionally ignored.
    return 'Node::create_partial(%s)' % text

  @compileE.when(icurry.IOr)
  def compileE(self, ior, primary=False):
    h_info = self.intern('Prelude.?')
    text = "&%s, %s, %s" % (
        h_info
      , self.compileE(ior.lhs, primary=True)
      , self.compileE(ior.rhs, primary=True)
      )
    return 'Node::create(%s)' % text if primary else text

