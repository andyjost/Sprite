'''
Functions for working with Curry expresions.  Handles conversions between Curry
and Python.
'''

from ..expr_modifiers import anchor, cons, nil, ref, unboxed
from .. import context
from .. import exceptions
from .. import expr_modifiers
from .. import inspect
from .. import objects
from .. import utility
from ..utility import exprutil
from ..utility import visitation
import collections
import itertools
import numbers

__all__ = [
    'anchor', 'cons', 'currytype', 'expr', 'getconverter', 'nil', 'ref'
  , 'topython', 'unbox', 'unboxed'
  ]

@utility.formatDocstring(__package__[:__package__.find('.')])
def expr(interp, *args, **kwds):
  '''
  Builds a Curry expression.

  The arguments form an expression specification.  Each positional argument
  must either be directly convertible to Curry or describe a node.  The
  following direct conversions are recognized:

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
  ``{0}.runtime.CurryNodeLabel`` specifies a node.  The remaining arguments are
  recursivly converted to Curry expressions to form the successors list.  Thus,
  given suitable definitions, it is possible to build the Curry list
  ``[0,1,2]`` with the following code:

      expr([Cons, 0, [Cons, 1, [Cons, 2, Nil]]])

  Several special symbols are recognized and can be used to control the
  conversion.  See ``anchor``, ``cons``, ``nil``, ``ref``, and ``unboxed``.

  Parameters:
  -----------
  ``interp``
      An interpreter object.
  ``*args``
      Positional arguments used to construct expressions.
  ``**kwds``
      Keyword arguments specifying subexpressions that may be referenced via
      ``ref``.  Each keyword specifies the name of an anchor.  See the examples
      below.
  ``target``
      Reserved keyword-only argument.  If a target is supplied, then it will be
      rewritten with the specified expression.  Otherwise a new node is
      created.

  Returns:
  --------
  The Node created or rewritten.
  '''
  builder = ExpressionBuilder(interp)
  target = kwds.pop('target', None)
  for anchorname, subexpr in kwds.iteritems():
    subexpr = anchor(subexpr, name=anchorname)
    builder(subexpr)
    assert anchorname in builder.anchors
  expr = builder(*args, target=target)
  return builder.fixrefs(expr)

class ExpressionBuilder(object):
  '''Implementation of ``expr``.'''
  def __init__(self, interp):
    self.interp = interp
    self.counter = itertools.count(1)
    self.anchors = {}
    self.brokenrefs = {}

  def fixrefs(self, expr):
    if self.brokenrefs:
      for state in exprutil.walk(expr):
        if isinstance(state.cursor, self.Node):
          anchorname = self.brokenrefs.get(id(state.cursor))
          if anchorname is not None:
            parent = state.parent
            if parent is None:
              # This is the trivial cycle a=a.
              state.cursor.rewrite(self.prelude._Fwd, state.cursor)
            else:
              parent.successors[state.path[-1]] = self.anchors[anchorname]
          else:
            state.push()
    return expr

  @property
  def prelude(self):
    return self.interp.prelude

  @property
  def Node(self):
    return self.interp.context.runtime.Node

  @visitation.dispatch.on('arg')
  def __call__(self, arg, *args, **kwds):
    raise TypeError(
        'cannot build a Curry expression from type "%s"' % type(arg).__name__
      )

  @__call__.when(str) # Char or [Char].
  def __call__(self, arg, *args, **kwds):
    if len(arg) == 1:
      return self.Node(self.prelude.Char, str(arg), *args, **kwds)
    else:
      return self(list(arg), *args, **kwds)

  @__call__.when(list)
  def __call__(self, l, target=None):
    if len(l) and isinstance(l[0], objects.CurryNodeLabel):
      return self(*l, target=target)
    else:
      Cons = self.prelude.Cons
      Nil = self.prelude.Nil
      sentinel = object()
      seq = iter(l)
      f = lambda x,g: [Cons, self(x), g()] if x is not sentinel else Nil
      g = lambda: f(next(seq, sentinel), g)
      return self(g(), target=target)

  @__call__.when(tuple)
  def __call__(self, args, **kwds):
    n = len(args)
    if n == 0:
      typename = 'Prelude.()'
    elif n == 1:
      raise TypeError("Curry has no 1-tuple.")
    else:
      typename = 'Prelude.(%s)' % (','*(n-1))
    return self.Node(self.interp.symbol(typename), *map(self, args), **kwds)

  @__call__.when(bool)
  def __call__(self, arg, **kwds):
    target = kwds.get('target', None)
    if arg:
      return self.Node(self.prelude.True, target=target)
    else:
      return self.Node(self.prelude.False, target=target)

  @__call__.when(numbers.Integral)
  def __call__(self, arg, target=None):
    return self.Node(self.prelude.Int, int(arg), target=target)

  @__call__.when(numbers.Real)
  def __call__(self, arg, target=None):
    return self.Node(self.prelude.Float, float(arg), target=target)

  @__call__.when(anchor)
  def __call__(self, arg, target=None):
    if arg.name is None:
      while True:
        anchorname = '_%s' % next(self.counter)
        if anchorname not in self.anchors:
          break
    else:
      anchorname = arg.name
    if anchorname in self.anchors:
      raise ValueError('multiple definitions of anchor %r' % anchorname)
    self.anchors[anchorname] = None
    subexpr = self(arg.value)
    self.anchors[anchorname] = subexpr
    return subexpr

  @__call__.when(ref)
  def __call__(self, arg, target=None):
    if arg.name is None:
      if len(self.anchors) != 1:
        raise ValueError(
            "invalid use of unqualified 'ref' with %s anchors defined"
                % len(self.anchors)
          )
      anchorname = next(iter(self.anchors))
    else:
      anchorname = arg.name
    target = self.anchors.get(anchorname)
    if target is None:
      placeholder = self(expr_modifiers._fail)
      self.brokenrefs[id(placeholder)] = anchorname
      return placeholder
    else:
      return target

  @__call__.when(collections.Iterator)
  def __call__(self, arg, target=None):
    pygen = self.prelude._PyGenerator
    return self.Node(pygen, arg, target=target)

  @__call__.when(objects.CurryNodeLabel)
  def __call__(self, ti, *args, **kwds):
    target = kwds.get('target', None)
    missing =  ti.info.arity - len(args)
    if missing > 0:
      partial = self.Node(ti, *map(lambda s: self(s), args), partial=True)
      return self.Node(
          self.prelude._PartApplic, missing, partial, target=target
        )
    else:
      return self.Node(ti, *map(lambda s: self(s), args), target=target)

  @__call__.when(context.Node)
  def __call__(self, node, target=None):
    if target is not None:
      return self.Node(self.prelude._Fwd, node, target=target)
    return node

  @__call__.when(unboxed)
  def __call__(self, arg, target=None):
    if target is not None:
      raise ValueError("cannot rewrite a node to an unboxed value")
    return arg.value

  @__call__.when(expr_modifiers.cons)
  def __call__(self, arg, target=None):
    return self.Node(
        self.prelude.Cons, self(arg.head), self(arg.tail), target=target
      )

  @__call__.when(type(expr_modifiers.nil))
  def __call__(self, arg, target=None):
    return self.Node(self.prelude.Nil, target=target)

  @__call__.when(expr_modifiers._setgrd)
  def __call__(self, arg, target=None):
    return self.Node(
        self.interp.setfunctions._SetGuard
      , arg.sid, self(arg.value), target=target
      )

  @__call__.when(type(expr_modifiers._fail))
  def __call__(self, arg, target=None):
    return self.Node(self.prelude._Failure, target=target)

  @__call__.when(expr_modifiers._strictconstr)
  def __call__(self, arg, target=None):
    return self.Node(
        self.prelude._StrictConstraint
      , self(arg.value), self(arg.pair), target=target
      )

  @__call__.when(expr_modifiers._nonstrictconstr)
  def __call__(self, arg, target=None):
    return self.Node(
        self.prelude._NonStrictConstraint
      , self(arg.value), self(arg.pair), target=target
      )

  @__call__.when(expr_modifiers._valuebinding)
  def __call__(self, arg, target=None):
    return self.Node(
        self.prelude._ValueBinding
      , self(arg.value), self(arg.pair), target=target
      )

  @__call__.when(expr_modifiers._var)
  def __call__(self, arg, target=None):
    return self.Node(
        self.prelude._Free
      , arg.vid
      , self.Node(self.prelude.Unit)
      , target=target
      )

  @__call__.when(expr_modifiers._fwd)
  def __call__(self, arg, target=None):
    return self.Node(self.prelude._Fwd, self(arg.value), target=target)

  @__call__.when(expr_modifiers._choice)
  def __call__(self, arg, target=None):
    return self.Node(
        self.prelude._Choice, arg.cid, self(arg.lhs), self(arg.rhs)
      , target=target
      )

def unbox(arg):
  '''Unbox a built-in primitive or IO type.'''
  assert isinstance(arg, context.Node)
  assert inspect.isa_primitive(arg) or inspect.isa_io(arg)
  return arg.successors[0]

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
  def __call__(self, value, convert_strings=True):
    '''Convert one value.'''
    return self.__convert(value, convert_strings)
  def __convert(self, value, convert_strings=True):
    if inspect.isa_boxed_primitive(value) or inspect.isa_io(value):
      return unbox(value)
    elif inspect.isa_bool(value):
      return inspect.isa_true(value)
    elif inspect.isa_list(value):
      l = [self.__convert(elem) for elem in _listiter(value)]
      if convert_strings and l:
        try:
          return ''.join(l)
        except TypeError:
          pass
      return l
    elif inspect.isa_tuple(value):
      return tuple(self.__convert(x) for x in value)
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
  return _topython(value, convert_strings)

def _topython(value, convert_strings=True):
  '''Internal version of ``topython`` that takes no interpreter.'''
  return _topython_converter_(value, convert_strings)

def _listiter(arg):
  '''Iterate through a Curry list.'''
  while inspect.isa_cons(arg):
    yield arg.successors[0]
    arg = arg.successors[1]
  if not inspect.isa_nil(arg):
    raise exceptions.NotConstructorError(arg)

def getconverter(converter):
  '''
  Get the converter corresponding to the argument.  The converter returned
  translates free variables into _a, _b, _c, etc.
  '''
  if converter is None or callable(converter):
    return converter
  elif converter == 'topython':
    return topython
    # return ToPython(convert_freevars=True)

