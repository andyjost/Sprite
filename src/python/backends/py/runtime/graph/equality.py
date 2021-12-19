'''Implements graph equality.'''
from ..... import inspect

class GraphEquality(object):
  '''
  Implements equality checks between Curry expressions.
  '''
  def __init__(self, skipfwd):
    self.skipfwd = bool(skipfwd)
    self.memo = {}

  def __call__(self, lhs, rhs):
    # This algorithm assumes in recursive calls that nodes previously found in
    # corresponding positions are equivalent.  This means pairs of nodes that
    # are still under evaluation can compare equal.  This is safe because every
    # pair of corresponsing nodes must eventually compare equal in their
    # entirety for a True result to be obtained.  In other words, even if we
    # incorectly consider two unequal nodes to be the same, we would always
    # discover this later and return False.
    if id(lhs) in self.memo:
      if id(rhs) in self.memo[id(lhs)]:
        return True
    if not all(inspect.isa_curry_expr(x) for x in [lhs, rhs]):
      raise TypeError('not a Curry expression')
    if all(inspect.is_boxed(x) for x in [lhs, rhs]):
      self.memo.setdefault(id(lhs), set())
      self.memo[id(lhs)].add(id(rhs)) # induction condition
      if lhs.info != rhs.info:
        return False
      if len(lhs.successors) != len(rhs.successors):
        return False
      if self.skipfwd:
        from .node import Node
        return all(
            self(inspect.fwd_chain_target(l), inspect.fwd_chain_target(r))
                for l, r in zip(lhs.successors, rhs.successors)
          )
      else:
        return all(self(l,r) for l, r in zip(lhs.successors, rhs.successors))
    elif all(inspect.isa_unboxed_primitive(x) for x in [lhs, rhs]):
      return lhs == rhs
    else:
      return False

def equal(lhs, rhs, skipfwd=False):
  '''
  Curry expression equality based on recursive graph comparison.  Cyclical
  expressions are handled by strictural induction.  By default, no special
  handling for nodes such as forward nodes is performed, so <Int 3> and <Fwd
  <Int 3>> are not equal by this metric.

  Examples:
    Equivalent cyclic expressions will always compare equal, provided
    sufficient resources (especially stack space).  The following, for example,
    will all compare equal:

        let a=(0:b), b=(1:a) in a
        let a=(0:1:a) in a
        let a=(0:1:b), b=(0:1:a) in a
        let a=(0:1:0:b), b=(1:0:1:a) in a
    '''
  equality = GraphEquality(skipfwd=skipfwd)
  return equality(lhs, rhs)

def structurally_equal(lhs, rhs):
  return equal(lhs, rhs, skipfwd=False)

def logically_equal(lhs, rhs):
  return equal(lhs, rhs, skipfwd=True)

