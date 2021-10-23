'''Code to compile Curry expressions.'''

from ..... import icurry
from .....utility import visitation

__all__ = ['compileE']

@visitation.dispatch.on('expr')
def compileE(cc, expr, primary=False):
  '''
  Compile an expression into a string.  For primary expressions, the string
  evaluates to a value (boxed or unboxed).  For non-primary expressions, it
  contains comma-separated arguments that may be passed to the Node constructor
  or Node.rewrite.
  '''
  assert False

@compileE.when(icurry.IVar)
def compileE(cc, ivar, primary=False):
  return '_%s' % ivar.vid

@compileE.when(icurry.IVarAccess)
def compileE(cc, ivaraccess, primary=False):
  return '%s[%s]' % (
      compileE(cc, ivaraccess.var, primary=primary)
    , ','.join(map(str, ivaraccess.path))
    )

@compileE.when(icurry.ILiteral)
def compileE(cc, iliteral, primary=False):
  h_lit = cc.intern(iliteral.fullname)
  text = '%s, %r' % (h_lit, iliteral.value)
  return 'rts.Node(%s)' % text if primary else text

@compileE.when(icurry.IString)
def compileE(cc, istring, primary=False):
  h_str = cc.intern(istring)
  text = 'rts.prelude._PyString, memoryview(%s)' % h_str
  return 'rts.Node(%s)' % text if primary else text

@compileE.when(icurry.IUnboxedLiteral)
def compileE(cc, iunboxed, primary=False):
  return repr(iunboxed)

@compileE.when(icurry.ILit)
def compileE(cc, ilit, primary=False):
  return compileE(cc, ilit.lit, primary)

@compileE.when(icurry.ICall)
def compileE(cc, icall, primary=False):
  subexprs = (compileE(cc, x, primary=True) for x in icall.exprs)
  h_info = cc.intern(icall.symbolname)
  text = '%s%s' % (h_info, ''.join(', ' + e for e in subexprs))
  return 'rts.Node(%s)' % text if primary else text

@compileE.when(icurry.IPartialCall)
def compileE(cc, ipcall, primary=False):
  subexprs = (compileE(cc, x, primary=True) for x in ipcall.exprs)
  h_info = cc.intern(ipcall.symbolname)
  h_part = cc.intern('Prelude._PartApplic')
  text = '%s, %s, rts.Node(%s%s, partial=True)' % (
      h_part
    , compileE(cc, ipcall.missing)
    , h_info
    , ''.join(', ' + e for e in subexprs)
    )
  return 'rts.Node(%s)' % text if primary else text

@compileE.when(icurry.IOr)
def compileE(cc, ior, primary=False):
  h_info = cc.intern('Prelude.?')
  text = "%s, %s, %s" % (
      h_info
    , compileE(cc, ior.lhs, primary=True)
    , compileE(cc, ior.rhs, primary=True)
    )
  return 'rts.Node(%s)' % text if primary else text
