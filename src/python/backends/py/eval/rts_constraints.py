'''
Implements RuntimeState methods related to constraints.  This module is not
intended to be imported except by rts.py.
'''

__all__ = ['constraint_type', 'constrain_equal', 'lift_constraint', 'occurs']

from ....common import LEFT, RIGHT, UNDETERMINED, T_FREE, T_CHOICE, T_CTOR
from ..graph.node import Node
from .. import graph
from .... import inspect

STRICT_CONSTRAINT = 0
NONSTRICT_CONSTRAINT = 1
VALUE_BINDING = 2

def constraint_type(rts, arg=None, config=None):
  '''Indicates the constraint type.'''
  arg = (config or rts.C).root if arg is None else arg
  mapping = {
      id(rts.StrictConstraint)   : STRICT_CONSTRAINT
    , id(rts.NonStrictConstraint): NONSTRICT_CONSTRAINT
    , id(rts.ValueBinding)       : VALUE_BINDING
    }
  return mapping[id(arg.info)]

def constrain_equal(
    rts, arg0, arg1, constraint_type=STRICT_CONSTRAINT, config=None
  ):
  '''
  Constrain the given arguments to be equal in the specified context.  This
  implements the equational constraints (=:=) and (=:<=).  For strict
  constraints, both arguments must be choices or both free variables, and, in
  the latter case, the free variables must represent values of the same type
  (as is guaranteed by the type system).  For non-strict constraints, the first
  argument must be a free variable, and the second is any expression.  This
  implements the "binding" part of (=:<=).  When the left-hand side is not a
  variable, ordinary pull-tabbing computations will proceed until the term is
  evaluated or this function is called.

  Recursive constraints arise from interleaving the rules of (=:=) or (=:<=)
  with narrowing steps.  Suppose x =:= y is first evaluated, then x and y are
  subsequently narrowed to (x0:x1) and (y0:y1), resp.  The recursive
  constraints over subvariables, x0 =:= y0 and x1 =:= y1, must then be
  evaluated.  The timing of this differs slightly for the two constraint types.
  With strict constraints, the subvariables are immediately equated.  For
  non-strict constraints this that would give incorrect semantics.  Instead,
  this function creates a binding.  When (and if) the binding is later applied,
  the recursive non-strict constraints between subvariables are evaluated.

  Args:
    arg0, arg1:
        The arguments to constrain.  Each must be a choice or free variable
        node, or ID. The associated IDs must refer to free variables.

     constraint_type:
         The constraint type.  Must be STRICT_CONSTRAINT or
         NONSTRICT_CONSTRAINT.

     config:
        The configuration to use as context.

  Returns:
    A Boolean indicating whether the resulting configuration remains
    consistent.

  '''
  return _constrain_equal(rts, arg0, arg1, constraint_type, config, False)

def _constrain_equal(rts, arg0, arg1, constraint_type, config, fresh):
  '''
  The body of ``constrain_equal``.  ``fresh`` is true for the pairs of the
  pairing of a generator with a clone made in the same call
  (``_constrain_equal_rec``).
  '''
  rts.telemetry._eqconstr += 1
  config = config or rts.C
  i, j = [rts.obj_id(arg, config) for arg in [arg0, arg1]]
  if i != j:
    if constraint_type == STRICT_CONSTRAINT:
      if not rts.equate_fp(i, j, config=config):
        return False
      # The bindings of a class sit under its root: the roots before the
      # union hand theirs to the root after it.  Two different bindings
      # make the merge inconsistent (issue #128).
      ri, rj = rts.grp_id(i, config), rts.grp_id(j, config)
      config.strict_constraints.write.unite(i, j)
      if not rts.update_binding(ri, config=config):
        return False
      if not rts.update_binding(rj, config=config):
        return False
      if any(map(inspect.isa_freevar, [arg0, arg1])):
        # The occurs check: a cycle through the merged class has no finite
        # instance, so the step fails as an inconsistent constraint does.
        # Two variables of one class (the fork's constraint of a variable
        # with its root; the pairing of two paired generators) identify
        # nothing new, and a fresh leaf of a clone has no instance and lies
        # in no instance outside the class the enclosing union tested:
        # neither needs the test.
        if ri != rj and not fresh and occurs(rts, i, j, ri, rj, config=config):
          return False
        return _constrain_equal_rec(rts, i, j, config=config)
    else:
      return rts.add_binding(i, arg1, config=config)
  return True

def occurs(rts, i, j, ri, rj, config=None):
  '''
  The occurs check at the union of two classes of free variables (the
  decision of 2026-10-12 on the Fair Scheme).  ``i`` and ``j`` are the two
  variables of the constraint, just united; ``ri`` and ``rj`` are the roots
  of their classes before the union.  Returns True when the merged class
  has a cycle: a member whose generator instance, as created so far,
  contains another member of the class.  Such a class has no finite
  instance (x = S x has no term), so the step fails.

  The test is local to the union.  It walks the generator instance of each
  side (the generator of the variable or of its old root; a side without
  one, undecided or fresh, has no instance): the choice nodes along the
  decided path, the constructor cells, through forward cells, down to the
  inner free variables.  An inner variable of the merged class is the
  cycle.  An inner variable of another decided class is bound through that
  class (Def 2.74), so the walk continues into the generator of that
  class, once per class.  A choice the configuration has not decided ends
  the walk there: the variable is not narrowed here, and its generator is
  no instance of it.  The C++ runtime has the same test (occurs in
  state/rts_constraints.cpp), and the checker verifies the invariant
  (D15 (occurs check)).
  '''
  config = config or rts.C
  root = rts.grp_id(i, config=config)
  seen = set()
  for vid, old in [(i, ri), (j, rj)]:
    gen = _class_generator(rts, vid, old)
    if gen is not None and _instance_reaches(rts, gen, root, seen, config):
      return True
  return False

def _class_generator(rts, vid, root):
  '''The generator of variable ``vid``, or of ``root``, the root of its
  class, or None.  A decided class has one at its root (E5).'''
  for k in [vid, root]:
    x = rts.vtable.get(k)
    if x is not None and rts.has_generator(x):
      return x.successors[1]
  return None

def _instance_reaches(rts, gen, root, seen, config):
  '''
  Whether the generator instance ``gen`` contains a variable of the class
  with root ``root``.  ``seen`` holds the roots of the classes whose
  generators were entered.
  '''
  stack = [gen]
  while stack:
    node = inspect.fwd_chain_target(stack.pop())
    if not isinstance(node, Node):
      continue
    tag = node.info.tag
    if tag == T_CHOICE:
      cid, lhs, rhs = node.successors
      lr = rts.read_fp(cid, config=config)
      if lr == LEFT:
        stack.append(lhs)
      elif lr == RIGHT:
        stack.append(rhs)
    elif tag == T_FREE:
      vid = node.successors[0]
      r = rts.grp_id(vid, config=config)
      if r == root:
        return True
      if r in seen:
        continue
      seen.add(r)
      gen = _class_generator(rts, vid, r)
      if gen is not None:
        stack.append(gen)
    elif tag >= T_CTOR:
      stack.extend(node.successors)
  return False

def _constrain_equal_rec(rts, arg0, arg1, config=None):
  '''
  Implements the recursive part of ``constrain_equal.``  Given two arguments
  of one class, if the class has been narrowed, ensure both and the root of
  the class are instantiated and then constrain the subvariables to be
  equal.  The arguments must all be free variables (or arguments
  convertible to free variables) of the same type.

  The pivot is a member of the class with a generator: one of the two
  arguments, the root, or any member (the union by size can make a member
  without a generator the root: the class {a, b} with b narrowed, united
  into {c, d, e}, has the root c, and the constraint a =:= c names neither b
  nor a generator; issue #127).  The root and the two arguments get a clone
  of the pivot's generator when they have none, paired with it, so a read
  at the root finds one (get_generator), and a decided class has a
  generator at its root.

  Examples:
    1. Suppose the arguments are free variables x and y, x has been narrowed to a
    non-empty list, (x0:x1), and y is uninstantiated.  Assuming lists are defined
    with constructor Nil before Cons, this implies xR is in the fingerprint
    (where x is the ID of variable x).  This function would instantiate y,
    creating fresh variables y0, y1, and giving it the generator "[] ?_y
    (y0:y1)"; update the fingerprint with yR; and evaluate the equational
    constraints x0 =:= y0 and x1 =:= y1.  Symbol ?_y means a choice whose ID
    equals the ID of variable y.

    If all these operations succeed in the sense that none invalidate the
    fingerprint, then True is returned.

    2. Suppose neither free variable was narrowed.  This function does
    nothing and returns True.

  Args:
    arg0, arg1:
        The arguments to check.  Each must be a choice or free variable node,
        or ID. If any associated ID does not correspond to a free variable in
        the ``vtable`` then this function does nothing.  At least one of the
        variables must have been narrowed in the given configuration.

     config:
        The configuration to use as context.

  Returns:
    A Boolean indicating whether the new constraints succeeded (i.e., could be
    consistent).
  '''
  config = config or rts.C
  try:
    xs = [rts.get_freevar(x) for x in [arg0, arg1]]
  except KeyError:
    return True
  if not rts.is_narrowed(xs[0], config=config):
    return True
  gid = rts.grp_id(xs[0], config=config)
  root = rts.vtable.get(gid)
  candidates = xs + ([root] if root is not None else [])
  pivot = next((x for x in candidates if rts.has_generator(x)), None)
  if pivot is None:
    parent = config.strict_constraints.read.parent.read
    for k in list(parent):
      x = rts.vtable.get(k) if rts.grp_id(k, config=config) == gid else None
      if x is not None and rts.has_generator(x):
        pivot = x
        break
  if pivot is None:
    return True
  u = rts.get_generator(pivot, config=config)
  seen = []
  for x in [root] + xs:
    if x is None or x is pivot or any(x is y for y in seen):
      continue
    seen.append(x)
    # The leaves of a clone made here are fresh (_constrain_equal).
    fresh = not rts.has_generator(x)
    if fresh:
      rts.clone_generator(pivot, x)
    v = rts.get_generator(x, config=config)
    for p, q in zip(*[graph.walk(uv) for uv in [u,v]]):
      if rts.is_nondet(p.cursor):
        if not _constrain_equal(
            rts, p.cursor, q.cursor, STRICT_CONSTRAINT, config, fresh
          ):
          return False
      if not inspect.isa_freevar(p.cursor):
        p.push()
        q.push()
  return True

def lift_constraint(rts, var, rewrite=None):
  '''
  Similar to a pull-tab step, lift the constraint at ``var.target`` above
  ``var.root.``
  '''
  rts.telemetry._constrlift += 1
  value, pair = var.target.successors
  value = graph.utility.copy_spine(var.root, var.realpath, end=value)
  return Node(var.target.info, value, pair, target=rewrite)

