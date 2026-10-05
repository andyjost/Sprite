'''
The type terms of the engine.

A term is a FlatCurry type whose leaves may be unification variables.  The
structural nodes are the constructors of the FlatCurry reader, ``TCons`` and
``FuncType``.  A leaf is a :class:`Var`, a union-find cell that is bound once
and never rebound, or a :class:`Rigid`, a type variable of an ``exprtype``
string, which unifies with itself alone.

The pseudo constructor ``Prelude.Apply`` applies a type variable to a type.
:func:`whnf` folds an ``Apply`` whose head became a constructor, up to the
declared arity of the constructor, so that ``Apply IO Int`` reads ``IO Int``,
and writes a saturated ``(->)`` as a ``FuncType``.  :func:`zonk` resolves a
term into a FlatCurry type with ``TVar`` leaves, for the printer and for the
defaulting table.
'''

from ..toolchain.flat2icurry import flatcurry as fc
from .sigtable import show_type
import itertools

__all__ = [
    'APPLY', 'ARROW', 'Naming', 'Rigid', 'Var', 'arrow', 'free_vars'
  , 'instantiate', 'is_ground', 'occurs', 'prune', 'tcons', 'tree_size'
  , 'type_arity', 'whnf', 'zonk'
  ]

APPLY = fc.prelude('Apply')
ARROW = fc.prelude('(->)')
LIST = fc.prelude('[]')

class Var:
  '''
  A unification variable.

  Attributes:
    binding:
        The term this variable is bound to, or None.  Only the representative
        of a class is ever bound.
    kind:
        The kind the scheme declared, for messages; None for a fresh variable.
    holders:
        The specs that own this variable: literal and free-variable specs.
        The lists of two classes are merged when the classes are united.
    preds:
        The class predicates on this variable, merged in the same way.
  '''
  __slots__ = ('_parent', 'binding', 'uid', 'kind', 'holders', 'preds')
  _counter = itertools.count(1)

  def __init__(self, kind=None):
    self._parent = None
    self.binding = None
    self.uid = next(Var._counter)
    self.kind = kind
    self.holders = []
    self.preds = []

  def find(self):
    '''The representative of this variable, with path compression.'''
    root = self
    while root._parent is not None:
      root = root._parent
    node = self
    while node is not root:
      parent = node._parent
      node._parent = root
      node = parent
    return root

  def union(self, other):
    '''Unites two unbound representatives; ``other`` becomes the root.'''
    assert self._parent is None and self.binding is None
    assert other._parent is None and other.binding is None
    if self is other:
      return
    self._parent = other
    other.holders.extend(self.holders)
    other.preds.extend(self.preds)
    self.holders = []
    self.preds = []
    if other.kind is None:
      other.kind = self.kind

  def __repr__(self):
    return '<Var %d>' % self.uid

class Rigid:
  '''
  A type variable of an ``exprtype`` string.  It is a constant to the
  unifier: it unifies with itself and with an unbound :class:`Var`, and with
  nothing else.
  '''
  __slots__ = ('name', 'source')

  def __init__(self, name, source=None):
    self.name = name
    self.source = source

  def __repr__(self):
    return '<Rigid %s>' % self.name

def tcons(name, *args):
  '''A constructor type of the Prelude, e.g., ``tcons('Maybe', a)``.'''
  return fc.TCons(fc.prelude(name), list(args))

def arrow(domain, range):
  return fc.FuncType(domain, range)

def type_arity(interp):
  '''
  A function from the qualified name of a type constructor to its declared
  arity, or None for a type without an interface entry.
  '''
  table = interp.sigtable
  cache = {}
  def arity(typename):
    if typename not in cache:
      decl = table.type_decl(typename)
      cache[typename] = None if decl is None else len(decl.typevars)
    return cache[typename]
  return arity

def prune(term):
  '''Follows the bindings of a variable to the term it stands for.'''
  while isinstance(term, Var):
    root = term.find()
    if root.binding is None:
      return root
    term = root.binding
  return term

def whnf(term, arity=None):
  '''
  The head of a term: a pruned term whose ``Apply`` is folded when its head
  is a constructor with room for one more argument, and whose saturated
  ``(->)`` is a ``FuncType``.  ``arity`` maps a qualified type name to its
  declared arity, or None; without it every such ``Apply`` is folded.
  '''
  term = prune(term)
  if isinstance(term, fc.TCons):
    name, args = term.name, term.args
    if name == APPLY and len(args) == 2:
      head = whnf(args[0], arity)
      if isinstance(head, fc.TCons) and head.name != APPLY:
        n = None if arity is None else arity('%s.%s' % head.name)
        if n is None or len(head.args) < n:
          return whnf(fc.TCons(head.name, list(head.args) + [args[1]]), arity)
      if head is not args[0]:
        return fc.TCons(APPLY, [head, args[1]])
    elif name == ARROW and len(args) == 2:
      return fc.FuncType(args[0], args[1])
  return term

def _parts(t):
  '''The subterms of a structural node, or None for a leaf.'''
  if isinstance(t, fc.FuncType):
    return (t.domain, t.range)
  if isinstance(t, fc.TCons):
    return t.args
  if isinstance(t, fc.ForallType):
    return (t.typeexpr,)
  return None

def occurs(var, term):
  '''
  Whether the unbound variable ``var`` occurs in ``term``.  A structural
  node is visited once, so a term whose tree is exponential in the size of
  its graph (the type of a value that shares a node between two components
  of a pair, at every level) costs the size of the graph.
  '''
  var = var.find()
  seen = set()
  stack = [term]
  while stack:
    t = prune(stack.pop())
    if isinstance(t, Var):
      if t is var:
        return True
      continue
    parts = _parts(t)
    if parts is not None and id(t) not in seen:
      seen.add(id(t))
      stack.extend(parts)
  return False

def free_vars(term):
  '''
  The unbound variables of a term, in the order of their first occurrence.
  A structural node is visited once (see :func:`occurs`).
  '''
  found = []
  seen = set()
  nodes = set()
  stack = [term]
  while stack:
    t = prune(stack.pop())
    if isinstance(t, Var):
      if t.uid not in seen:
        seen.add(t.uid)
        found.append(t)
      continue
    parts = _parts(t)
    if parts is not None and id(t) not in nodes:
      nodes.add(id(t))
      stack.extend(reversed(parts))
  return found

def tree_size(term, cap=None):
  '''
  The number of nodes of the type :func:`zonk` would write for ``term``: the
  size of its tree, counted over its graph, so a shared subterm is measured
  once and counted at every occurrence.  With ``cap``, a count above it is
  reported as ``cap + 1``; the walk itself costs the size of the graph.
  '''
  sizes = {}
  stack = [(term, False)]
  while stack:
    t, ready = stack.pop()
    t = prune(t)
    key = id(t)
    parts = _parts(t)
    if ready:
      size = 1 + sum(sizes[id(prune(p))] for p in parts)
      if cap is not None and size > cap:
        size = cap + 1
      sizes[key] = size
      continue
    if key in sizes:
      continue
    if parts is None:
      sizes[key] = 1
      continue
    stack.append((t, True))
    for p in parts:
      if id(prune(p)) not in sizes:
        stack.append((p, False))
  return sizes[id(prune(term))]

def is_ground(term):
  '''Whether a term holds no unbound variable and no rigid variable.'''
  stack = [term]
  while stack:
    t = prune(stack.pop())
    if isinstance(t, (Var, Rigid)):
      return False
    elif isinstance(t, fc.FuncType):
      stack.append(t.domain)
      stack.append(t.range)
    elif isinstance(t, fc.TCons):
      stack.extend(t.args)
    elif isinstance(t, fc.ForallType):
      stack.append(t.typeexpr)
  return True

def instantiate(typeexpr, mapping, kinds=None):
  '''
  The term of a FlatCurry type.  ``mapping`` takes the index of a type
  variable to its :class:`Var`; a variable absent from it gets a fresh one,
  with the kind ``kinds`` gives for the index.  A nested ``ForallType``
  quantifies fresh variables for its own indices.
  '''
  if isinstance(typeexpr, fc.TVar):
    var = mapping.get(typeexpr.index)
    if var is None:
      kind = None if kinds is None else kinds.get(typeexpr.index)
      var = mapping[typeexpr.index] = Var(kind)
    return var
  if isinstance(typeexpr, fc.FuncType):
    return fc.FuncType(
        instantiate(typeexpr.domain, mapping, kinds)
      , instantiate(typeexpr.range, mapping, kinds)
      )
  if isinstance(typeexpr, fc.TCons):
    return fc.TCons(
        typeexpr.name, [instantiate(a, mapping, kinds) for a in typeexpr.args]
      )
  if isinstance(typeexpr, fc.ForallType):
    inner = dict(mapping)
    for index, kind in typeexpr.typevars:
      inner[index] = Var(kind)
    return instantiate(typeexpr.typeexpr, inner, kinds)
  if isinstance(typeexpr, (Var, Rigid)):
    return typeexpr
  raise TypeError('not a type expression: %r' % (typeexpr,))

class Naming:
  '''
  Names the unbound variables of the terms it zonks, in the order of their
  first occurrence.  ``names`` maps the index of a rigid variable to its
  name, for the printer.
  '''
  def __init__(self):
    self.indices = {}
    self.leaves = {}
    self.names = {}

  def index(self, leaf):
    '''The index of an unbound or rigid variable; a new one on first use.'''
    index = self.indices.get(leaf)
    if index is None:
      index = self.indices[leaf] = len(self.leaves)
      self.leaves[index] = leaf
      if isinstance(leaf, Rigid):
        self.names[index] = leaf.name
    return index

  def leaf(self, index):
    '''The variable of an index.'''
    return self.leaves[index]

  def show(self, typeexpr, module=None):
    '''Prints a zonked type with the rigid names.'''
    return show_type(typeexpr, names=self.names, module=module)

def zonk(term, naming=None, arity=None):
  '''
  Resolves a term into a FlatCurry type.  An unbound variable becomes a
  ``TVar`` whose index ``naming`` assigns; a rigid variable too, with its
  name recorded.  ``Apply`` of a constructor is folded on the way.
  '''
  if naming is None:
    naming = Naming()
  t = whnf(term, arity)
  if isinstance(t, (Var, Rigid)):
    return fc.TVar(naming.index(t))
  if isinstance(t, fc.FuncType):
    return fc.FuncType(zonk(t.domain, naming, arity), zonk(t.range, naming, arity))
  if isinstance(t, fc.TCons):
    return fc.TCons(t.name, [zonk(a, naming, arity) for a in t.args])
  if isinstance(t, fc.ForallType):
    return fc.ForallType(t.typevars, zonk(t.typeexpr, naming, arity))
  if isinstance(t, fc.TVar):
    return t
  raise TypeError('not a type term: %r' % (t,))
