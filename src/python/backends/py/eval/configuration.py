from copy import copy
from ....common import Fingerprint
from ....utility import shared, unionfind
from . import callstack

__all__ = ['Bindings', 'Configuration']

Bindings = lambda: shared.Shared(dict)

class Configuration(object):
  def __init__(
      self, root, fingerprint=None, strict_constraints=None, bindings=None
    , escape_all=False
    ):
    self.root = root
    self.fingerprint = Fingerprint() if fingerprint is None else fingerprint
    self.strict_constraints = shared.Shared(unionfind.UnionFind) \
        if strict_constraints is None else strict_constraints
    self.bindings = Bindings() if bindings is None else bindings
    self.residuals = set()
    self.callstack = callstack.CallStack()
    self.escape_all = escape_all
    # The number of rewrite steps taken for this configuration.  Steps of a
    # nested set-function evaluation count as well.  See rts_control.count_step.
    self.steps = 0
    # The steps taken since this configuration last spent its step budget.
    self.budget_used = 0
    # The value of ``steps`` when this configuration last overflowed the Python
    # stack, or None.  See rts_control.overflow.
    self.overflow_at = None
    # The value of the global step count when this configuration last
    # overflowed inside a nested queue, or None.  See rts_control.overflow.
    self.overflow_total = None

  def __copy__(self):
    return self.clone(self.root)

  def clone(self, root):
    state = self.fingerprint, self.strict_constraints, self.bindings, self.escape_all
    assert not self.residuals
    return Configuration(root, *map(copy, state))

  def share(self):
    '''
    A copy for a second queue over the same configurations, the clone of a
    capsule (rts_setfunctions.clone_queue): the same root, copies of the
    state, and the residuals the configuration waits on.  The C++ runtime
    shares the configuration between the queues and clones it before a
    step (Queue::unshare_front); the queues of this backend hold
    references, so the copy is made at once.
    '''
    state = self.fingerprint, self.strict_constraints, self.bindings, self.escape_all
    cp = Configuration(self.root, *map(copy, state))
    cp.residuals = set(self.residuals)
    return cp

  @property
  def realpath(self):
    '''Gives the full real path to the cursor.'''
    return tuple(self.callstack.realpath())

  def __repr__(self):
    return '{{fp=%s, cst=%s, bnd=%s}}' % (
        self.fingerprint, self.strict_constraints.read, self.bindings
      )
