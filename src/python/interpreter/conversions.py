'''
Functions for working with Curry expresions.  Handles conversions between Curry
and Python.
'''

from . import analysis
from . import runtime
from ..visitation import dispatch
import collections
import numbers

def expr(interp, arg, *args, **kwds):
  # Special case: if the argument is a single string, interpret it as a Curry
  # expression.  To convert a Python string to a Curry string, put it into a
  # list or use ``tocurry``.  Keyword arguments are forwarded so that the
  # import list can be specified.
  if isinstance(arg, str) and not len(args):
    return interp.compile(arg, mode='expr', **kwds)
  else:
    return _expr(interp, arg, *args, **kwds)

@dispatch.on('arg')
def _expr(interp, arg, *args, **kwds):
  '''
  Builds a Curry expression from Python.  The keyword 'target' specifies a
  target node.  If one is supplied, the result will be placed there.
  '''
  raise TypeError(
      'cannot build a Curry expression from type "%s"' % type(arg).__name__
    )

@_expr.when(str) # Char or [Char].
def _expr(interp, arg, *args, **kwds):
  if len(arg) == 1:
    args = (str(arg),) + args
    target = kwds.get('target', None)
    return runtime.Node(interp.prelude.Char, *args, target=target)
  else:
    raise RuntimeError('multi-char strings not supported yet.')

@_expr.when(collections.Sequence, no=str)
def _expr(interp, arg, target=None):
  # Supports nested structures, e.g., Cons 0 [Cons 1 Nil].
  return _expr(interp, *arg, target=target)

@_expr.when(bool)
def _expr(interp, arg, **kwds):
  target = kwds.get('target', None)
  if arg:
    return runtime.Node(interp.prelude.True, target=target)
  else:
    return runtime.Node(interp.prelude.False, target=target)

@_expr.when(numbers.Integral)
def _expr(interp, arg, target=None):
  return runtime.Node(interp.prelude.Int, int(arg), target=target)

@_expr.when(numbers.Real)
def _expr(interp, arg, target=None):
  return runtime.Node(interp.prelude.Float, float(arg), target=target)

@_expr.when(runtime.NodeInfo)
def _expr(interp, ti, *args, **kwds):
  target = kwds.get('target', None)
  missing =  ti.info.arity - len(args)
  if missing > 0:
    partial = runtime.Node(ti, *map(lambda s: _expr(interp, s), args), partial=True)
    # note: "missing" an unboxed int by design.
    return runtime.Node(interp.ni_PartApplic, missing, partial, target=target)
  else:
    return runtime.Node(ti, *map(lambda s: _expr(interp, s), args), target=target)

@_expr.when(runtime.Node)
def _expr(interp, node, target=None):
  if target is not None:
    target.rewrite(interp.ni_Fwd, node)
  return node

def box(interp, arg):
  '''Box a built-in primitive.'''
  if interp.flags['debug']:
    assert isinstance(arg, (str, numbers.Integral, numbers.Real))
    assert not isinstance(arg, str) or len(arg) == 1 # Char, not [Char].
  return _expr(interp, arg)

def unbox(interp, arg):
  '''Unbox a built-in primitive or IO type.'''
  if interp.flags['debug']:
    assert isinstance(arg, runtime.Node)
    assert analysis.isa_primitive(interp, arg) or analysis.isa_io(interp, arg)
  return arg[0]

@dispatch.on('data')
def tocurry(interp, data):
  '''Converts Python data or types to Curry by substituting built-in types.'''
  return _expr(interp, data)

@tocurry.when(list)
def tocurry(interp, data):
  # [a,b] -> _expr([Cons, tocurry(a), [Cons, tocurry(b), Nil])
  Cons = getattr(interp.prelude, ':')
  Nil = getattr(interp.prelude, '[]')
  sentinel = object()
  seq = iter(data)
  f = lambda x,g: [Cons, tocurry(interp, x), g()] if x is not sentinel else Nil
  g = lambda: f(next(seq, sentinel), g)
  result = _expr(interp, g())
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
  return _expr(interp, [TupleType] + [tocurry(interp, x) for x in data])

# @tocurry.when(collections.Iterator)
# def tocurry(interp, data):
#   FIXME: this needs to create an I/O type.
#   return (tocurry(interp, x) for x in data)

@tocurry.when(type)
def tocurry(interp, ty):
  '''Converts a Python type to the corresponding built-in Curry type.'''
  if issubclass(ty, bool):
    return interp.type('Prelude.Bool')
  if issubclass(ty, str):
    return interp.type('Prelude.Char')
  if issubclass(ty, numbers.Integral):
    return interp.type('Prelude.Int')
  if issubclass(ty, numbers.Real):
    return interp.type('Prelude.Float')
  if issubclass(ty, list):
    return interp.type('Prelude.[]')
  raise TypeError('cannot convert "%s" to a Curry type' % ty.__name__)

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

