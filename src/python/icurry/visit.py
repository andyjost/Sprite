from . import types
import collections.abc
from ..utility.visitation import dispatch

__all__ = ['replace', 'visit', 'visitslots']

# The walk is iterative.  The nest of cons calls of a literal list of
# thousands of elements is one path of the tree, and a walk that recursed
# once per node ran out of frames at about 5400 elements under maxrecursion
# (issue #125, the bounds left after the fix of the port).  ``_parts`` tells
# how the walk treats an object: a container (a mapping or a sequence) is
# iterated and never shown to the visitor; an ICurry object is shown to the
# visitor, after its parts by default and before them under ``topdown``.
# The parts are read when the object is expanded, so a top-down visitor
# that replaces a part (``replace``) is followed into the replacement, as
# the recursive walk was.

@dispatch.on('arg')
def _parts(arg):
  '''
  The pair (node, parts) of an object of the walk: whether the visitor sees
  the object, and a callable that gives its parts in order.  None for an
  object the walk ignores.
  '''
  return None

@_parts.when(collections.abc.Mapping, no=(str,))
def _parts(mapping):
  return False, lambda: list(mapping.values())

@_parts.when(collections.abc.Sequence, no=(str,))
def _parts(seq):
  return False, lambda: list(seq)

@_parts.when(types.IModule)
def _parts(imodule):
  return True, lambda: [imodule.types, imodule.functions]

@_parts.when(types.IDataType)
def _parts(idatatype):
  return True, lambda: [idatatype.constructors]

@_parts.when(types.IFunction)
def _parts(ifun):
  return True, lambda: [ifun.body]

@_parts.when(types.IObject)
def _parts(iobj):
  return True, lambda: list(iobj.children)

@_parts.when(types.IBlock)
def _parts(iblock):
  return True, lambda: [iblock.vardecls, iblock.assigns, iblock.stmt]


def visit(visitor, arg=None, **kwds):
  '''
  Apply a visitor to ICurry.  The visitor is called on every ICurry object
  under ``arg``: after the parts of the object (post-order), or before them
  under ``topdown``.  Without ``arg`` the result is the walk as a function
  of its argument.  The depth of the tree costs no frame of Python (see the
  note above).
  '''
  if arg is None:
    return lambda xarg: visit(visitor, xarg, **kwds)
  topdown = bool(kwds.get('topdown', False))
  # Each item is an object with a flag: False, the object is to be
  # expanded; True, its parts were walked and the visitor sees it now.
  stack = [(arg, False)]
  while stack:
    obj, expanded = stack.pop()
    if expanded:
      visitor(obj)
      continue
    parts = _parts(obj)
    if parts is None:
      continue
    is_node, children = parts
    if is_node and topdown:
      visitor(obj)
    elif is_node:
      stack.append((obj, True))
    # The parts go on the stack in reverse, so the first part is walked
    # first.
    stack.extend((child, False) for child in reversed(children()))


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
