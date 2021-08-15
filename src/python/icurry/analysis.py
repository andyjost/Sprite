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

def set_monadic_metadata(modulename, imodules):
  '''
  Determines whether each ICurry function in a module is monadic.  The result
  is stored in the 'all.monadic' metadata.

  To determine whether a function is monadic, itshe call graph is walked.  If
  the function calls any monadic function, then it is determined to be monadic.

  Parameters:
  -----------
    ``modulename``
      The name of the module to analyze.

    ``imodules``
      A dictionary from module names to IModule objects containing
      ``modulename`` and (recursively) all of its imports.
  '''
  limit = sys.getrecursionlimit()
  try:
    sys.setrecursionlimit(1<<30)
    for ifun in imodules[modulename].functions.values():
      is_monadic(ifun, imodules)
  finally:
    sys.setrecursionlimit(limit)

def is_monadic(ifun, imodules=None):
  '''
  Tells or determines whether an ICurry function is monadic.  ``imodules`` is
  required only if the property needs to be determined.
  '''
  if isinstance(ifun, types.IFunction):
    if 'all.monadic' not in ifun.metadata:
      assert imodules is not None
      ifun.update_metadata({'all.monadic': False})
      visitor = lambda iobj: _checkmonadic(imodules, iobj)
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

def _checkmonadic(imodules, iobj):
  if isinstance(iobj, types.ICall):
    modulename, name = types.splitname(iobj.name)
    ifun = imodules[modulename].functions.get(name, None)
    if ifun is not None:
      if is_monadic(ifun, imodules):
        raise TRUE()
