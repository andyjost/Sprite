from ...generic.compiler import module_compiler, ir, function_compiler, render
from .... import icurry
from ....utility import visitation
from . import synthesize
import collections

__all__ = ['compile']

class IR(ir.IR):
  CODETYPE = 'Python'

def compile(interp, icy, extern=None):
  moduleobj = interp.module(icy.fullname)
  compileM = ModuleCompiler(interp, moduleobj, extern)
  return compileM.compile(icy)

class ModuleCompiler(module_compiler.ModuleCompiler):
  @property
  def IR(self):
    return IR

  @property
  def FunctionCompiler(self):
    return FunctionCompiler

  def synthesize_function(self, *args, **kwds):
    return synthesize.synthesize_function(*args, **kwds)


class FunctionCompiler(function_compiler.FunctionCompiler):
  def make_function_decl(self):
    yield 'def %s(rts, _0):' % self.entry, self.ifun.fullname

  def make_function_prelude(self):
    pass

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
    yield '%s = None' % varname

  @compileS.when(icurry.IFreeDecl)
  def compileS(self, vardecl):
    varname = self.compileE(vardecl.lhs)
    yield '%s = rts.freshvar()' % varname

  @compileS.when(icurry.IVarAssign)
  def compileS(self, assign):
    lhs = self.compileE(assign.lhs, primary=True)
    rhs = self.compileE(assign.rhs, primary=True)
    yield '%s = %s' % (lhs, rhs)

  @compileS.when(icurry.INodeAssign)
  def compileS(self, assign):
    lhs = self.compileE(assign.lhs)
    rhs = self.compileE(assign.rhs, primary=True)
    yield '%s = %s' % (lhs, rhs)

  @compileS.when(icurry.IBlock)
  def compileS(self, block):
    for sect in [block.vardecls, block.assigns, block.stmt]:
      for line in self.compileS(sect):
        yield line

  @compileS.when(icurry.IExempt)
  def compileS(self, exempt):
    h_failure = self.intern('Prelude._Failure')
    yield '_0.rewrite(%s)' % h_failure

  @compileS.when(icurry.IReturn)
  def compileS(self, ret):
    if isinstance(ret.expr, icurry.IReference):
      h_fwd = self.intern('Prelude._Fwd')
      yield '_0.rewrite(%s, %s)' % (
          h_fwd, self.compileE(ret.expr, primary=True)
        )
    else:
      yield '_0.rewrite(%s)' % self.compileE(ret.expr)

  @compileS.when(icurry.ICaseCons)
  def compileS(self, icase):
    varident = self.compileE(icase.var)
    assert icase.branches
    h_typedef = self.intern(self.casetype(self.interp, icase))
    yield '%s.hnf(typedef=%s)' % (varident, h_typedef)
    yield 'selector = %s.tag' % varident
    el = ''
    for branch in icase.branches[:-1]:
      rhs = self.interp.symbol(branch.symbolname).info.tag
      yield '%sif selector == %s:' % (el, rhs), branch.symbolname
      yield list(self.compileS(branch.block))
      el = 'el'
    if el:
      yield 'else:', icase.branches[-1].symbolname
      yield list(self.compileS(icase.branches[-1].block))
    else:
      for line in self.compileS(icase.branches[-1].block):
        yield line

  @compileS.when(icurry.ICaseLit)
  def compileS(self, icase):
    h_sel = self.compileE(icase.var)
    h_typedef = self.intern(self.casetype(self.interp, icase))
    values = tuple(branch.lit.value for branch in icase.branches)
    h_values = self.intern(values)
    yield '%s.hnf(typedef=%s, values=%s)' % (h_sel, h_typedef, h_values)
    yield 'selector = %s.unboxed_value' % h_sel
    el = ''
    for branch in icase.branches:
      rhs = repr(branch.lit.value)
      yield '%sif selector == %s:' % (el, rhs)
      yield list(self.compileS(branch.block))
      el = 'el'
    h_failure = self.intern('Prelude._Failure')
    last_line = '_0.rewrite(%s)' % h_failure
    if el:
      yield 'else:'
      yield [last_line]
    else:
      yield last_line

  @visitation.dispatch.on('expr')
  def compileE(self, expr, primary=False):
    '''
    Compile an expression into a string.  For primary expressions, the string
    evaluates to a value (boxed or unboxed).  For non-primary expressions, it
    contains comma-separated arguments that may be passed to the Node constructor
    or Node.rewrite.
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
    text = '%s, %r' % (h_lit, iliteral.value)
    return 'rts.Node(%s)' % text if primary else text

  @compileE.when(icurry.IString)
  def compileE(self, istring, primary=False):
    h_str = self.intern(istring)
    text = 'rts.prelude._PyString, memoryview(%s)' % h_str
    return 'rts.Node(%s)' % text if primary else text

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
    text = '%s%s' % (h_info, ''.join(', ' + e for e in subexprs))
    return 'rts.Node(%s)' % text if primary else text

  @compileE.when(icurry.IPartialCall)
  def compileE(self, ipcall, primary=False):
    subexprs = (self.compileE(x, primary=True) for x in ipcall.exprs)
    h_info = self.intern(ipcall.symbolname)
    h_part = self.intern('Prelude._PartApplic')
    text = '%s, %s, rts.Node(%s%s, partial=True)' % (
        h_part
      , self.compileE(ipcall.missing)
      , h_info
      , ''.join(', ' + e for e in subexprs)
      )
    return 'rts.Node(%s)' % text if primary else text

  @compileE.when(icurry.IOr)
  def compileE(self, ior, primary=False):
    h_info = self.intern('Prelude.?')
    text = "%s, %s, %s" % (
        h_info
      , self.compileE(ior.lhs, primary=True)
      , self.compileE(ior.rhs, primary=True)
      )
    return 'rts.Node(%s)' % text if primary else text
