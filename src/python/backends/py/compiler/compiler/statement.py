'''Code to compile Curry statements.'''

from .expression import compileE
from ..... import icurry
from .....utility import visitation
import collections

__all__ = ['compileS']

@visitation.dispatch.on('stmt')
def compileS(cc, stmt):
  '''
  Compile a statement.  Returns list-structured Python code.
  '''
  assert False

@compileS.when(collections.Sequence, no=str)
def compileS(cc, seq):
  for lines in (compileS(cc, x) for x in seq):
    for line in lines:
      yield line

@compileS.when(icurry.IVarDecl)
def compileS(cc, vardecl):
  varname = compileE(cc, vardecl.lhs)
  yield '%s = None' % varname

@compileS.when(icurry.IFreeDecl)
def compileS(cc, vardecl):
  varname = compileE(cc, vardecl.lhs)
  yield '%s = rts.freshvar()' % varname

@compileS.when(icurry.IVarAssign)
def compileS(cc, assign):
  lhs = compileE(cc, assign.lhs, primary=True)
  rhs = compileE(cc, assign.rhs, primary=True)
  yield '%s = %s' % (lhs, rhs)

@compileS.when(icurry.INodeAssign)
def compileS(cc, assign):
  lhs = compileE(cc, assign.lhs)
  rhs = compileE(cc, assign.rhs, primary=True)
  yield '%s = %s' % (lhs, rhs)

@compileS.when(icurry.IBlock)
def compileS(cc, block):
  for sect in [block.vardecls, block.assigns, block.stmt]:
    for line in compileS(cc, sect):
      yield line

@compileS.when(icurry.IExempt)
def compileS(cc, exempt):
  h_failure = cc.intern('Prelude._Failure')
  yield '_0.rewrite(%s)' % h_failure

@compileS.when(icurry.IReturn)
def compileS(cc, ret):
  if isinstance(ret.expr, icurry.IReference):
    h_fwd = cc.intern('Prelude._Fwd')
    yield '_0.rewrite(%s, %s)' % (
        h_fwd, compileE(cc, ret.expr, primary=True)
      )
  else:
    yield '_0.rewrite(%s)' % compileE(cc, ret.expr)

@compileS.when(icurry.ICaseCons)
def compileS(cc, icase):
  varident = compileE(cc, icase.var)
  assert icase.branches
  h_typedef = cc.intern(casetype(cc.interp, icase))
  yield '%s.hnf(typedef=%s)' % (varident, h_typedef)
  yield 'selector = %s.tag' % varident
  el = ''
  for branch in icase.branches[:-1]:
    rhs = cc.interp.symbol(branch.symbolname).info.tag
    yield '%sif selector == %s:' % (el, rhs)
    yield list(compileS(cc, branch.block))
    el = 'el'
  if el:
    yield 'else:'
    yield list(compileS(cc, icase.branches[-1].block))
  else:
    for line in compileS(cc, icase.branches[-1].block):
      yield line

@compileS.when(icurry.ICaseLit)
def compileS(cc, icase):
  h_sel = compileE(cc, icase.var)
  h_typedef = cc.intern(casetype(cc.interp, icase))
  values = tuple(branch.lit.value for branch in icase.branches)
  h_values = cc.intern(values)
  yield '%s.hnf(typedef=%s, values=%s)' % (h_sel, h_typedef, h_values)
  yield 'selector = %s.unboxed_value' % h_sel
  el = ''
  for branch in icase.branches:
    rhs = repr(branch.lit.value)
    yield '%sif selector == %s:' % (el, rhs)
    yield list(compileS(cc, branch.block))
    el = 'el'
  h_failure = cc.intern('Prelude._Failure')
  last_line = '_0.rewrite(%s)' % h_failure
  if el:
    yield 'else:'
    yield [last_line]
  else:
    yield last_line


@visitation.dispatch.on('arg')
def casetype(interp, arg):
  '''
  Returns the name of the Curry type over which a case expression operates.
  '''
  assert False

@casetype.when(icurry.ICaseCons)
def casetype(interp, icase):
  return interp.symbol(icase.branches[0].symbolname).typedef()

@casetype.when(icurry.ICaseLit)
def casetype(interp, icase):
  return casetype(interp, icase.branches[0].lit)

@casetype.when(icurry.IInt)
def casetype(interp, _):
  return interp.type('Prelude.Int')

@casetype.when(icurry.IChar)
def casetype(interp, _):
  return interp.type('Prelude.Char')

@casetype.when(icurry.IFloat)
def casetype(interp, _):
  return interp.type('Prelude.Float')

