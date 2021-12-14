from . import context, icurry, objects, utility
from .exceptions import CurryTypeError
from .utility import strings, visitation
import collections, itertools, numbers, six

__all__ = [
    'anchor', 'choice', 'cons', 'expr', 'fail', 'fwd', 'free', 'nil'
  , 'raw_expr', 'ref', 'unboxed'
  ]

class anchor(object):
  '''
  Creates an anchor in an expression.  This can be used to build nonlinear
  expressions.

  When no argument is supplied, the anchor name is automatically generated from
  the sequence _1, _2, ..., according to its position in a left-to-right,
  depth-first traversal.
  '''
  def __init__(self, value, name=None):
    self.value = value
    self.name = name

class ref(object):
  '''
  Creates a reference to another node in a call to ``expr``.  This can be used
  to build nonlinear expressions.

  The argument is optional when the expression contains exactly one anchor at
  the point where the reference appears.
  '''
  def __init__(self, name=None):
    self.name = name

class cons(object):
  '''
  Places one or more list constructors into a Curry expression.
  '''
  def __init__(self, head, tail0, *tail):
    self.head = head
    if tail:
      self.tail = cons(tail0, *tail)
    else:
      self.tail = tail0

class _nil(object):
  '''Places a list terminator into a Curry expression.'''
  pass
nil = _nil()
del _nil

class unboxed(object):
  '''Unboxes its argument into a Curry expression.'''
  def __init__(self, value):
    if not isinstance(value, icurry.IUnboxedLiteral):
      raise CurryTypeError('expected an unboxed literal, got %r' % value)
    self.value = value

class _setgrd(object):
  '''Places a set guard into a Curry expression.'''
  def __init__(self, sid, value=None):
    if value is None:
      sid, value = 0, sid # shift right
    self.sid = int(sid)
    self.value = value

class _failcls(object):
  '''Places a failure into a Curry expression.'''
  pass
fail = _failcls()
del _failcls

class _strictconstr(object):
  '''Places a strict constraint into a Curry expression.'''
  def __init__(self, value, pair):
    self.value = value
    self.pair = pair

class _nonstrictconstr(object):
  '''Places a nonstrict constraint into a Curry expression.'''
  def __init__(self, value, pair):
    self.value = value
    self.pair = pair

class _valuebinding(object):
  '''Places a value binding into a Curry expression.'''
  def __init__(self, value, pair):
    self.value = value
    self.pair = pair

class free(object):
  '''Places a free variable into a Curry expression.'''
  def __init__(self, vid=0):
    self.vid = int(vid)

class fwd(object):
  '''Places a forwarding node into a Curry expression.'''
  def __init__(self, value):
    self.value = value

class choice(object):
  '''Places a choice into a Curry expression.'''
  def __init__(self, cid, lhs, rhs=None):
    if rhs is None:
      cid, lhs, rhs = 0, cid, lhs # shift right
    self.cid = int(cid)
    self.lhs = lhs
    self.rhs = rhs

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
  ``{0}.runtime.CurryNodeInfo`` specifies a node.  The remaining arguments are
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
  An instance of ``object.CurryExpression``.
  '''
  raw = raw_expr(interp, *args, **kwds)
  # return objects.CurryExpression(raw)
  return raw

def raw_expr(interp, *args, **kwds):
  '''
  Like ``expr`` except the result is not wrapped.  It will either be an unboxed
  expression or a backend-dependent instance of ``context.Node``.
  '''
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

  def fixrefs(self, expr):
    if self.brokenrefs:
      for state in expr.walk():
        if isinstance(state.cursor, self.Node):
          anchorname = self.brokenrefs.get(id(state.cursor))
          if anchorname is not None:
            parent = state.parent
            if parent is None:
              # This is the trivial cycle a=a.
              state.cursor.rewrite(self.prelude._Fwd, state.cursor)
            else:
              parent.successors[state.realpath[-1]] = self.anchors[anchorname]
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
      return self.Node(self.prelude.Char, str(arg), target=self.target)
    else:
      return self(list(arg))

  @__call__.when(list)
  def __call__(self, lst, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % lst)
    if len(lst) and isinstance(lst[0], objects.CurryNodeInfo):
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
    return self.Node(
        self.interp.symbol(typename), *map(self, tup), target=self.target
      )

  @__call__.when(bool)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    if arg:
      return self.Node(self.prelude.True_, target=self.target)
    else:
      return self.Node(self.prelude.False_, target=self.target)

  @__call__.when(numbers.Integral)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    return self.Node(self.prelude.Int, int(arg), target=self.target)

  @__call__.when(numbers.Real)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    return self.Node(
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
      self.brokenrefs[id(placeholder)] = anchorname
      return placeholder
    else:
      return target

  @__call__.when(collections.Iterator)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    pygen = self.prelude._PyGenerator
    return self.Node(pygen, arg, target=self.target)

  @__call__.when(objects.CurryNodeInfo)
  def __call__(self, ti, *args):
    missing =  ti.info.arity - len(args)
    if missing > 0:
      partial = self.Node(ti, *map(lambda s: self(s), args), partial=True)
      return self.Node(
          self.prelude._PartApplic, missing, partial
        , target=self.target
        )
    else:
      return self.Node(
          ti, *map(lambda s: self(s), args), target=self.target
        )

  @__call__.when(context.Node)
  def __call__(self, node, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r node' % node.info.name)
    if self.target is not None:
      return self.Node(self.prelude._Fwd, node, target=self.target)
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
    return self.Node(
        self.prelude.Cons, self(arg.head), self(arg.tail)
      , target=self.target
      )

  @__call__.when(type(nil))
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'nil')
    return self.Node(self.prelude.Nil, target=self.target)

  @__call__.when(_setgrd)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % '_setgrd')
    return self.Node(
        self.interp.setfunctions._SetGuard
      , arg.sid, self(arg.value), target=self.target
      )

  @__call__.when(type(fail))
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'fail')
    return self.Node(self.prelude._Failure, target=self.target)

  @__call__.when(_strictconstr)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % '_strictconstr')
    return self.Node(
        self.prelude._StrictConstraint
      , self(arg.value), self(arg.pair), target=self.target
      )

  @__call__.when(_nonstrictconstr)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % '_nonstrictconstr')
    return self.Node(
        self.prelude._NonStrictConstraint
      , self(arg.value), self(arg.pair), target=self.target
      )

  @__call__.when(_valuebinding)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % '_valuebinding')
    return self.Node(
        self.prelude._ValueBinding
      , self(arg.value), self(arg.pair), target=self.target
      )

  @__call__.when(free)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'free')
    return self.Node(
        self.prelude._Free
      , arg.vid
      , self.Node(self.prelude.Unit)
      , target=self.target
      )

  @__call__.when(fwd)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'fwd')
    return self.Node(
        self.prelude._Fwd, self(arg.value), target=self.target
      )

  @__call__.when(choice)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'choice')
    return self.Node(
        self.prelude._Choice, arg.cid, self(arg.lhs), self(arg.rhs)
      , target=self.target
      )

