'''
The variables of a step that the C++ backend reads as plain pointers.

A step of generated code builds a Variable for every argument it reads: the
slot that holds the node, the path to it from the redex, and the set guards
crossed on the way.  An argument that the step only passes on to another call
needs none of that: nothing head-normalizes it from this step (the path), and
the value it denotes is the node in its slot (the guards).  Such a variable is
a plain ``Node *`` in the generated code, read through Node::successor_node or
Variable::successor_node (see cyrt/graph/node.hxx and indexing.hxx).

The rule.  A variable is plain when all of the following hold:

  * It is declared by IVarDecl.  A free variable (IFreeDecl) is a plain
    pointer already.
  * It is assigned once, and the right side is a successor of the redex or
    of another variable with a path of one entry (IVarAccess), a node the
    step builds (a call, a partial application, a choice, a literal, or a
    string), or another plain variable.
  * Every use passes the value on: an argument of a call, of a partial
    application, or of a choice; the whole expression of a return; the right
    side of a node assignment (the patch of a recursive let).

A variable that a case scrutinizes keeps the Variable: hnf needs the path for
the scan and the guards for the escape set of a pull-tabbed choice.  So does
the base of a successor path (the path continues from its target and its
guards) and the base of a node assignment (set_successor).  Two variables of
a var-to-var assignment have one kind: both plain, or both Variables.

Why the guard rule holds.  The redex of a step is a function node, never a
set guard, so a slot of the redex holds the whole guarded argument, and a
plain read keeps the guard.  A successor of a Variable may lie under the
guards the Variable crossed, which the ICurry does not show; for such a read
Variable::successor_node decides at run time, and builds the guards again
when it crossed any.  A path of more than one entry stays a Variable.
'''
from ... import icurry

__all__ = ['plain_variables']

def plain_variables(ifun):
  '''
  The variables of ``ifun`` that the generated step keeps as plain pointers,
  as a frozen set of variable ids.  A function without an ICurry body, or
  with a statement or expression of an unknown kind, has none.
  '''
  # An external or built-in body is an IBody without a block.
  block = getattr(ifun.body, 'block', None)
  if block is None:
    return frozenset()
  uses = _Uses()
  try:
    uses.stmt(block)
  except _Unknown:
    return frozenset()
  return uses.plain()

class _Unknown(Exception):
  '''A statement or expression the analysis does not know.'''

# The right sides that make a node the step builds, or name a value.  A
# plain variable may hold one of these.
_BUILT = (
    icurry.ICall, icurry.IOr, icurry.ILit, icurry.ILiteral, icurry.IString
  )

class _Uses(object):
  def __init__(self):
    self.declared = set()  # IVarDecl, not IFreeDecl
    self.assigned = {}     # vid -> the right side
    self.bound = set()     # needs a Variable
    self.aliases = []      # (vid, vid) of the var-to-var assignments

  def plain(self):
    bound = set(self.bound)
    # A variable assigned twice, or never, is left alone.
    for vid in self.declared:
      if vid not in self.assigned:
        bound.add(vid)
    changed = True
    while changed:
      changed = False
      for lhs, rhs in self.aliases:
        for a, b in (lhs, rhs), (rhs, lhs):
          if a in bound and b not in bound:
            bound.add(b)
            changed = True
    return frozenset(
        vid for vid, rhs in self.assigned.items()
            if vid in self.declared and vid not in bound
               and self.plain_rhs(rhs)
      )

  def plain_rhs(self, rhs):
    if isinstance(rhs, icurry.IVarAccess):
      return len(rhs.path) == 1
    elif isinstance(rhs, icurry.IVar):
      return True # an alias; plain() made both sides one kind
    else:
      return isinstance(rhs, _BUILT)

  def stmt(self, stmt):
    if isinstance(stmt, icurry.IBlock):
      for part in stmt.vardecls, stmt.assigns:
        for item in part:
          self.stmt(item)
      self.stmt(stmt.stmt)
    elif isinstance(stmt, icurry.IFreeDecl):
      self.bound.add(stmt.vid)
    elif isinstance(stmt, icurry.IVarDecl):
      self.declared.add(stmt.vid)
    elif isinstance(stmt, icurry.IVarAssign):
      if stmt.vid in self.assigned:
        self.bound.add(stmt.vid)
      self.assigned[stmt.vid] = stmt.expr
      if isinstance(stmt.expr, icurry.IVar):
        self.aliases.append((stmt.vid, stmt.expr.vid))
      else:
        self.expr(stmt.expr)
    elif isinstance(stmt, icurry.INodeAssign):
      self.bound.add(stmt.vid)
      self.expr(stmt.expr)
    elif isinstance(stmt, icurry.IReturn):
      self.expr(stmt.expr)
    elif isinstance(stmt, icurry.ICase):
      self.bound.add(stmt.vid)
      for branch in stmt.branches:
        self.stmt(branch.block)
    elif isinstance(stmt, icurry.IExempt):
      pass
    else:
      raise _Unknown(stmt)

  def expr(self, expr):
    '''Visits an expression whose value is passed on.'''
    if isinstance(expr, icurry.IVar):
      pass
    elif isinstance(expr, icurry.IVarAccess):
      self.bound.add(expr.vid)
    elif isinstance(expr, icurry.ICall):
      for arg in expr.exprs:
        self.expr(arg)
    elif isinstance(expr, icurry.IOr):
      self.expr(expr.lhs)
      self.expr(expr.rhs)
    elif isinstance(expr, _BUILT + (icurry.IUnboxedLiteral,)):
      pass
    else:
      raise _Unknown(expr)
