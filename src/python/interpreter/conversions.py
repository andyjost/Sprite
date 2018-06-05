'''
Functions for working with Curry expresions.  Handles conversions between Curry
and Python.
'''

from . import analysis
from . import runtime
from ..visitation import dispatch
import collections
import numbers
import types
import __builtin__

@dispatch.on('arg')
def expr(interp, arg, *args, **kwds):
  '''
  Builds a Curry expression.

  The arguments form an expression specification.  Each element must either be
  directly convertible to Curry or describe a node.  The following direct
  conversions are recognized:

  ``bool``
    Converted to ``Prelude.Bool``.
  ``float``
    Converted to ``Prelude.Float``.
  ``int``
    Converted to ``Prelude.Int``.
  ``iterator``
    Converted to ``Prelude.[_]`` (list) lazily.
  ``list``
    Converted to ``Prelude.[_]`` (list) eagerly.
  ``str``
    For strings of length one, Prelude.Char.  Otherwise, ``[Prelude.Char]``.
  ``tuple``
    Converted to a Curry tuple.

  Any (possibly nested) sequence whose first element is an instance of
  ``curry.runtime.NodeInfo`` describes a node.  The remaining arguments are
  recursivly converted to Curry expressions to form the successors list.  Thus,
  given suitable definitions, it is possible to build the Curry list
  ``[0,1,2]`` with the following code:

      expr([Cons, 0, [Cons, 1, [Cons, 2, Nil]]])

  Parameters:
  -----------
  ``interp``
      An interpreter object.
  ``*args``
      Positional arguments passed to ``Node.__new__``.
  ``target``
      Keyword-only argument.  If a ``Node`` object is provided, then it will be
      rewritten with the contents specified.  Otherwise a new node is created.

  Returns:
  --------
  The Node created or rewritten.
  '''
  raise TypeError(
      'cannot build a Curry expression from type "%s"' % type(arg).__name__
    )

@expr.when(str) # Char or [Char].
def expr(interp, arg, *args, **kwds):
  if len(arg) == 1:
    args = (str(arg),) + args
    target = kwds.get('target', None)
    return runtime.Node(interp.prelude.Char, *args, target=target)
  else:
    raise RuntimeError('multi-char strings not supported yet.')

@expr.when(list)
def expr(interp, l, target=None):
  if len(l) and isinstance(l[0], runtime.NodeInfo):
    return expr(interp, *l, target=target)
  else:
    Cons = interp.ni_Cons
    Nil = interp.ni_Nil
    sentinel = object()
    seq = iter(l)
    f = lambda x,g: [Cons, expr(interp, x), g()] if x is not sentinel else Nil
    g = lambda: f(next(seq, sentinel), g)
    return expr(interp, g(), target=target)

@expr.when(tuple)
def expr(interp, t, **kwds):
  n = len(t)
  if n == 0:
    typename = '()'
  elif n == 1:
    raise TypeError("Curry has no 1-tuple.")
  else:
    typename = '(%s)' % (','*(n-1))
  TupleType = interp.symbol('Prelude.%s' % typename)
  return expr(
      interp
    , [TupleType] + [expr(interp, x) for x in t]
    , **kwds
    )

@expr.when(bool)
def expr(interp, arg, **kwds):
  target = kwds.get('target', None)
  if arg:
    return runtime.Node(interp.prelude.True, target=target)
  else:
    return runtime.Node(interp.prelude.False, target=target)

@expr.when(numbers.Integral)
def expr(interp, arg, target=None):
  return runtime.Node(interp.prelude.Int, int(arg), target=target)

@expr.when(numbers.Real)
def expr(interp, arg, target=None):
  return runtime.Node(interp.prelude.Float, float(arg), target=target)

@expr.when(collections.Iterator)
def expr(interp, arg, target=None):
  pygen = interp.symbol('_System._python_generator_')
  return runtime.Node(pygen, arg, target=target)

@expr.when(runtime.NodeInfo)
def expr(interp, ti, *args, **kwds):
  target = kwds.get('target', None)
  missing =  ti.info.arity - len(args)
  if missing > 0:
    partial = runtime.Node(ti, *map(lambda s: expr(interp, s), args), partial=True)
    # note: "missing" an unboxed int by design.
    return runtime.Node(interp.ni_PartApplic, missing, partial, target=target)
  else:
    return runtime.Node(ti, *map(lambda s: expr(interp, s), args), target=target)

@expr.when(runtime.Node)
def expr(interp, node, target=None):
  if target is not None:
    target.rewrite(interp.ni_Fwd, node)
  return node

def box(interp, arg):
  '''Box a built-in primitive.'''
  if interp.flags['debug']:
    assert isinstance(arg, (str, numbers.Integral, numbers.Real))
    assert not isinstance(arg, str) or len(arg) == 1 # Char, not [Char].
  return expr(interp, arg)

def unbox(interp, arg):
  '''Unbox a built-in primitive or IO type.'''
  if interp.flags['debug']:
    assert isinstance(arg, runtime.Node)
    assert analysis.isa_primitive(interp, arg) or analysis.isa_io(interp, arg)
  return arg[0]

def currytype(interp, ty):
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

