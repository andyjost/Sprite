from copy import copy
from ....cxx.runtime.pybindings import Fingerprint
from .....utility import shared, unionfind
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

  def __copy__(self):
    return self.clone(self.root)

  def clone(self, root):
    state = self.fingerprint, self.strict_constraints, self.bindings, self.escape_all
    assert not self.residuals
    return Configuration(root, *map(copy, state))

  @property
  def realpath(self):
    '''Gives the full real path to the cursor.'''
    return tuple(self.callstack.realpath())

  def __repr__(self):
    return '{{fp=%s, cst=%s, bnd=%s}}' % (
        self.fingerprint, self.strict_constraints.read, self.bindings
      )
