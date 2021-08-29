from . import types
from . import visit
from ..utility.visitation import dispatch
import sys

def varinfo(iobj):
  '''Captures information about ICurry variables.'''
  info = {0: VarInfo([])}
  visitor = lambda arg: _getvarinfo(arg, info)
  visit.visit(visitor, iobj, topdown=True)
  return info

class VarInfo(object):
  def __init__(self, path=None):
    self.path = path
  def __repr__(self):
    return str(self.path)

@dispatch.on('arg')
def _getvarinfo(arg, state):
  pass

@_getvarinfo.when(types.IVarDecl)
def _getvarinfo(ivardecl, state):
  assert ivardecl.vid not in state
  state[ivardecl.vid] = VarInfo()

@_getvarinfo.when(types.IVarAssign)
def _getvarinfo(ivarassign, state):
  info = state[ivarassign.vid]
  if isinstance(ivarassign.expr, types.IVarAccess):
    rhs = ivarassign.expr
    assert not info.path
    info.path = state[rhs.vid].path + rhs.path

class TRUE(BaseException): pass

def set_monadic_metadata(imodule, modules):
  '''
  Determines whether each ICurry function in a module is monadic.  The result
  is stored in the 'all.monadic' metadata.

  To determine whether a function is monadic, its call graph is walked.  If
  the function calls any monadic function, then it is determined to be monadic.
  '''
  limit = sys.getrecursionlimit()
  try:
    sys.setrecursionlimit(1<<30)
    for ifun in imodule.functions.values():
      is_monadic(ifun, modules)
  finally:
    sys.setrecursionlimit(limit)

def is_monadic(ifun, modules):
  '''
  Tells or determines whether an ICurry function is monadic.
  '''
  if isinstance(ifun, types.IFunction):
    if 'all.monadic' not in ifun.metadata:
      ifun.update_metadata({'all.monadic': False})
      visitor = lambda iobj: _checkmonadic(iobj, modules)
      try:
        visit.visit(visitor, ifun.body)
      except TRUE:
        result = True
      else:
        result = False
      ifun.update_metadata({'all.monadic': result})
    return ifun.metadata['all.monadic']
  else:
    return False

def _lookupfunction(symbolname, modules):
  # interp.symbol cannot be used because analysis must occur before the symbols
  # are created.  For example, we need to determine whether something like
  # Prelude.putStr is monadic before creating its symbol (which would have
  # is_monadic=True set).  interp.symbol cannot, of course, be used before the
  # symbol tables are generated.
  obj = modules
  parts = iter(symbolname.split('.'))
  while not isinstance(obj, types.IModule):
    part = next(parts)
    obj = obj[part]
    obj = getattr(obj, '.icurry', obj)
  return obj.functions.get('.'.join(parts), None)

def _checkmonadic(iobj, modules):
  if isinstance(iobj, types.ICall):
    ifun = _lookupfunction(iobj.symbolname, modules)
    if ifun is not None:
      if is_monadic(ifun, modules):
        raise TRUE()
