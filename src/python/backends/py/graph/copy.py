'''
Code to copy Curry expressions.
'''

from ....common import T_FREE, T_FWD, T_SETGRD
from copy import copy
from .... import inspect
from . import node

__all__ = ['copygraph', 'copynode', 'GraphCopier', 'Skipper']

class GraphCopier(object):
  '''
  Deep-copies an expression.  The skipper can be used to remove nodes.  This
  can be used to remove forward nodes and set guards from values.

  The traversal keeps its own stack, so a deep graph such as a long list
  cannot exhaust the Python stack.  The copy of a node is created, and
  recorded in the memo, before its successors are copied.  So a node reached
  by several paths is copied once, the copy keeps the sharing, and a cycle in
  the graph becomes a cycle in the copy.
  '''
  def __init__(self, skipper=None):
    self.skipper = skipper
    # The number of free variables copied.  See rts_control.make_value.
    self.freevars = 0

  def __call__(self, expr, memo=None):
    '''
    Copies ``expr``.

    The memo maps the ID of a node to its copy, as in ``copy.deepcopy``.  Pass
    one memo to several calls to keep the sharing between the copies.  The
    memo keeps the copied nodes alive, so their IDs stay unique.
    '''
    if memo is None:
      memo = {}
      keep = None
    else:
      keep = memo.setdefault(id(memo), [])
    skip = self.skipper
    # The nodes whose copies are under construction.  Each frame holds the
    # node, its copy, and the index of the successor copied next.
    stack = []
    cur = expr
    while True:
      # Descend from ``cur`` until a value is at hand.
      while True:
        if not isinstance(cur, node.Node):
          # An unboxed value: an int, a float, a str of length one, a
          # memoryview of code points (a string literal), or an iterator (the
          # argument of a generator node).  The copy shares it: the first four
          # cannot change, and an iterator cannot be copied.  copy.deepcopy
          # rejects a memoryview and an iterator.
          value = cur
          break
        value = memo.get(id(cur))
        if value is not None:
          break
        if skip is not None:
          target = skip(cur)
          if target is not None:
            cur = target
            continue
        # The copy starts as a shallow copy.  The copies of the successors
        # replace the originals one by one.  A valid node needs no check of
        # its arity or its successors, so ``new_node`` is not called.
        value = object.__new__(type(cur))
        value.info = cur.info
        value.successors = list(cur.successors)
        if cur.info.tag == T_FREE:
          self.freevars += 1
        memo[id(cur)] = value
        if keep is not None:
          keep.append(cur)
        if not value.successors:
          break
        stack.append([cur, value, 0])
        cur = value.successors[0]
      # Deliver ``value`` to the innermost frame.  A finished frame produces
      # the value for its parent.
      while True:
        if not stack:
          return value
        frame = stack[-1]
        successors = frame[1].successors
        i = frame[2]
        successors[i] = value
        i += 1
        if i < len(successors):
          frame[2] = i
          cur = successors[i]
          break
        value = frame[1]
        stack.pop()

class Skipper(object):
  '''
  Indicates which nodes to skip.  If a node should be skipped, the
  __call__ method should return its replacement.
  '''
  def __init__(self, skipfwd=False, skipgrds=None):
    self.skipfwd = skipfwd
    self.skipgrds = set() if skipgrds is None else skipgrds

  def __call__(self, expr):
    tag = expr.info.tag
    if tag == T_FWD:
      if self.skipfwd:
        return inspect.fwd_target(expr)
    elif tag == T_SETGRD:
      if inspect.get_set_id(expr) in self.skipgrds:
        return inspect.get_setguard_value(expr)

def copygraph(expr, memo=None, **kwds):
  '''
  Copies a Curry expression with the option to remove certain nodes.

  Args:
    expr:
      An instance of ``graph.Node`` or a built-in type such as ``int``,
      ``str``, or ``float``.

    memo:
      A dictionary that maps the ID of a node to its copy.  See
      ``GraphCopier``.

    skipfwd:
      Indicates whether to skip FWD nodes.

    skipgrds:
      A container of set identifer indicating which set guards to skip.

  Returns:
    A deep copy of ``expr``.

  '''
  copier = GraphCopier(skipper=Skipper(**kwds))
  return copier(expr, memo=memo)

def copynode(expr, mapf=None):
  '''
  Makes a shallow copy of a Curry expression.

  Args:
    expr
      The expression to copy.  Can be an instance of ``graph.Node`` or a
      built-in type such as ``int``, ``str``, or ``float``.

    mapf
      An optional map function.  If supplied, this function will be applied
      to the successors.

  Returns:
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
