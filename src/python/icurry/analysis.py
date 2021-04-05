from . import types
from . import visit
from ..utility.visitation import dispatch

class VarInfo(object):
  def __init__(self, path=None):
    self.path = path
  def __repr__(self):
    return str(self.path)

def varinfo(iobj):
  info = {0: VarInfo([])}
  visitor = lambda arg: _getvarinfo(arg, info)
  visit.visit(visitor, iobj, topdown=True)
  return info

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

