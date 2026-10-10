'''
The checker of the run-time invariants of the Fair Scheme: the checker mode
of section 6.5 of the memo on the Fair Scheme proofs, behind the interpreter
flag ``checker``.  The runtime state holds one Checker when the flag is on
(RuntimeState.checker) and None otherwise; every hook in the runtime is one
test of that attribute.  The checker observes.  It changes no step, no
value and no counter.  A violation raises InvariantViolation, an
AssertionError whose message names the invariant, the event, the
configuration, the identifiers and the goal position.

The events the memo names, and the checks at each:

* A fork (a choice at the root of a configuration; rts_fingerprint.fork).
  B1: the fingerprint of the configuration and of each clone is a function,
  its group invariant holds (every decided identifier agrees with the root
  of its group, and no member disagrees), and the fingerprints along the
  dispatch chain agree; each clone keeps every decision of its parent,
  has the decision of the fork and adds at most the forked identifier and
  its group root (rule D.2).  S0: a fork inside a capsule is on an
  identifier that is function-derived for the capsule, that is in the
  escape set of no enclosing capsule and that no enclosing configuration
  decided, or on one the queue was split on before (def:s-escapes).  The
  escape sets only grow.

* An escape (rule SF.1, the split of a queue; rts_setfunctions.split_queue).
  B1 for every configuration of the queue.  S0: the escaping identifier is
  argument-derived for the capsule or for an enclosing one, or an enclosing
  configuration decided it.  S-split: the kept queue holds the LEFT and the
  undecided configurations, the new one the RIGHT and the undecided,
  nothing else and nothing lost, both record the identifier, both name one
  set (one escape set).

* An insertion into an escape set (a pull-tab across a box;
  update_escape_set).  S0: the identifier is argument-derived for the set.

* A pull-tab (rts_fingerprint.pull_tab).  B1: the created choice carries the
  identifier of its source, and the two alternatives are faithful copies of
  the spine: fresh cells along the path, the cells off the path shared, the
  alternative at the end.  S0 (def:s-pull): the identifier is in the escape
  set of every box the path crosses.

* A yield (rts_control.release_value).  B1 as at a fork; no choice cell,
  operation cell, failure or constraint is reachable from the value (the
  generator of a free variable and the arguments of a partial application
  are not entered); X-c: no bound variable remains in the value, and for
  every variable with a decided root identifier the identifiers on the
  decided path of its generator are decided.

* An instantiation (rule S.x; rts_freevars.instantiate), the copy of rule
  N.x (fairscheme.N and hnf), and the creation of a generator.  X1: one
  generator per variable, with the variable's identifier at its root.
  X-b': the write is a faithful copy of the spine with the generator at the
  end, and the reduct of every configuration that references the redex,
  read under the fingerprint it is compatible with, is the same before and
  after the write; the same for the private copy of rule N.x against the
  root it replaces.  The reduct is read with the generator image of the
  memo: a decided choice is its side, a bound variable is its binding or
  its generator, a free variable is its group.  The comparison is bounded
  (SIGNATURE_BUDGET cells per event); an event over the budget is counted,
  not checked.

* A step (fairscheme.S, after a completed step).  The choice a step creates
  is tagged with the boxes above it: the set guards crossed on the path
  from the root of each configuration of the dispatch chain to the redex,
  and the capsules whose arguments reached the redex (the flags of the
  cell, set by the entry walk of the capsule and inherited by the cells a
  step creates at a flagged redex: the walk starts at the successors of
  the result, under PROPAGATE_BUDGET).  The tags define "argument-derived".
  B2: a replacement by failure comes from an exempt leaf of the
  definitional tree of the operation, or from a built-in.

* An inductive position (fairscheme.hnf, at entry).  B2: the position is an
  inductive position of a branch of the definitional tree of the operation
  at the redex that matches the constructors already at the positions above
  it.  The tree is rebuilt from the ICurry case structure of the operation.
  A built-in has no tree and is not checked.

Section 6.5 of the memo asks for these checks in the Python backend first;
the C++ runtime mirrors them behind the same flag in a later lane.
'''

from ....common import (
    LEFT, RIGHT, UNDETERMINED, T_SETGRD, T_FAIL, T_CONSTR, T_FREE, T_FWD
  , T_CHOICE, T_FUNC, T_CTOR
  )
from .... import icurry, inspect
from ..graph.node import Node
import collections, hashlib

__all__ = ['Checker', 'InvariantViolation']

# The number of cells one reduct comparison may read.  An event whose
# reducts are larger is counted in ``counts['over_budget']`` and not
# compared.
SIGNATURE_BUDGET = 5000

# The number of cells the entry walk of a capsule may flag.  A capsule with
# a larger argument is counted and its S0 checks are skipped.
ENTRY_BUDGET = 50000

# The number of fresh cells one step or one copy may flag.
PROPAGATE_BUDGET = 1024

# The number of cells a description of an expression prints.
TEXT_LIMIT = 48

class InvariantViolation(AssertionError):
  '''A run-time invariant of the Fair Scheme does not hold.'''
  def __init__(self, invariant, event, detail, context=()):
    self.invariant = invariant
    self.event = event
    self.detail = detail
    lines = ['Fair Scheme invariant %s violated at %s: %s' % (invariant, event, detail)]
    lines.extend('  ' + line for line in context)
    AssertionError.__init__(self, '\n'.join(lines))

class _OverBudget(Exception):
  pass

# ----------------------------------------------------------------------------
# Read-only views of the state.  The checker must not change the state, so
# it reads the union-find without path compression, the bindings without
# the absorption of _find_binding, and the generators without their
# creation.
# ----------------------------------------------------------------------------

def _root(config, i):
  '''The root of the group of identifier ``i`` in ``config``.'''
  parent = config.strict_constraints.read.parent.read
  while True:
    j = parent.get(i, i)
    if j == i:
      return i
    i = j

def _is_leaf_value(node):
  '''A constructor or a failure without a successor cell.'''
  tag = node.info.tag
  if tag < T_CTOR and tag != T_FAIL:
    return False
  return not any(isinstance(s, Node) for s in node.successors)

def _is_node(arg):
  return isinstance(arg, Node)

def _deref(node):
  '''Passes through forward nodes and set guards.'''
  hops = 0
  while isinstance(node, Node):
    tag = node.info.tag
    if tag == T_FWD:
      node = node.successors[0]
    elif tag == T_SETGRD:
      node = node.successors[1]
    else:
      break
    hops += 1
    if hops > 100000:
      break
  return node

def _at(root, realpath):
  '''The node at ``realpath`` from ``root``: plain indexing.'''
  node = root
  for i in realpath or ():
    node = node.successors[i]
  return node

def _logical(node, path):
  '''The node at the logical ``path``, through forward nodes and guards.'''
  for i in path:
    node = _deref(node)
    if not isinstance(node, Node) or i >= len(node.successors):
      return None
    node = node.successors[i]
  return _deref(node)

def _logical_path(root, realpath):
  '''The logical path of a real path: the steps through forward nodes and
  set guards removed.'''
  path = []
  node = root
  for i in realpath or ():
    if isinstance(node, Node) and node.info.tag in (T_FWD, T_SETGRD):
      pass
    else:
      path.append(i)
    node = node.successors[i]
  return path

def _text(node, limit=TEXT_LIMIT):
  '''A bounded description of an expression.'''
  out = []
  count = [0]
  def go(n, depth):
    count[0] += 1
    if count[0] > limit or depth > 40:
      out.append('...')
      return
    if not isinstance(n, Node):
      out.append(repr(n))
      return
    tag = n.info.tag
    if tag == T_FWD:
      go(n.successors[0], depth + 1)
    elif tag == T_CHOICE:
      out.append('(?%s ' % n.successors[0])
      go(n.successors[1], depth + 1)
      out.append(' ')
      go(n.successors[2], depth + 1)
      out.append(')')
    elif tag == T_FREE:
      out.append('_x%s' % n.successors[0])
    elif tag == T_SETGRD:
      out.append('{box %s|' % n.successors[0])
      go(n.successors[1], depth + 1)
      out.append('}')
    elif not n.successors:
      out.append(n.info.name)
    else:
      out.append('(' + n.info.name)
      for s in n.successors:
        out.append(' ')
        go(s, depth + 1)
      out.append(')')
  go(node, 0)
  return ''.join(out)

# ----------------------------------------------------------------------------
# The definitional tree of an operation, from its ICurry case structure.
# ----------------------------------------------------------------------------

class _Case(object):
  '''A case of the tree: the position of its inductive variable (a logical
  path from the redex, or None when the variable is not a position), and
  the subtree per constructor tag or per literal value.'''
  __slots__ = ('path', 'branches', 'literal')
  def __init__(self, path, branches, literal):
    self.path = path
    self.branches = branches
    self.literal = literal

RETURN = 'return'
EXEMPT = 'exempt'

def _build_tree(rts, block, env):
  '''Builds the tree of ``block``.  ``env`` maps a variable id to its path.'''
  env = dict(env)
  for assign in block.assigns:
    if isinstance(assign, icurry.IVarAssign):
      expr = assign.expr
      if isinstance(expr, icurry.IVarAccess) and env.get(expr.vid) is not None:
        env[assign.vid] = env[expr.vid] + list(expr.path)
      elif isinstance(expr, icurry.IVar) and env.get(expr.vid) is not None:
        env[assign.vid] = env[expr.vid]
      else:
        env[assign.vid] = None
  stmt = block.stmt
  if isinstance(stmt, icurry.ICaseCons):
    branches = {}
    for branch in stmt.branches:
      tag = rts.symbol(branch.symbolname).info.tag
      branches[tag] = _build_tree(rts, branch.block, env)
    return _Case(env.get(stmt.vid), branches, False)
  elif isinstance(stmt, icurry.ICaseLit):
    branches = {
        branch.lit.value: _build_tree(rts, branch.block, env)
            for branch in stmt.branches
      }
    return _Case(env.get(stmt.vid), branches, True)
  elif isinstance(stmt, icurry.IExempt):
    return EXEMPT
  elif isinstance(stmt, icurry.IReturn):
    return RETURN
  elif isinstance(stmt, icurry.IBlock):
    return _build_tree(rts, stmt, env)
  return None

def _cell_key(cell, literal):
  '''The branch key of a constructor cell: its tag, or its literal value.'''
  if not isinstance(cell, Node) or cell.info.tag < T_CTOR:
    return None
  if literal:
    return cell.successors[0] if cell.successors else None
  return cell.info.tag

# ----------------------------------------------------------------------------
# The checker.
# ----------------------------------------------------------------------------

class Checker(object):
  def __init__(self, rts):
    self.rts = rts
    # The tags of an identifier: the set ids of the boxes above its
    # creation.  A choice, a free variable (its generator inherits), or a
    # value binding.
    self.tags = {}
    # The kind of the creation of an identifier: 'choice', 'generator',
    # 'binding', 'variable', 'entry'.
    self.created = {}
    # The generator of a variable, by variable id (X1).
    self.generators = {}
    # The shadow of every escape set: the insertions seen by the hook.
    self.escape_sets = {}
    # The sets whose entry walk exceeded its budget.  Their S0 checks are
    # skipped.
    self.unbounded_sets = set()
    # The flags of a cell: the capsules whose arguments reached it (the
    # entry walk and the inheritance of def:s-flags).  Keyed by id, with
    # the node kept alive beside its set.
    self.flags = {}
    # The trees of the operations, by the id of the info table.
    self.trees = {}
    self._modules_seen = -1
    self._symbols = {}
    self.counts = collections.Counter()

  # --------------------------------------------------------------------------
  # Reporting.
  # --------------------------------------------------------------------------

  def _locate(self, config):
    '''The queue and the index of a configuration.'''
    for qid, queue in self.rts.qtable.items():
      for k, cfg in enumerate(queue):
        if cfg is config:
          return qid, queue.sid, k
    return None, None, None

  def _describe(self, config):
    if config is None:
      return []
    qid, sid, k = self._locate(config)
    try:
      groups = sorted(
          (i, _root(config, i))
              for i in config.strict_constraints.read.parent.read
              if _root(config, i) != i
        )
    except Exception:
      groups = '?'
    return [
        'configuration: queue %s (set %s), index %s, escape_all=%s'
            % (qid, sid, k, config.escape_all)
      , 'fingerprint: %s' % (config.fingerprint,)
      , 'groups (member, root): %s' % (groups,)
      , 'goal position: %s' % (list(config.callstack.realpath()),)
      , 'root: %s' % _text(config.root)
      ]

  def _violation(self, invariant, event, detail, config=None, ids=None, extra=()):
    context = []
    if ids:
      context.append('identifiers: %s' % (ids,))
    context.extend(self._describe(config))
    context.extend(extra)
    self.counts['violations'] += 1
    raise InvariantViolation(invariant, event, detail, context)

  # --------------------------------------------------------------------------
  # Read-only views.
  # --------------------------------------------------------------------------

  def _decision(self, i, config):
    '''The decision of identifier ``i`` for ``config``, read through its
    group and the dispatch chain, as read_fp reads it.'''
    r = _root(config, i)
    for cfg in self.rts.walk_qstack(firstconfig=config):
      if r in cfg.fingerprint:
        return cfg.fingerprint[r]
    return UNDETERMINED

  def _binding(self, vid, config):
    '''The binding of variable ``vid`` for ``config``, or None: the walk of
    _find_binding without its absorption.'''
    rts = self.rts
    for level, qid in enumerate(reversed(rts.qstack)):
      Q = rts.qtable[qid]
      if level and not Q:
        continue
      cfg = config if level == 0 else Q[0]
      gid = _root(cfg, vid)
      if gid in cfg.bindings.read:
        return cfg.bindings.read[gid]
      if gid in Q.absorbed:
        return Q.absorbed[gid]
    return None

  def _has_generator(self, node):
    return node.successors[1].info is not self.rts.prelude.Unit.info

  def _boxes_above(self):
    '''The set ids of the boxes above the current site: the guards crossed
    on the path from the root of each configuration of the dispatch chain
    to its cursor, and the set of a configuration whose root was under the
    guard of its own set (escape_all).'''
    rts = self.rts
    boxes = set()
    for qid in rts.qstack:
      Q = rts.qtable[qid]
      if not Q:
        continue
      C = Q[0]
      if C.escape_all and Q.sid is not None:
        boxes.add(Q.sid)
      for frame in C.callstack.frames:
        obj = frame.obj
        boxes.update(getattr(obj, 'guards', ()))
        boxes.update(getattr(obj, 'base_guards', ()))
        boxes.update(s for s in getattr(obj, 'data', ()) if s is not None)
    return boxes

  def _flags_of(self, node):
    entry = self.flags.get(id(node))
    return frozenset() if entry is None else entry[1]

  def _chain(self):
    '''The configurations enclosing the current one, outermost last.'''
    chain = list(self.rts.walk_qstack())
    return chain[1:]

  # --------------------------------------------------------------------------
  # B1: fingerprints.
  # --------------------------------------------------------------------------

  def _check_fingerprint(self, config, event, chain=None):
    '''The fingerprint of ``config`` is a function, its group invariant
    holds, and it agrees with the fingerprints of ``chain`` (the enclosing
    configurations).'''
    fp = config.fingerprint
    entries = list(fp)
    for i, d in entries:
      if d == UNDETERMINED:
        self._violation(
            'B1', event, 'identifier %s is in the fingerprint undetermined' % i
          , config, ids=[i]
          )
      r = _root(config, i)
      dr = fp.get(r, UNDETERMINED)
      if dr != d:
        self._violation(
            'B1 (group)', event
          , 'identifier %s is decided %s, the root %s of its group is %s'
                % (i, d, r, dr)
          , config, ids=[i, r]
          )
    if chain is None:
      chain = ()
    for cfg in chain:
      for i, d in entries:
        r = _root(cfg, i)
        for j in (i, r):
          dj = cfg.fingerprint.get(j, UNDETERMINED)
          if dj != UNDETERMINED and dj != d:
            self._violation(
                'B1 (dispatch chain)', event
              , 'identifier %s is decided %s here and %s (as %s) in an '
                'enclosing configuration' % (i, d, dj, j)
              , config, ids=[i, j]
              , extra=['enclosing ' + line for line in self._describe(cfg)]
              )

  def _check_escape_sets(self, event, config=None):
    '''Every escape set holds what the hook saw, and nothing less.'''
    for sid, shadow in self.escape_sets.items():
      setf = self.rts.sftable.get(sid)
      actual = set() if setf is None else setf.escape_set
      if not shadow <= actual:
        self._violation(
            'S0 (escape sets grow)', event
          , 'the escape set of set %s lost %s' % (sid, sorted(shadow - actual))
          , config, ids=sorted(shadow - actual)
          )
      if actual - shadow:
        self._violation(
            'S0 (escape sets grow)', event
          , 'the escape set of set %s gained %s outside the rule'
                % (sid, sorted(actual - shadow))
          , config, ids=sorted(actual - shadow)
          )

  # --------------------------------------------------------------------------
  # The events.
  # --------------------------------------------------------------------------

  def fork(self, config, clones):
    '''After rts_fingerprint.fork made ``clones`` of ``config``, whose root
    is a choice.'''
    self.counts['forks'] += 1
    rts = self.rts
    cid = config.root.successors[0]
    chain = self._chain()
    self._check_fingerprint(config, 'fork', chain)
    parent = list(config.fingerprint)
    sides = []
    for clone in clones:
      self._check_fingerprint(clone, 'fork', chain)
      self._check_clone(clone, cid, parent)
      # The decision is recorded in the clone, or an enclosing configuration
      # made it before (update_fp writes nothing then, and one side alone
      # survives).
      d = self._decision(cid, clone)
      if d == UNDETERMINED:
        self._violation(
            'B1', 'fork', 'the clone does not record the decision of %s' % cid
          , clone, ids=[cid]
          )
      sides.append(d)
    if len(clones) > 2 or len(set(sides)) != len(sides):
      self._violation(
          'B1', 'fork', 'the clones decide %s as %s' % (cid, sides)
        , config, ids=[cid]
        )
    if rts.in_recursive_call and cid not in rts.Q.decisions:
      # def:s-escapes: the choice escapes when it is argument-derived for
      # the capsule or for an enclosing one, or when an enclosing
      # configuration decided it.  A fork on such an identifier is allowed
      # after the split alone (cid in the decisions of the queue).
      sid = rts.sid
      tags = self.tags.get(cid, frozenset())
      if sid in tags and sid not in self.unbounded_sets:
        self._violation(
            'S0', 'fork'
          , 'identifier %s is argument-derived for set %s (tags %s) and forks '
            'inside the capsule; it is not in the escape set %s and the '
            'queue was not split on it'
                % (cid, sid, sorted(tags), sorted(rts.sftable[sid].escape_set))
          , config, ids=[cid]
          )
      # The enclosing capsules: the escape sets themselves (the tags of an
      # enclosing set over-approximate them: a choice a function makes
      # inside the inner capsule is created under the box of the outer one).
      chain_sids = set(
          rts.qtable[q].sid for q in rts.qstack if rts.qtable[q].sid is not None
        )
      escaped = sorted(
          s for s in chain_sids if s != sid and cid in self.escape_sets.get(s, ())
        )
      if escaped:
        self._violation(
            'S0', 'fork'
          , 'identifier %s is in the escape sets of the enclosing sets %s and '
            'forks inside the capsule of set %s; the queue was not split on it'
                % (cid, escaped, sid)
          , config, ids=[cid]
          )
      gid = _root(config, cid)
      decided = [
          cfg for cfg in chain
              if gid in cfg.fingerprint or cid in cfg.fingerprint
        ]
      if decided:
        self._violation(
            'S0', 'fork'
          , 'identifier %s was decided by an enclosing configuration and '
            'forks inside the capsule of set %s; the queue was not split on it'
                % (cid, sid)
          , config, ids=[cid, gid]
          , extra=['enclosing ' + line for line in self._describe(decided[0])]
          )
    self._check_escape_sets('fork', config)

  def _check_clone(self, clone, cid, parent):
    '''Rule D.2: the clone keeps every decision of its parent (``parent``
    is the list of the entries of the parent's fingerprint), and adds at
    most the forked identifier ``cid`` and the root of its group.'''
    fp = clone.fingerprint
    for i, d in parent:
      di = fp.get(i, UNDETERMINED)
      if di == UNDETERMINED:
        di = fp.get(_root(clone, i), UNDETERMINED)
      if di != d:
        self._violation(
            'B1 (fork)', 'fork'
          , 'the clone lost the decision %s of identifier %s of its parent '
            '(it reads %s)' % (d, i, di)
          , clone, ids=[i, cid]
          )
    if cid in self.rts.vtable:
      # A fork on a free variable applies its bindings and equates its
      # group (rts_fingerprint.fork), so the clone may add more entries.
      return
    gid = _root(clone, cid)
    known = set(i for i, _ in parent)
    extra = sorted(i for i, _ in fp if i not in known and i not in (cid, gid))
    if extra:
      self._violation(
          'B1 (fork)', 'fork'
        , 'the clone adds the identifiers %s beside the forked identifier %s '
          'and its root %s' % (extra, cid, gid)
        , clone, ids=extra
        )

  def escape(self, qid, cid, before, rhs_qid):
    '''After split_queue split queue ``qid`` on ``cid`` (rule SF.1):
    ``before`` is the list of its configurations before the split and
    ``rhs_qid`` the new queue.'''
    self.counts['escapes'] += 1
    rts = self.rts
    Q = rts.qtable[qid]
    R = rts.qtable[rhs_qid]
    sid = Q.sid
    chain = list(rts.walk_qstack())
    for cfg in before:
      self._check_fingerprint(cfg, 'escape', chain)
    kept = set(map(id, Q))
    moved = set(map(id, R))
    known = set(map(id, before))
    for cfg in before:
      d = cfg.fingerprint.get(_root(cfg, cid), UNDETERMINED)
      expect_kept = d in (LEFT, UNDETERMINED)
      expect_moved = d in (RIGHT, UNDETERMINED)
      if (id(cfg) in kept) != expect_kept or (id(cfg) in moved) != expect_moved:
        self._violation(
            'S-split', 'escape'
          , 'a configuration that decided %s as %s is kept=%s, moved=%s'
                % (cid, d, id(cfg) in kept, id(cfg) in moved)
          , cfg, ids=[cid]
          )
    for queue, name in ((Q, 'kept'), (R, 'new')):
      for cfg in queue:
        if id(cfg) not in known:
          self._violation(
              'S-split', 'escape'
            , 'the %s queue holds a configuration that was not in the queue'
                  % name
            , cfg, ids=[cid]
            )
    if cid not in Q.decisions or cid not in R.decisions:
      self._violation(
          'S-split', 'escape'
        , 'the queues do not both record %s (kept %s, new %s)'
              % (cid, sorted(Q.decisions), sorted(R.decisions))
        , None, ids=[cid]
        )
    if R.sid != sid:
      self._violation(
          'S-split', 'escape'
        , 'the new queue names set %s, the kept queue set %s' % (R.sid, sid)
        , None, ids=[cid]
        )
    if sid not in self.unbounded_sets:
      chain_sids = set(
          rts.qtable[q].sid for q in rts.qstack if rts.qtable[q].sid is not None
        )
      chain_sids.add(sid)
      tags = self.tags.get(cid, frozenset())
      if not (tags & chain_sids):
        decided = any(_root(c, cid) in c.fingerprint for c in chain)
        if not decided:
          self._violation(
              'S0', 'escape'
            , 'identifier %s escapes set %s but is function-derived: its tags '
              'are %s, the capsules of the chain are %s, and no enclosing '
              'configuration decided it'
                  % (cid, sid, sorted(tags), sorted(chain_sids))
            , chain[0] if chain else None, ids=[cid]
            )
    self._check_escape_sets('escape')

  def escape_insert(self, sid, cid):
    '''After update_escape_set added ``cid`` to the escape set of ``sid``.'''
    self.counts['escape_insertions'] += 1
    shadow = self.escape_sets.setdefault(sid, set())
    if cid not in shadow:
      shadow.add(cid)
      if sid not in self.unbounded_sets:
        tags = self.tags.get(cid)
        if tags is None or sid not in tags:
          self._violation(
              'S0 (E in A)', 'escape-set insertion'
            , 'identifier %s enters the escape set of set %s but is not '
              'argument-derived for it (tags %s)'
                  % (cid, sid, None if tags is None else sorted(tags))
            , self.rts.C, ids=[cid]
            )

  def pulltab(self, root, target, realpath, lhs, rhs):
    '''Before pull_tab rewrites: the two copies of the spine from ``root``
    along ``realpath`` with the alternatives of ``target`` at their ends.'''
    self.counts['pulltabs'] += 1
    cid, l, r = target.successors
    if _at(root, realpath) is not target:
      self._violation(
          'B1 (pull-tab)', 'pull-tab'
        , 'the source is not at the path %s of the target' % (list(realpath),)
        , self.rts.C, ids=[cid]
        )
    for copy, end, side in ((lhs, l, 'left'), (rhs, r, 'right')):
      self._check_spine_copy(
          root, realpath, copy, end, 'B1 (pull-tab)', 'pull-tab', side
        )
    self._check_crossed_boxes(root, realpath, cid)
    flags = self._flags_of(root)
    if flags:
      self._propagate(lhs, flags, stop_at=l)
      self._propagate(rhs, flags, stop_at=r)

  def _check_crossed_boxes(self, root, realpath, cid):
    '''def:s-pull: the identifier ``cid`` is in the escape set of every
    box the path from ``root`` to the source crosses.  The insertions
    precede the pull-tab in N and in hnf, so the check is exact here.'''
    node = root
    for k, i in enumerate(realpath or ()):
      if not isinstance(node, Node):
        return
      if node.info.tag == T_SETGRD:
        sid = node.successors[0]
        setf = self.rts.sftable.get(sid)
        if setf is None or cid not in setf.escape_set:
          self._violation(
              'S0 (pull-tab)', 'pull-tab'
            , 'identifier %s crosses the box of set %s at depth %d of the '
              'path %s but is not in its escape set %s'
                  % (cid, sid, k, list(realpath)
                    , None if setf is None else sorted(setf.escape_set))
            , self.rts.C, ids=[cid]
            )
        if cid not in self.escape_sets.get(sid, ()):
          self._violation(
              'S0 (pull-tab)', 'pull-tab'
            , 'identifier %s crosses the box of set %s at depth %d of the '
              'path %s but no insertion into its escape set was seen'
                  % (cid, sid, k, list(realpath))
            , self.rts.C, ids=[cid]
            )
      node = node.successors[i]

  def pulltab_done(self, node, target):
    '''After pull_tab made ``node``, the choice over the copies.'''
    cid = target.successors[0]
    if node.info.tag != T_CHOICE or node.successors[0] != cid:
      self._violation(
          'B1 (pull-tab)', 'pull-tab'
        , 'the created choice carries identifier %s, the source %s'
              % (node.successors[0] if node.successors else None, cid)
        , self.rts.C, ids=[cid]
        )

  def yield_(self, config):
    '''Before release_value makes a value of ``config``.'''
    self.counts['yields'] += 1
    chain = self._chain()
    self._check_fingerprint(config, 'yield', chain)
    self._check_value(config)
    self._check_decided_variables(config)
    self._check_escape_sets('yield', config)

  def _check_value(self, config):
    '''No choice, operation, failure or constraint cell is reachable from
    the root of ``config``, and no bound variable remains in it (X-c).'''
    rts = self.rts
    seen = set()
    stack = [config.root]
    while stack:
      node = stack.pop()
      if not isinstance(node, Node) or id(node) in seen:
        continue
      seen.add(id(node))
      info = node.info
      tag = info.tag
      if tag == T_FWD or tag == T_SETGRD:
        stack.append(node.successors[-1])
      elif tag == T_CHOICE:
        self._violation(
            'B1 (yield)', 'yield'
          , 'choice %s is reachable from the yielded value' % node.successors[0]
          , config, ids=[node.successors[0]]
          )
      elif tag == T_FREE:
        vid = node.successors[0]
        if self._binding(vid, config) is not None:
          self._violation(
              'X-c', 'yield', 'variable %s is bound and remains in the value' % vid
            , config, ids=[vid]
            )
        d = self._decision(vid, config)
        if d != UNDETERMINED:
          self._violation(
              'X-c', 'yield'
            , 'variable %s is decided %s and remains in the value' % (vid, d)
            , config, ids=[vid]
            )
      elif tag == T_FUNC or tag == T_FAIL or tag == T_CONSTR:
        self._violation(
            'B1 (yield)', 'yield'
          , 'the cell %s is reachable from the yielded value' % info.name
          , config
          )
      elif tag >= T_CTOR:
        if not getattr(info, 'is_partial', False):
          stack.extend(node.successors)

  def _check_decided_variables(self, config):
    '''Every identifier on the decided path of the generator of a decided
    variable is decided (X-c).'''
    for vid, x in list(self.rts.vtable.items()):
      gen = x.successors[1]
      if not isinstance(gen, Node) or not self._has_generator(x):
        continue
      if self._decision(vid, config) == UNDETERMINED:
        continue
      node = _deref(gen)
      while isinstance(node, Node) and node.info.tag == T_CHOICE:
        cid = node.successors[0]
        d = self._decision(cid, config)
        if d == UNDETERMINED:
          self._violation(
              'X-c', 'yield'
            , 'variable %s is decided but the inner identifier %s of its '
              'generator is not' % (vid, cid)
            , config, ids=[vid, cid]
            )
        node = _deref(node.successors[1 if d == LEFT else 2])

  # --------------------------------------------------------------------------
  # FS-x: generators, the instantiation, the private copies.
  # --------------------------------------------------------------------------

  def variable(self, node):
    '''After freshvar made the free variable ``node``.'''
    vid = node.successors[0]
    self.created.setdefault(vid, 'variable')
    self.tags[vid] = frozenset(self._boxes_above()) | self.tags.get(vid, frozenset())

  def generator(self, x, gen):
    '''After _make_generator gave the variable ``x`` the generator ``gen``.'''
    self.counts['generators'] += 1
    vid = x.successors[0]
    known = self.generators.get(vid)
    if known is not None and known is not gen:
      self._violation(
          'X1', 'generator'
        , 'variable %s gets a second generator' % vid, self.rts.C, ids=[vid]
        )
    self.generators[vid] = gen
    root = _deref(gen)
    if not isinstance(root, Node) or root.info.tag != T_CHOICE \
        or root.successors[0] != vid:
      self._violation(
          'X1', 'generator'
        , 'the root of the generator of variable %s is %s' % (vid, _text(root))
        , self.rts.C, ids=[vid]
        )
    base = frozenset(self._boxes_above()) | self.tags.get(vid, frozenset()) \
         | self._flags_of(x)
    self.tags[vid] = base
    self.created.setdefault(vid, 'generator')
    stack = [gen]
    seen = set()
    while stack:
      node = stack.pop()
      if not isinstance(node, Node) or id(node) in seen:
        continue
      seen.add(id(node))
      tag = node.info.tag
      if tag == T_CHOICE:
        cid = node.successors[0]
        if cid != vid:
          self.created.setdefault(cid, 'generator')
        self.tags[cid] = self.tags.get(cid, frozenset()) | base
        stack.extend(node.successors[1:])
      elif tag == T_FREE:
        leaf = node.successors[0]
        self.tags[leaf] = self.tags.get(leaf, frozenset()) | base
      else:
        stack.extend(node.successors)
    flags = self._flags_of(x)
    if flags:
      self._propagate(gen, flags)

  def value_bindings(self, x, tree):
    '''After make_value_bindings made ``tree`` for the variable ``x``.'''
    vid = x.successors[0]
    base = frozenset(self._boxes_above()) | self.tags.get(vid, frozenset()) \
         | self._flags_of(x)
    stack = [tree]
    while stack:
      node = stack.pop()
      if isinstance(node, Node) and node.info.tag == T_CHOICE:
        cid = node.successors[0]
        self.created.setdefault(cid, 'binding')
        self.tags[cid] = self.tags.get(cid, frozenset()) | base
        stack.extend(node.successors[1:])

  def instantiate_begin(self, var):
    '''Before instantiate writes the generator into the spine of the redex
    ``var.root``: the variable at the slot, the spine, and the reducts of
    the configurations that reference the redex.'''
    self.counts['instantiations'] += 1
    root, realpath, gen = var.root, var.realpath or [], var.target
    x = _at(root, realpath)
    if not isinstance(x, Node) or x.info.tag != T_FREE:
      self._violation(
          'X1', 'instantiation'
        , 'the slot at %s holds %s, not a free variable' % (list(realpath), _text(x))
        , self.rts.C
        )
    vid = x.successors[0]
    if x.successors[1] is not gen:
      self._violation(
          'X1', 'instantiation'
        , 'the generator written for variable %s is not its generator' % vid
        , self.rts.C, ids=[vid]
        )
    known = self.generators.get(vid)
    if known is not None and known is not gen:
      self._violation(
          'X1', 'instantiation'
        , 'variable %s has two generators' % vid, self.rts.C, ids=[vid]
        )
    reducts = self._reducts(root)
    return x, reducts

  def instantiate_end(self, var, before):
    '''After the write of instantiate.'''
    x, reducts = before
    root, realpath, gen = var.root, var.realpath or [], var.target
    new = _at(root, realpath)
    if new is not gen:
      self._violation(
          'X-b\'', 'instantiation'
        , 'the slot at %s holds %s after the write, not the generator'
              % (list(realpath), _text(new))
        , self.rts.C, ids=[x.successors[0]]
        )
    if reducts is not None:
      self._compare_reducts(reducts, 'instantiation', x.successors[0])
    flags = self._flags_of(root)
    if flags:
      self._propagate(root, flags, stop_at=gen)

  def copied(self, old, new, realpath, end, kind):
    '''After a private copy of the spine from ``old`` along ``realpath``
    with ``end`` at its end replaced the root of the current configuration
    (rule N.x; ``kind`` names the replacement).'''
    self.counts['copies'] += 1
    config = self.rts.C
    self._check_spine_copy(old, realpath, new, end, 'X-b\'', 'copy (%s)' % kind)
    try:
      state = _SigState(SIGNATURE_BUDGET)
      a = self._sig(old, config, state)
      b = self._sig(new, config, state)
    except (_OverBudget, RecursionError):
      self.counts['over_budget'] += 1
    else:
      if a != b:
        self._violation(
            'X-b\'', 'copy (%s)' % kind
          , 'the reduct of the configuration changed under its fingerprint'
          , config
          , extra=['before: %s' % _text(old), 'after: %s' % _text(new)]
          )
    flags = self._flags_of(old)
    if flags:
      self._propagate(new, flags, stop_at=end)

  def _check_spine_copy(self, root, realpath, copy, end, invariant, event, side=''):
    '''``copy`` is a fresh copy of the spine from ``root`` along
    ``realpath`` with ``end`` at its end: fresh cells of the same symbols
    along the path, the cells off the path shared.'''
    orig, cp = root, copy
    for k, i in enumerate(realpath or ()):
      if cp is orig:
        self._violation(
            invariant, event
          , 'the %s copy shares the cell at depth %d of the spine' % (side, k)
          , self.rts.C
          )
      if not isinstance(cp, Node) or cp.info is not orig.info:
        self._violation(
            invariant, event
          , 'the %s copy has %s at depth %d where the spine has %s'
                % (side, _text(cp), k, _text(orig))
          , self.rts.C
          )
      so, sc = orig.successors, cp.successors
      if len(so) != len(sc):
        self._violation(
            invariant, event, 'the %s copy has another arity at depth %d' % (side, k)
          , self.rts.C
          )
      for j in range(len(so)):
        if j != i and sc[j] is not so[j]:
          self._violation(
              invariant, event
            , 'the %s copy does not share the cell off the path at depth %d, '
              'index %d' % (side, k, j)
            , self.rts.C
            )
      orig, cp = so[i], sc[i]
    if end is not None and cp is not end:
      self._violation(
          invariant, event
        , 'the end of the %s copy is %s, not the replacement %s'
              % (side, _text(cp), _text(end))
        , self.rts.C
        )

  def _reducts(self, watch):
    '''The reducts of the configurations of every queue that reach the
    cell ``watch``: a map from the id of the configuration to the
    configuration and its signature.  None when the walk exceeds the
    budget.'''
    # One state per configuration: the signature of a cell depends on the
    # fingerprint.  The budget is shared.
    budget = SIGNATURE_BUDGET
    found = {}
    try:
      for queue in list(self.rts.qtable.values()):
        for cfg in list(queue):
          state = _SigState(budget, watch)
          sig = self._sig(cfg.root, cfg, state)
          budget = state.budget
          if state.reached:
            found[id(cfg)] = (cfg, sig)
    except (_OverBudget, RecursionError):
      self.counts['over_budget'] += 1
      return None
    return found

  def _compare_reducts(self, reducts, event, vid):
    try:
      for cfg, sig in reducts.values():
        state = _SigState(SIGNATURE_BUDGET)
        after = self._sig(cfg.root, cfg, state)
        if after != sig:
          self._violation(
              'X-b\'', event
            , 'the reduct of a configuration that references the redex '
              'changed under its fingerprint at the instantiation of variable '
              '%s' % vid
            , cfg, ids=[vid]
            )
    except (_OverBudget, RecursionError):
      self.counts['over_budget'] += 1

  def _sig(self, node, config, state):
    '''The signature of the reduct of ``node`` under the fingerprint of
    ``config``, read with the generator image: a decided choice is its
    side, a bound variable its binding or its generator, a free variable
    and an undecided generator root the group of the variable.'''
    rts = self.rts
    unit = rts.prelude.Unit.info
    hops = 0
    while True:
      if not isinstance(node, Node):
        return _digest(b'L' + repr(node).encode('utf-8', 'replace'))
      if node is state.watch:
        state.reached = True
      key = id(node)
      hit = state.memo.get(key)
      if hit is not None:
        return hit
      if key in state.onstack:
        return _digest(b'cycle')
      tag = node.info.tag
      hops += 1
      if hops > 100000:
        return _digest(b'cycle')
      if tag == T_FWD:
        node = node.successors[0]
      elif tag == T_SETGRD:
        node = node.successors[1]
      elif tag == T_CHOICE:
        cid = node.successors[0]
        d = self._decision(cid, config)
        if d == LEFT:
          node = node.successors[1]
        elif d == RIGHT:
          node = node.successors[2]
        elif cid in rts.vtable:
          return _digest(b'F%d' % _root(config, cid))
        else:
          break
      elif tag == T_FREE:
        vid = node.successors[0]
        binding = self._binding(vid, config)
        if binding is not None:
          node = binding
        elif node.successors[1].info is not unit \
            and self._decision(vid, config) != UNDETERMINED:
          node = node.successors[1]
        else:
          return _digest(b'F%d' % _root(config, vid))
      else:
        break
    state.budget -= 1
    if state.budget < 0:
      raise _OverBudget()
    if tag == T_CHOICE:
      label = b'?%d' % node.successors[0]
      kids = node.successors[1:]
    else:
      label = ('%s/%d' % (node.info.name, tag)).encode('utf-8', 'replace')
      kids = node.successors
    state.onstack.add(key)
    parts = [self._sig(kid, config, state) for kid in kids]
    state.onstack.discard(key)
    digest = _digest(label + b'(' + b''.join(parts) + b')')
    state.memo[key] = digest
    return digest

  # --------------------------------------------------------------------------
  # FS-S: the tags and the flags.
  # --------------------------------------------------------------------------

  def capsule_entry(self, sid, goal):
    '''After create_queue set the goal of set ``sid``: every cell reachable
    from a boxed argument of the goal is inside the capsule (the entry step
    of def:s-flags).'''
    self.counts['capsules'] += 1
    self.escape_sets.setdefault(sid, set())
    if not isinstance(goal, Node):
      return
    budget = ENTRY_BUDGET
    stack = [
        s for s in goal.successors
          if isinstance(s, Node) and s.info.tag == T_SETGRD and s.successors[0] == sid
      ]
    while stack:
      node = stack.pop()
      if not isinstance(node, Node):
        continue
      key = id(node)
      entry = self.flags.get(key)
      if entry is not None and sid in entry[1]:
        continue
      budget -= 1
      if budget < 0:
        self.unbounded_sets.add(sid)
        self.counts['entry_over_budget'] += 1
        return
      self.flags[key] = (node, (frozenset() if entry is None else entry[1]) | {sid})
      tag = node.info.tag
      if tag == T_CHOICE:
        cid = node.successors[0]
        self.created.setdefault(cid, 'entry')
        self.tags[cid] = self.tags.get(cid, frozenset()) | {sid}
      elif tag == T_FREE:
        vid = node.successors[0]
        self.tags[vid] = self.tags.get(vid, frozenset()) | {sid}
      stack.extend(node.successors)

  def _propagate(self, node, flags, stop_at=None):
    '''The cells reachable from ``node`` that carry no flags yet inherit
    ``flags``: the cells a pull-tab, a copy or a generator created at a
    flagged site.  The walk stops at a flagged cell and at ``stop_at``.'''
    self._propagate_all([node], flags, stop_at)

  def _propagate_all(self, seeds, flags, stop_at=None):
    '''The walk of _propagate from every cell of ``seeds``, under one
    budget: the cells a step made (see step).  A walk over the budget
    leaves cells without the flags, so the sets of ``flags`` become
    unbounded: their checks of S0 are suppressed, not reported, as after
    an entry walk over its budget.  A leaf value (a constructor or a
    failure without a successor cell) is not flagged: it never steps and
    holds no cell.'''
    budget = PROPAGATE_BUDGET
    stack = list(seeds)
    while stack:
      n = stack.pop()
      if not isinstance(n, Node) or n is stop_at or _is_leaf_value(n):
        continue
      key = id(n)
      entry = self.flags.get(key)
      if entry is not None:
        if flags <= entry[1]:
          continue
        self.flags[key] = (n, entry[1] | flags)
        continue
      budget -= 1
      if budget < 0:
        self.unbounded_sets.update(flags)
        self.counts['propagate_over_budget'] += 1
        return
      self.flags[key] = (n, flags)
      tag = n.info.tag
      if tag == T_CHOICE:
        cid = n.successors[0]
        self.tags[cid] = self.tags.get(cid, frozenset()) | flags
      elif tag == T_FREE:
        vid = n.successors[0]
        self.tags[vid] = self.tags.get(vid, frozenset()) | flags
      stack.extend(n.successors)

  # --------------------------------------------------------------------------
  # Steps and the definitional trees.
  # --------------------------------------------------------------------------

  def step(self, node, info, args):
    '''After S completed a step at ``node``, which held ``info`` with the
    successors ``args`` before the step.'''
    self.counts['steps'] += 1
    tag = node.info.tag
    flagged = self.flags.get(id(node))
    if tag == T_CHOICE:
      cid = node.successors[0]
      if cid not in self.created:
        self.created[cid] = 'choice'
        tags = frozenset(self._boxes_above())
        if flagged is not None:
          tags |= flagged[1]
        self.tags[cid] = tags | self.tags.get(cid, frozenset())
    if flagged is not None:
      # The cells the step made inherit the flags of the redex: the cells
      # under the result.  The redex carries the flags already, so a walk
      # that started there stopped at once, and a cell made under it (the
      # `?` of Just (A ? B)) inherited nothing: the false report of S0
      # (E in A) at the pull-tab across the box (2026-10-09).
      self._propagate_all(node.successors, flagged[1])
    if tag == T_FAIL:
      tree = self._tree(info)
      if tree is not None:
        self._check_exempt(info, args, tree)

  def hnf(self, var, typedef, values):
    '''At the entry of hnf for the inductive position ``var``.'''
    self.counts['hnfs'] += 1
    root = var.root
    if not isinstance(root, Node) or root.info.tag != T_FUNC:
      return
    tree = self._tree(root.info)
    if tree is None:
      self.counts['hnf_untracked'] += 1
      return
    path = _logical_path(root, var.realpath)
    self._check_position(root, root.successors, tree, path)

  def _check_position(self, root, args, tree, path):
    '''``path`` is the position of a case of ``tree`` whose branches above
    it match the constructors at their positions (B2 a, b).'''
    node = tree
    matched = []
    while isinstance(node, _Case):
      if node.path is None:
        self.counts['hnf_untracked'] += 1
        return
      if node.path == path:
        return
      cell = _logical_from_args(args, node.path)
      key = _cell_key(cell, node.literal)
      if key is None:
        self._violation(
            'B2', 'hnf'
          , 'operation %s demands position %s before the inductive position '
            '%s above it, which holds %s' % (root.info.name, path, node.path, _text(cell))
          , self.rts.C
          , extra=['matched: %s' % matched]
          )
      branch = node.branches.get(key)
      if branch is None:
        self._violation(
            'B2', 'hnf'
          , 'operation %s demands position %s under a constructor at %s that '
            'matches no branch' % (root.info.name, path, node.path)
          , self.rts.C
          , extra=['matched: %s' % matched]
          )
      matched.append((node.path, key))
      node = branch
    self._violation(
        'B2', 'hnf'
      , 'operation %s demands position %s, which is not an inductive position '
        'of a branch that matches (the tree ends in %s)'
            % (root.info.name, path, node)
      , self.rts.C
      , extra=['matched: %s' % matched]
      )

  def _check_exempt(self, info, args, tree):
    '''A replacement by failure comes from an exempt leaf (B2 c).'''
    node = tree
    matched = []
    while isinstance(node, _Case):
      if node.path is None:
        return
      cell = _logical_from_args(args, node.path)
      key = _cell_key(cell, node.literal)
      if key is None:
        self._violation(
            'B2 (failure)', 'step'
          , 'operation %s failed while its inductive position %s holds %s'
                % (info.name, node.path, _text(cell))
          , self.rts.C
          , extra=['matched: %s' % matched]
          )
      branch = node.branches.get(key)
      if branch is None:
        if node.literal:
          return
        self._violation(
            'B2 (failure)', 'step'
          , 'operation %s failed on a constructor at %s that matches no branch'
                % (info.name, node.path)
          , self.rts.C
          , extra=['matched: %s' % matched]
          )
      matched.append((node.path, key))
      node = branch
    if node is not EXEMPT:
      self._violation(
          'B2 (failure)', 'step'
        , 'operation %s was replaced by a failure from a %s leaf'
              % (info.name, node)
        , self.rts.C
        , extra=['matched: %s' % matched]
        )

  def _tree(self, info):
    '''The definitional tree of the operation with ``info``, or None for a
    built-in or an operation the checker cannot find.'''
    key = id(info)
    hit = self.trees.get(key)
    if hit is not None:
      return hit[1]
    symbol = self._symbol(info)
    tree = None
    if symbol is not None:
      try:
        ifun = inspect.geticurry(symbol)
      except Exception:
        ifun = None
      body = getattr(ifun, 'body', None)
      block = getattr(body, 'block', None)
      if isinstance(block, icurry.IBlock):
        try:
          tree = _build_tree(self.rts, block, {0: []})
        except Exception:
          tree = None
    self.trees[key] = (info, tree)
    return tree

  def _symbol(self, info):
    '''The symbol whose info table is ``info``, from the modules of the
    interpreter.'''
    key = id(info)
    modules = self.rts.interp.modules
    if key not in self._symbols or len(modules) != self._modules_seen:
      for module in list(modules.values()):
        try:
          symbols = inspect.symbols(module, private=True)
        except Exception:
          continue
        for symbol in symbols.values():
          self._symbols.setdefault(id(symbol.info), symbol)
      self._modules_seen = len(modules)
    return self._symbols.get(key)

class _SigState(object):
  __slots__ = ('budget', 'memo', 'onstack', 'reached', 'watch')
  def __init__(self, budget, watch=None):
    self.budget = budget
    self.memo = {}
    self.onstack = set()
    self.reached = False
    self.watch = watch

def _digest(data):
  return hashlib.blake2b(data, digest_size=16).digest()

def _logical_from_args(args, path):
  '''The node at the logical ``path`` from a redex given by its successors
  ``args``.'''
  if not path:
    return None
  i = path[0]
  if i >= len(args):
    return None
  return _logical(args[i], path[1:])
