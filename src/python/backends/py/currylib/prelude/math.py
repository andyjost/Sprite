from ..... import inspect
import math
import operator as op

__all__ = [
    'apply_unboxed', 'modInt', 'prim_divFloat', 'prim_minusFloat'
  , 'prim_roundFloat', 'quotInt', 'remInt'
  ]

def apply_unboxed(rts, unboxedfunc, _0):
  '''Apply an unboxed function to the successors of _0 and box the result.'''
  result_value = unboxedfunc(*_unbox(rts, _0))
  box = BOXER[type(result_value)]
  return rts.Node(*box(rts, result_value), target=_0)

def modInt(x, y):
  return x - y * op.floordiv(x,y)

def prim_divFloat(x, y):
  return op.truediv(y, x)

def prim_minusFloat(x, y):
  return y - x

def prim_roundFloat(x):
  # Half away from zero, as std::round of the C++ backend and PAKCS round;
  # Python's round halves to even.
  magnitude = math.floor(abs(x))
  if abs(x) - magnitude >= 0.5:
    magnitude += 1
  return int(math.copysign(magnitude, x))

def quotInt(x, y):
  return int(op.truediv(x, y))

def remInt(x, y):
  return x - y * quotInt(x, y)

def _unbox(rts, _0):
  # The arguments are evaluated from the left, and the step suspends at the
  # first free variable before it touches the arguments after it, as the
  # C++ backend does (currylib/defs/unboxed.def) and as PAKCS does.  A
  # generator in a later argument then does not run while the step cannot
  # complete; that run forked the configuration once per alternative, and
  # a conjunction of such steps forked their product before it suspended.
  args = []
  for i in range(len(_0.successors)):
    arg = rts.variable(_0, i).hnf_or_free()
    if inspect.isa_freevar(arg.target):
      rts.suspend(arg.target)
    args.append(arg)
  return (arg.unboxed_value for arg in args)

BOXER = {
    bool:  lambda rts, rv: [getattr(rts.prelude, 'True' if rv else 'False')]
  , float: lambda rts, rv: [rts.prelude.Float, rv]
  , int:   lambda rts, rv: [rts.prelude.Int, rv]
  , str:   lambda rts, rv: [rts.prelude.Char, rv]
  }

