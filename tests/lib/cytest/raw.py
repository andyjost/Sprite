'''Node operations for tests of the runtime and its internal builder.

Tests of Python values use module calls, curry.term, curry.parse and
curry.eval. Tests of nodes use this module, including raw.values when an
evaluation must expose forwarding, sharing or the runtime representation.
'''
import curry
from curry import expressions

cons = expressions.cons
nil = expressions.nil
unboxed = expressions.unboxed
fail = expressions.fail
typed = expressions.typed
fwd = expressions.fwd
choice = expressions.choice
free = expressions.free
ref = expressions.ref

def interp():
  return curry._interpreter_

def expr(*args, **kwds):
  '''Build nodes; typed=True also checks types and supplies dictionaries.'''
  interpreter = kwds.pop('interpreter', None) or interp()
  build = expressions.expr if kwds.pop('typed', False) else expressions.raw_expr
  return build(interpreter, *args, **kwds)

def values(goal, *, interpreter=None):
  '''The nodes of an evaluation, without value conversion.'''
  return (interpreter or interp()).eval_nodes(goal)

def show(node):
  return curry.show(node)


def import_(descriptor, **kwds):
  """Import an ICurry object for a test of the compiler or runtime."""
  return interp().import_(descriptor, **kwds)
