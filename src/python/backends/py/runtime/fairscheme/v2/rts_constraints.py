'''
Implements RuntimeState methods related to constraints.  This module is not
intended to be imported except by state.py.
'''

import itertools
from ......utility import exprutil
from .. import freevars

STRICT_CONSTRAINT = True
NONSTRICT_CONSTRAINT = False

def constraint_type(self, arg=None, config=None):
  '''Indicates the constraint type.'''
  arg = (config or self.C).root if arg is None else arg
  return arg.info is self.prelude._StrictConstraint.info

def constrain_equal(
    self, arg0, arg1, constraint_type=STRICT_CONSTRAINT, config=None
  ):
  '''
  Constrain the given arguments to be equal in the specified context.  This
  implements the equational constraints (=:=) and (=:<=).  For strict
  constraints, both arguments must be choices or both free variables, and, in
  the latter case, the free variables must represent values of the same type.
  For non-strict constraints, the first argument must be a free variable; the
  second is any expression.  Any non-strict constraint that makes it to this
  function implicates a binding (otherwise it would be handled by ordinary
  narrowing).

  The return value indicates whether the resulting configuration remains
  consistent.

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
  '''
  config = config or self.C
  i, j = [self.obj_id(arg, config) for arg in [arg0, arg1]]
  if i != j:
    if constraint_type == STRICT_CONSTRAINT:
      if not self.equate_fp(i, j, config=config):
        return False
      config.strict_constraints.write.unite(i, j)
      self.update_binding(i, config=config)
      self.update_binding(j, config=config)
      if any(map(self.is_freevar_node, [arg0, arg1])):
        if not _constrain_equal_rec(self, i, j, config=config):
          return False
    else:
      return self.add_binding(i, arg1, config=config)
  return True

def _constrain_equal_rec(self, arg0, arg1, config=None):
  '''
  Implements the recursive part of ``constrain_equal.``  Given two arguments,
  if at least one has been narrowed, ensure both are instantiated and then
  constrain the subvariables to be equal.  The arguments must all be free
  variables (or arguments convertible to free variables) of the same type.

  Example:
  --------
  1. Suppose the arguments are free variables x and y.  x has been narrowed
  to a non-empty list, (x0:x1), and so xR is in the fingerprint.  y is
  uninstantiated.  This function would instantiate y, giving it the generator
  "[] ?_y (y0:y1)", update the fingerprint with yR, and evaluate the
  equational constraints x0 =:= y0 and x1 =:= y1.

  If all these operations succeed in the sense that none invalidate the
  fingerprint, then True is returned.

  2. Now suppose neither free variable was narrowed.  This function does
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
    xs = map(self.get_freevar, [arg0, arg1])
  except KeyError:
    return True
  else:
    try:
      pivot = next(
          x for x in xs if self.is_narrowed(x, config=config)
                        and self.has_generator(x)
        )
    except StopIteration:
      return True
    else:
      u = self.get_generator(pivot, config=config)
      for x in xs:
        if x is not pivot:
          if not self.has_generator(x):
            freevars.clone_generator(self, pivot, x)
          v = self.get_generator(x, config=config)
          for p, q in itertools.izip(*[exprutil.walk(uv) for uv in [u,v]]):
            if self.is_choice_or_freevar_node(p.cursor):
              if not self.constrain_equal(p.cursor, q.cursor, config=config):
                return False
            if not self.is_freevar_node(p.cursor):
              p.push()
              q.push()
      return True

