'''
Code to copy Curry expressions.
'''
from __future__ import absolute_import

from .....common import T_SETGRD, T_FWD
from copy import copy, deepcopy
from ..... import inspect
from . import node

__all__ = ['copygraph', 'copynode', 'GraphCopier', 'Skipper']

class GraphCopier(object):
  '''
  Deep-copies an expression.  The skipper can be used to remove nodes.  This
  can be used to remove forward nodes and set guards from values.
  '''
  def __init__(self, skipper=None):
    self.expr = None
    self.skipper = skipper

  def __call__(self, expr, memo=None):
    self.expr = expr
    return deepcopy(self, memo)

  def __deepcopy__(self, memo):
    if not isinstance(self.expr, node.Node):
      return deepcopy(self.expr, memo)
    else:
      target = self.skipper(self.expr)
      if target is not None:
        return self(target, memo)
      else:
        info = self.expr.info
        partial = info.arity > len(self.expr.successors)
        return node.Node(
            info
          , *(self(succ) for succ in self.expr.successors)
          , partial=partial
          )

class Skipper(object):
  '''
  Indicates which nodes to skip.  If a node should be skipped, the
  __call__ method should return its replacement.
  '''
  def __init__(self, skipfwd=False, skipgrds=None):
    self.skipfwd = skipfwd
    self.skipgrds = set() if skipgrds is None else skipgrds

  def __call__(self, expr):
    if expr.info.tag == T_FWD:
      if skipfwd:
        return inspect.fwd_target(expr)
    elif expr.info.tag == T_SETGRD:
      if inspect.get_set_id(expr) in self.skipgrds:
        return inspect.get_setguard_value(expr)

def copygraph(expr, memo=None, **kwds):
  '''
  Copies a Curry expression with the option to remove certain nodes.

  Parameters:
  -----------
    ``expr``
      An instance of ``graph.Node`` or a built-in type such as ``int``,
      ``str``, or ``float``.

    ``skipfwd``
      Indicates whether to skip FWD nodes.

    ``skipgrds``
      A container of set identifer indicating which set guards to skip.

  Returns:
  --------
  A deep copy of ``expr``.

  '''
  copier = GraphCopier(skipper=Skipper(**kwds))
  return copier(expr, memo=memo)

def copynode(expr, mapf=None):
  '''
  Makes a shallow copy of a Curry expression.

  Paramters:
  ----------
    ``expr``
      The expression to copy.  Can be an instance of ``graph.Node`` or a
      built-in type such as ``int``, ``str``, or ``float``.

    ``mapf``
      An optional map function.  If supplied, this function will be applied
      to the successors.

  Returns:
  --------
  A shallow copy of ``expr``.
  '''
  if isinstance(expr, node.Node):
    info = expr.info
    partial = info.arity > len(expr.successors)
    if mapf is None:
      successors = expr.successors
    else:
      successors = map(mapf, expr.successors)
    return node.Node(info, *successors, partial=partial)
  else:
    return copy(expr)

