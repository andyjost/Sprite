'''Code to compile a function body.'''

from ..... import icurry
from .. import misc
from .statement import compileS
from .....utility import visitation
import collections, logging

logger = logging.getLogger(__name__)

__all__ = ['compileF']

@visitation.dispatch.on('iobj')
def compileF(cc, iobj):
  '''
  Compile an IFunction.  Appends list-structured Python.
  '''
  assert False

@compileF.when(collections.Sequence, no=str)
def compileF(cc, seq):
  for x in seq:
    compileF(cc, x)

@compileF.when(icurry.IFunction)
def compileF(cc, ifun):
  compileF(cc, ifun.body)

@compileF.when(icurry.IExternal)
def compileF(cc, iexternal):
  fname = cc.ifun.fullname
  extmod = cc.extern # IModule containing external functions.
  assert fname == iexternal.symbolname
  assert extmod is None or fname.startswith(extmod.fullname)
  try:
    localname = fname[len(extmod.fullname)+1:]
    ifun = extmod.functions[localname]
  except (KeyError, AttributeError):
    msg = 'external function %r is not defined' % fname
    logger.warn(msg)
    stmt = icurry.IReturn(icurry.IFCall('Prelude.prim_error', [msg]))
    compileF(cc, stmt)
  else:
    raise misc.ExternallyDefined(ifun)

@compileF.when(icurry.IFuncBody)
def compileF(cc, function):
  lines = compileS(cc, function.block)
  cc.lines.append(list(lines))

@compileF.when(icurry.IStatement)
def compileF(cc, stmt):
  lines = compileS(cc, stmt)
  cc.lines.append(list(lines))

