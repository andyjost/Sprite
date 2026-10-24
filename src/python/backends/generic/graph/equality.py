'''Implements graph equality.'''
from .... import inspect

class GraphEquality(object):
  '''
  Implements equality checks between Curry expressions.
  '''
  def __init__(self, skipfwd):
    self.skipfwd = bool(skipfwd)
    self.memo = {}
    # The compared nodes.  The memo holds their IDs, which stay unique while
    # the nodes live.  The C++ backend makes a fresh wrapper for a node on
    # each access, so a wrapper can die during the comparison.
    self.keep = []

  def __call__(self, lhs, rhs):
    # The comparison keeps its own stack of pairs, so a deep expression such
    # as a long list cannot exhaust the Python stack.  The pairs are visited
    # in the order of a left-to-right, depth-first traversal.
    #
    # A pair of nodes enters the memo before its successors are compared, and
    # a pair found in the memo counts as equal.  This means pairs of nodes
    # that are still under comparison can compare equal.  This is safe because
    # every pair of corresponding nodes must eventually compare equal in their
    # entirety for a True result to be obtained.  In other words, even if we
    # incorrectly consider two unequal nodes to be the same, we would always
    # discover this later and return False.
    memo = self.memo
    pending = [(lhs, rhs)]
    while pending:
      lhs, rhs = pending.pop()
      seen = memo.get(id(lhs))
      if seen is not None and id(rhs) in seen:
        continue
      if not all(inspect.isa_curry_expr(x) for x in [lhs, rhs]):
        raise TypeError('not a Curry expression')
      if all(inspect.is_boxed(x) for x in [lhs, rhs]):
        if seen is None:
          seen = memo[id(lhs)] = set()
        seen.add(id(rhs)) # induction condition
        self.keep.append((lhs, rhs))
        if lhs.info != rhs.info:
          return False
        lsucc, rsucc = lhs.successors, rhs.successors
        if len(lsucc) != len(rsucc):
          return False
        if self.skipfwd:
          pairs = [
              (inspect.fwd_chain_target(l), inspect.fwd_chain_target(r))
                  for l, r in zip(lsucc, rsucc)
            ]
        else:
          pairs = list(zip(lsucc, rsucc))
        pairs.reverse()
        pending.extend(pairs)
      elif all(inspect.isa_unboxed_primitive(x) for x in [lhs, rhs]):
        if not lhs == rhs:
          return False
      else:
        return False
    return True

def equal(lhs, rhs, skipfwd=False):
  '''
  Curry expression equality based on graph comparison.  Cyclical expressions
  are handled by structural induction.  By default, no special handling for
  nodes such as forward nodes is performed, so <Int 3> and <Fwd <Int 3>> are
  not equal by this metric.

  Examples:
    Equivalent cyclic expressions will always compare equal.  The following,
    for example, will all compare equal:

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
