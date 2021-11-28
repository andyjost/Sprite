'''
Implements RuntimeState methods related to constraints.  This module is not
intended to be imported except by state.py.
'''

__all__ = ['constraint_type', 'constrain_equal', 'lift_constraint']

from .....common import T_FREE, T_CHOICE
from ..graph.node import Node
from .. import graph
from ..... import inspect
import six

STRICT_CONSTRAINT = 0
NONSTRICT_CONSTRAINT = 1
VALUE_BINDING = 2

def constraint_type(rts, arg=None, config=None):
  '''Indicates the constraint type.'''
  arg = (config or rts.C).root if arg is None else arg
  mapping = {
      id(rts.prelude._StrictConstraint.info)   : STRICT_CONSTRAINT
    , id(rts.prelude._NonStrictConstraint.info): NONSTRICT_CONSTRAINT
    , id(rts.prelude._ValueBinding.info)       : VALUE_BINDING
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

  Parameters:
  -----------
    ``arg0``, ``arg1``
        The arguments to constrain.  Each must be a choice or free variable
        node, or ID. The associated IDs must refer to free variables.

     ``constraint_type``
         The constraint type.  Must be STRICT_CONSTRAINT or
         NONSTRICT_CONSTRAINT.

     ``config``
        The configuration to use as context.

  Returns:
  --------
  A Boolean that indicates whether the resulting configuration remains
  consistent.

  '''
  rts.telemetry._eqconstr += 1
  config = config or rts.C
  # arg0, arg1 = [rts.variable(arg, ()) for arg in [arg0, arg1]]
  i, j = [rts.obj_id(arg, config) for arg in [arg0, arg1]]
  if i != j:
    if constraint_type == STRICT_CONSTRAINT:
      if not rts.equate_fp(i, j, config=config):
        return False
      config.strict_constraints.write.unite(i, j)
      # for sid in arg0.guards.union(arg1.guards):
      #   rts.update_escape_set(sid, i)
      #   rts.update_escape_set(sid, j)
      rts.update_binding(i, config=config)
      rts.update_binding(j, config=config)
      if any(map(inspect.isa_freevar, [arg0, arg1])):
        return _constrain_equal_rec(rts, i, j, config=config)
    else:
      return rts.add_binding(i, arg1, config=config)
  return True

def _constrain_equal_rec(rts, arg0, arg1, config=None):
  '''
  Implements the recursive part of ``constrain_equal.``  Given two arguments,
  if at least one has been narrowed, ensure both are instantiated and then
  constrain the subvariables to be equal.  The arguments must all be free
  variables (or arguments convertible to free variables) of the same type.

  Example:
  --------
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

  Parameters:
  -----------
    ``arg0``, ``arg1``
        The arguments to check.  Each must be a choice or free variable node,
        or ID. If any associated ID does not correspond to a free variable in
        the ``vtable`` then this function does nothing.  At least one of the
        variables must have been narrowed in the given configuration.

     ``config``
        The configuration to use as context.

  Returns:
  --------
  A Boolean indicating whether the new constraints succeeded (i.e., could be
  consistent).
  '''
  try:
    xs = [rts.get_freevar(x) for x in [arg0, arg1]]
  except KeyError:
    return True
  else:
    try:
      pivot = next(
          x for x in xs if rts.is_narrowed(x, config=config)
                        and rts.has_generator(x)
        )
    except StopIteration:
      return True
    else:
      u = rts.get_generator(pivot, config=config)
      for x in xs:
        if x is not pivot:
          if not rts.has_generator(x):
            rts.clone_generator(pivot, x)
          v = rts.get_generator(x, config=config)
          for p, q in six.moves.zip(*[graph.walk(uv) for uv in [u,v]]):
            if rts.is_nondet(p.cursor):
              if not rts.constrain_equal(p.cursor, q.cursor, config=config):
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

