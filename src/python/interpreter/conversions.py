'''
Functions for working with Curry expresions.  Handles conversions between Curry
and Python.
'''

from .. import context
from .. import exceptions
from .. import inspect
from .. import objects
from .. import utility
from ..utility import visitation
from ..utility.unboxed import unboxed
import collections
# import itertools
import numbers

@visitation.dispatch.on('arg')
@utility.formatDocstring(__package__[:__package__.find('.')])
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
    Lazily Converted to a list.
  ``list``
    Eagerly Converted to a list.
  ``str``
    For strings of length one, Prelude.Char.  Otherwise, ``[Prelude.Char]``.
  ``tuple``
    Converted to a Curry tuple.

  Any (possibly nested) sequence whose first element is an instance of
  ``{0}.runtime.CurryNodeLabel`` describes a node.  The remaining arguments are
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
    return interp.context.runtime.Node(
        interp.prelude.Char, str(arg), *args, **kwds
      )
  else:
    return expr(interp, list(arg), *args, **kwds)

@expr.when(list)
def expr(interp, l, target=None):
  if len(l) and isinstance(l[0], objects.CurryNodeLabel):
    return expr(interp, *l, target=target)
  else:
    Cons = interp.prelude.Cons
    Nil = interp.prelude.Nil
    sentinel = object()
    seq = iter(l)
    f = lambda x,g: [Cons, expr(interp, x), g()] if x is not sentinel else Nil
    g = lambda: f(next(seq, sentinel), g)
    return expr(interp, g(), target=target)

@expr.when(tuple)
def expr(interp, args, **kwds):
  n = len(args)
  if n == 0:
    typename = 'Prelude.()'
  elif n == 1:
    raise TypeError("Curry has no 1-tuple.")
  else:
    typename = 'Prelude.(%s)' % (','*(n-1))
  return interp.context.runtime.Node(
      interp.symbol(typename), *map(interp.expr,args), **kwds
    )

@expr.when(bool)
def expr(interp, arg, **kwds):
  target = kwds.get('target', None)
  if arg:
    return interp.context.runtime.Node(interp.prelude.True, target=target)
  else:
    return interp.context.runtime.Node(interp.prelude.False, target=target)

@expr.when(numbers.Integral)
def expr(interp, arg, target=None):
  return interp.context.runtime.Node(
      interp.prelude.Int, int(arg), target=target
    )

@expr.when(numbers.Real)
def expr(interp, arg, target=None):
  return interp.context.runtime.Node(
      interp.prelude.Float, float(arg), target=target
    )

@expr.when(unboxed)
def expr(interp, arg, target=None):
  if target is not None:
    raise ValueError("cannot rewrite a node to an unboxed value")
  return arg.value

@expr.when(collections.Iterator)
def expr(interp, arg, target=None):
  pygen = interp.prelude._PyGenerator
  return interp.context.runtime.Node(pygen, arg, target=target)

@expr.when(objects.CurryNodeLabel)
def expr(interp, ti, *args, **kwds):
  target = kwds.get('target', None)
  missing =  ti.info.arity - len(args)
  if missing > 0:
    partial = interp.context.runtime.Node(
        ti, *map(lambda s: expr(interp, s), args), partial=True
      )
    # note: "missing" an unboxed int by design.
    return interp.context.runtime.Node(
        interp.prelude._PartApplic, missing, partial, target=target
      )
  else:
    return interp.context.runtime.Node(
        ti, *map(lambda s: expr(interp, s), args), target=target
      )

@expr.when(context.Node)
def expr(interp, node, target=None):
  if target is not None:
    return interp.context.runtime.Node(
        interp.prelude._Fwd, node, target=target
      )
  return node

def unbox(interp, arg):
  '''Unbox a built-in primitive or IO type.'''
  if interp.flags['debug']:
    assert isinstance(arg, context.Node)
    assert inspect.isa_primitive(interp, arg) or inspect.isa_io(interp, arg)
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

class ToPython(object):
  def __init__(self, convert_freevars=True):
    self.convert_freevars = convert_freevars
  def __call__(self, interp, value, convert_strings=True):
    '''Convert one value.'''
    # self.reset()
    return self.__convert(interp, value, convert_strings)
  def __convert(self, interp, value, convert_strings=True):
    if inspect.isa_primitive(interp, value):
      return unbox(interp, value)
    elif inspect.isa_bool(interp, value):
      return inspect.isa_true(interp, value)
    elif inspect.isa_list(interp, value):
      l = [self.__convert(interp, elem) for elem in _listiter(interp, value)]
      if convert_strings and l:
        try:
          return ''.join(l)
        except TypeError:
          pass
      return l
    elif inspect.isa_tuple(interp, value):
      return tuple(self.__convert(interp, x) for x in value)
    else:
      return value

_topython_converter_ = ToPython(convert_freevars=False)

def topython(interp, value, convert_strings=True):
  '''
  Converts a Curry value to Python by substituting built-in types.

  This functions converts (recursively) the types ``int``, ``float``, ``str``,
  ``bool``, ``list``, and ``tuple``.  Other types are passed through untouched.

  Parameters:
  -----------
  ``value``
      The Curry value to convert.
  ``convert_strings``
      If true, then lists of characters are converted to Python strings.

  Raises:
  -------
    ``NotConstructorError`` if a free variable is encountered along a list
    spine.

  Returns:
  --------
  The value converted to Python.
  '''
  return _topython_converter_(interp, value, convert_strings)

def _listiter(interp, arg):
  '''Iterate through a Curry list.'''
  Cons = getattr(interp.prelude, ':')
  while inspect.isa(arg, Cons):
    yield arg[0]
    arg = arg[1]
  if not inspect.isa_list(interp, arg):
    raise exceptions.NotConstructorError(arg)

def getconverter(converter):
  '''
  Get the converter corresponding to the argument.  The converter returned
  translates free variables into _a, _b, _c, etc.
  '''
  if converter is None or callable(converter):
    return converter
  elif converter == 'topython':
    return ToPython(convert_freevars=True)

