from . import backends, config, icurry, objects, utility
from .exceptions import CurryTypeError
from .utility import strings, visitation
import collections, itertools, numbers, six

__all__ = [
    'anchor', 'choice', 'cons', 'expr', 'fail', 'fwd', 'free', 'nil'
  , 'raw_expr', 'ref', 'unboxed'
  ]

class anchor(object):
  '''
  Used with :func:`expr` to create an anchor in an expression.  This can be
  used to construct nonlinear expressions.

  When no argument is supplied, the anchor name is automatically generated from
  the sequence _1, _2, ..., according to its position in a left-to-right,
  depth-first traversal.
  '''
  def __init__(self, value, name=None):
    self.value = value
    self.name = name

class ref(object):
  '''
  Used with :func:`expr` to create a reference to a named subexpression.
  This can be used to construct nonlinear expressions.

  The argument is optional when the expression contains exactly one anchor at
  the point where the reference appears.
  '''
  def __init__(self, name=None):
    self.name = name

class cons(object):
  '''
  Used with :func:`expr` to place one or more list constructors into a Curry
  expression.
  '''
  def __init__(self, head, tail0, *tail):
    self.head = head
    if tail:
      self.tail = cons(tail0, *tail)
    else:
      self.tail = tail0

class _nilcls(object): pass
nil = _nilcls()
'''
Used with :func:`expr` to place a list terminator into a Curry expression.
'''
del _nilcls

class unboxed(object):
  '''
  Used with :func:`expr` to place an unboxed argument into a Curry expression.
  '''
  def __init__(self, value):
    if not isinstance(value, icurry.IUnboxedLiteral):
      raise CurryTypeError('expected an unboxed literal, got %r' % value)
    self.value = value

class _setgrd(object):
  '''Used with :func:`expr` to place a set guard into a Curry expression.'''
  def __init__(self, sid, value=None):
    if value is None:
      sid, value = 0, sid # shift right
    self.sid = int(sid)
    self.value = value

class _failcls(object): pass
fail = _failcls()
'''Used with :func:`expr` to place a failure into a Curry expression.'''
del _failcls

class _strictconstr(object):
  '''Used with :func:`expr` to place a strict constraint into a Curry expression.'''
  def __init__(self, value, pair):
    self.value = value
    self.pair = pair

class _nonstrictconstr(object):
  '''Used with :func:`expr` to place a nonstrict constraint into a Curry expression.'''
  def __init__(self, value, pair):
    self.value = value
    self.pair = pair

class _valuebinding(object):
  '''Used with :func:`expr` to place a value binding into a Curry expression.'''
  def __init__(self, value, pair):
    self.value = value
    self.pair = pair

class free(object):
  '''Used with :func:`expr` to place a free variable into a Curry expression.'''
  def __init__(self, vid=0):
    self.vid = int(vid)

class fwd(object):
  '''Used with :func:`expr` to place a forward node into a Curry expression.'''
  def __init__(self, value):
    self.value = value

class choice(object):
  '''Used with :func:`expr` to place a choice into a Curry expression.'''
  def __init__(self, cid, lhs, rhs=None):
    if rhs is None:
      cid, lhs, rhs = 0, cid, lhs # shift right
    self.cid = int(cid)
    self.lhs = lhs
    self.rhs = rhs

@utility.formatDocstring(config.python_package_name())
def expr(interp, *args, **kwds):
  '''
  Builds a Curry expression.

  The arguments specify the expression to build.  Each positional argument must
  be directly convertible to Curry or describe a node.  The following direct
  conversions are recognized:

    * ``bool``:
      Converted to ``Prelude.Bool``.
    * ``float``
      Converted to ``Prelude.Float``.
    * ``int``
      Converted to ``Prelude.Int``.
    * ``iterator``
      Lazily Converted to a Curry list.
    * ``list``
      Eagerly Converted to a Curry list.
    * ``str``
      For strings of length one, ``Prelude.Char``.  Otherwise, ``[Prelude.Char]``.
    * ``tuple``
      Converted to a Curry tuple.

  Any (possibly nested) sequence whose first element is an instance of
  :class:`NodeInfo <{0}.objects.CurryNodeInfo>` specifies a node.  The remaining
  arguments are recursively converted to Curry expressions to form the
  successors list.  Thus, given suitable definitions, it is possible to build
  the Curry list ``[0,1,2]`` with the following code:

      expr([Cons, 0, [Cons, 1, [Cons, 2, Nil]]])

  Several special symbols are provided.  See :class:`anchor`, :class:`choice`,
  :class:`cons`, :data:`fail`, :class:`free`, :data:`nil`, :class:`ref`, and
  :class:`unboxed`.

  Args:
    interp:
        An interpreter object.
    *args:
        Positional arguments used to construct expressions.
    **kwds:
        Keyword arguments specifying subexpressions that may be referenced via
        ``ref``.  Each keyword specifies the name of an anchor.  See the
        examples below.
    target:
        Reserved keyword-only argument.  If a target is supplied, then it will
        be rewritten with the specified expression.  Otherwise a new node is
        created.

  Returns:
    A Curry expression.
  '''
  return raw_expr(interp, *args, **kwds)

def raw_expr(interp, *args, **kwds):
  '''Equivalent to expr.'''
  builder = ExpressionBuilder(interp)
  target = kwds.pop('target', None)
  for anchorname, subexpr in six.iteritems(kwds):
    subexpr = anchor(subexpr, name=anchorname)
    builder(subexpr)
    assert anchorname in builder.anchors
  builder.target = target
  expr = builder(*args)
  return builder.fixrefs(expr)

class ExpressionBuilder(object):
  '''Implementation of ``expr``.'''
  def __init__(self, interp):
    self.interp = interp
    self.counter = itertools.count(1)
    self.anchors = {}
    self.brokenrefs = {}
    self.target = None
    self._mknode = interp.backend.make_node
    self.prelude = self.interp.prelude
    self.fsyms = self.interp.backend.fundamental_symbols

  def fixrefs(self, expr):
    if self.brokenrefs:
      # for state in expr.walk():
      from .backends.py.graph.walkexpr import walk
      for state in walk(expr):
        if isinstance(state.cursor, backends.Node):
          anchorname = self.brokenrefs.get(state.cursor.id())
          if anchorname is not None:
            parent = state.parent
            if parent is None:
              # This is the trivial cycle a=a.
              state.cursor.forward_to(state.cursor)
            else:
              parent.set_successor(state.realpath[-1], self.anchors[anchorname])
          else:
            state.push()
    return expr

  @visitation.dispatch.on('arg')
  def __call__(self, arg, *args, **kwds):
    if hasattr(arg, 'rvalue'): # handle Variable
      return self(arg.rvalue, *args, **kwds)
    raise TypeError(
        'cannot build a Curry expression from type %r' % type(arg).__name__
      )

  @__call__.when(six.string_types + (six.binary_type,)) # Char or [Char].
  def __call__(self, arg, *trailing):
    arg = strings.ensure_str(arg)
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    if len(arg) == 1:
      return self._mknode(self.prelude.Char, str(arg), target=self.target)
    else:
      return self(list(arg))

  @__call__.when(list)
  def __call__(self, lst, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % lst)
    if len(lst) and isinstance(lst[0], (objects.CurryNodeInfo, backends.InfoTable)):
      return self(*lst)
    else:
      Cons = self.prelude.Cons
      Nil = self.prelude.Nil
      sentinel = object()
      seq = iter(lst)
      f = lambda x,g: [Cons, self(x), g()] if x is not sentinel else Nil
      g = lambda: f(next(seq, sentinel), g)
      return self(g())

  @__call__.when(tuple)
  def __call__(self, tup, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %s' % repr(tup))
    n = len(tup)
    if n == 0:
      typename = 'Prelude.()'
    elif n == 1:
      raise CurryTypeError("Curry has no 1-tuple.")
    else:
      typename = 'Prelude.(%s)' % (','*(n-1))
    return self._mknode(
        self.interp.symbol(typename), *map(self, tup), target=self.target
      )

  @__call__.when(bool)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    if arg:
      return self._mknode(self.prelude.True_, target=self.target)
    else:
      return self._mknode(self.prelude.False_, target=self.target)

  @__call__.when(numbers.Integral)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    return self._mknode(self.prelude.Int, int(arg), target=self.target)

  @__call__.when(numbers.Real)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    return self._mknode(
        self.prelude.Float, float(arg), target=self.target
      )

  @__call__.when(anchor)
  def __call__(self, arg, *trailing):
    if arg.name is None:
      while True:
        anchorname = '_%s' % next(self.counter)
        if anchorname not in self.anchors:
          break
    else:
      anchorname = arg.name
    if trailing:
      raise CurryTypeError('invalid arguments after anchor %r' % anchorname)
    if anchorname in self.anchors:
      raise ValueError('multiple definitions of anchor %r' % anchorname)
    self.anchors[anchorname] = None
    subexpr = self(arg.value)
    self.anchors[anchorname] = subexpr
    return subexpr

  @__call__.when(ref)
  def __call__(self, arg, *trailing):
    if arg.name is None:
      if len(self.anchors) != 1:
        raise ValueError(
            "invalid use of unqualified 'ref' with %s anchors defined"
                % len(self.anchors)
          )
      anchorname = next(iter(self.anchors))
    else:
      anchorname = arg.name
    if trailing:
      raise CurryTypeError('invalid arguments after ref %r' % anchorname)
    target = self.anchors.get(anchorname)
    if target is None:
      placeholder = self(fail)
      self.brokenrefs[placeholder.id()] = anchorname
      return placeholder
    else:
      return target

  @__call__.when(collections.Iterator)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    pygen = self.prelude._PyGenerator
    return self._mknode(pygen, arg, target=self.target)

  @__call__.when((objects.CurryNodeInfo, backends.InfoTable))
  def __call__(self, ti, *args):
    missing =  getattr(ti, 'info', ti).arity - len(args)
    partial_info = self.fsyms.PartApplic if missing > 0 else None
    return self._mknode(
        ti, *map(lambda s: self(s), args), target=self.target
      , partial_info=partial_info
      )

  @__call__.when(backends.Node)
  def __call__(self, node, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r node' % node.info.name)
    if self.target is not None:
      return self._mknode(self.fsyms.Fwd, node, target=self.target)
    return node

  @__call__.when(unboxed)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after unboxed %r' % arg.value)
    if self.target is not None:
      raise ValueError("cannot rewrite a node to an unboxed value")
    return arg.value

  @__call__.when(cons)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'cons')
    return self._mknode(
        self.prelude.Cons, self(arg.head), self(arg.tail)
      , target=self.target
      )

  @__call__.when(type(nil))
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'nil')
    return self._mknode(self.prelude.Nil, target=self.target)

  @__call__.when(_setgrd)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % '_setgrd')
    return self._mknode(
        self.fsyms.SetGuard
      , arg.sid, self(arg.value), target=self.target
      )

  @__call__.when(type(fail))
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'fail')
    return self._mknode(self.fsyms.Failure, target=self.target)

  @__call__.when(_strictconstr)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % '_strictconstr')
    return self._mknode(
        self.fsyms.StrictConstraint
      , self(arg.value), self(arg.pair), target=self.target
      )

  @__call__.when(_nonstrictconstr)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % '_nonstrictconstr')
    return self._mknode(
        self.fsyms.NonStrictConstraint
      , self(arg.value), self(arg.pair), target=self.target
      )

  @__call__.when(_valuebinding)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % '_valuebinding')
    return self._mknode(
        self.fsyms.ValueBinding
      , self(arg.value), self(arg.pair), target=self.target
      )

  @__call__.when(free)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'free')
    return self._mknode(
        self.fsyms.Free
      , arg.vid
      , self._mknode(self.prelude.Unit)
      , target=self.target
      )

  @__call__.when(fwd)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'fwd')
    return self._mknode(
        self.fsyms.Fwd, self(arg.value), target=self.target
      )

  @__call__.when(choice)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'choice')
    return self._mknode(
        self.fsyms.Choice, arg.cid, self(arg.lhs), self(arg.rhs)
      , target=self.target
      )

