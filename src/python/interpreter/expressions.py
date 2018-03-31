'''
Functions for working with Curry expresions.  Handles conversions between Curry
and Python.
'''

from . import runtime
from ..visitation import dispatch
import collections
import numbers


@dispatch.on('arg')
def expr(interp, arg, *args):
  '''
  Builds a Curry expression from Python.
  '''
  raise TypeError(
      'cannot build a Curry expression from type "%s"' % type(arg).__name__
    )

@expr.when(str) # Char or [Char].
def expr(interp, arg, *args):
  if len(arg) == 1:
    args = (arg,) + args
    interp.prelude.Char._check_call(*args)
    return runtime.Node(interp.prelude.Char.info, *args)
  else:
    raise RuntimeError('multi-char strings not supported yet.')

@expr.when(collections.Sequence, no=str)
def expr(interp, arg):
  # Supports nested structures, e.g., Cons 0 [Cons 1 Nil].
  return interp.expr(*arg)

@expr.when(numbers.Integral)
def expr(interp, arg, *args):
  args = (int(arg),) + args
  interp.prelude.Int._check_call(*args)
  return runtime.Node(interp.prelude.Int.info, *args)

@expr.when(numbers.Real)
def expr(interp, arg, *args):
  args = (float(arg),) + args
  interp.prelude.Float._check_call(*args)
  return runtime.Node(interp.prelude.Float.info, *args)

@expr.when(runtime.TypeInfo)
def expr(interp, info, *args):
  return info(*map(interp.expr, args))

@expr.when(runtime.Node)
def expr(interp, node):
  return node

def box(interp, x):
  '''Box a built-in primitive.'''
  if interp.flags['debug']:
    assert isinstance(x, (str, numbers.Integral, numbers.Real))
    assert not isinstance(x, str) or len(x) == 1 # Char, not [Char].
  return expr(interp, x)

def unbox(interp, x):
  '''Unbox a built-in primitive.'''
  if interp.flags['debug']:
    assert isinstance(x, runtime.Node)
    p = interp.prelude
    try:
      assert x[()].info in (p.Int.info, p.Char.info, p.Float.info)
    except:
      breakpoint()
  return x[0]

