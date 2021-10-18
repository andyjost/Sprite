from ...... import inspect
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
  return int(round(x))

def quotInt(x, y):
  return int(op.truediv(x, y))

def remInt(x, y):
  return x - y * quotInt(x, y)

def _unbox(rts, _0):
  args = [
      rts.variable(_0, i).hnf_or_free()
          for i in xrange(len(_0.successors))
    ]
  freevars = [arg for arg in args if inspect.isa_freevar(arg.target)]
  if freevars:
    rts.suspend(freevars)
  else:
    return (arg.unboxed_value for arg in args)

BOXER = {
    bool:  lambda rts, rv: [getattr(rts.prelude, 'True' if rv else 'False')]
  , float: lambda rts, rv: [rts.prelude.Float, rv]
  , int:   lambda rts, rv: [rts.prelude.Int, rv]
  , str:   lambda rts, rv: [rts.prelude.Char, rv]
  }

