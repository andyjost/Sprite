from ...exceptions import CompileError
from ..generic import compiler, renderer
from ... import icurry
import collections, itertools, json, re

__all__ = ['compile', 'write_module']

def compile(interp, imodule, extern=None):
  compileM = PyCompiler(interp, imodule, extern)
  return compileM.compile()

class PyCompiler(compiler.CompilerBase):
  def __init__(self, interp, imodule, extern=None):
    compiler.CompilerBase.__init__(self, interp, imodule, extern)
    self.counts = collections.defaultdict(itertools.count)

  def vEmitHeader(self):
    return []

  def vEmitStepfuncFwd(self, h_stepfunc):
    return []

  def vEmitInfotabFwd(self, h_info):
    return []

  def vEmitDataTypeFwd(self, h_datatype):
    return []

  def vEmitStepfuncHead(self, ifun, h_stepfunc):
    yield 'def %s(rts, _0):' % h_stepfunc, ifun.fullname

  def vEmitStepfuncEntry(self):
    return []

  def vEmitFunctionInfotab(self, ifun, h_info, h_stepfunc):
    return []
    # yield 'InfoTable const %s{'                 % h_info
    # yield '    /*tag*/        T_FUNC'
    # yield '  , /*arity*/      %s'               % ifun.arity
    # yield '  , /*alloc_size*/ %s'               % _sizeof(ifun.arity)
    # yield '  , /*flags*/      F_STATIC_OBJECT'
    # yield '  , /*name*/       %s'               % _dquote(ifun.name)
    # yield '  , /*format*/     "%s"'             % ('p' * ifun.arity)
    # yield '  , /*step*/       %s'               % h_stepfunc
    # yield '  , /*typecheck*/  nullptr'
    # yield '  , /*type*/       nullptr'
    # yield '  };'
    # yield ''

  def vEmitConstructorInfotab(self, i, ictor, h_info, h_datatype):
    flags = ictor.metadata.get('all.flags', 0)
    return []
    # yield 'InfoTable const %s{'                     % h_info
    # yield '    /*tag*/        T_CTOR + %s'          % str(i)
    # yield '  , /*arity*/      %s'                   % ictor.arity
    # yield '  , /*alloc_size*/ %s'                   % _sizeof(ictor.arity)
    # yield '  , /*flags*/      F_STATIC_OBJECT | %s' % flags
    # yield '  , /*name*/       %s'                   % _dquote(ictor.name)
    # yield '  , /*format*/     "%s"'                 % ('p' * ictor.arity)
    # yield '  , /*step*/       nullptr'
    # yield '  , /*typecheck*/  nullptr'
    # yield '  , /*type*/       &%s'                  % h_datatype
    # yield '  };'
    # yield ''

  def vEmitDataType(self, itype, h_datatype, ctor_handles):
    return []
    # h_ctortable = self.next_private_symbolname(compiler.CONSTRUCTOR_TABLE)
    # self.symtab.insert(
    #     h_ctortable, compiler.CONSTRUCTOR_TABLE
    #   , 'constructor table for %r' % itype.fullname
    #   )
    # yield 'static InfoTable const * %s[] = { %s };' % (
    #     h_ctortable, ', '.join('&%s' % h for h in ctor_handles)
    #   )
    # self.symtab.make_defined(h_ctortable)
    # yield 'Type const %s { %s, %r, %r, F_STATIC_OBJECT };' % (
    #     h_datatype, h_ctortable, 't', len(itype.constructors)
    #   )
    # yield ''

  def vEmitStringLiteral(self, h_string, string):
    yield '%s = %r' % (h_string, string)

  def vEmitValueSetLiteral(self, h_valueset, values):
    yield '%s = %r' % (h_valueset, values)

  def vEmit_compileS_IVarDecl(self, vardecl, varname):
    yield '%s = None' % varname

  def vEmit_compileS_IFreeDecl(self, vardecl, varname):
    yield '%s = rts.freshvar()' % varname

  def vEmit_compileS_IVarAssign(self, assign, lhs, rhs):
    yield '%s = %s' % (lhs, rhs)

  def vEmit_compileS_INodeAssign(self, assign, lhs, rhs):
    yield '%s = %s' % (lhs, rhs)

  def vEmit_compileS_IExempt(self, exempt):
    h_failure = self.importSymbol('Prelude._Failure')
    yield '_0.rewrite(%s)' % h_failure

  def vEmit_compileS_IReturn(self, iret, expr):
    if isinstance(iret.expr, icurry.IReference):
      h_fwd = self.importSymbol('Prelude._Fwd')
      yield '_0.rewrite(%s, %s)' % (h_fwd, expr)
    else:
      yield '_0.rewrite(%s)' % expr

  def vEmit_compileS_ICaseCons(self, icase, h_datatype, varident):
    yield '%s.hnf(typedef=%s)' % (varident, h_datatype)
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

  _TYPENAMES = {
      icurry.IInt  : 'Prelude.Int'
    , icurry.IChar : 'Prelude.Char'
    , icurry.IFloat: 'Prelude.Float'
    }

  def vEmit_compileS_ICaseLit(self, icase, h_sel, h_values):
    # Is the datatype needed here?
    h_datatype = self.importSymbol(icase.branches[0].lit.fullname)

    yield '%s.hnf(typedef=%s, values=%s)' % (h_sel, h_datatype, h_values)
    yield 'selector = %s.unboxed_value' % h_sel
    el = ''
    for branch in icase.branches:
      rhs = repr(branch.lit.value)
      yield '%sif selector == %s:' % (el, rhs)
      yield list(self.compileS(branch.block))
      el = 'el'
    h_failure = self.importSymbol('Prelude._Failure')
    last_line = '_0.rewrite(%s)' % h_failure
    if el:
      yield 'else:'
      yield [last_line]
    else:
      yield last_line

  def vEmit_compileE_IVar(self, ivar):
    return '_%s' % ivar.vid

  def vEmit_compileE_IVarAccess(self, ivaraccess, var):
    return '%s[%s]' % (var, ','.join(map(str, ivaraccess.path)))

  def vEmit_compileE_ILiteral(self, iliteral, h_ctor, primary):
    text = '%s, %r' % (h_ctor, iliteral.value)
    return 'rts.Node(%s)' % text if primary else text

  def vEmit_compileE_IString(self, istring, h_string, primary):
    text = 'rts.prelude._PyString, memoryview(%s)' % h_string
    return 'rts.Node(%s)' % text if primary else text

  def vEmit_compileE_IUnboxedLiteral(self, iunboxed, primary):
    return repr(iunboxed)

  def vEmit_compileE_ICall(self, icall, h_info, args, primary):
    text = '%s%s' % (h_info, ''.join(', ' + e for e in args))
    return 'rts.Node(%s)' % text if primary else text

  def vEmit_compileE_IPartialCall(self, ipcall, h_info, args, primary):
    h_part = self.importSymbol('Prelude._PartApplic')
    text = '%s, %s, rts.Node(%s%s, partial=True)' % (
        h_part
      , self.compileE(ipcall.missing)
      , h_info
      , ''.join(', ' + e for e in args)
      )
    return 'rts.Node(%s)' % text if primary else text

  def vEmit_compileE_IOr(self, ior, h_choice, lhs, rhs, primary):
    text = "&%s, %s, %s" % (h_choice, lhs, rhs)
    return 'Node::create(%s)' % text if primary else text
