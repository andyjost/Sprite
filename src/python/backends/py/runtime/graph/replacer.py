from .....common import T_SETGRD, T_CONSTR, T_VAR, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from ..... import inspect
from . import node

class Replacer(object):
  '''
  Performs replacements in a context, using the alternatives at a target
  position.

  For context C and path p, the target position is C[p].  The Item access self[i]
  returns a copy of C in which C[p] is replaced with C[p][i].  Only nodes along
  the spine are copied.

  The default getter is just getitem, so it will return a successor of the
  target.  This is handy when the target is a choice, since R[1], R[2] will
  return a copy of the expression with the left and right alternatives,
  respectively, in place (note: the zeroth successor is the choice ID).

  A custom getter can be used to construct any replacement desired.

  If a target is supplied, then its subexpressions will be used to construct
  the alternatives.

  Example:
  --------
  Let cxt = [a ? b, c], path = [0], and R = Replacer(cxt, path).  Then R[1] is
  [a, c] and R[2] is [b, c].  Note well that the first successor of a choice is
  the choice ID, so i=1 and i=2 are the left and right alternatives, resp.  In
  each case, a new cons node is created, but c is not copied.

  '''
  def __init__(
      self, context, path
    , getter=node.Node.getitem_with_guards, alternatives=None
    ):
    self.context = context
    self.path = path
    self.target = alternatives # has value after first __getitem__, unless supplied.
    self.getter = getter
    self.guards = set()

  def _a_(self, expr, depth=0):
    '''Recurse along the spine.  At the target, call the getter.'''
    if inspect.tag_of(expr) == T_SETGRD:
      sid = expr.successors[0]
      self.guards.add(sid)
      return node.Node(expr.info, sid, self._a_(expr.successors[1], depth))
    if depth < len(self.path):
      return node.Node(*self._b_(expr, depth))
    else:
      if self.target is None:
        self.target = expr
      return self.getter(self.target, self.index)

  def _b_(self, expr, depth):
    '''
    Perform a shallow copy at one node.  Recurse along the spine; reference
    subexpressions not on the spine.
    '''
    if inspect.tag_of(expr) == T_SETGRD:
      sid = expr.successors[0]
      self.guards.add(sid)
      yield expr.info
      yield sid
      yield node.Node(*self._b_(expr.successors[1], depth))
    else:
      pos = self.path[depth]
      yield expr.info
      for j,_ in enumerate(expr.successors):
        if j == pos:
          yield self._a_(node.Node.getitem(expr, j, skipguards=False), depth+1) # spine
        else:
          yield node.Node.getitem(expr, j, skipguards=False) # not spine

  def __getitem__(self, i):
    self.index = i
    return self._a_(self.context)


