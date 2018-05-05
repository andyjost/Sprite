'''
Functions for working with Curry expresions.  Handles conversions between Curry
and Python.
'''

from . import analysis
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
    args = (str(arg),) + args
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
def expr(interp, ti, *args):
  missing =  ti.info.arity - len(args)
  if missing > 0:
    partial = interp.symbol('_System.PartApplic')
    expr = ti.curry(*map(interp.expr, args))
    return partial.construct(missing, expr) # note: unboxed int "missing".
  else:
    return ti.construct(*map(interp.expr, args))

@expr.when(runtime.Node)
def expr(interp, node):
  return node

def box(interp, arg):
  '''Box a built-in primitive.'''
  if interp.flags['debug']:
    assert isinstance(arg, (str, numbers.Integral, numbers.Real))
    assert not isinstance(arg, str) or len(arg) == 1 # Char, not [Char].
  return expr(interp, arg)

def unbox(interp, arg):
  '''Unbox a built-in primitive.'''
  if interp.flags['debug']:
    assert isinstance(arg, runtime.Node)
    assert analysis.isa_primitive(interp, arg)
  return arg[0]

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
    types = set(x[()].info for x in _iter_(interp, result))
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

def topython(interp, expr):
  '''Converts a Curry value to Python by substituting built-in types.'''
  if analysis.isa_primitive(interp, expr):
    return unbox(interp, expr)
  elif analysis.isa_bool(interp, expr):
    return analysis.isa_true(interp, expr)
  elif analysis.isa_list(interp, expr):
    return list(topython(interp, x) for x in _iter_(interp, expr))
  elif analysis.isa_tuple(interp, expr):
    return tuple(topython(interp, x) for x in expr)
  return expr

def _iter_(interp, arg):
  '''Iterate through a Curry list.'''
  Cons = getattr(interp.prelude, ':')
  while analysis.isa(arg, Cons):
    yield arg[0]
    arg = arg[1]

def getconverter(converter):
  if converter is None or callable(converter):
    return converter
  elif converter == 'topython':
    return topython

