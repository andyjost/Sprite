'''Utilities for working with Curry expressions.'''

from ..... import context, icurry
from . import indexing

__all__ = ['iterexpr', 'walk']

def iterexpr(expr, once=True):
  '''Generate each node in a Curry expression exactly once.'''
  queue = [expr]
  seen = set()
  while queue:
    x = queue.pop()
    if id(x) not in seen:
      seen.add(id(x))
      try:
        l = list(x)
      except TypeError:
        pass
      else:
        queue.extend(l)
      yield x

class WalkState(object):
  '''See ``walk``.'''
  def __init__(self, root, path=()):
    self.stack = []
    self.path = list(path)
    self.spine = [
        indexing.subexpr(root, p)
            for p in [path[:i] for i in xrange(len(path)+1)]
      ]
    self.data = []

  def advance(self):
    while self.stack and not self.stack[-1]:
      self.pop()
    if self.stack:
      self.path[-1], self.spine[-1] = self.stack[-1].pop()
      return True

  def __iter__(self):
    while True:
      yield self
      if not self.advance():
        break

  def pop(self):
    self.stack.pop()
    self.path.pop()
    self.spine.pop()
    self.data.pop()

  def push(self, data=None):
    self.stack.append(
        [] if isinstance(self.cursor, icurry.ILiteral)
           else list(enumerate(self.cursor))[::-1]
      )
    self.path.append(None)
    self.spine.append(None)
    self.data.append(data)

  @property
  def cursor(self):
    '''The current node.'''
    return self.spine[-1]

  @property
  def parent(self):
    '''The parent of the current node.'''
    try:
      return self.spine[-2]
    except IndexError:
      return None


def walk(root, path=None):
  '''
  Walk a Curry expression.

  This yields a "state" objects for each successor of the given root.  The state
  consists of a cursor pointing to a subexpression, current path to the cursor,
  and other attributes.  Iteration may be pruned or deepened by modifying the
  state.  The subexpression under the cursor may be modified.

  Attributes:
  -----------
    ``stack``
        The remaining iteration state.  May be modified to control the search.
        Call ``push`` to add the successors of the node under the cursor.
    ``path``
        A list of integers giving the path from the root to the cursor.  Not to
        be modified.
    ``spine``
        A list of nodes, equal in length to ``path``, giving the node at each
        point along the path.  Not to be modified.
    ``cursor``
        The node currently being visited.  Equivalent to spine[-1].
    ``parent``
        The parent of the node at the cursore.  Equivalent to spine[-2].
  '''
  return WalkState(root, () if path is None else path)

