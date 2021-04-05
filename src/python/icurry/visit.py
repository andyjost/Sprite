from . import types
import collections
from ..utility.visitation import dispatch

@dispatch.on('arg')
def visit(visitor, arg=None, **kwds):
  '''Apply a visitor to ICurry.'''
  if arg is None:
    return lambda xarg: visit(visitor, xarg, **kwds)

@visit.when(collections.Sequence, no=(str,))
def visit(visitor, seq, **kwds):
  for item in seq:
    visit(visitor, item, **kwds)

@visit.when(types.IModule)
def visit(visitor, imodule, **kwds):
  if kwds.get('topdown', False):
    visitor(imodule)
    visit(visitor, imodule.types, **kwds)
    visit(visitor, imodule.functions, **kwds)
  else:
    visit(visitor, imodule.types, **kwds)
    visit(visitor, imodule.functions, **kwds)
    visitor(imodule)

@visit.when(types.IDataType)
def visit(visitor, idatatype, **kwds):
  if kwds.get('topdown', False):
    visitor(idatatype)
    visit(visitor, idatatype.constructors, **kwds)
  else:
    visit(visitor, idatatype.constructors, **kwds)
    visitor(idatatype)

@visit.when(types.IFunction)
def visit(visitor, ifun, **kwds):
  if kwds.get('topdown', False):
    visitor(ifun)
    visit(visitor, ifun.body, **kwds)
  else:
    visit(visitor, ifun.body, **kwds)
    visitor(ifun)

@visit.when(types.IObject)
def visit(visitor, iobj, **kwds):
  if kwds.get('topdown', False):
    visitor(iobj)
    for child in iobj.children:
      visit(visitor, child, **kwds)
  else:
    for child in iobj.children:
      visit(visitor, child, **kwds)
    visitor(iobj)

@visit.when(types.IBlock)
def visit(visitor, iblock, **kwds):
  if kwds.get('topdown', False):
    visitor(iblock)
    visit(visitor, iblock.vardecls, **kwds)
    visit(visitor, iblock.assigns, **kwds)
    visit(visitor, iblock.stmt, **kwds)
  else:
    visit(visitor, iblock.vardecls, **kwds)
    visit(visitor, iblock.assigns, **kwds)
    visit(visitor, iblock.stmt, **kwds)
    visitor(iblock)
