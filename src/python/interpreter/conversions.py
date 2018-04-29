'''
Functions for working with Curry expresions.  Handles conversions between Curry
and Python.
'''

from . import analysis
from . import runtime
from ..visitation import dispatch
import collections
import numbers
import re

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
    return interp.prelude.Char.construct(*args)
  else:
    raise RuntimeError('multi-char strings not supported yet.')

@expr.when(collections.Sequence, no=str)
def expr(interp, arg):
  # Supports nested structures, e.g., Cons 0 [Cons 1 Nil].
  return interp.expr(*arg)

@expr.when(numbers.Integral)
def expr(interp, arg, *args):
  args = (int(arg),) + args
  return interp.prelude.Int.construct(*args)

@expr.when(numbers.Real)
def expr(interp, arg, *args):
  args = (float(arg),) + args
  return interp.prelude.Float.construct(*args)

@expr.when(runtime.TypeInfo)
def expr(interp, info, *args):
  return info.construct(*map(interp.expr, args))

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
    assert analysis.isa(x, interp.BuiltinVariant)
  return x[0]

@dispatch.on('data')
def tocurry(interp, data):
  '''Converts Python data to Curry by substituting built-in types.'''
  return data

@tocurry.when(list)
def tocurry(interp, data):
  # [a,b] -> expr([Cons, tocurry(a), [Cons, tocurry(b), Nil])
  Cons = getattr(interp.prelude, ':')
  Nil = getattr(interp.prelude, '[]')
  sentinel = object()
  seq = iter(data)
  f = lambda x,g: [Cons, tocurry(interp, x), g()] if x is not sentinel else Nil
  g = lambda: f(next(seq, sentinel), g)
  result = expr(interp, g())
  if interp.flags['debug']:
    types = set(x[()].info for x in _listgen(interp, result))
    if len(types) != 1:
      raise TypeError(
          'malformed Curry list containing types %s'
              % (tuple(sorted(ty.name for ty in types)),)
        )
  return result

@tocurry.when(tuple)
def tocurry(interp, data):
  n = len(data)
  if n == 0:
    typename = '()'
  elif n == 1:
    raise TypeError("Curry has no 1-tuple.")
  else:
    typename = '(%s)' % (','*(n-1))
  TupleType = interp.symbol('Prelude.%s' % typename)
  return expr(interp, [TupleType] + [tocurry(interp, x) for x in data])

# @tocurry.when(collections.Iterator)
# def tocurry(interp, data):
#   FIXME: this needs to create an I/O type.
#   return (tocurry(interp, x) for x in data)

@dispatch.on('guide')
def topython(interp, expr, guide=None):
  '''Converts a Curry value to Python by substituting built-in types.'''
  isa = analysis.isa
  if isa(expr, interp.BuiltinVariant):
    return unbox(interp, expr)
  elif isa(expr, interp.type('Prelude.List')):
    return topython(interp, expr, [])
  elif re.match(r'\(,*\)$', expr[()].info.name):
    return topython(interp, expr, ())
  return expr

def _listgen(interp, x):
  Cons = getattr(interp.prelude, ':')
  while analysis.isa(x, Cons):
    yield x[0]
    x = x[1]

@topython.when(list)
def topython(interp, expr, _):
  return list(topython(interp, x) for x in _listgen(interp, expr))

@topython.when(tuple)
def topython(interp, expr, _):
  expr = expr[()]
  n = expr.info.arity
  return tuple([topython(interp, x) for x in expr])

def getconverter(converter):
  if converter is None or callable(converter):
    return converter
  elif converter == 'topython':
    return topython

