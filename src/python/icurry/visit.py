from . import types
import collections
from ..utility.visitation import dispatch

__all__ = ['replace', 'visit', 'visitslots']

@dispatch.on('arg')
def visit(visitor, arg=None, **kwds):
  '''Apply a visitor to ICurry.'''
  if arg is None:
    return lambda xarg: visit(visitor, xarg, **kwds)

@visit.when(collections.Mapping, no=(str,))
def visit(visitor, mapping, **kwds):
  for elem in mapping.itervalues():
    visit(visitor, elem, **kwds)

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


def visitslots(visitor, iobj, **kwds):
  sv = SlotVisitor(visitor)
  visit(sv, iobj, **kwds)

class SlotVisitor(object):
  def __init__(self, visitor):
    self.visitor = visitor

  @dispatch.on('iobj')
  def __call__(self, iobj, **kwds):
    pass

  @__call__.when(types.IAssign)
  def __call__(self, iassign, **kwds):
    self.visitor(iassign.__dict__, 'expr')

  @__call__.when(types.IBlock)
  def __call__(self, iblock, **kwds):
    self.visitor(iblock.__dict__, 'stmt')

  @__call__.when(types.IBody)
  def __call__(self, ibody, **kwds):
    self.visitor(ibody.__dict__, 'block')

  @__call__.when(types.ICall)
  def __call__(self, icall, **kwds):
    for key, _ in enumerate(icall.exprs):
      self.visitor(icall.exprs, key)

  @__call__.when(types.IFunction)
  def __call__(self, ifun, **kwds):
    self.visitor(ifun.__dict__, 'body')

  @__call__.when(types.IReturn)
  def __call__(self, ireturn, **kwds):
    self.visitor(ireturn.__dict__, 'expr')


def replace(iobj, spec):
  if spec:
    visitor = SlotVisitor(Replacer(spec))
    visit(visitor, iobj, topdown=True)


class Replacer(object):
  def __init__(self, spec):
    self.spec = spec

  def __call__(self, owner, key):
    value = owner[key]
    if value is not None:
      repl = self.spec.get(id(value), None)
      if repl is not None:
        owner[key] = repl

